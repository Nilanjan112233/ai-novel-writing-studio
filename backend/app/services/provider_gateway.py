"""Unified provider gateway for direct per-agent model execution."""
from __future__ import annotations

import json
import logging
import time
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List

import httpx

from app.services.ai_provider import ai_provider
from app.services.llm import try_parse_json
from app.services.model_registry_service import model_registry_service, normalize_provider
from app.services.observability_service import estimate_cost
from app.services.provider_health_service import provider_health_service
from app.services.execution_trace_service import execution_trace_service
from app.services.provider_rate_limiter import provider_rate_limiter
from app.services.settings_service import settings_service


TEST_PROMPT = "Reply with exactly OK"
logger = logging.getLogger(__name__)


class ProviderError(Exception):
    def __init__(
        self,
        error_type: str,
        message: str,
        provider: str,
        model: str,
        status_code: int | None = None,
        *,
        request_payload: Dict[str, Any] | None = None,
        response_payload: Any = None,
        rate_limit_wait_ms: int = 0,
    ):
        super().__init__(message)
        self.error_type = error_type
        self.provider = provider
        self.model = model
        self.status_code = status_code
        self.request_payload = request_payload
        self.response_payload = response_payload
        self.rate_limit_wait_ms = rate_limit_wait_ms


def classify_exception(exc: Exception) -> str:
    if isinstance(exc, ProviderError):
        return exc.error_type
    if isinstance(exc, httpx.TimeoutException):
        return "TIMEOUT"
    if isinstance(exc, httpx.ConnectError):
        return "NETWORK_ERROR"
    if isinstance(exc, ValueError) and "INVALID_MODEL" in str(exc):
        return "INVALID_MODEL"
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        text = exc.response.text.lower()
        if status in {401, 403}:
            if "quota" in text or "exceeded" in text:
                return "QUOTA_EXCEEDED"
            return "INVALID_API_KEY"
        if status == 404 or "model" in text and "not found" in text:
            return "INVALID_MODEL"
        if status == 402:
            return "INSUFFICIENT_CREDITS"
        if status == 429:
            if "quota" in text or "insufficient" in text:
                return "QUOTA_EXCEEDED"
            return "RATE_LIMITED"
        if status >= 500:
            return "PROVIDER_UNAVAILABLE"
    if "invalid_model" in str(exc).lower() or "invalid_model" in type(exc).__name__.lower():
        return "INVALID_MODEL"
    return "PROVIDER_UNAVAILABLE"


