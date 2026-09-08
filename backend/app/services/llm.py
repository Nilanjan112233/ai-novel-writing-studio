# llm.py
"""
Unified LLM service - ALL LLM execution happens here.
Multi-provider fallback with retry logic, cooldown, and circuit breaker.
"""
import json
import logging
import re
import httpx
import asyncio
import time
from typing import Optional, Dict, Any, List
from datetime import datetime

from app.services.ai_provider import ai_provider, get_provider_delay, PROVIDER_MIN_DELAYS, DEFAULT_DELAY_SECONDS

logger = logging.getLogger(__name__)


# =============================================================================
# ERROR TYPES
# =============================================================================

class LLMError(Exception):
    """Base LLM error with type classification."""
    
    def __init__(self, message: str, error_type: str = "unknown", provider: str = None, details: Dict[str, Any] = None):
        super().__init__(message)
        self.error_type = error_type  # "cooldown" | "rate_limit" | "server" | "parse" | "unknown"
        self.provider = provider
        self.details = details or {}
    
    def __str__(self):
        base = f"[{self.error_type.upper()}]"
        if self.provider:
            base += f" {self.provider}:"
        return f"{base} {super().__str__()}"


class CooldownError(LLMError):
    """Provider is in cooldown period."""
    def __init__(self, provider: str, remaining_seconds: float):
        super().__init__(
            f"Provider in cooldown ({remaining_seconds:.0f}s remaining)",
            error_type="cooldown",
            provider=provider,
            details={"remaining_seconds": remaining_seconds}
        )
        self.remaining_seconds = remaining_seconds


class RateLimitError(LLMError):
    """Rate limit exceeded (429)."""
    def __init__(self, provider: str, retry_after: int = 60):
        super().__init__(
            f"Rate limit exceeded. Retry after {retry_after}s",
            error_type="rate_limit",
            provider=provider,
            details={"retry_after": retry_after}
        )
        self.retry_after = retry_after


class ServerError(LLMError):
    """Server error (500/503)."""
    def __init__(self, provider: str, status_code: int, message: str = None):
        super().__init__(
            message or f"Server error {status_code}",
            error_type="server",
            provider=provider,
            details={"status_code": status_code}
        )
        self.status_code = status_code


class ParseError(LLMError):
    """JSON parsing error."""
    def __init__(self, provider: str, original_error: str = None):
        super().__init__(
            f"Failed to parse response: {original_error}" if original_error else "Failed to parse response",
            error_type="parse",
            provider=provider,
            details={"original_error": original_error}
        )


def is_rate_limit_error(error: Exception) -> bool:
    """Check if an error is a rate limit error (429)."""
    if isinstance(error, RateLimitError):
        return True
    if isinstance(error, LLMError) and error.error_type == "rate_limit":
        return True
    error_str = str(error).lower()
    return "rate limit" in error_str or "429" in error_str


# =============================================================================
# COOLDOWN MANAGEMENT
# =============================================================================

cooldown_tracker: Dict[str, float] = {}

COOLDOWN_DURATION = {
    "rate_limit": 60,
    "server": 30,
    "timeout": 30,
    "default": 60
}


def get_remaining_cooldown(provider: str) -> float:
    """Get remaining cooldown seconds for a provider. Returns 0 if available."""
    if provider not in cooldown_tracker:
        return 0.0
    
    cooldown_until = cooldown_tracker[provider]
    now = time.time()
    remaining = max(0, cooldown_until - now)
    
    if remaining <= 0 and provider in cooldown_tracker:
        del cooldown_tracker[provider]
    
    return remaining


def set_provider_cooldown(provider: str, duration_seconds: int = None, error_type: str = "default"):
    """Set a provider into cooldown."""
    if duration_seconds is None:
        duration_seconds = COOLDOWN_DURATION.get(error_type, COOLDOWN_DURATION["default"])
    
    cooldown_tracker[provider] = time.time() + duration_seconds
    logger.warning(f"{provider} set to cooldown for {duration_seconds}s (reason: {error_type})")


def reset_provider_cooldown(provider: str):
    """Reset cooldown for a provider (on success)."""
    if provider in cooldown_tracker:
        del cooldown_tracker[provider]
        logger.info(f"{provider} cooldown reset due to success")


