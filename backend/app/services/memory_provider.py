"""Optional memory-provider boundary for controlled NovelForge experiments.

NovelForge's Mongo collections remain the authority.  Providers behind this
module are retrieval/observation helpers only.  In particular, a Tencent
response is never written to canon, decisions, structured story records,
Story Bible, Narrative Intelligence, prose, or manuscript state.
"""
from __future__ import annotations

import hashlib
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Iterable, List

import httpx
from bson import ObjectId

from app.services.memory_retrieval_service import retrieve_relevant_context
from app.services.settings_service import settings_service

logger = logging.getLogger(__name__)

MEMORY_MODES = {"native", "tencent", "hybrid", "benchmark"}


@dataclass
class MemoryHit:
    content: str
    score: float = 0.0
    source_type: str = "memory"
    source_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "score": round(float(self.score or 0), 6),
            "source_type": self.source_type,
            "source_id": self.source_id,
            "metadata": self.metadata,
        }


@dataclass
class MemoryRecall:
    provider: str
    hits: List[MemoryHit] = field(default_factory=list)
    latency_ms: int = 0
    token_estimate: int = 0
    strategy: str = ""
    degraded: bool = False
    error: str | None = None
    diagnostics: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "hits": [hit.as_dict() for hit in self.hits],
            "latency_ms": self.latency_ms,
            "token_estimate": self.token_estimate,
            "strategy": self.strategy,
            "degraded": self.degraded,
            "error": self.error,
            "diagnostics": self.diagnostics,
        }