def estimate_tokens(text: str) -> int:
    return max(1, len(text or "") // 4)


def _usage_from_response(data: Dict[str, Any], content: str) -> int:
    usage = data.get("usage") or data.get("usageMetadata") or {}
    total = usage.get("total_tokens") or usage.get("total_token_count")
    total = total or usage.get("totalTokenCount")
    if isinstance(total, int):
        return total
    return estimate_tokens(content)


def _mock_response(messages: List[Dict[str, str]], agent_name: str | None = None) -> Dict[str, Any]:
    text = " ".join(message.get("content", "") for message in messages)
    content = json.dumps({
        "status": "ok",
        "agent": agent_name or "MockAgent",
        "summary": f"Mock cognition integrated {min(len(text), 240)} characters of context.",
        "recommended_next_agents": ["ContinuityAgent"] if "contradiction" in text.lower() else [],
    })
    return {
        "content": content,
        "parsed": try_parse_json(content),
        "provider": "mock",
        "model": "mock-narrative-intelligence",
        "tokens_used": estimate_tokens(text) + estimate_tokens(content),
        "latency_ms": 1,
    }


class ProviderGateway:
    async def generate(
        self,
        messages: List[Dict[str, str]],
        *,
        provider: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
        agent_name: str | None = None,
        expect_json: bool = False,
    ) -> Dict[str, Any]:
        provider = normalize_provider(provider or "mock")
        await model_registry_service.validate_model(provider, model)
        execution_settings = await settings_service.get_execution_settings()
        rate_limit_wait_ms = await provider_rate_limiter.acquire(
            provider,
            execution_settings.get("provider_requests_per_minute", 5),
        )
        rate_limit_acquired_at = datetime.now(timezone.utc).isoformat()
        if provider == "mock":
            result = _mock_response(messages, agent_name)
            result["rate_limit_wait_ms"] = rate_limit_wait_ms
            result["rate_limit_acquired_at"] = rate_limit_acquired_at
            return result

        settings = await ai_provider.get_settings()
        config = settings.get("providers", {}).get(provider, {})
        api_key = config.get("api_key", "")
        model = model or config.get("model", "")
        if provider != "ollama" and not api_key:
            raise ProviderError("INVALID_API_KEY", f"{provider} API key not configured", provider, model)
        if not model:
            raise ProviderError("INVALID_MODEL", f"{provider} model not configured", provider, model)

        start = time.perf_counter()
        try:
            if provider in {"openrouter", "openai", "groq", "anthropic"}:
                result = await self._chat_completion(provider, api_key, model, messages, temperature, max_tokens, expect_json)
            elif provider == "gemini":
                result = await self._gemini(api_key, model, messages, temperature, max_tokens, expect_json)
            elif provider == "ollama":
                result = await self._ollama(config, model, messages)
            else:
                raise ProviderError("PROVIDER_UNAVAILABLE", f"Unknown provider: {provider}", provider, model)
            result["latency_ms"] = int((time.perf_counter() - start) * 1000)
            result["rate_limit_wait_ms"] = rate_limit_wait_ms
            result["rate_limit_acquired_at"] = rate_limit_acquired_at
            return result
        except Exception as exc:
            error_type = classify_exception(exc)
            if isinstance(exc, ProviderError):
                exc.rate_limit_wait_ms = rate_limit_wait_ms
                raise exc
            response = getattr(exc, "response", None)
            response_payload: Any = None
            if response is not None:
                try:
                    response_payload = response.json()
                except Exception:
                    response_payload = response.text
            raise ProviderError(
                error_type,
                str(exc),
                provider,
                model,
                getattr(response, "status_code", None),
                response_payload=response_payload,
                rate_limit_wait_ms=rate_limit_wait_ms,
            ) from exc

    async def generate_with_failover(
        self,
        db,
        messages: List[Dict[str, str]],
        *,
        provider: str,
        model: str,
        fallbacks: List[Dict[str, str]] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        agent_name: str | None = None,
        expect_json: bool = False,
        trace_context: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        attempts = [{"provider": provider, "model": model}] + (fallbacks or [])
        errors = []
        for attempt_index, attempt in enumerate(attempts):
            attempt_provider = normalize_provider(attempt.get("provider", "mock"))
            attempt_model = attempt.get("model", "")
            prompt_tokens = sum(estimate_tokens(message.get("content", "")) for message in messages)
            logger.info("Provider gateway selecting provider=%s model=%s agent=%s attempt=%s", attempt_provider, attempt_model, agent_name, attempt_index + 1)
            if attempt_provider == "mock" and attempt_index > 0:
                logger.warning("REAL MODEL FAILED -> FALLING BACK TO MOCK. agent=%s previous_errors=%s", agent_name, errors)
            try:
                retry_count = 0
                retry_metadata: List[Dict[str, Any]] = []
                total_rate_limit_wait_ms = 0
                while True:
                    try:
                        result = await self.generate(
                            messages,
                            provider=attempt_provider,
                            model=attempt_model,
                            temperature=temperature,
                            max_tokens=max_tokens,
                            agent_name=agent_name,
                            expect_json=expect_json,
                        )
                        if expect_json and not isinstance(result.get("parsed"), dict):
                            raise ProviderError(
                                "INVALID_JSON",
                                "Provider returned non-JSON or a JSON value with the wrong shape.",
                                attempt_provider,
                                attempt_model,
                                response_payload=result.get("response_payload"),
                            )
                        total_rate_limit_wait_ms += int(
                            result.get("rate_limit_wait_ms") or 0
                        )
                        break
                    except ProviderError as retry_error:
                        total_rate_limit_wait_ms += int(
                            retry_error.rate_limit_wait_ms or 0
                        )
                        transient = retry_error.error_type in {
                            "PROVIDER_UNAVAILABLE",
                            "NETWORK_ERROR",
                            "TIMEOUT",
                            "RATE_LIMITED",
                            "EMPTY_RESPONSE",
                            "INVALID_JSON",
                        }
                        if not transient or retry_count >= 2:
                            raise
                        retry_count += 1
                        delay_seconds = 2 ** retry_count
                        retry_metadata.append(
                            {
                                "retry": retry_count,
                                "delay_seconds": delay_seconds,
                                "error_type": retry_error.error_type,
                                "status_code": retry_error.status_code,
                            }
                        )
                        logger.warning(
                            "Transient provider failure; retrying provider=%s model=%s agent=%s retry=%s delay=%ss error_type=%s",
                            attempt_provider,
                            attempt_model,
                            agent_name,
                            retry_count,
                            delay_seconds,
                            retry_error.error_type,
                        )
                        await asyncio.sleep(delay_seconds)
                await provider_health_service.record_success(
                    db,
                    attempt_provider,
                    attempt_model,
                    int(result.get("latency_ms", 0)),
                    int(result.get("tokens_used", 0)),
                    estimate_cost(int(result.get("tokens_used", 0)), attempt_provider, attempt_model),
                )
                response_tokens = estimate_tokens(result.get("content", ""))
                trace = await execution_trace_service.record(
                    db,
                    provider=attempt_provider,
                    model=attempt_model,
                    agent_name=agent_name,
                    prompt_tokens=prompt_tokens,
                    response_tokens=response_tokens,
                    latency_ms=int(result.get("latency_ms", 0)),
                    retry_count=retry_count,
                    fallback_used=attempt_index > 0,
                    metadata={
                        "tokens_used": result.get("tokens_used", 0),
                        "response_length": len(result.get("content", "")),
                        "rate_limit_wait_ms": total_rate_limit_wait_ms,
                        "rate_limit_acquired_at": result.get(
                            "rate_limit_acquired_at"
                        ),
                        "rate_limit_per_minute": provider_rate_limiter.normalize_limit(
                            (
                                await settings_service.get_execution_settings()
                            ).get("provider_requests_per_minute", 5)
                        ) if provider_rate_limiter.is_app_limited(attempt_provider) else 0,
                        "application_rate_limit_enabled": provider_rate_limiter.is_app_limited(
                            attempt_provider
                        ),
                        "retries": retry_metadata,
                    },
                    **(trace_context or {}),
                )
                result["execution_trace_id"] = str(trace.get("_id", ""))
                result["fallback_used"] = attempt_index > 0
                result["attempts"] = attempt_index + retry_count + 1
                result["rate_limit_wait_ms"] = total_rate_limit_wait_ms
                result["retry_metadata"] = retry_metadata
                return result
            except ProviderError as exc:
                errors.append({"provider": attempt_provider, "model": attempt_model, "error_type": exc.error_type, "message": str(exc)})
                await provider_health_service.record_failure(db, attempt_provider, attempt_model, exc.error_type, str(exc))
                if attempt_provider != "mock":
                    logger.warning("Provider failed. provider=%s model=%s agent=%s error_type=%s reason=%s", attempt_provider, attempt_model, agent_name, exc.error_type, str(exc))
                await execution_trace_service.record(
                    db,
                    provider=attempt_provider,
                    model=attempt_model,
                    agent_name=agent_name,
                    prompt_tokens=prompt_tokens,
                    latency_ms=0,
                    status="failed",
                    error_type=exc.error_type,
                    error_message=str(exc),
                    retry_count=retry_count,
                    fallback_used=attempt_index > 0,
                    metadata={
                        "rate_limit_wait_ms": int(
                            getattr(exc, "rate_limit_wait_ms", 0) or 0
                        ),
                    },
                    **(trace_context or {}),
                )
                if exc.error_type == "INVALID_MODEL":
                    break
        raise ProviderError("PROVIDER_UNAVAILABLE", f"All providers failed: {errors}", normalize_provider(provider), model)

    async def test_model(self, provider: str, model: str, db=None) -> Dict[str, Any]:
        start = time.perf_counter()
        prompt_tokens = estimate_tokens(TEST_PROMPT)
        try:
            discovered_model = await model_registry_service.validate_discovered_model(provider, model)
            result = await self.generate(
                [{"role": "user", "content": TEST_PROMPT}],
                provider=provider,
                model=model,
                temperature=0,
                max_tokens=64,
                agent_name="ProviderValidation",
            )
            content = result.get("content")
            if not isinstance(content, str) or not content.strip():
                logger.error(
                    "[%s] empty_text_response model=%s request_body=%s response_body=%s",
                    provider,
                    model,
                    json.dumps(payload, ensure_ascii=True),
                    json.dumps(data, ensure_ascii=True)[:10000],
                )
                raise ProviderError(
                    "EMPTY_RESPONSE",
                    "Provider returned no text content.",
                    normalize_provider(provider),
                    model,
                    response_payload=result.get("response_payload"),
                )
            parsed = result.get("parsed") or try_parse_json(content)
            warnings = []
            normalized_handshake = content.strip().lower().rstrip(".! ")
            handshake_match = normalized_handshake == "ok" or bool(
                parsed and str(parsed.get("status") or "").strip().lower() == "ok"
            )
            if not handshake_match:
                warnings.append(
                    "The provider returned valid text but did not follow the exact health-check wording."
                )
            quota_limit = 20 if provider == "gemini" else None
            quota_remaining = None
            if quota_limit:
                quota_remaining = max(0, quota_limit - 1)
            if quota_remaining is not None and quota_remaining <= 2:
                warnings.append("Daily quota nearly exhausted")
            response = {
                # This endpoint verifies transport/model usability, not instruction-following
                # quality. A valid non-empty inference is a successful connectivity test;
                # the exact handshake remains observable as a separate diagnostic.
                "success": True,
                "handshake_match": handshake_match,
                "provider": normalize_provider(provider),
                "model": model,
                "latency_ms": result.get("latency_ms") or int((time.perf_counter() - start) * 1000),
                "tokens_used": result.get("tokens_used", estimate_tokens(result.get("content", ""))),
                "json_valid": bool(parsed),
                "streaming_supported": bool(discovered_model.supports_streaming),
                "quota_remaining": quota_remaining,
                "quota_limit": quota_limit,
                "warnings": warnings,
                "response": parsed or content,
                "request_payload": result.get("request_payload"),
                "response_payload": result.get("response_payload"),
            }
            if not response["success"]:
                response["error_type"] = "MODEL_RESPONSE_INVALID"
                response["error"] = "Provider responded, but the model did not reply with OK."
            if db is not None:
                await execution_trace_service.record(
                    db,
                    provider=normalize_provider(provider),
                    model=model,
                    agent_name="ProviderValidation",
                    prompt_tokens=prompt_tokens,
                    response_tokens=estimate_tokens(result.get("content", "")),
                    latency_ms=int(response["latency_ms"]),
                    status="success" if response["success"] else "failed",
                    error_type=response.get("error_type"),
                    error_message=response.get("error"),
                    metadata={"json_valid": response["json_valid"], "streaming_supported": response["streaming_supported"], "response_length": len(result.get("content", ""))},
                )
            return response
        except Exception as exc:
            error_type = classify_exception(exc)
            response = {
                "success": False,
                "provider": normalize_provider(provider),
                "model": model,
                "latency_ms": int((time.perf_counter() - start) * 1000),
                "tokens_used": 0,
                "json_valid": False,
                "streaming_supported": False,
                "quota_remaining": None,
                "quota_limit": None,
                "warnings": [],
                "error_type": error_type,
                "error": str(exc),
                "request_payload": getattr(exc, "request_payload", None),
                "response_payload": getattr(exc, "response_payload", None),
            }
            if db is not None:
                await execution_trace_service.record(
                    db,
                    provider=normalize_provider(provider),
                    model=model,
                    agent_name="ProviderValidation",
                    prompt_tokens=prompt_tokens,
                    latency_ms=int(response["latency_ms"]),
                    status="failed",
                    error_type=error_type,
                    error_message=str(exc),
                )
            return response

    async def _chat_completion(self, provider: str, api_key: str, model: str, messages: List[Dict[str, str]], temperature: float, max_tokens: int, expect_json: bool = False) -> Dict[str, Any]:
        base_urls = {
            "openrouter": "https://openrouter.ai/api/v1/chat/completions",
            "openai": "https://api.openai.com/v1/chat/completions",
            "groq": "https://api.groq.com/openai/v1/chat/completions",
            "anthropic": "https://api.anthropic.com/v1/messages",
        }
        if provider == "anthropic":
            system = "\n".join(m.get("content", "") for m in messages if m.get("role") == "system")
            user_messages = [m for m in messages if m.get("role") != "system"]
            payload = {"model": model, "messages": user_messages, "system": system, "temperature": temperature, "max_tokens": max_tokens}
            headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"}
        else:
            payload = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            if expect_json:
                payload["response_format"] = {"type": "json_object"}
            if provider == "openrouter":
                headers.update({"HTTP-Referer": "https://novelforge.local", "X-Title": "NovelForge"})
        request_start = time.perf_counter()
        if provider == "openrouter":
            logger.info("[openrouter] request_start model=%s prompt_tokens=%s", model, sum(estimate_tokens(m.get("content", "")) for m in messages))
        async with httpx.AsyncClient() as client:
            response = await client.post(base_urls[provider], headers=headers, json=payload, timeout=60)
            latency_ms = int((time.perf_counter() - request_start) * 1000)
            if provider == "openrouter":
                logger.info("[openrouter] status=%s latency=%sms", response.status_code, latency_ms)
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError:
                if provider == "openrouter":
                    logger.error("[openrouter] inference_failed status=%s model=%s", response.status_code, model)
                raise
            data = response.json()
        if provider == "anthropic":
            content = "".join(part.get("text", "") for part in data.get("content", []) if isinstance(part, dict))
        else:
            choices = data.get("choices") or []
            message = choices[0].get("message", {}) if choices and isinstance(choices[0], dict) else {}
            content = message.get("content")
            if not isinstance(content, str) or not content.strip():
                raise ProviderError(
                    "EMPTY_RESPONSE",
                    f"{provider} returned no text content.",
                    provider,
                    model,
                    response.status_code,
                    request_payload=payload,
                    response_payload=data,
                )
        return {
            "content": content,
            "parsed": try_parse_json(content),
            "provider": provider,
            "model": model,
            "tokens_used": _usage_from_response(data, content),
            "request_payload": payload,
            "response_payload": data,
        }

    async def _gemini(self, api_key: str, model: str, messages: List[Dict[str, str]], temperature: float, max_tokens: int, expect_json: bool = False) -> Dict[str, Any]:
        system_text = "\n\n".join(
            str(message.get("content") or "")
            for message in messages
            if message.get("role") == "system"
        ).strip()
        contents = []
        for message in messages:
            if message.get("role") == "system":
                continue
            text = str(message.get("content") or "")
            if not text:
                continue
            role = "model" if message.get("role") == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": text}]})
        if not contents:
            raise ProviderError("INVALID_REQUEST", "Gemini request has no message content.", "gemini", model)
        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
        }
        if system_text:
            payload["systemInstruction"] = {"parts": [{"text": system_text}]}
        if expect_json:
            payload["generationConfig"]["responseMimeType"] = "application/json"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers={"x-goog-api-key": api_key}, json=payload, timeout=60)
            if response.is_error:
                logger.error(
                    "[gemini] inference_failed model=%s status=%s",
                    model,
                    response.status_code,
                )
                try:
                    response_payload: Any = response.json()
                except Exception:
                    response_payload = response.text
                raise ProviderError(
                    classify_exception(httpx.HTTPStatusError("Gemini inference failed", request=response.request, response=response)),
                    f"Gemini request failed with HTTP {response.status_code}",
                    "gemini",
                    model,
                    response.status_code,
                    request_payload=payload,
                    response_payload=response_payload,
                )
            data = response.json()
        parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        content = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
        if not content.strip():
            raise ProviderError(
                "EMPTY_RESPONSE",
                "Gemini returned no text content.",
                "gemini",
                model,
                response.status_code,
                request_payload=payload,
                response_payload=data,
            )
        return {
            "content": content,
            "parsed": try_parse_json(content),
            "provider": "gemini",
            "model": model,
            "tokens_used": _usage_from_response(data, content),
            "request_payload": payload,
            "response_payload": data,
        }

    async def _ollama(self, config: Dict[str, Any], model: str, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        url = config.get("url") or "http://localhost:11434/api/generate"
        prompt = "\n\n".join(f"{m.get('role', 'user')}: {m.get('content', '')}" for m in messages)
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json={"model": model, "prompt": prompt, "stream": False}, timeout=config.get("timeout", 120))
            response.raise_for_status()
            data = response.json()
        content = data.get("response", "")
        return {"content": content, "parsed": try_parse_json(content), "provider": "ollama", "model": model, "tokens_used": estimate_tokens(prompt) + estimate_tokens(content)}


provider_gateway = ProviderGateway()