def is_provider_in_cooldown(provider: str) -> bool:
    """Check if provider is currently in cooldown."""
    remaining = get_remaining_cooldown(provider)
    return remaining > 0


PROVIDER_TIMEOUTS = {
    "gemini": 60,
    "groq": 30,
    "huggingface": 60,
    "openrouter": 60,
    "local": 120
}

provider_failures: Dict[str, Dict[str, Any]] = {
    "gemini": {"fail_count": 0, "last_fail": None},
    "groq": {"fail_count": 0, "last_fail": None},
    "openrouter": {"fail_count": 0, "last_fail": None},
    "huggingface": {"fail_count": 0, "last_fail": None},
    "local": {"fail_count": 0, "last_fail": None}
}


async def wait_for_available_provider(cooldowns: Dict[str, float]) -> None:
    """Wait until the earliest cooldown expires."""
    if not cooldowns:
        return
    
    min_wait = min(cooldowns.values())
    wait_time = min_wait + 1
    
    logger.warning(f"All providers in cooldown. Waiting {wait_time:.0f}s...")
    logger.warning(f"  Cooldowns: {cooldowns}")
    
    await asyncio.sleep(wait_time)
    
    logger.info(f"Wait complete. Retrying providers...")


COOLDOWN_SECONDS = 60
MAX_FAIL_COUNT = 3


def _is_provider_in_cooldown(provider: str) -> bool:
    """Check if provider is in cooldown due to repeated failures."""
    failures = provider_failures.get(provider, {})
    fail_count = failures.get("fail_count", 0)
    last_fail = failures.get("last_fail")
    
    if fail_count >= MAX_FAIL_COUNT and last_fail:
        elapsed = time.time() - last_fail
        if elapsed < COOLDOWN_SECONDS:
            logger.warning(f"{provider} in cooldown ({COOLDOWN_SECONDS - elapsed:.0f}s remaining)")
            return True
    return False


def _record_provider_failure(provider: str, error_type: str = "default"):
    """Record a failure for circuit breaker tracking."""
    if provider in provider_failures:
        provider_failures[provider]["fail_count"] += 1
        provider_failures[provider]["last_fail"] = time.time()
        logger.warning(f"{provider} failure recorded (count: {provider_failures[provider]['fail_count']})")
        
        if provider_failures[provider]["fail_count"] >= MAX_FAIL_COUNT:
            set_provider_cooldown(provider, error_type=error_type)


def _record_provider_success(provider: str):
    """Reset failure count on success."""
    if provider in provider_failures:
        if provider_failures[provider]["fail_count"] > 0:
            logger.info(f"{provider} success - resetting failure count")
        provider_failures[provider]["fail_count"] = 0
        provider_failures[provider]["last_fail"] = None
    
    reset_provider_cooldown(provider)


# =============================================================================
# JSON PARSING
# =============================================================================

def try_parse_json(text: str) -> Optional[Dict[str, Any]]:
    """Safely parse JSON text. Returns None if parsing fails."""
    if not text or not text.strip():
        return None
    
    cleaned = clean_llm_output(text)
    
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
        return None
    except Exception:
        pass
    
    match = re.search(r'\{.*\}', cleaned, re.DOTALL)
    if not match:
        return None
    
    json_text = match.group(0)
    
    json_text = json_text.replace("'", '"')
    json_text = re.sub(r',\s*}', '}', json_text)
    json_text = re.sub(r',\s*\]', ']', json_text)
    
    try:
        data = json.loads(json_text)
        if isinstance(data, dict):
            return data
        return None
    except Exception:
        return None


def clean_llm_output(text: str) -> str:
    """Clean LLM output by removing markdown code blocks."""
    text = re.sub(r"```json", "", text)
    text = re.sub(r"```", "", text)
    return text.strip()


def safe_json_parse(text: str) -> Dict[str, Any]:
    """Safely parse JSON from LLM response with extraction and auto-fixing."""
    if not text or not text.strip():
        raise Exception("LLM returned empty response")
    
    cleaned = clean_llm_output(text)
    
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    
    match = re.search(r'\{.*\}', cleaned, re.DOTALL)
    if not match:
        raise Exception("No JSON object found in response")
    
    json_text = match.group(0)
    
    json_text = json_text.replace("'", '"')
    json_text = re.sub(r',\s*}', '}', json_text)
    json_text = re.sub(r',\s*\]', ']', json_text)
    
    try:
        data = json.loads(json_text)
        if not isinstance(data, dict):
            raise Exception(f"LLM did not return valid JSON object, got {type(data).__name__}")
        return data
    except Exception as e:
        raise Exception(f"JSON parse failed after cleanup: {str(e)}")