def _estimate_tokens(value: Any) -> int:
    # This is intentionally the same bounded approximation used by the native
    # context path; it is a measurement, not a prompt-generation dependency.
    return max(0, len(str(value or "")) // 4)


def _short_error(exc: Exception) -> str:
    return f"{type(exc).__name__}: {str(exc)[:300]}"


class MemoryProvider:
    name = "memory"

    async def capture(
        self,
        *,
        project_id: str,
        user_content: str,
        assistant_content: str,
        session_key: str,
        source_type: str,
        source_id: str,
    ) -> Dict[str, Any]:
        raise NotImplementedError

    async def recall(
        self,
        *,
        project_id: str,
        query: str,
        top_k: int,
        refresh_index: bool = False,
        retrieval_context: Dict[str, Any] | None = None,
    ) -> MemoryRecall:
        raise NotImplementedError

    async def health(self) -> Dict[str, Any]:
        return {"provider": self.name, "available": True}


class NativeNovelForgeMemoryProvider(MemoryProvider):
    """Adapter over the existing Mongo-backed retrieval implementation."""

    name = "native"

    def __init__(self, db):
        self.db = db

    async def capture(
        self,
        *,
        project_id: str,
        user_content: str,
        assistant_content: str,
        session_key: str,
        source_type: str,
        source_id: str,
    ) -> Dict[str, Any]:
        # Native memory is already populated by the owning NovelForge services
        # (chapter intelligence, planning, canon, decisions, and assistant
        # history).  This acknowledgement lets dual-run telemetry prove that
        # the same event was observed without indexing raw prose a second time.
        return {
            "provider": self.name,
            "accepted": True,
            "authoritative": False,
            "source_type": source_type,
            "source_id": source_id,
            "native_path": "existing Mongo retrieval services",
        }

    async def recall(
        self,
        *,
        project_id: str,
        query: str,
        top_k: int,
        refresh_index: bool = False,
        retrieval_context: Dict[str, Any] | None = None,
    ) -> MemoryRecall:
        started = time.perf_counter()
        retrieval_context = dict(retrieval_context or {})
        from app.services.memory_incremental_index_service import memory_incremental_index_service
        readiness = await memory_incremental_index_service.prepare_for_retrieval(
            self.db,
            project_id,
            strict_writing=bool(retrieval_context.get("safe_for_writing")),
        )
        diagnostics: Dict[str, Any] = {
            "index": readiness,
            "full_source_scans_query": 0,
            "owner_records_inspected_query": 0,
            "index_writes_query": 0,
            "legacy_refresh_requested": bool(refresh_index),
        }
        source_documents = None
        if readiness.get("fallback_required"):
            source_documents, fallback_stats = await memory_incremental_index_service.direct_authority_documents(
                self.db, project_id
            )
            diagnostics.update(fallback_stats)
        rows = await retrieve_relevant_context(
            self.db,
            project_id,
            query,
            top_k=max(1, min(int(top_k or 8), 50)),
            refresh_index=False,
            safe_for_writing=bool(retrieval_context.get("safe_for_writing")),
            consumer=str(retrieval_context.get("consumer") or "conversation"),
            as_of_chapter=retrieval_context.get("as_of_chapter"),
            as_of_scene=retrieval_context.get("as_of_scene"),
            pov_character=retrieval_context.get("pov_character"),
            branch_id=retrieval_context.get("branch_id"),
            index_revision=(
                int(readiness.get("processed_version") or 0)
                if readiness.get("status") == "READY" and source_documents is None
                else None
            ),
            source_documents=source_documents,
            resolve_legacy_aliases=readiness.get("status") != "READY",
            diagnostics=diagnostics,
        )
        hits = [
            MemoryHit(
                content=str(row.get("content") or ""),
                score=float(row.get("score") or 0),
                source_type=str(row.get("source_type") or "memory"),
                source_id=str(row.get("source_id") or ""),
                metadata={
                    **dict(row.get("metadata") or {}),
                    "logical_identity": row.get("logical_identity"),
                    "source_version": row.get("source_version"),
                    "authority_level": row.get("authority_level"),
                    "validity": row.get("validity"),
                    "estimated_tokens": row.get("estimated_tokens"),
                    "why_selected": row.get("why_selected"),
                    "rank": row.get("rank"),
                },
            )
            for row in rows
        ]
        return MemoryRecall(
            provider=self.name,
            hits=hits,
            latency_ms=round((time.perf_counter() - started) * 1000),
            token_estimate=_estimate_tokens("\n".join(hit.content for hit in hits)),
            strategy=(
                "native-direct-authority-fallback"
                if readiness.get("fallback_required")
                else str(diagnostics.get("ranking_strategy") or "native-checkpointed-mongo-hash-embedding")
            ),
            degraded=bool(readiness.get("fallback_required")),
            diagnostics=diagnostics,
        )


class TencentAgentMemoryProvider(MemoryProvider):
    """HTTP adapter for Tencent's standalone MemoryCore gateway.

    It targets the documented compatibility endpoints (``/capture`` and
    ``/recall``), so the provider remains compatible with both the local
    open-source gateway and a future v3 service adapter.  No Tencent-specific
    objects are imported into NovelForge's authority services.
    """

    name = "tencent"

    def __init__(self, config: Dict[str, Any] | None = None):
        config = config or {}
        self.endpoint = str(config.get("endpoint") or "").rstrip("/")
        self.api_key = str(config.get("api_key") or "")
        self.service_id = str(config.get("service_id") or "default")
        self.timeout_ms = max(250, min(int(config.get("timeout_ms") or 3000), 30000))

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json", "x-tdai-service-id": self.service_id}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _session_key(self, project_id: str) -> str:
        return f"novelforge-project-{project_id}"

    async def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.endpoint:
            raise RuntimeError("Tencent memory endpoint is not configured")
        timeout = httpx.Timeout(self.timeout_ms / 1000)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{self.endpoint}{path}",
                headers=self._headers(),
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, dict) else {}

    async def capture(
        self,
        *,
        project_id: str,
        user_content: str,
        assistant_content: str,
        session_key: str,
        source_type: str,
        source_id: str,
    ) -> Dict[str, Any]:
        # Avoid sending Mongo identifiers as narrative content.  Provenance is
        # retained by NovelForge's derived telemetry record instead.
        payload = {
            "user_content": str(user_content or "")[:12000],
            "assistant_content": str(assistant_content or "")[:12000],
            "session_key": session_key or self._session_key(project_id),
            "session_id": str(source_id or "novelforge"),
        }
        result = await self._post("/capture", payload)
        return {"provider": self.name, "accepted": True, "response": result}

    async def recall(
        self,
        *,
        project_id: str,
        query: str,
        top_k: int,
        refresh_index: bool = False,
        retrieval_context: Dict[str, Any] | None = None,
    ) -> MemoryRecall:
        started = time.perf_counter()
        result = await self._post(
            "/recall",
            {"query": str(query or "")[:4000], "session_key": self._session_key(project_id)},
        )
        code = int(result.get("code") or 0)
        if code:
            raise RuntimeError(str(result.get("message") or f"Tencent recall failed ({code})"))
        context = str(result.get("context") or "").strip()
        strategy = str(result.get("strategy") or "tencent-gateway-recall")
        fallback_search = False
        # Standalone Tencent can record L0 immediately while L1 extraction is
        # still waiting for an LLM. In that valid state /recall may be empty
        # even though FTS5 conversation search is ready. Use the documented
        # L0 endpoint before declaring the provider empty.
        if not context:
            try:
                conversation = await self._post(
                    "/search/conversations",
                    {
                        "query": str(query or "")[:4000],
                        "limit": max(1, min(int(top_k or 8), 50)),
                        "session_key": self._session_key(project_id),
                    },
                )
                if int(conversation.get("total") or 0) > 0:
                    candidate = str(conversation.get("results") or "").strip()
                    if candidate and not candidate.lower().startswith(("embedding service is", "conversation search requires")):
                        context = candidate
                        strategy = "tencent-gateway-conversation-search"
                        fallback_search = True
            except Exception as exc:
                logger.debug("Tencent conversation fallback unavailable: %s", _short_error(exc))
        hits = []
        if context and fallback_search:
            # The v1 conversation endpoint returns a human-readable list of
            # individually scored messages. Keep those boundaries instead of
            # treating the whole response as one giant context hit.
            # The standalone gateway currently emits a blank line before the
            # separator (``\n\n---\n``), while older builds emitted a single
            # newline.  Accept both forms so each scored message remains an
            # independently attributable hit and token estimates stay honest.
            entries = [
                part.strip()
                for part in re.split(r"\n\s*---\s*\n", context)
                if "**[" in part
            ]
            if not entries and context:
                # Keep compatibility with gateways/proxies that return a
                # plain text result rather than the formatted v1 list.
                entries = [context]
            for entry in entries[: max(1, min(int(top_k or 8), 50))]:
                score_match = re.search(r"\(score:\s*([0-9.]+)\)", entry)
                hits.append(
                    MemoryHit(
                        content=entry[:12000],
                        score=float(score_match.group(1)) if score_match else 0.0,
                        source_type="tencent_agent_conversation",
                        source_id=self._session_key(project_id),
                        metadata={
                            "memory_count": result.get("memory_count"),
                            "strategy": strategy,
                            "fallback_search": True,
                            "provenance": "Tencent derived conversation search; verify against NovelForge authority",
                        },
                    )
                )
        elif context:
            hits.append(
                MemoryHit(
                    content=context[:12000],
                    score=1.0,
                    source_type="tencent_agent_memory",
                    source_id=self._session_key(project_id),
                    metadata={
                        "memory_count": result.get("memory_count"),
                        "strategy": strategy,
                        "provenance": "Tencent derived recall; verify against NovelForge authority",
                    },
                )
            )
        return MemoryRecall(
            provider=self.name,
            hits=hits[: max(1, min(int(top_k or 8), 50))],
            latency_ms=round((time.perf_counter() - started) * 1000),
            token_estimate=_estimate_tokens("\n".join(hit.content for hit in hits)),
            strategy=strategy,
        )

    async def health(self) -> Dict[str, Any]:
        if not self.endpoint:
            return {"provider": self.name, "available": False, "error": "endpoint_not_configured"}
        started = time.perf_counter()
        try:
            timeout = httpx.Timeout(self.timeout_ms / 1000)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(f"{self.endpoint}/health", headers=self._headers())
                response.raise_for_status()
                body = response.json()
            return {
                "provider": self.name,
                "available": True,
                "latency_ms": round((time.perf_counter() - started) * 1000),
                "gateway": body,
            }
        except Exception as exc:
            return {
                "provider": self.name,
                "available": False,
                "latency_ms": round((time.perf_counter() - started) * 1000),
                "error": _short_error(exc),
            }


