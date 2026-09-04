"""Provider catalog metadata that is not available through discovery APIs."""
from __future__ import annotations

from typing import Any, Dict, List


PROVIDER_ALIASES = {"claude": "anthropic", "local": "ollama"}

DISCOVERY_PROVIDERS = {"gemini", "openrouter", "openai", "anthropic", "groq"}

ANTHROPIC_MODELS: List[Dict[str, Any]] = [
    {
        "model_id": "claude-3-5-sonnet-latest",
        "model_name": "Claude 3.5 Sonnet",
        "context_window": 200000,
        "pricing_input": 0.003,
        "pricing_output": 0.015,
        "supports_large_context": True,
        "supports_reasoning": True,
        "recommended_for": ["continuity", "themes", "character"],
        "tags": ["premium", "reasoning", "large-context"],
    },
    {
        "model_id": "claude-sonnet",
        "model_name": "Claude Sonnet",
        "context_window": 200000,
        "pricing_input": 0.003,
        "pricing_output": 0.015,
        "supports_large_context": True,
        "supports_reasoning": True,
        "recommended_for": ["continuity", "themes", "character"],
        "tags": ["premium", "reasoning", "large-context"],
    },
    {
        "model_id": "claude-opus",
        "model_name": "Claude Opus",
        "context_window": 200000,
        "pricing_input": 0.015,
        "pricing_output": 0.075,
        "supports_large_context": True,
        "supports_reasoning": True,
        "recommended_for": ["drafting", "deep-reasoning"],
        "tags": ["premium", "drafting", "reasoning"],
    },
]

LOCAL_MODELS: List[Dict[str, Any]] = [
    {
        "model_id": "phi3",
        "model_name": "Phi-3 Local",
        "context_window": 4096,
        "pricing_input": 0,
        "pricing_output": 0,
        "free_tier": True,
        "recommended_for": ["local", "testing"],
        "tags": ["free", "local"],
    },
]

MOCK_MODELS: List[Dict[str, Any]] = [
    {
        "model_id": "mock-narrative-intelligence",
        "model_name": "Mock Narrative Intelligence",
        "context_window": 120000,
        "pricing_input": 0,
        "pricing_output": 0,
        "supports_tools": True,
        "supports_large_context": True,
        "free_tier": True,
        "recommended_for": ["testing", "routing"],
        "tags": ["free", "fast"],
    },
]