# =============================================================================
# PROVIDER CALLS
# =============================================================================

async def _call_gemini(
    messages: List[Dict[str, str]],
    model: str,
    api_key: str,
    temperature: float,
    max_tokens: int,
    timeout: int = 60
) -> str:
    """Call Gemini API with dual-endpoint fallback."""
    if not model:
        raise ValueError("No model configured for gemini")
    
    max_tokens = max(max_tokens, 4096)
    logger.info(f"Gemini max_output_tokens set to {max_tokens}")
    
    system_content = ""
    user_content = ""
    
    for msg in messages:
        if msg.get("role") == "system":
            system_content = msg.get("content", "")
        elif msg.get("role") == "user":
            user_content = msg.get("content", "")
    
    full_content = f"{system_content}\n\n{user_content}" if system_content else user_content
    
    base_v1 = f"https://generativelanguage.googleapis.com/v1/models/{model}:generateContent"
    base_v1beta = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    
    payload = {
        "contents": [{"parts": [{"text": full_content}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
            "topP": 0.9
        }
    }
    
    async with httpx.AsyncClient() as client:
        try:
            logger.info(f"Gemini: trying v1 endpoint for model={model}")
            response = await client.post(base_v1, headers={"x-goog-api-key": api_key}, json=payload, timeout=timeout)
            
            if response.status_code == 200:
                result = response.json()
                candidates = result.get("candidates", [])
                if candidates:
                    content = candidates[0].get("content", {})
                    parts = content.get("parts", [])
                    if parts:
                        return parts[0].get("text", "")
                raise Exception("No content in Gemini v1 response")
            
            if response.status_code == 404:
                logger.warning(f"Gemini v1 returned 404 for model={model}, trying v1beta...")
            elif response.status_code == 429:
                raise Exception("LLM rate limit exceeded. Try again later.")
            else:
                response.raise_for_status()
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code != 404:
                raise
            logger.warning(f"Gemini v1 failed with 404, falling back to v1beta for model={model}")
        
        logger.info(f"Gemini: trying v1beta endpoint for model={model}")
        response = await client.post(base_v1beta, headers={"x-goog-api-key": api_key}, json=payload, timeout=timeout)
        
        if response.status_code == 404:
            logger.error("Gemini model unavailable. model=%s status=404", model)
            raise httpx.HTTPStatusError(
                f"Gemini model not found on v1 or v1beta: {model}",
                request=response.request,
                response=response
            )
        
        if response.status_code == 429:
            raise Exception("LLM rate limit exceeded. Try again later.")
        
        response.raise_for_status()
        result = response.json()
        
        candidates = result.get("candidates", [])
        if not candidates:
            raise Exception("No candidates in Gemini v1beta response")
        
        content = candidates[0].get("content", {})
        parts = content.get("parts", [])
        if not parts:
            raise Exception("No content parts in Gemini v1beta response")
        
        return parts[0].get("text", "")


GEMINI_FALLBACK_MODELS = [
    "gemini-flash-lite-latest",
    "gemini-3-flash-preview",
    "gemini-2.5-flash-lite",
]


async def _call_gemini_with_fallback(
    messages: List[Dict[str, str]],
    configured_model: str,
    api_key: str,
    temperature: float,
    max_tokens: int,
    timeout: int = 60
) -> str:
    """Call Gemini with model fallback chain."""
    models_to_try = [configured_model] if configured_model else []
    for model in GEMINI_FALLBACK_MODELS:
        if model not in models_to_try:
            models_to_try.append(model)
    
    logger.info(f"[gemini] Will try models in order: {models_to_try}")
    
    last_error = None
    
    for i, model in enumerate(models_to_try):
        try:
            logger.info(f"[gemini] Attempting model {i+1}/{len(models_to_try)}: {model}")
            result = await _call_gemini(
                messages=messages,
                model=model,
                api_key=api_key,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout
            )
            
            if result and result.strip():
                logger.info(f"[gemini] SUCCESS with model: {model}")
                return result
            else:
                logger.warning(f"[gemini] Model {model} returned empty result, trying next...")
                
        except Exception as e:
            last_error = e
            error_str = str(e).lower()
            
            if "rate limit" in error_str or "429" in error_str:
                logger.warning(f"[gemini] Rate limit on {model} → switching provider immediately")
                raise
            
            if "404" in error_str or "not found" in error_str:
                logger.warning(f"[gemini] Model {model} not found (404), trying next model...")
                continue
            
            logger.warning(f"[gemini] Model {model} failed: {e}, trying next model...")
            continue
    
    logger.error(f"[gemini] ALL models failed after trying {len(models_to_try)} options")
    if last_error:
        raise last_error
    raise Exception("All Gemini models failed")


async def _call_groq(
    messages: List[Dict[str, str]],
    model: str,
    api_key: str,
    temperature: float,
    max_tokens: int,
    timeout: int = 30
) -> str:
    """Call Groq API with model validation."""
    VALID_GROQ_MODELS = [
        "llama-3.1-8b-instant",
        "llama-3.1-70b-versatile",
        "llama-3.3-70b-versatile",
        "mixtral-8x7b-32768",
        "gemma2-9b-it"
    ]
    
    if not model:
        raise ValueError("No model configured for groq")
    
    if model not in VALID_GROQ_MODELS:
        logger.warning(f"Groq model '{model}' not in known list: {VALID_GROQ_MODELS}")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=timeout
        )
        
        if response.status_code == 400:
            logger.error("Groq rejected the request for model='%s' with status=400", model)
            raise httpx.HTTPStatusError(
                f"Invalid Groq model: {model}",
                request=response.request,
                response=response
            )
        
        if response.status_code == 429:
            raise Exception("LLM rate limit exceeded. Try again later.")
        
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]


