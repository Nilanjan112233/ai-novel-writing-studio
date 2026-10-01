import asyncio
from bson import ObjectId

from app.services.memory_provider import (
    MemoryProvider,
    MemoryProviderService,
    MemoryRecall,
    MemoryHit,
    TencentAgentMemoryProvider,
)


class _Collection:
    def __init__(self):
        self.rows = []

    async def insert_one(self, value):
        self.rows.append(value)


class _Db:
    def __init__(self):
        self.memory_provider_events = _Collection()
        self.memory_provider_comparisons = _Collection()


class _FixedProvider(MemoryProvider):
    def __init__(self, name, *, failure=None):
        self.name = name
        self.failure = failure

    async def capture(self, **kwargs):
        return {"provider": self.name, "accepted": True, "authoritative": False}

    async def recall(self, **kwargs):
        if self.failure:
            raise RuntimeError(self.failure)
        return MemoryRecall(
            provider=self.name,
            hits=[MemoryHit(content=f"{self.name} recalled evidence", source_type=self.name)],
            latency_ms=2,
            token_estimate=6,
            strategy=f"{self.name}-test",
        )


def test_benchmark_keeps_native_primary_and_records_comparison(monkeypatch):
    async def run():
        db = _Db()
        service = MemoryProviderService()
        native = _FixedProvider("native")
        tencent = _FixedProvider("tencent")
        async def providers(db, mode=None):
            return {"native": native, "tencent": tencent}
        async def config(db, runtime=True):
            return {"mode": "benchmark"}
        monkeypatch.setattr(service, "config", config)
        monkeypatch.setattr(service, "providers", providers)
        result = await service.recall(db, str(ObjectId()), "Mara injury", mode="benchmark")
        assert result["primary"]["provider"] == "native"
        assert set(result["comparison"]["providers"]) == {"native", "tencent", "hybrid"}
        assert result["comparison"]["authoritative"] is False
        assert len(db.memory_provider_comparisons.rows) == 1
        assert all(row["authoritative"] is False for row in db.memory_provider_events.rows)

    asyncio.run(run())


def test_hybrid_is_observational_and_safe_for_writing(monkeypatch):
    async def run():
        db = _Db()
        service = MemoryProviderService()
        native = _FixedProvider("native")
        tencent = _FixedProvider("tencent")
        async def config(db, runtime=True):
            return {"mode": "hybrid"}
        async def providers(db, mode=None):
            return {"native": native, "tencent": tencent}
        monkeypatch.setattr(service, "config", config)
        monkeypatch.setattr(service, "providers", providers)
        result = await service.recall(db, str(ObjectId()), "old promise", mode="hybrid")
        assert result["primary"]["provider"] == "hybrid"
        assert result["comparison"]["providers"]["hybrid"]["provider"] == "hybrid"
        safe = await service.recall(db, str(ObjectId()), "old promise", mode="hybrid", safe_for_writing=True)
        assert safe["primary"]["provider"] == "native"
        assert safe["comparison"]["authoritative"] is False

    asyncio.run(run())


def test_tencent_failure_falls_back_to_native_without_authority_change(monkeypatch):
    async def run():
        db = _Db()
        service = MemoryProviderService()
        native = _FixedProvider("native")
        tencent = _FixedProvider("tencent", failure="gateway unavailable")
        async def providers(db, mode=None):
            return {"tencent": tencent, "native": native}
        async def config(db, runtime=True):
            return {"mode": "tencent"}
        monkeypatch.setattr(service, "config", config)
        monkeypatch.setattr(service, "providers", providers)
        result = await service.recall(db, str(ObjectId()), "Northglass", mode="tencent")
        assert result["primary"]["provider"] == "native"
        assert result["comparison"]["fallback_used"] is True
        assert result["comparison"]["errors"]["tencent"]
        assert db.memory_provider_events.rows[0]["provider"] == "tencent"
        assert db.memory_provider_events.rows[0]["status"] == "failed"
        assert all(row["authoritative"] is False for row in db.memory_provider_events.rows)

    asyncio.run(run())


def test_tencent_recall_uses_documented_conversation_search_when_l1_is_empty():
    async def run():
        provider = TencentAgentMemoryProvider({"endpoint": "http://tencent.test"})
        calls = []
        async def fake_post(path, payload):
            calls.append(path)
            if path == "/recall":
                return {"code": 0, "context": "", "memory_count": 0}
            return {"total": 1, "results": "Stored NovelForgeSmokeToken-7 with provenance."}
        provider._post = fake_post
        recall = await provider.recall(project_id=str(ObjectId()), query="NovelForgeSmokeToken-7", top_k=5)
        assert recall.hits
        assert recall.strategy == "tencent-gateway-conversation-search"
        assert recall.hits[0].source_type == "tencent_agent_conversation"
        assert recall.hits[0].metadata["provenance"]
        assert calls == ["/recall", "/search/conversations"]

    asyncio.run(run())


def test_tencent_conversation_search_preserves_scored_message_boundaries():
    async def run():
        provider = TencentAgentMemoryProvider({"endpoint": "http://tencent.test"})

        async def fake_post(path, payload):
            if path == "/recall":
                return {"code": 0, "context": "", "memory_count": 0}
            return {
                "total": 2,
                "results": (
                    "Found 2 matching message(s):\n\n---\n"
                    "**[user]** Session: test (score: 0.91)\n\nMara's hand hurts.\n\n"
                    "---\n**[assistant]** Session: test (score: 0.74)\n\nThe promise remains."
                ),
            }

        provider._post = fake_post
        recall = await provider.recall(
            project_id=str(ObjectId()), query="hand promise", top_k=5,
        )
        assert len(recall.hits) == 2
        assert recall.hits[0].score == 0.91
        assert "Mara's hand" in recall.hits[0].content
        assert "The promise" in recall.hits[1].content
        assert recall.token_estimate < 50

    asyncio.run(run())


def test_writing_safe_recall_keeps_native_primary_during_tencent_experiment(monkeypatch):
    async def run():
        db = _Db()
        service = MemoryProviderService()
        native = _FixedProvider("native")
        tencent = _FixedProvider("tencent")
        async def config(db, runtime=True):
            return {"mode": "tencent"}
        async def providers(db, mode=None):
            return {"tencent": tencent, "native": native}
        monkeypatch.setattr(service, "config", config)
        monkeypatch.setattr(service, "providers", providers)
        result = await service.recall(
            db, str(ObjectId()), "old injury", mode="tencent", safe_for_writing=True,
        )
        assert result["comparison"]["configured_primary"] == "tencent"
        assert result["comparison"]["primary"] == "native"
        assert result["primary"]["provider"] == "native"

    asyncio.run(run())
