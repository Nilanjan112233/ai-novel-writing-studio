# ai_provider.py
"""
AI Provider Service - Single source of truth for AI settings.
This module ONLY stores settings and tests connections.
NO generation logic - all LLM execution is handled by llm.py
"""
from typing import Optional, Dict, Any
import httpx
import logging
from openai import OpenAI

from app.services.settings_service import settings_service

logger = logging.getLogger(__name__)

# In-memory cache for settings (optional, for performance)
_cached_settings: Optional[Dict[str, Any]] = None


# Provider-specific minimum delays (seconds)
# These are ENFORCED - user cannot set delay lower than these values
PROVIDER_MIN_DELAYS = {
    "gemini": 70,      # Gemini has strict rate limits
    "groq": 70,        # Groq has strict rate limits
    "openrouter": 60,  # OpenRouter recommends 60s between calls
    "huggingface": 5,  # HuggingFace is more lenient
    "local": 0         # Local has no rate limit
}

# Default delay between sequential calls (seconds, not ms)
DEFAULT_DELAY_SECONDS = 5
MAX_DELAY_SECONDS = 500

# Default settings structure - SOURCE OF TRUTH
DEFAULT_SETTINGS = {
    "providers": {
        "gemini": {"api_key": "", "model": ""},
        "groq": {"api_key": "", "model": ""},
        "openrouter": {"api_key": "", "model": ""},
        "huggingface": {"api_key": "", "model": ""},
        "openai": {"api_key": "", "model": ""},
        "anthropic": {"api_key": "", "model": ""},
        "ollama": {"url": "http://localhost:11434/api/generate", "model": "phi3", "enabled": False, "timeout": 900},
        "local": {"url": "http://localhost:11434/api/generate", "model": "phi3", "enabled": False, "timeout": 900}
    },
    "fallback_priority": ["gemini", "groq", "openrouter"],
    "llm_delay_seconds": DEFAULT_DELAY_SECONDS  # Changed from ms to seconds
}


