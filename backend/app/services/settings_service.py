"""Canonical application settings persistence.

This service owns the singleton settings document used by the backend,
provider runtime, and frontend settings page.
"""
from __future__ import annotations

import copy
import logging
from datetime import datetime
from typing import Any, Dict, List

from app.core.database import Database
from app.core.config import settings as app_config
from app.services.secret_encryption_service import secret_encryption_service

logger = logging.getLogger(__name__)

SETTINGS_COLLECTION = "app_settings"
SETTINGS_ID = "global_settings"

DEFAULT_PROVIDER_SETTINGS: Dict[str, Any] = {
    "providers": {
        "gemini": {"api_key_encrypted": "", "configured": False, "model": ""},
        "groq": {"api_key_encrypted": "", "configured": False, "model": ""},
        "openrouter": {"api_key_encrypted": "", "configured": False, "model": ""},
        "huggingface": {"api_key_encrypted": "", "configured": False, "model": ""},
        "openai": {"api_key_encrypted": "", "configured": False, "model": ""},
        "anthropic": {"api_key_encrypted": "", "configured": False, "model": ""},
        "ollama": {"url": "http://localhost:11434/api/generate", "model": "phi3", "enabled": False, "timeout": 900},
        "local": {"url": "http://localhost:11434/api/generate", "model": "phi3", "enabled": False, "timeout": 900},
    },
    "fallback_priority": ["gemini", "groq", "openrouter"],
    "llm_delay_seconds": 5,
}

# Memory providers are an experimental retrieval/observation boundary.  The
# default deliberately remains native; Tencent is never enabled implicitly.
DEFAULT_MEMORY_SETTINGS: Dict[str, Any] = {
    "mode": "native",
    "endpoint": "http://127.0.0.1:8420",
    "api_key_encrypted": "",
    "configured": False,
    "service_id": "default",
    "team_id": "default",
    "agent_id": "novelforge",
    "user_id": "default",
    "timeout_ms": 3000,
}

DEFAULT_EXECUTION_SETTINGS: Dict[str, Any] = {
    "execution_mode": "full",
    "default_provider": "gemini",
    "default_model": "",
    "enable_streaming": True,
    "enable_reflection_loops": True,
    "enable_dynamic_routing": True,
    "max_context_tokens": 120000,
    "max_cycle_cost_usd": 2.0,
    "max_agent_calls_per_cycle": 10,
    "max_orchestration_depth": 5,
    "provider_requests_per_minute": 5,
    "max_reflection_loops": 2,
}

AGENT_NAMES = [
    "NarrativeDirectorAgent",
    "StoryArchitectAgent",
    "CharacterJourneyAgent",
    "WorldAgent",
    "PowerSystemAgent",
    "FactionAgent",
    "RelationshipAgent",
    "ThemeAgent",
    "MysteryAgent",
    "ArcArchitectAgent",
    "PacingAgent",
    "QuestionAgent",
    "ReadinessAgent",
    "KnowledgeAgent",
    "StoryDevelopmentAgent",
    "ScenePlannerAgent",
    "SceneWriterAgent",
    "ChapterAssemblerAgent",
    "EditorAgent",
    "DialogueAgent",
    "RevisionAgent",
    "ManuscriptAgent",
    "CanonAgent",
    "StoryAuditorAgent",
]

DEFAULT_ASSIGNMENTS: List[Dict[str, Any]] = [
    {
        "agent_name": name,
        "provider": "gemini",
        "model": "",
        "temperature": 0.7,
        "max_tokens": 4096,
        "enabled": True,
        "use_mock_in_hybrid": False,
    }
    for name in AGENT_NAMES
]