async def _call_openrouter(
    messages: List[Dict[str, str]],
    model: str,
    api_key: str,
    temperature: float,
    max_tokens: int,
    timeout: int = 60
) -> str:
    """Call OpenRouter API with improved error logging."""
    if not model:
        raise ValueError("No model configured for openrouter")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://novelforge.local",
        "X-Title": "NovelForge"
    }
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=timeout
        )
        
        if response.status_code == 404:
            logger.warning(f"OpenRouter model '{model}' not found or unavailable (404)")
            raise httpx.HTTPStatusError(
                f"OpenRouter model not found: {model}",
                request=response.request,
                response=response
            )
        
        if response.status_code == 429:
            raise Exception("LLM rate limit exceeded. Try again later.")
        
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]


async def _call_huggingface(
    messages: List[Dict[str, str]],
    model: str,
    api_key: str,
    temperature: float,
    max_tokens: int,
    timeout: int = 60
) -> str:
    """Call HuggingFace Inference API."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    formatted = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "system":
            formatted.append(f"System: {content}")
        elif role == "user":
            formatted.append(f"User: {content}")
        else:
            formatted.append(f"Assistant: {content}")
    prompt = "\n\n".join(formatted) + "\n\nAssistant:"
    
    payload = {
        "inputs": prompt,
        "parameters": {
            "temperature": temperature,
            "max_new_tokens": max_tokens,
            "return_full_text": False
        }
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://api-inference.huggingface.co/models/{model}",
            headers=headers,
            json=payload,
            timeout=timeout
        )
        
        if response.status_code == 429:
            raise Exception("LLM rate limit exceeded. Try again later.")
        
        response.raise_for_status()
        result = response.json()
        
        if isinstance(result, list) and len(result) > 0:
            return result[0].get("generated_text", "")
        return str(result)


def _messages_to_prompt(messages: List[Dict[str, str]]) -> str:
    """Convert OpenAI-style messages to a single prompt string for Ollama /api/generate."""
    parts = []
    
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        
        if role == "system":
            parts.append(f"[System Instructions] {content}")
        elif role == "user":
            parts.append(content)
        elif role == "assistant":
            parts.append(f"Assistant: {content}")
        else:
            parts.append(content)
    
    return "\n\n".join(parts)


async def _call_local(prompt: str, config: dict) -> str:
    """Call local LLM via Ollama /api/generate endpoint."""
    if config is None:
        raise LLMError("Local config missing", error_type="config", provider="local")
    
    url = config.get("url")
    model = config.get("model")
    timeout = config.get("timeout", 900)
    
    if not url or not url.startswith("http"):
        raise LLMError("Invalid local URL", error_type="config", provider="local")
    
    url = url.rstrip("/")
    
    if not model:
        raise LLMError("Local model missing", error_type="config", provider="local")
    
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    
    logger.info(f"[LOCAL] Calling {url} with model={model}")
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload)
        
        if response.status_code == 404:
            raise LLMError(
                f"Model '{model}' not found. Run: ollama pull {model}",
                error_type="config",
                provider="local",
                details={"status_code": 404}
            )
        
        if response.status_code >= 500:
            raise LLMError(
                f"Ollama server error: HTTP {response.status_code}",
                error_type="server",
                provider="local",
                details={"status_code": response.status_code}
            )
        
        response.raise_for_status()
        data = response.json()
        
        if "response" not in data:
            raise LLMError(
                "Invalid local response format",
                error_type="parse",
                provider="local",
                details={"response_keys": list(data.keys())}
            )
        
        result = data["response"].strip()
        logger.info("[LOCAL] Success")
        return result
        
    except httpx.TimeoutException:
        logger.error("[LOCAL] Failed: timeout")
        raise LLMError("Local LLM timeout", error_type="timeout", provider="local")
    
    except httpx.RequestError as e:
        logger.error(f"[LOCAL] Failed: connection error - {e}")
        raise LLMError(f"Local connection error: {str(e)}", error_type="server", provider="local")
    
    except LLMError:
        logger.error("[LOCAL] Failed")
        raise


async def _try_provider_with_retry(
    provider: str,
    model: str,
    api_key: str,
    messages: List[Dict[str, str]],
    temperature: float,
    max_tokens: int,
    max_retries: int = 2,
    provider_config: dict = None
) -> Optional[str]:
    """Try a single provider with exponential backoff retry."""
    timeout = PROVIDER_TIMEOUTS.get(provider, 60)
    
    if provider == "local":
        if not provider_config:
            raise LLMError("Local provider config missing", error_type="config", provider="local")
        if not provider_config.get("enabled", False):
            raise LLMError("Local provider is not enabled", error_type="config", provider="local")
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Trying {provider} (attempt {attempt+1}/{max_retries}) with model={model}")
            start_time = time.time()
            
            if provider == "gemini":
                result = await _call_gemini_with_fallback(messages, model, api_key, temperature, max_tokens, timeout)
            elif provider == "groq":
                result = await _call_groq(messages, model, api_key, temperature, max_tokens, timeout)
            elif provider == "openrouter":
                result = await _call_openrouter(messages, model, api_key, temperature, max_tokens, timeout)
            elif provider == "huggingface":
                result = await _call_huggingface(messages, model, api_key, temperature, max_tokens, timeout)
            elif provider == "local":
                prompt = _messages_to_prompt(messages)
                result = await _call_local(prompt, provider_config)
            else:
                logger.error(f"Unknown provider: {provider}")
                raise LLMError(f"Unknown provider: {provider}", error_type="unknown", provider=provider)
            
            elapsed = time.time() - start_time
            logger.info(f"{provider} success | model={model} | time={elapsed:.2f}s")
            _record_provider_success(provider)
            return result
            
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            logger.warning(f"Provider {provider} failed: HTTP {status_code} (attempt {attempt+1}/{max_retries})")
            
            if status_code in [404, 401]:
                raise LLMError(f"HTTP {status_code}", error_type="server", provider=provider, details={"status_code": status_code})
            
            if status_code == 400:
                if attempt == 0:
                    logger.warning(f"{provider} 400 error, retrying once...")
                    delay = min(2 ** attempt, 4)
                    await asyncio.sleep(delay)
                    continue
                raise LLMError("Bad request (400)", error_type="server", provider=provider, details={"status_code": 400})
            
            if status_code == 429:
                logger.warning(f"Provider {provider} failed: rate_limit")
                set_provider_cooldown(provider, error_type="rate_limit")
                raise RateLimitError(provider, retry_after=60)
            
            if status_code in [500, 502, 503, 504]:
                logger.warning(f"Provider {provider} failed: server error {status_code}")
                set_provider_cooldown(provider, error_type="server")
                if attempt < max_retries - 1:
                    delay = min(2 ** attempt, 4)
                    logger.info(f"Retrying {provider} in {delay}s...")
                    await asyncio.sleep(delay)
                    continue
                raise ServerError(provider, status_code)
            
            if attempt < max_retries - 1:
                delay = min(2 ** attempt, 4)
                await asyncio.sleep(delay)
                continue
            raise LLMError(f"HTTP {status_code}", error_type="server", provider=provider, details={"status_code": status_code})
            
        except httpx.TimeoutException:
            logger.warning(f"Provider {provider} failed: timeout after {timeout}s")
            set_provider_cooldown(provider, error_type="timeout")
            if attempt < max_retries - 1:
                delay = min(2 ** attempt, 4)
                await asyncio.sleep(delay)
                continue
            raise LLMError(f"Timeout after {timeout}s", error_type="server", provider=provider)
            
        except LLMError:
            raise
            
        except Exception as e:
            logger.warning(f"Provider {provider} failed: {type(e).__name__}: {e}")
            if attempt < max_retries - 1:
                delay = min(2 ** attempt, 4)
                await asyncio.sleep(delay)
                continue
            raise LLMError(str(e), error_type="unknown", provider=provider, details={"exception_type": type(e).__name__})
    
    return None


async def call_llm_with_fallback(
    messages: List[Dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 2000,
    max_retries_per_provider: int = 1,
    delay_seconds: Optional[float] = None,
    max_cycles: int = 3,
    expect_json: bool = True
) -> Dict[str, Any]:
    """
    Call LLM with intelligent fallback and retry.
    
    Args:
        messages: List of message dicts with role and content
        temperature: Temperature for generation
        max_tokens: Maximum tokens to generate
        max_retries_per_provider: Max retries per provider
        delay_seconds: Base delay between calls in seconds
        max_cycles: Maximum global retry cycles
        expect_json: If False, skip JSON parsing and return raw text
    
    Returns:
        Dict with "content", "parsed", "provider", "model" keys
    """
    settings = await ai_provider.get_settings()
    priority = settings.get("fallback_priority", [])
    providers_config = settings.get("providers", {})
    
    if "local" not in priority and "local" in providers_config:
        priority = priority + ["local"]
    
    if delay_seconds is None:
        delay_seconds = settings.get("llm_delay_seconds", DEFAULT_DELAY_SECONDS)
    
    logger.info(f"LLM fallback priority: {priority}")
    logger.info(f"Max cycles: {max_cycles}, Provider retries: {max_retries_per_provider}")
    logger.info(f"User-configured delay: {delay_seconds}s")
    
    provider_errors: Dict[str, str] = {}
    
    for cycle in range(max_cycles):
        logger.info(f"=== Retry cycle {cycle + 1}/{max_cycles} ===")
        
        cooldowns: Dict[str, float] = {}
        last_provider = None
        
        for provider in priority:
            config = providers_config.get(provider, {})
            api_key = config.get("api_key", "").strip()
            model = config.get("model", "").strip()
            
            if provider == "local":
                if not config.get("enabled", False):
                    logger.info("[LOCAL] Not enabled, skipping")
                    provider_errors[provider] = "not_enabled"
                    continue
                
                if not model:
                    logger.error("[LOCAL] No model configured")
                    provider_errors[provider] = "no_model"
                    continue
                
                max_local_attempts = max_retries_per_provider + 1
                local_failed = False
                
                for attempt in range(max_local_attempts):
                    try:
                        prompt = _messages_to_prompt(messages)
                        raw = await _call_local(prompt, config)
                        
                        if not expect_json:
                            logger.info(f"[LOCAL] SUCCESS (raw text, expect_json=False)")
                            return {
                                "content": raw,
                                "parsed": None,
                                "provider": provider,
                                "model": model
                            }
                        
                        parsed = try_parse_json(raw)
                        
                        if parsed is None:
                            logger.warning(f"[LOCAL] Attempt {attempt+1}/{max_local_attempts}: JSON parsing failed")
                            if attempt < max_local_attempts - 1:
                                retry_delay = 2
                                logger.info(f"[LOCAL] Waiting {retry_delay}s before retry...")
                                await asyncio.sleep(retry_delay)
                                continue
                            logger.warning(f"[LOCAL] JSON parsing failed after {max_local_attempts} attempts → Switching provider")
                            provider_errors[provider] = "parse_error"
                            local_failed = True
                            break
                        
                        logger.info(f"[LOCAL] SUCCESS")
                        return {
                            "content": raw,
                            "parsed": parsed,
                            "provider": provider,
                            "model": model
                        }
                        
                    except LLMError as e:
                        logger.warning(f"[LOCAL] Attempt {attempt+1}/{max_local_attempts}: {e.error_type} - {e}")
                        if attempt < max_local_attempts - 1:
                            retry_delay = 2
                            logger.info(f"[LOCAL] Waiting {retry_delay}s before retry...")
                            await asyncio.sleep(retry_delay)
                            continue
                        logger.warning(f"[LOCAL] Failed after {max_local_attempts} attempts → Switching provider")
                        provider_errors[provider] = e.error_type
                        local_failed = True
                        break
                    
                    except Exception as e:
                        logger.warning(f"[LOCAL] Attempt {attempt+1}/{max_local_attempts}: {type(e).__name__} - {e}")
                        if attempt < max_local_attempts - 1:
                            retry_delay = 2
                            logger.info(f"[LOCAL] Waiting {retry_delay}s before retry...")
                            await asyncio.sleep(retry_delay)
                            continue
                        logger.warning(f"[LOCAL] Failed after {max_local_attempts} attempts → Switching provider")
                        provider_errors[provider] = f"error_{type(e).__name__}"
                        local_failed = True
                        break
                
                if local_failed:
                    continue
            
            remaining = get_remaining_cooldown(provider)
            if remaining > 0:
                logger.info(f"{provider} in cooldown ({remaining:.0f}s remaining), skipping")
                cooldowns[provider] = remaining
                provider_errors[provider] = "cooldown"
                continue
            
            if not api_key:
                logger.info(f"{provider}: no API key, skipping")
                provider_errors[provider] = "no_api_key"
                continue
            
            if not model:
                logger.error(f"{provider}: NO MODEL CONFIGURED")
                provider_errors[provider] = "no_model"
                continue
            
            effective_delay = get_provider_delay(provider, delay_seconds)
            
            if last_provider and effective_delay > 0:
                logger.info(f"[{provider}] Waiting {effective_delay}s before attempting (user setting)...")
                await asyncio.sleep(effective_delay)
            
            last_provider = provider
            
            logger.info(f"Attempting {provider} with model={model}")
            
            max_attempts = max_retries_per_provider + 1
            cloud_failed = False
            
            for attempt in range(max_attempts):
                try:
                    result = await _try_provider_with_retry(
                        provider=provider,
                        model=model,
                        api_key=api_key,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        max_retries=1,
                        provider_config=config
                    )
                    
                    if not result:
                        logger.warning(f"[{provider}] Attempt {attempt+1}/{max_attempts}: No response")
                        if attempt < max_attempts - 1:
                            retry_delay = get_provider_delay(provider, delay_seconds)
                            logger.info(f"[{provider}] Waiting {retry_delay}s before retry...")
                            await asyncio.sleep(retry_delay)
                            continue
                        provider_errors[provider] = "no_response"
                        cloud_failed = True
                        break
                    
                    if not expect_json:
                        logger.info(f"[{provider}] SUCCESS (raw text, expect_json=False)")
                        return {
                            "content": result,
                            "parsed": None,
                            "provider": provider,
                            "model": model
                        }
                    
                    cleaned = result.strip()
                    if not cleaned or cleaned in ["{}", "[]", "null", "undefined"]:
                        logger.warning(f"[{provider}] Attempt {attempt+1}/{max_attempts}: Empty structure")
                        if attempt < max_attempts - 1:
                            retry_delay = get_provider_delay(provider, delay_seconds)
                            logger.info(f"[{provider}] Waiting {retry_delay}s before retry...")
                            await asyncio.sleep(retry_delay)
                            continue
                        provider_errors[provider] = "empty_response"
                        cloud_failed = True
                        break
                    
                    parsed = try_parse_json(result)
                    
                    if parsed is None:
                        logger.warning(f"[{provider}] Attempt {attempt+1}/{max_attempts}: JSON parsing failed")
                        if attempt < max_attempts - 1:
                            retry_delay = get_provider_delay(provider, delay_seconds)
                            logger.info(f"[{provider}] Waiting {retry_delay}s before retry...")
                            await asyncio.sleep(retry_delay)
                            continue
                        logger.warning(f"[{provider}] JSON parsing failed after {max_attempts} attempts → Switching provider")
                        provider_errors[provider] = "parse_error"
                        cloud_failed = True
                        break
                    
                    logger.info(f"[{provider}] SUCCESS")
                    return {
                        "content": result,
                        "parsed": parsed,
                        "provider": provider,
                        "model": model
                    }
                    
                except CooldownError as e:
                    cooldowns[provider] = e.remaining_seconds
                    provider_errors[provider] = "cooldown"
                    logger.warning(f"[{provider}] In cooldown: {e.remaining_seconds:.0f}s → Switching provider")
                    cloud_failed = True
                    break
                    
                except RateLimitError as e:
                    cooldowns[provider] = e.retry_after
                    provider_errors[provider] = "rate_limit"
                    logger.warning(f"[{provider}] Rate limited: {e.retry_after}s → Switching provider")
                    cloud_failed = True
                    break
                    
                except ServerError as e:
                    provider_errors[provider] = f"server_{e.status_code}"
                    logger.warning(f"[{provider}] Server error {e.status_code}")
                    if attempt < max_attempts - 1:
                        retry_delay = get_provider_delay(provider, delay_seconds)
                        logger.info(f"[{provider}] Waiting {retry_delay}s before retry...")
                        await asyncio.sleep(retry_delay)
                        continue
                    logger.warning(f"[{provider}] Failed after {max_attempts} attempts → Switching provider")
                    cloud_failed = True
                    break
                    
                except LLMError as e:
                    logger.warning(f"[{provider}] Attempt {attempt+1}/{max_attempts}: {e.error_type} - {e}")
                    if is_rate_limit_error(e):
                        logger.warning(f"[{provider}] Rate limit detected → Switching provider immediately (no retry)")
                        provider_errors[provider] = "rate_limit"
                        cloud_failed = True
                        break
                    if attempt < max_attempts - 1:
                        retry_delay = get_provider_delay(provider, delay_seconds)
                        logger.info(f"[{provider}] Waiting {retry_delay}s before retry...")
                        await asyncio.sleep(retry_delay)
                        continue
                    logger.warning(f"[{provider}] Failed after {max_attempts} attempts → Switching provider")
                    provider_errors[provider] = e.error_type
                    cloud_failed = True
                    break
                    
                except Exception as e:
                    logger.warning(f"[{provider}] Attempt {attempt+1}/{max_attempts}: {type(e).__name__} - {e}")
                    if is_rate_limit_error(e):
                        logger.warning(f"[{provider}] Rate limit detected → Switching provider immediately (no retry)")
                        provider_errors[provider] = "rate_limit"
                        cloud_failed = True
                        break
                    if attempt < max_attempts - 1:
                        retry_delay = get_provider_delay(provider, delay_seconds)
                        logger.info(f"[{provider}] Waiting {retry_delay}s before retry...")
                        await asyncio.sleep(retry_delay)
                        continue
                    logger.warning(f"[{provider}] Failed after {max_attempts} attempts → Switching provider")
                    provider_errors[provider] = f"error_{type(e).__name__}"
                    cloud_failed = True
                    break
            
            if cloud_failed:
                continue
        
        if cooldowns and len(cooldowns) == len([p for p in priority if _should_try_provider(p, providers_config)]):
            logger.warning(f"All {len(cooldowns)} available providers in cooldown")
            await wait_for_available_provider(cooldowns)
            continue
        
        real_errors = {k: v for k, v in provider_errors.items() if v not in ["cooldown", "rate_limit"]}
        if real_errors and not cooldowns:
            logger.warning(f"All providers failed with real errors, continuing to next cycle...")
            await asyncio.sleep(2)
            continue
    
    error_details = {
        "error": "All providers failed",
        "cycles": max_cycles,
        "details": provider_errors
    }
    
    logger.error(f"All LLM providers failed after {max_cycles} cycles. Errors: {provider_errors}")
    
    raise LLMError(
        f"All providers failed after {max_cycles} cycles",
        error_type="unknown",
        details=error_details
    )


def _should_try_provider(provider: str, providers_config: Dict[str, Any]) -> bool:
    """Check if provider should be tried based on configuration."""
    config = providers_config.get(provider, {})
    
    if provider == "local":
        return True
    
    return bool(config.get("api_key", "").strip())