def deep_merge(default: Dict[str, Any], current: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge current settings into defaults."""
    result = {}
    
    # Copy all default values first
    for key, value in default.items():
        if isinstance(value, dict):
            result[key] = dict(value)
        else:
            result[key] = value
    
    # Merge current values, recursively for dicts
    for key, value in current.items():
        if isinstance(value, dict) and key in result and isinstance(result[key], dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    
    return result


def _ensure_all_providers(settings: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure all required providers exist in settings with proper defaults."""
    if "providers" not in settings:
        settings["providers"] = {}
    
    # Ensure cloud providers exist
    for provider in ["gemini", "groq", "openrouter", "huggingface", "openai", "anthropic"]:
        if provider not in settings["providers"]:
            settings["providers"][provider] = {"api_key": "", "model": ""}
    if "claude" in settings["providers"] and "anthropic" not in settings["providers"]:
        settings["providers"]["anthropic"] = settings["providers"].pop("claude")
    
    # Ensure local/Ollama providers exist with full config
    for local_name in ["local", "ollama"]:
        if local_name not in settings["providers"]:
            settings["providers"][local_name] = {
                "url": "http://localhost:11434/api/generate",
                "model": "phi3",
                "enabled": False,
                "timeout": 900
            }
            continue
        # Ensure local has all required fields
        local_config = settings["providers"][local_name]
        if not isinstance(local_config, dict):
            local_config = {}
        local_config.setdefault("url", "http://localhost:11434/api/generate")
        local_config.setdefault("model", "phi3")
        local_config.setdefault("enabled", False)
        local_config.setdefault("timeout", 900)
        settings["providers"][local_name] = local_config
    
    return settings


def _remove_legacy_fields(settings: Dict[str, Any]) -> Dict[str, Any]:
    """Remove legacy fields that should not persist."""
    settings.pop("provider", None)  # Legacy single provider field
    return settings


def _normalize_delay_setting(settings: Dict[str, Any], is_incoming: bool = False) -> Dict[str, Any]:
    """
    Normalize delay setting from old ms format to new seconds format.
    
    Args:
        settings: The settings dict to normalize
        is_incoming: If True, this is incoming settings from user - preserve their values
    """
    # Convert old llm_delay_ms to llm_delay_seconds
    if "llm_delay_ms" in settings:
        old_ms = settings.pop("llm_delay_ms")  # Remove old field
        # Only convert if llm_delay_seconds doesn't already exist (don't override)
        if "llm_delay_seconds" not in settings:
            seconds = min(old_ms / 1000, MAX_DELAY_SECONDS)
            settings["llm_delay_seconds"] = seconds
            logger.warning(f"Converted legacy llm_delay_ms={old_ms} → llm_delay_seconds={seconds}")
    
    # Ensure llm_delay_seconds exists and is within bounds
    delay_seconds = settings.get("llm_delay_seconds", DEFAULT_DELAY_SECONDS)
    delay_seconds = max(0, min(delay_seconds, MAX_DELAY_SECONDS))
    settings["llm_delay_seconds"] = delay_seconds
    
    return settings


def get_provider_delay(provider: str, user_delay_seconds: Optional[float] = None) -> float:
    """
    Get the effective delay for a provider.
    
    NOW: Respects user delay completely (no hardcoded provider minimums).
    Only enforces 0-500 bounds for safety.
    
    Args:
        provider: The provider name (kept for API compatibility)
        user_delay_seconds: User's preferred delay (from settings)
        
    Returns:
        User's configured delay in seconds (bounded 0-500)
    """
    user_delay = user_delay_seconds if user_delay_seconds is not None else DEFAULT_DELAY_SECONDS
    
    # Cap at max/min bounds only
    effective_delay = max(0, min(user_delay, MAX_DELAY_SECONDS))
    
    return effective_delay


def _get_default_settings() -> Dict[str, Any]:
    """Return default settings structure for first run."""
    return dict(DEFAULT_SETTINGS)


async def load_settings_from_db() -> Dict[str, Any]:
    """Load canonical settings from MongoDB and normalize."""
    global _cached_settings
    
    try:
        doc = await settings_service.get_provider_settings()
        normalized = deep_merge(DEFAULT_SETTINGS, _remove_legacy_fields(doc))
        normalized = _normalize_delay_setting(normalized)
        normalized = _ensure_all_providers(normalized)
        _cached_settings = dict(normalized)
        return normalized
            
    except Exception as e:
        logger.error(f"Failed to load settings from DB: {e}")
        return dict(DEFAULT_SETTINGS)


async def save_settings_to_db(settings: Dict[str, Any]) -> bool:
    """Save settings to canonical MongoDB document with read-after-write verification."""
    global _cached_settings
    
    try:
        settings = _normalize_delay_setting(dict(settings), is_incoming=True)
        settings = _ensure_all_providers(_remove_legacy_fields(settings))
        local_config = settings.get("providers", {}).get("local", {})
        if local_config.get("enabled"):
            url = local_config.get("url", "")
            if not url.startswith("http"):
                raise ValueError("Local URL must start with http")
            if "/api/generate" not in url:
                raise ValueError("Local URL must include /api/generate")
        saved = await settings_service.save_provider_settings(settings)
        _cached_settings = dict(saved)
        return True
            
    except Exception as e:
        logger.error(f"Failed to save settings to DB: {e}")
        return False


def get_settings_sync() -> Dict[str, Any]:
    """Synchronous version - returns cached or defaults."""
    if _cached_settings:
        return dict(_cached_settings)
    return dict(DEFAULT_SETTINGS)


class AIProviderService:
    """
    Service for managing AI provider settings and testing connections.
    Does NOT execute LLM calls - use llm.py for that.
    """
    
    def __init__(self):
        # No in-memory storage - all persistence in DB
        pass
    
    async def update_settings(self, provider_settings: Dict[str, Any]) -> bool:
        """Update AI provider settings in DB."""
        return await save_settings_to_db(provider_settings)
    
    async def get_settings(self) -> Dict[str, Any]:
        """
        Get current AI provider settings from DB.
        Returns default structure if no settings stored.
        """
        return await load_settings_from_db()
    
    def get_settings_sync(self) -> Dict[str, Any]:
        """Synchronous version for non-async contexts."""
        return get_settings_sync()
    
    async def test_connection(self, provider_type: Optional[str] = None, settings_override: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Test API connection for a provider.
        Supports: gemini, groq, openrouter, huggingface.
        
        Args:
            provider_type: The provider to test
            settings_override: Optional settings from UI (not yet saved to DB)
        """
        try:
            provider_type = (provider_type or "").lower().strip()
            
            if not provider_type:
                return {"success": False, "error": "No provider specified"}
            
            # Use override settings if provided (from UI), otherwise use DB
            if settings_override:
                logger.info(f"Test connection using override settings for {provider_type}")
                settings = settings_override
                
                # Validate override has required structure
                if "providers" not in settings:
                    return {"success": False, "error": "Invalid test settings: missing providers"}
            else:
                logger.info(f"Test connection using DB settings for {provider_type}")
                settings = await self.get_settings()
            
            provider_config = settings.get("providers", {}).get(provider_type, {})
            api_key = provider_config.get("api_key", "")
            model = provider_config.get("model", "")
            
            if not api_key:
                return {"success": False, "error": f"{provider_type} API key not configured"}
            
            if not model:
                return {"success": False, "error": f"{provider_type} model not configured"}
            
            if provider_type == "gemini":
                return await self._test_gemini(api_key)
            elif provider_type == "groq":
                return await self._test_groq(api_key)
            elif provider_type == "openrouter":
                return await self._test_openrouter(api_key)
            elif provider_type == "huggingface":
                return await self._test_huggingface(api_key)
            elif provider_type == "local":
                return await self._test_local(provider_config)
            else:
                return {"success": False, "error": f"Unknown provider: {provider_type}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _test_gemini(self, api_key: str) -> Dict[str, Any]:
        """Test Gemini API connection."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://generativelanguage.googleapis.com/v1/models",
                headers={"x-goog-api-key": api_key},
                timeout=10.0
            )
            if response.status_code == 200:
                return {"success": True}
            return {"success": False, "error": f"HTTP {response.status_code}"}
    
    async def _test_groq(self, api_key: str) -> Dict[str, Any]:
        """Test Groq API connection."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10.0
            )
            if response.status_code == 200:
                return {"success": True}
            return {"success": False, "error": f"HTTP {response.status_code}"}
    
    async def _test_openrouter(self, api_key: str) -> Dict[str, Any]:
        """Test OpenRouter API connection."""
        try:
            client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=api_key,
            )
            response = client.chat.completions.create(
                model="openrouter/free",
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=10
            )
            return {"success": True, "model": response.model}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _test_huggingface(self, api_key: str) -> Dict[str, Any]:
        """Test HuggingFace API connection."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://huggingface.co/api/whoami",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10.0
            )
            if response.status_code == 200:
                return {"success": True}
            return {"success": False, "error": f"HTTP {response.status_code}"}
    
    async def _test_local(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Test local Ollama connection via /api/generate."""
        url = config.get("url", "")
        model = config.get("model", "")
        enabled = config.get("enabled", False)
        
        if not enabled:
            return {"success": False, "error": "Local provider is not enabled"}
        
        if not url or not url.startswith("http"):
            return {"success": False, "error": "Invalid local URL configured"}
        
        if not model:
            return {"success": False, "error": "Local model not configured"}
        
        # Validate URL includes /api/generate
        if "/api/generate" not in url:
            return {"success": False, "error": "Local URL must include /api/generate"}
        
        # Test by calling /api/generate with a simple prompt
        payload = {
            "model": model,
            "prompt": "test",
            "stream": False
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=10.0)
                
                if response.status_code == 200:
                    data = response.json()
                    if "response" in data:
                        return {"success": True, "model": model}
                    else:
                        return {"success": False, "error": "Invalid response format from Ollama"}
                elif response.status_code == 404:
                    return {"success": False, "error": f"Model '{model}' not found. Run: ollama pull {model}"}
                else:
                    return {"success": False, "error": f"Ollama returned HTTP {response.status_code}"}
                    
        except httpx.ConnectError:
            return {"success": False, "error": "Cannot connect to Ollama. Is it running?"}
        except httpx.TimeoutException:
            return {"success": False, "error": "Connection timeout"}
        except Exception as e:
            return {"success": False, "error": f"Connection failed: {str(e)}"}


# Global instance
ai_provider = AIProviderService()