def _deep_merge(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in (patch or {}).items():
        if key == "_id":
            continue
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _redact(settings: Dict[str, Any]) -> Dict[str, Any]:
    redacted = copy.deepcopy(settings)
    for config in redacted.get("providers", {}).values():
        if isinstance(config, dict) and config.get("api_key"):
            config["api_key"] = "***redacted***"
        if isinstance(config, dict) and config.get("api_key_encrypted"):
            config["api_key_encrypted"] = "***encrypted***"
    return redacted


def default_app_settings() -> Dict[str, Any]:
    return {
        **copy.deepcopy(DEFAULT_PROVIDER_SETTINGS),
        "memory": copy.deepcopy(DEFAULT_MEMORY_SETTINGS),
        "execution": copy.deepcopy(DEFAULT_EXECUTION_SETTINGS),
        "agent_assignments": copy.deepcopy(DEFAULT_ASSIGNMENTS),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }


class SettingsService:
    async def _collection(self):
        db = Database.get_db()
        return db[SETTINGS_COLLECTION]

    async def _legacy_payload(self) -> Dict[str, Any]:
        """Best-effort migration from pre-canonical settings collections."""
        db = Database.get_db()
        payload: Dict[str, Any] = {}

        legacy_providers = await db.api_settings.find_one({"_id": SETTINGS_ID})
        if legacy_providers:
            legacy_providers.pop("_id", None)
            payload = _deep_merge(payload, legacy_providers)

        legacy_execution = await db.ai_execution_settings.find_one({"_id": "global"})
        if legacy_execution:
            legacy_execution.pop("_id", None)
            payload["execution"] = legacy_execution

        assignments = await db.agent_model_assignments.find().to_list(length=100)
        if assignments:
            payload["agent_assignments"] = [
                {k: v for k, v in item.items() if k != "_id"}
                for item in assignments
            ]
        return payload

    async def get_app_settings(self) -> Dict[str, Any]:
        collection = await self._collection()
        doc = await collection.find_one({"_id": SETTINGS_ID})
        if not doc:
            migrated = await self._legacy_payload()
            doc = _deep_merge(default_app_settings(), migrated)
            doc["providers"] = secret_encryption_service.prepare_provider_storage(
                doc.get("providers") or {}
            )
            doc["_id"] = SETTINGS_ID
            now = datetime.utcnow()
            doc["created_at"] = doc.get("created_at") or now
            doc["updated_at"] = now
            await collection.update_one({"_id": SETTINGS_ID}, {"$set": doc}, upsert=True)
            logger.info("[settings] Saved global settings successfully")
        doc.pop("_id", None)
        normalized = _deep_merge(default_app_settings(), doc)
        normalized["providers"] = secret_encryption_service.prepare_provider_storage(
            normalized.get("providers") or {},
            doc.get("providers") or {},
        )
        if normalized["providers"] != doc.get("providers"):
            await collection.update_one(
                {"_id": SETTINGS_ID},
                {"$set": {"providers": normalized["providers"]}},
            )
        logger.info("[settings] Loaded global settings successfully")
        return normalized

    async def save_app_settings(self, patch: Dict[str, Any]) -> Dict[str, Any]:
        collection = await self._collection()
        current = await self.get_app_settings()
        merged = _deep_merge(current, patch or {})
        merged["updated_at"] = datetime.utcnow()
        doc = copy.deepcopy(merged)
        doc["_id"] = SETTINGS_ID
        result = await collection.update_one({"_id": SETTINGS_ID}, {"$set": doc}, upsert=True)
        if not result.acknowledged:
            raise RuntimeError("settings update was not acknowledged")

        reread = await collection.find_one({"_id": SETTINGS_ID})
        if not reread:
            raise RuntimeError("settings save verification failed: document missing after save")
        comparable = copy.deepcopy(reread)
        comparable.pop("_id", None)
        if comparable.get("providers") != merged.get("providers"):
            logger.error("[settings] Save verification mismatch: %s", _redact(comparable))
            raise RuntimeError("settings save verification failed: providers mismatch")

        logger.info("[settings] Saved global settings successfully")
        return _deep_merge(default_app_settings(), comparable)

    async def get_provider_settings(self) -> Dict[str, Any]:
        settings = await self.get_app_settings()
        providers = secret_encryption_service.runtime_providers(
            settings.get("providers", {})
        )
        if not app_config.use_mock_llm:
            providers.pop("mock", None)
        return {
            "providers": providers,
            "fallback_priority": settings.get("fallback_priority", []),
            "llm_delay_seconds": settings.get("llm_delay_seconds", 5),
            "memory": self._public_memory(settings.get("memory") or {}),
        }

    async def get_public_provider_settings(self) -> Dict[str, Any]:
        settings = await self.get_app_settings()
        providers = secret_encryption_service.public_providers(
            settings.get("providers", {})
        )
        if not app_config.use_mock_llm:
            providers.pop("mock", None)
        return {
            "providers": providers,
            "fallback_priority": settings.get("fallback_priority", []),
            "llm_delay_seconds": settings.get("llm_delay_seconds", 5),
            "memory": self._public_memory(settings.get("memory") or {}),
        }

    @staticmethod
    def _public_memory(memory: Dict[str, Any]) -> Dict[str, Any]:
        public = copy.deepcopy(DEFAULT_MEMORY_SETTINGS)
        public.update({key: value for key, value in (memory or {}).items() if key != "api_key_encrypted"})
        public.pop("api_key", None)
        public.pop("api_key_encrypted", None)
        public["configured"] = bool((memory or {}).get("api_key_encrypted") or (memory or {}).get("configured"))
        return public

    async def get_memory_settings(self, *, runtime: bool = False) -> Dict[str, Any]:
        current = await self.get_app_settings()
        memory = _deep_merge(DEFAULT_MEMORY_SETTINGS, current.get("memory") or {})
        if runtime:
            encrypted = str(memory.pop("api_key_encrypted", "") or "")
            memory["api_key"] = secret_encryption_service.decrypt(encrypted) if encrypted else ""
            memory["configured"] = bool(encrypted)
        else:
            memory = self._public_memory(memory)
        return memory

    async def save_memory_settings(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        current = await self.get_app_settings()
        prior = _deep_merge(DEFAULT_MEMORY_SETTINGS, current.get("memory") or {})
        allowed = {"mode", "endpoint", "service_id", "team_id", "agent_id", "user_id", "timeout_ms"}
        next_memory = {key: payload[key] for key in allowed if key in payload}
        mode = str(next_memory.get("mode") or prior.get("mode") or "native").lower()
        if mode not in {"native", "tencent", "hybrid", "benchmark"}:
            raise ValueError("memory mode must be native, tencent, hybrid, or benchmark")
        next_memory["mode"] = mode
        next_memory["endpoint"] = str(next_memory.get("endpoint") or prior.get("endpoint") or "").rstrip("/")
        next_memory["timeout_ms"] = max(250, min(int(next_memory.get("timeout_ms") or prior.get("timeout_ms") or 3000), 30000))
        supplied_key = str(payload.get("api_key") or "")
        clear_key = bool(payload.get("clear_api_key"))
        if clear_key:
            encrypted = ""
        elif supplied_key and supplied_key != "***redacted***":
            encrypted = secret_encryption_service.encrypt(supplied_key)
        else:
            encrypted = str(prior.get("api_key_encrypted") or "")
        next_memory["api_key_encrypted"] = encrypted
        next_memory["configured"] = bool(encrypted)
        saved = await self.save_app_settings({"memory": next_memory})
        return self._public_memory(saved.get("memory") or next_memory)

    async def save_provider_settings(self, provider_settings: Dict[str, Any]) -> Dict[str, Any]:
        provider_settings = copy.deepcopy(provider_settings)
        if not app_config.use_mock_llm:
            provider_settings.get("providers", {}).pop("mock", None)
        current = await self.get_app_settings()
        provider_settings["providers"] = (
            secret_encryption_service.prepare_provider_storage(
                provider_settings.get("providers") or {},
                current.get("providers") or {},
            )
        )
        settings = await self.save_app_settings(provider_settings)
        providers = secret_encryption_service.runtime_providers(
            settings.get("providers", {})
        )
        if not app_config.use_mock_llm:
            providers.pop("mock", None)
        return {
            "providers": providers,
            "fallback_priority": settings.get("fallback_priority", []),
            "llm_delay_seconds": settings.get("llm_delay_seconds", 5),
        }

    async def get_execution_settings(self) -> Dict[str, Any]:
        settings = await self.get_app_settings()
        execution = _deep_merge(DEFAULT_EXECUTION_SETTINGS, settings.get("execution", {}))
        if not app_config.use_mock_llm and (
            execution.get("default_provider") == "mock"
            or execution.get("default_model") == "mock-narrative-intelligence"
        ):
            db = Database.get_db()
            verified = await db.provider_model_health.find_one(
                {"success": True, "provider": {"$ne": "mock"}},
                sort=[("latency", 1)],
            )
            execution.update({
                "execution_mode": "full",
                "default_provider": verified.get("provider") if verified else "gemini",
                "default_model": verified.get("model") if verified else "",
            })
            await self.save_app_settings({"execution": execution})
        return execution

    async def save_execution_settings(self, execution: Dict[str, Any]) -> Dict[str, Any]:
        if not app_config.use_mock_llm and (
            execution.get("execution_mode") == "mock"
            or execution.get("default_provider") == "mock"
            or execution.get("default_model") == "mock-narrative-intelligence"
        ):
            raise ValueError("Mock AI execution is disabled")
        requests_per_minute = int(
            execution.get(
                "provider_requests_per_minute",
                DEFAULT_EXECUTION_SETTINGS["provider_requests_per_minute"],
            )
        )
        if not 5 <= requests_per_minute <= 10:
            raise ValueError("provider_requests_per_minute must be between 5 and 10")
        max_calls = int(
            execution.get(
                "max_agent_calls_per_cycle",
                DEFAULT_EXECUTION_SETTINGS["max_agent_calls_per_cycle"],
            )
        )
        if not 0 <= max_calls <= 10:
            raise ValueError("max_agent_calls_per_cycle must be between 0 and 10")
        max_depth = int(
            execution.get(
                "max_orchestration_depth",
                DEFAULT_EXECUTION_SETTINGS["max_orchestration_depth"],
            )
        )
        if not 0 <= max_depth <= 5:
            raise ValueError("max_orchestration_depth must be between 0 and 5")
        if float(execution.get("max_cycle_cost_usd", 0)) < 0:
            raise ValueError("max_cycle_cost_usd cannot be negative")
        settings = await self.save_app_settings({"execution": execution})
        return _deep_merge(DEFAULT_EXECUTION_SETTINGS, settings.get("execution", {}))

    async def get_agent_assignments(self) -> List[Dict[str, Any]]:
        settings = await self.get_app_settings()
        by_name = {item.get("agent_name"): item for item in settings.get("agent_assignments", [])}
        assignments = [
            _deep_merge(default, by_name.get(default["agent_name"], {}))
            for default in DEFAULT_ASSIGNMENTS
        ]
        execution = _deep_merge(
            DEFAULT_EXECUTION_SETTINGS, settings.get("execution", {})
        )
        for assignment in assignments:
            if not assignment.get("provider"):
                assignment["provider"] = execution.get("default_provider", "gemini")
            if not assignment.get("model"):
                assignment["provider"] = execution.get(
                    "default_provider", assignment.get("provider") or "gemini"
                )
                assignment["model"] = execution.get("default_model", "")
        if not app_config.use_mock_llm:
            for assignment in assignments:
                if assignment.get("provider") == "mock" or assignment.get("model") == "mock-narrative-intelligence":
                    assignment["provider"] = "gemini"
                    assignment["model"] = ""
                    assignment["use_mock_in_hybrid"] = False
        return assignments

    async def save_agent_assignments(self, assignments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not app_config.use_mock_llm and any(
            item.get("provider") == "mock" or item.get("model") == "mock-narrative-intelligence"
            for item in assignments
        ):
            raise ValueError("Mock agent assignments are disabled")
        by_name = {item.get("agent_name"): item for item in await self.get_agent_assignments()}
        for item in assignments:
            if item.get("agent_name"):
                by_name[item["agent_name"]] = _deep_merge(by_name.get(item["agent_name"], {}), item)
        ordered = [
            _deep_merge(default, by_name.get(default["agent_name"], {}))
            for default in DEFAULT_ASSIGNMENTS
        ]
        await self.save_app_settings({"agent_assignments": ordered})
        return ordered


settings_service = SettingsService()