class MemoryProviderService:
    """Selects and compares providers while keeping native memory in charge."""

    @staticmethod
    def _merge_recalls(native: MemoryRecall, tencent: MemoryRecall) -> MemoryRecall:
        """Build an observational hybrid without changing authority ordering."""
        merged: List[MemoryHit] = []
        seen: Dict[str, MemoryHit] = {}
        for provider_recall in (native, tencent):
            for hit in provider_recall.hits:
                key = hashlib.sha256(hit.content.strip().encode("utf-8")).hexdigest()
                if key in seen:
                    existing = seen[key]
                    existing.metadata = {
                        **existing.metadata,
                        "providers": sorted(set((existing.metadata.get("providers") or ["native"]) + [provider_recall.provider])),
                    }
                    existing.score = max(existing.score, hit.score)
                    continue
                clone = MemoryHit(
                    content=hit.content,
                    score=hit.score,
                    source_type=hit.source_type,
                    source_id=hit.source_id,
                    metadata={**hit.metadata, "providers": [provider_recall.provider]},
                )
                seen[key] = clone
                merged.append(clone)
        merged.sort(key=lambda item: item.score, reverse=True)
        return MemoryRecall(
            provider="hybrid",
            hits=merged,
            latency_ms=max(native.latency_ms, tencent.latency_ms),
            token_estimate=_estimate_tokens("\n".join(hit.content for hit in merged)),
            strategy="native-plus-tencent-deduplicated",
            degraded=native.degraded and tencent.degraded,
            error=native.error or tencent.error,
        )

    async def config(self, db, *, runtime: bool = True) -> Dict[str, Any]:
        return await settings_service.get_memory_settings(runtime=runtime)

    async def providers(self, db, mode: str | None = None) -> Dict[str, MemoryProvider]:
        config = await self.config(db, runtime=True)
        selected = str(mode or config.get("mode") or "native").lower()
        native = NativeNovelForgeMemoryProvider(db)
        if selected == "native":
            return {"native": native}
        tencent = TencentAgentMemoryProvider(config)
        if selected == "tencent":
            return {"tencent": tencent, "native": native}
        if selected in {"hybrid", "benchmark"}:
            return {"native": native, "tencent": tencent}
        raise ValueError(f"Unsupported memory mode: {selected}")

    async def _event(
        self,
        db,
        *,
        project_id: str,
        provider: str,
        operation: str,
        status: str,
        source_type: str = "",
        source_id: str = "",
        content: str = "",
        latency_ms: int = 0,
        token_estimate: int = 0,
        error: str | None = None,
        metadata: Dict[str, Any] | None = None,
    ) -> None:
        if not ObjectId.is_valid(project_id):
            return
        await db.memory_provider_events.insert_one({
            "project_id": ObjectId(project_id),
            "provider": provider,
            "operation": operation,
            "status": status,
            "source_type": source_type,
            "source_id": str(source_id or ""),
            "content_hash": hashlib.sha256(str(content or "").encode("utf-8")).hexdigest() if content else "",
            "content_excerpt": str(content or "")[:600],
            "latency_ms": int(latency_ms or 0),
            "token_estimate": int(token_estimate or 0),
            "error": error,
            "metadata": metadata or {},
            "authoritative": False,
            "created_at": datetime.utcnow(),
        })

    async def capture(
        self,
        db,
        project_id: str,
        *,
        user_content: str,
        assistant_content: str,
        source_type: str,
        source_id: str,
        mode: str | None = None,
    ) -> Dict[str, Any]:
        """Best-effort observation.  Never raises into an author save path."""
        try:
            selected = str(mode or (await self.config(db, runtime=True)).get("mode") or "native")
            providers = await self.providers(db, selected)
        except Exception as exc:
            logger.warning("Memory provider setup failed: %s", _short_error(exc))
            return {"mode": "native", "providers": {}, "degraded": True, "error": _short_error(exc)}

        result: Dict[str, Any] = {"mode": selected, "providers": {}, "degraded": False}
        for name, provider in providers.items():
            started = time.perf_counter()
            try:
                accepted = await provider.capture(
                    project_id=project_id,
                    user_content=user_content,
                    assistant_content=assistant_content,
                    session_key=f"novelforge-project-{project_id}",
                    source_type=source_type,
                    source_id=source_id,
                )
                elapsed = round((time.perf_counter() - started) * 1000)
                result["providers"][name] = {**accepted, "latency_ms": elapsed}
                await self._event(
                    db, project_id=project_id, provider=name, operation="capture", status="accepted",
                    source_type=source_type, source_id=source_id,
                    content=assistant_content, latency_ms=elapsed,
                    token_estimate=_estimate_tokens(assistant_content),
                )
            except Exception as exc:
                error = _short_error(exc)
                result["degraded"] = True
                result["providers"][name] = {"accepted": False, "error": error}
                await self._event(
                    db, project_id=project_id, provider=name, operation="capture", status="failed",
                    source_type=source_type, source_id=source_id,
                    content=assistant_content, latency_ms=round((time.perf_counter() - started) * 1000),
                    token_estimate=_estimate_tokens(assistant_content), error=error,
                )
        return result

    async def recall(
        self,
        db,
        project_id: str,
        query: str,
        *,
        top_k: int = 8,
        mode: str | None = None,
        refresh_index: bool = False,
        safe_for_writing: bool = False,
        consumer: str = "conversation",
        as_of_chapter: int | None = None,
        as_of_scene: int | None = None,
        pov_character: str | None = None,
        branch_id: str | None = None,
    ) -> Dict[str, Any]:
        selected = str(mode or (await self.config(db, runtime=True)).get("mode") or "native")
        providers = await self.providers(db, selected)
        # Native remains the safe primary packet in benchmark mode.  Tencent
        # is observed side-by-side and only becomes primary in explicit
        # experimental mode, with native fallback on every failure.
        ordered = list(providers.items())
        if selected == "tencent":
            ordered = [("tencent", providers["tencent"]), ("native", providers["native"])]
        recalls: Dict[str, MemoryRecall] = {}
        errors: Dict[str, str] = {}
        for name, provider in ordered:
            try:
                recalls[name] = await provider.recall(
                    project_id=project_id, query=query, top_k=top_k,
                    refresh_index=refresh_index,
                    retrieval_context={
                        "safe_for_writing": safe_for_writing,
                        "consumer": consumer,
                        "as_of_chapter": as_of_chapter,
                        "as_of_scene": as_of_scene,
                        "pov_character": pov_character,
                        "branch_id": branch_id,
                    },
                )
            except Exception as exc:
                errors[name] = _short_error(exc)
                recalls[name] = MemoryRecall(provider=name, degraded=True, error=errors[name])
                await self._event(
                    db, project_id=project_id, provider=name, operation="recall", status="failed",
                    content=query, error=errors[name], metadata={"fallback": name == "tencent"},
                )
        configured_primary = "native" if selected in {"native", "benchmark", "hybrid"} else "tencent"
        if selected in {"benchmark", "hybrid"} and "native" in recalls and "tencent" in recalls:
            recalls["hybrid"] = self._merge_recalls(recalls["native"], recalls["tencent"])
        # Tencent is a derived observation layer.  Context packets used by
        # writing/orchestration must keep Native authority first even when an
        # advanced user is testing Tencent retrieval.  The comparison still
        # exposes both providers for measurement.
        primary_name = "native" if safe_for_writing else ("hybrid" if selected == "hybrid" else configured_primary)
        primary = recalls.get(primary_name) or MemoryRecall(provider="native", degraded=True)
        if not primary.hits and primary_name != "native":
            primary = recalls.get("native") or primary
            primary.degraded = True
        for name, recall in recalls.items():
            if name not in errors:
                await self._event(
                    db, project_id=project_id, provider=name, operation="recall", status="completed",
                    content=query, latency_ms=recall.latency_ms, token_estimate=recall.token_estimate,
                    metadata={"hit_count": len(recall.hits), "strategy": recall.strategy, "diagnostics": recall.diagnostics},
                )
        comparison = {
            "mode": selected,
            "configured_primary": configured_primary,
            "primary": primary_name if not (primary.degraded and primary.provider == "native") else "native",
            "query": query,
            "providers": {name: recall.as_dict() for name, recall in recalls.items()},
            "errors": errors,
            "fallback_used": primary.provider != configured_primary and not (selected == "hybrid" and primary.provider == "hybrid"),
            "authoritative": False,
        }
        if selected == "benchmark":
            await db.memory_provider_comparisons.insert_one({
                "project_id": ObjectId(project_id),
                **comparison,
                "created_at": datetime.utcnow(),
            })
        return {"primary": primary.as_dict(), "comparison": comparison}

    async def smoke_test(self, db, project_id: str, *, minimum_expected: int = 8) -> Dict[str, Any]:
        """Run a bounded, provider-only retrieval gate before paid benchmarks."""
        config = await self.config(db, runtime=True)
        provider = TencentAgentMemoryProvider(config)
        health = await provider.health()
        if not health.get("available"):
            return {"passed": False, "minimum_expected": minimum_expected, "health": health, "error": "Tencent gateway unavailable"}

        # Keep the smoke corpus on the same scoped session key used by the
        # normal NovelForge adapter so recall also verifies project scoping.
        session_key = provider._session_key(project_id)
        cases = [
            {"id": f"smoke-{index}", "token": f"NovelForgeSmokeToken-{index}", "fact": f"the glass orchard marker {index}"}
            for index in range(1, 11)
        ]
        captures = []
        for case in cases:
            started = time.perf_counter()
            try:
                response = await provider.capture(
                    project_id=project_id,
                    user_content=f"Synthetic memory {case['id']}: remember {case['token']} and {case['fact']}.",
                    assistant_content=f"Stored {case['token']} for the Tencent retrieval smoke gate.",
                    session_key=session_key,
                    source_type="tencent_smoke_test",
                    source_id=case["id"],
                )
                captures.append({"id": case["id"], "accepted": True, "latency_ms": round((time.perf_counter() - started) * 1000), "response": response})
            except Exception as exc:
                captures.append({"id": case["id"], "accepted": False, "error": _short_error(exc)})

        recalls = []
        for case in cases:
            try:
                recall = await provider.recall(project_id=project_id, query=case["token"], top_k=5, refresh_index=False)
                matched = any(case["token"].lower() in hit.content.lower() for hit in recall.hits)
                recalls.append({"id": case["id"], "matched": matched, "hit_count": len(recall.hits), "latency_ms": recall.latency_ms, "strategy": recall.strategy, "provenance": [hit.metadata.get("provenance") for hit in recall.hits]})
            except Exception as exc:
                recalls.append({"id": case["id"], "matched": False, "error": _short_error(exc)})
        matched = sum(1 for item in recalls if item.get("matched"))
        capture_ok = sum(1 for item in captures if item.get("accepted"))
        avg_latency = round(sum(int(item.get("latency_ms") or 0) for item in recalls) / max(1, len(recalls)), 1)
        passed = capture_ok == len(cases) and matched >= int(minimum_expected)
        return {
            "passed": passed,
            "minimum_expected": minimum_expected,
            "expected": len(cases),
            "captures_accepted": capture_ok,
            "matched": matched,
            "average_recall_latency_ms": avg_latency,
            "health": health,
            "captures": captures,
            "recalls": recalls,
            "provenance_present": all(bool(item.get("provenance")) for item in recalls if item.get("matched")),
            "authoritative": False,
        }

    async def status(self, db) -> Dict[str, Any]:
        config = await self.config(db, runtime=False)
        mode = str(config.get("mode") or "native")
        native = {"provider": "native", "available": True, "authoritative": False}
        tencent = await TencentAgentMemoryProvider(await self.config(db, runtime=True)).health()
        return {
            "mode": mode,
            "default_mode": "native",
            "native": native,
            "tencent": {**tencent, "experimental": True, "authoritative": False},
            "authority_note": "MongoDB story systems remain authoritative. Provider memory is derived retrieval only.",
        }

    async def compare(self, db, project_id: str, query: str, top_k: int = 8) -> Dict[str, Any]:
        return await self.recall(db, project_id, query, top_k=top_k, mode="benchmark", refresh_index=False)


memory_provider_service = MemoryProviderService()