# Runtime compatibility metadata. Discovery-backed UI and validation never use
# this list as a substitute for a provider discovery result.
RUNTIME_COMPATIBILITY_MODELS: Dict[str, List[Dict[str, Any]]] = {
    "gemini": [
        {
            "model_id": "gemini-3.1-flash-lite",
            "model_name": "Gemini 3.1 Flash-Lite",
            "context_window": 1000000,
            "supports_large_context": True,
            "supports_multimodal": True,
            "recommended_for": ["discussion", "planning", "artifact-generation"],
            "tags": ["fast", "cost-efficient", "large-context"],
        },
        {
            "model_id": "gemini-2.5-flash",
            "model_name": "Gemini 2.5 Flash",
            "context_window": 1000000,
            "pricing_input": 0.0003,
            "pricing_output": 0.0025,
            "supports_large_context": True,
            "supports_multimodal": True,
            "recommended_for": ["brainstorming", "character", "large-context"],
            "tags": ["fast", "large-context"],
        },
        {
            "model_id": "gemini-2.5-pro",
            "model_name": "Gemini 2.5 Pro",
            "context_window": 1000000,
            "pricing_input": 0.00125,
            "pricing_output": 0.01,
            "supports_large_context": True,
            "supports_reasoning": True,
            "supports_multimodal": True,
            "recommended_for": ["architect", "continuity"],
            "tags": ["reasoning", "large-context"],
        },
        {
            "model_id": "gemini-2.0-flash",
            "model_name": "Gemini 2.0 Flash",
            "context_window": 1000000,
            "pricing_input": 0.0001,
            "pricing_output": 0.0004,
            "supports_large_context": True,
            "supports_multimodal": True,
            "recommended_for": ["fast", "brainstorming"],
            "tags": ["fast", "large-context"],
        },
    ],
    "openrouter": [
        {
            "model_id": "deepseek/deepseek-v4-flash",
            "model_name": "DeepSeek V4 Flash",
            "context_window": 1048576,
            "pricing_input": 0.00014,
            "pricing_output": 0.00028,
            "supports_large_context": True,
            "supports_reasoning": True,
            "supports_tools": True,
            "recommended_for": ["planning", "continuity", "large-context", "drafting"],
            "tags": ["fast", "reasoning", "large-context"],
        },
        {
            "model_id": "google/gemma-3-27b-it:free",
            "model_name": "Gemma 3 27B Free",
            "context_window": 96000,
            "pricing_input": 0,
            "pricing_output": 0,
            "free_tier": True,
            "recommended_for": ["brainstorming", "cheap"],
            "tags": ["free", "drafting"],
        },
        {
            "model_id": "qwen/qwen-2.5-72b-instruct:free",
            "model_name": "Qwen 2.5 72B Free",
            "context_window": 32000,
            "pricing_input": 0,
            "pricing_output": 0,
            "free_tier": True,
            "supports_reasoning": True,
            "recommended_for": ["critic", "reasoning"],
            "tags": ["free", "reasoning"],
        },
        {
            "model_id": "deepseek/deepseek-chat-v3-0324:free",
            "model_name": "DeepSeek Chat V3 Free",
            "context_window": 64000,
            "pricing_input": 0,
            "pricing_output": 0,
            "free_tier": True,
            "supports_reasoning": True,
            "recommended_for": ["critic", "continuity"],
            "tags": ["free", "reasoning"],
        },
        {
            "model_id": "anthropic/claude-3.5-sonnet",
            "model_name": "Claude 3.5 Sonnet",
            "context_window": 200000,
            "supports_large_context": True,
            "supports_reasoning": True,
            "recommended_for": ["continuity", "themes"],
            "tags": ["premium", "reasoning", "large-context"],
        },
    ],
    "groq": [
        {
            "model_id": "llama-3.1-8b-instant",
            "model_name": "Llama 3.1 8B Instant",
            "context_window": 131000,
            "pricing_input": 0.00005,
            "pricing_output": 0.00008,
            "recommended_for": ["routing", "fast"],
            "tags": ["fast", "cheap"],
        },
        {
            "model_id": "llama-3.3-70b-versatile",
            "model_name": "Llama 3.3 70B Versatile",
            "context_window": 131000,
            "pricing_input": 0.00059,
            "pricing_output": 0.00079,
            "supports_reasoning": True,
            "recommended_for": ["brainstorming", "critic"],
            "tags": ["fast", "reasoning"],
        },
    ],
    "openai": [
        {
            "model_id": "gpt-4o",
            "model_name": "GPT-4o",
            "context_window": 128000,
            "pricing_input": 0.0025,
            "pricing_output": 0.01,
            "supports_tools": True,
            "supports_reasoning": True,
            "supports_multimodal": True,
            "recommended_for": ["drafting", "editor"],
            "tags": ["premium", "drafting"],
        },
        {
            "model_id": "gpt-4",
            "model_name": "GPT-4",
            "context_window": 8192,
            "pricing_input": 0.03,
            "pricing_output": 0.06,
            "supports_tools": True,
            "supports_reasoning": True,
            "recommended_for": ["drafting"],
            "tags": ["premium", "reasoning"],
        },
    ],
    "anthropic": ANTHROPIC_MODELS,
    "ollama": LOCAL_MODELS,
    "mock": MOCK_MODELS,
}


def normalize_provider(provider: str) -> str:
    key = (provider or "").strip().lower()
    return PROVIDER_ALIASES.get(key, key)


def configured_models(provider: str) -> List[Dict[str, Any]]:
    return [dict(item) for item in RUNTIME_COMPATIBILITY_MODELS.get(normalize_provider(provider), [])]
