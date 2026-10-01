import httpx
import pytest
from types import SimpleNamespace

from app.services.provider_gateway import ProviderError, classify_exception, provider_gateway
from app.services.model_registry_service import model_registry_service


class StubClient:
    def __init__(self, handler):
        self.handler = handler

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, **kwargs):
        return self.handler(url, kwargs)


def response(status_code, payload, url):
    request = httpx.Request("POST", url)
    return httpx.Response(status_code, json=payload, request=request)


def test_openrouter_402_is_classified_as_insufficient_credits():
    response_value = response(
        402,
        {"error": {"message": "Insufficient credits"}},
        "https://openrouter.ai/api/v1/chat/completions",
    )
    error = httpx.HTTPStatusError(
        "Payment required",
        request=response_value.request,
        response=response_value,
    )

    assert classify_exception(error) == "INSUFFICIENT_CREDITS"


@pytest.mark.asyncio
async def test_gemini_uses_valid_roles_json_config_and_usage(monkeypatch):
    captured = {}

    def handler(url, kwargs):
        captured.update({"url": url, **kwargs})
        return response(
            200,
            {
                "candidates": [{"content": {"parts": [{"text": "OK"}], "role": "model"}}],
                "usageMetadata": {"totalTokenCount": 17},
            },
            url,
        )

    monkeypatch.setattr(
        "app.services.provider_gateway.httpx.AsyncClient",
        lambda: StubClient(handler),
    )
    result = await provider_gateway._gemini(
        "key",
        "gemini-test",
        [
            {"role": "system", "content": "System instruction"},
            {"role": "user", "content": "Reply with exactly OK"},
        ],
        0,
        64,
        True,
    )

    assert captured["url"].endswith("/models/gemini-test:generateContent")
    assert captured["json"]["contents"] == [{
        "role": "user",
        "parts": [{"text": "Reply with exactly OK"}],
    }]
    assert captured["json"]["systemInstruction"]["parts"][0]["text"] == "System instruction"
    assert captured["json"]["generationConfig"]["responseMimeType"] == "application/json"
    assert "response_mime_type" not in captured["json"]["generationConfig"]
    assert result["content"] == "OK"
    assert result["tokens_used"] == 17


@pytest.mark.asyncio
async def test_gemini_error_preserves_request_and_response(monkeypatch):
    def handler(url, kwargs):
        return response(400, {"error": {"message": "Bad generation config"}}, url)

    monkeypatch.setattr(
        "app.services.provider_gateway.httpx.AsyncClient",
        lambda: StubClient(handler),
    )
    with pytest.raises(ProviderError) as raised:
        await provider_gateway._gemini(
            "key",
            "gemini-test",
            [{"role": "user", "content": "Reply with exactly OK"}],
            0,
            64,
        )

    assert raised.value.status_code == 400
    assert raised.value.request_payload["contents"][0]["role"] == "user"
    assert raised.value.response_payload["error"]["message"] == "Bad generation config"


@pytest.mark.asyncio
async def test_openrouter_null_content_returns_provider_error(monkeypatch):
    def handler(url, kwargs):
        return response(
            200,
            {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "reasoning": "No visible answer was produced.",
                    }
                }],
                "usage": {"total_tokens": 12},
            },
            url,
        )

    monkeypatch.setattr(
        "app.services.provider_gateway.httpx.AsyncClient",
        lambda: StubClient(handler),
    )
    with pytest.raises(ProviderError) as raised:
        await provider_gateway._chat_completion(
            "openrouter",
            "key",
            "provider/model",
            [{"role": "user", "content": "Reply with exactly OK"}],
            0,
            64,
        )

    assert raised.value.error_type == "EMPTY_RESPONSE"
    assert "no text content" in str(raised.value).lower()
    assert raised.value.response_payload["choices"][0]["message"]["content"] is None


@pytest.mark.asyncio
async def test_model_health_accepts_valid_nonempty_inference_with_handshake_warning(monkeypatch):
    async def discovered(_provider, _model):
        return SimpleNamespace(supports_streaming=True)

    async def generated(*_args, **_kwargs):
        return {
            "content": "The model is available and ready.",
            "provider": "gemini",
            "model": "gemini-test",
            "latency_ms": 12,
            "tokens_used": 8,
        }

    monkeypatch.setattr(model_registry_service, "validate_discovered_model", discovered)
    monkeypatch.setattr(provider_gateway, "generate", generated)
    result = await provider_gateway.test_model("gemini", "gemini-test")

    assert result["success"] is True
    assert result["handshake_match"] is False
    assert "valid text" in result["warnings"][0]
