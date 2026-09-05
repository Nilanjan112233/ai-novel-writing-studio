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
            "memory": self._puÛ7ÖÚ$z{-®éÜj×€€€É”¹%9=IM°(€€€€€€€€€€€€€€€€€€€€¤(€€€€€€€€€€€€€€€€€€€™¥ÉÍÑ}Á•ÉÍ½¹}±•…¬€ô…ÑÕ…±}Á•ÉÍ½¸€ôô€‰™¥ÉÍÐÁ•ÉÍ½¸ˆ(€€€€€€€€€€€€€€€€€€€¥˜€¡­¹½Ý±•‘•}Ù•Éˆ½È™¥ÉÍÑ}Á•ÉÍ½¹}±•…¬¤…¹¹½Ð}•áÁ±¥¥Ñ±å}Á±…¹¹•‘}¡…¹”¡‘É…™Ð°€‰±•…É¸ˆ°Ñ¥Ñ±”¹±½Ý•È ¤¤è(€€€€€€€€€€€€€€€€€€€€€€€…‘‘}™¥¹‘¥¹œ (€€€€€€€€€€€€€€€€€€€€€€€€€€€€‰¡…É…Ñ•É}­¹½Ý±•‘•}±•…­…”ˆ°(€€€€€€€€€€€€€€€€€€€€€€€€€€€˜‰Q¡”‘É…™ÐÁÉ•Í•¹ÑÌíÑ¥Ñ±”½È€É•ÍÑÉ¥Ñ•¥¹™½Éµ…Ñ¥½¸ô…Ì­¹½Ý¸‰äíÁ½Ù}¡…É…Ñ•Éô‰•™½É”Ñ¡”­¹½Ý±•‘”±•‘•ÈÁ•Éµ¥ÑÌ¥Ð¸ˆ°(€€€€€€€€€€€€€€€€€€€€€€€€€€€Ù¥½±…Ñ¥½¹}­•äô‰µ¥ÍÍ¥¹}­¹½Ý±•‘”ˆ°(€€€€€€€€€€€€€€€€€€€€€€€€€€€•Ù¥‘•¹”õì(€€€€€€€€€€€€€€€€€€€€€€€€€€€€€€€€‰•¹ÑÉå}¥ˆè­¹½Ý±•‘”¹•Ð ‰•¹ÑÉå}¥ˆ¤°(€€€€€€€€€€€€€€€€€€€€€€€€€€€€€€€€‰­¹½Ý¹}‰äˆèÍ½ÉÑ•¡­¹½Ý¹}‰ä¤°(€€€€€€€€€€€€€€€€€€€€€€€€€€€€€€€€‰¹½Ñ}­¹½Ý¹}‰äˆèÍ½ÉÑ•¡¹½Ñ}­¹½Ý¹}‰ä¤°(€€€€€€€€€€€€€€€€€€€€€€€€€€€ô°(€€€€€€€€€€€€€€€€€€€€€€€€¤(€€€€€€€€€€€É•ÑÕÉ¸…Ý…¥ÐÍ•±˜¹}É•Á½ÉÐ (€€€€€€€€€€€€€€€‘ˆ°ÁÉ½©•Ñ}¥õÁÉ½©•Ñ}¥°…É}¥ôˆˆ°¡…ÁÑ•É}Á±…¹}¥ôˆˆ°Í•¹•}¥õ9½¹”°(€€€€€€€€€€€€€€€ÍÕ‰©•Ñ}ÑåÁ”ô‰¡…ÁÑ•É}‘É…™Ðˆ°ÍÕ‰©•Ñ}¥õÍÑÈ¡‘É…™Ð¹•Ð ‰‘É…™Ñ}¥ˆ¤½È€ˆˆ¤°(€€€€€€€€€€€€€€€Ù•ÉÍ¥½¹}¹Õµ‰•Èõ¥¹Ð¡‘É…™Ð¹•Ð ‰Ù•ÉÍ¥½¹}¹Õµ‰•Èˆ¤½È€Ä¤°ÍÑ…”õÍÑ…”°(€€€€€€€€€€€€€€€Ù¥½±…Ñ¥½¹ÌõÙ¥½±…Ñ¥½¹Ì°Ý…É¹¥¹ÌõÝ…É¹¥¹Ì°™¥¹‘¥¹Ìõ™¥¹‘¥¹Ì°(€€€€€€€€€€€€€€€•Ù¥‘•¹”õl‰Ý½É­™±½Ý}µ½‘”õ‘¥Í½Ù•Éäˆ°˜‰Ý½É‘}½Õ¹Ðõí½Õ¹Ñô‰t°Á•ÉÍ¥ÍÐõÁ•ÉÍ¥ÍÐ°(€€€€€€€€€€€€¤(€€€€€€€¡…ÁÑ•È€ô…Ý…¥Ð‘ˆ¹¡…ÁÑ•É}Á±…¹Ì¹™¥¹‘}½¹” (€€€€€€€€€€€ì(€€€€€€€€€€€€€€€€‰ÁÉ½©•Ñ}¥ˆèÁ¥°(€€€€€€€€€€€€€€€€‰¡…ÁÑ•É}Á±…¹}¥ˆè‘É…™Ð¹•Ð ‰¡…ÁÑ•É}Á±…¹}¥ˆ¤°(€€€€€€€€€€€ô(€€€€€€€€¤(€€€€€€€Ù¥½±…Ñ¥½¹Ìè¥ÑmÍÑÈ°±¥ÍÑmÍÑÉut€ôì(€€€€€€€€€€€€‰µ¥ÍÍ¥¹}­¹½Ý±•‘”ˆèmt°(€€€€€€€€€€€€‰½¹ÑÉ…‘¥Ñ¥½¹Ìˆèmt°(€€€€€€€€€€€€‰…ÉÑ¥™…Ñ}Ù¥½±…Ñ¥½¹Ìˆèmt°(€€€€€€€€€€€€‰Ñ¥µ•±¥¹•}Ù¥½±…Ñ¥½¹Ìˆèmt°(€€€€€€€€€€€€‰¡…É…Ñ•É}Ù¥½±…Ñ¥½¹Ìˆèmt°(€€€€€€€€€€€€‰Á½Ý•É}Ù¥½±…Ñ¥½¹Ìˆèmt°(€€€€€€€€€€€€‰‘•Á•¹‘•¹å}Ù¥½±…Ñ¥½¹Ìˆèmt°(€€€€€€€€€€€€‰™½É•Í¡…‘½Ý}Ù¥½±…Ñ¥½¹Ìˆèmt°(€€€€€€€€€€€€‰¡…ÁÑ•É}µ•µ‰•ÉÍ¡¥Á}Ù¥½±…Ñ¥½¹Ìˆèmt°(€€€€€€€€€€€€‰Í•¹•}½É‘•É¥¹}Ù¥½±…Ñ¥½¹Ìˆèmt°(€€€€€€€ô(€€€€€€€¥˜¹½Ð¡…ÁÑ•Èè(€€€€€€€€€€€Ù¥½±…Ñ¥½¹Íl‰¡…ÁÑ•É}µ•µ‰•ÉÍ¡¥Á}Ù¥½±…Ñ¥½¹Ì‰t¹…ÁÁ•¹ (€€€€€€€€€€€€€€€€‰¡…ÁÑ•ÈÁ±…¸¹½Ð™½Õ¹ˆ(€€€€€€€€€€€€¤(€€€€€€€€€€€Í•¹•Ì€ômt(€€€€€€€•±Í”è(€€€€€€€€€€€¥˜ÍÑÈ¡¡…ÁÑ•È¹•Ð ‰ÍÑ…ÑÕÌˆ¤½È€ˆˆ¤¹±½Ý•È ¤€„ô€‰…ÁÁÉ½Ù•ˆè(€€€€€€€€€€€€€€€Ù¥½±…Ñ¥½¹Íl‰¡…ÁÑ•É}µ•µ‰•ÉÍ¡¥Á}Ù¥½±…Ñ¥½¹Ì‰t¹…ÁÁ•¹ (€€€€€€€€€€€€€€€€€€€€‰¡…ÁÑ•ÈÁ±…¸¥Ì¹½Ð…ÁÁÉ½Ù•ˆ(€€€€€€€€€€€€€€€€¤(€€€€€€€€€€€‘•Ù•±½Áµ•¹Ð€ô…Ý…¥Ð…É}‘•Ù•±½Áµ•¹Ñ}Í•ÉÙ¥”¹•Ù…±Õ…Ñ” (€€€€€€€€€€€€€€€‘ˆ°ÁÉ½©•Ñ}¥°ÍÑÈ¡¡…ÁÑ•È¹•Ð ‰…É}¥ˆ¤½È€ˆˆ¤°Á•ÉÍ¥ÍÐõ…±Í”(€€€€€€€€€€€€¤(€€€€€€€€€€€¥˜¹½Ð‘•Ù•±½Áµ•¹Ñl‰‘É…™Ñ…‰±”‰tè(€€€€€€€€€€€€€€€Ù¥½±…Ñ¥½¹Íl‰‘•Á•¹‘•¹å}Ù¥½±…Ñ¥½¹Ì‰t¹•áÑ•¹ (€€€€€€€€€€€€€€€€€€€‘•Ù•±½Áµ•¹Ð¹•Ð ‰‰±½­•ÉÌˆ¤½Èl‰ÉŒ¥Ì¹½Ð‘É…™Ñ…‰±”‰t(€€€€€€€€€€€€€€€€¤(€€€€€€€€€€€Í•¹•Ì€ô…Ý…¥Ð‘ˆ¹Í•¹•}Á±…¹Ì¹™¥¹ (€€€€€€€€€€€€€€€ì(€€€€€€€€€€€€€€€€€€€€‰ÁÉ½©•Ñ}¥ˆèÁ¥°(€€€€€€€€€€€€€€€€€€€€‰¡…ÁÑ•É}Á±…¹}¥ˆè¡…ÁÑ•È¹•Ð ‰¡…ÁÑ•É}Á±…¹}¥ˆ¤°(€€€€€€€€€€€€€€€ô(€€€€€€€€€€€€¤¹Í½ÉÐ ‰½É‘•Èˆ°€Ä¤¹Ñ½}±¥ÍÐ¡±•¹Ñ ôÄÀÀÀ¤(€€€€€€€•áÁ•Ñ•‘}Í•¹•}¥‘Ì€ômÍ•¹•l‰Í•¹•}¥‰t™½ÈÍ•¹”¥¸Í•¹•Ít(€€€€€€€Í½ÕÉ•}¥‘Ì€ô}¥‘Ì¡‘É…™Ð¹•Ð ‰Í½ÕÉ•}Í•¹•}‘É…™Ñ}¥‘Ìˆ¤¤(€€€€€€€Í½ÕÉ•}‘É…™ÑÌ€ômt(€€€€€€€™½ÈÍ½ÕÉ•}¥¥¸Í½ÕÉ•}¥‘Ìè(€€€€€€€€€€€Í½ÕÉ”€ô…Ý…¥Ð‘ˆ¹Í•¹•}‘É…™ÑÌ¹™¥¹‘}½¹” (€€€€€€€€€€€€€€€ì‰ÁÉ½©•Ñ}¥ˆèÁ¥°€‰‘É…™Ñ}¥ˆèÍ½ÕÉ•}¥‘ô(€€€€€€€€€€€€¤(€€€€€€€€€€€¥˜¹½ÐÍ½ÕÉ”è(€€€€€€€€€€€€€€€Ù¥½±…Ñ¥½¹Íl‰¡…ÁÑ•É}µ•µ‰•ÉÍ¡¥Á}Ù¥½±…Ñ¥½¹Ì‰t¹…ÁÁ•¹ (€€€€€€€€€€€€€€€€€€€˜‰U¹­¹½Ý¸Í•¹”‘É…™ÐíÍ½ÕÉ•}¥‘ôˆ(€€€€€€€€€€€€€€€€¤(€€€€€€€€€€€€€€€½¹Ñ¥¹Õ”(€€€€€€€€€€€Í½ÕÉ•}‘É…™ÑÌ¹…ÁÁ•¹¡Í½ÕÉ”¤(€€€€€€€€€€€¥˜¹½ÐÍ½ÕÉ”¹•Ð ‰…Ñ¥Ù”ˆ¤½ÈÍ½ÕÉ”¹•Ð ‰ÍÑ…ÑÕÌˆ¤€„ô€‰…ÁÁÉ½Ù•ˆè(€€€€€€€€€€€€€€€Ù¥½±…Ñ¥½¹Íl‰¡…ÁÑ•É}µ•µ‰•ÉÍ¡¥Á}Ù¥½±…Ñ¥½¹Ì‰t¹…ÁÁ•¹ (€€€€€€€€€€€€€€€€€€€˜‰M•¹”‘É…™ÐíÍ½ÕÉ•}¥‘ô¥Ì¹½Ð…Ñ¥Ù”…¹…ÁÁÉ½Ù•ˆ(€€€€€€€€€€€€€€€€¤(€€€€€€€…ÑÕ…±}Í•¹•}¥‘Ì€ômÍÑÈ¡¥Ñ•´¹•Ð ‰Í•¹•}¥ˆ¤½È€ˆˆ¤™½È¥Ñ•´¥¸Í½ÕÉ•}‘É…™ÑÍt(€€€€€€€¥˜…ÑÕ…±}Í•¹•}¥‘Ì€„ô•áÁ•Ñ•‘}Í•¹•}¥‘Ìè(€€€€€€€€€€€Ù¥½±…Ñ¥½¹Íl‰Í•¹•}½É‘•É¥¹}Ù¥½±…Ñ¥½¹Ì‰t¹…ÁÁ•¹ (€€€€€€€€€€€€€€€€‰ÁÁÉ½Ù•Í•¹”‘É…™ÑÌ‘¼¹½Ð•á…Ñ±äµ…Ñ ¡…ÁÑ•ÈÍ•¹”½É‘•Èˆ(€€€€€€€€€€€€¤(€€€€€€€•¹•É…Ñ•‘}Ñ•áÐ€ôÍÑÈ¡‘É…™Ð¹•Ð ‰•¹•É…Ñ•‘}Ñ•áÐˆ¤½È€ˆˆ¤(€€€€€€€ÕÉÍ½È€ô€À(€€€€€€€™½ÈÍ½ÕÉ”¥¸Í½ÕÉ•}‘É…™ÑÌè(€€€€€€€€€€€Ñ•áÐ€ôÍÑÈ¡Í½ÕÉ”¹•Ð ‰•¹•É…Ñ•‘}Ñ•áÐˆ¤½È€ˆˆ¤(€€€€€€€€€€€¥¹‘•à€ô•¹•É…Ñ•‘}Ñ•áÐ¹™¥¹¡Ñ•áÐ°ÕÉÍ½È¤(€€€€€€€€€€€¥˜¥¹‘•à€ð€Àè(€€€€€€€€€€€€€€€Ù¥½±…Ñ¥½¹Íl‰½¹ÑÉ…‘¥Ñ¥½¹Ì‰t¹…ÁÁ•¹ (€€€€€€€€€€€€€€€€€€€˜‰¡…ÁÑ•È‘½•Ì¹½ÐÁÉ•Í•ÉÙ”Í•¹”‘É…™ÐíÍ½ÕÉ”¹•Ð ‘É…™Ñ}¥œ¥ôÙ•É‰…Ñ¥´ˆ(€€€€€€€€€€€€€€€€¤(€€€€€€€€€€€€€€€½¹Ñ¥¹Õ”(€€€€€€€€€€€ÕÉÍ½È€ô¥¹‘•à€¬±•¸¡Ñ•áÐ¤(€€€€€€€ÑÉ…¹Í¥Ñ¥½¹}Á…¥ÉÌ€ôì(€€€€€€€€€€€€ (€€€€€€€€€€€€€€€ÍÑÈ¡¥Ñ•´¹•Ð ‰™É½µ}Í•¹•}‘É…™Ñ}¥ˆ¤½È€ˆˆ¤°(€€€€€€€€€€€€€€€ÍÑÈ¡¥Ñ•´¹•Ð ‰Ñ½}Í•¹•}‘É…™Ñ}¥ˆ¤½È€ˆˆ¤°(€€€€€€€€€€€€¤(€€€€€€€€€€€™½È¥Ñ•´¥¸‘É…™Ð¹•Ð ‰ÑÉ…¹Í¥Ñ¥½¹Ìˆ¤½Èmt(€€€€€€€€€€€¥˜¥Í¥¹ÍÑ…¹”¡¥Ñ•´°‘¥Ð¤(€€€€€€€ô(€€€€€€€…±±½Ý•‘}Á…¥ÉÌ€ôÍ•Ð¡é¥À¡Í½ÕÉ•}¥‘Ì°Í½ÕÉ•}¥‘ÍlÄét¤¤(€€€€€€€¥¹Ù…±¥‘}Á…¥ÉÌ€ôÑÉ…¹Í¥Ñ¥½¹}Á…¥ÉÌ€´…±±½Ý•‘}Á…¥ÉÌ(€€€€€€€¥˜¥¹Ù…±¥‘}Á…¥ÉÌè(€€€€€€€€€€€Ù¥½±…Ñ¥½¹Íl‰Í•¹•}½É‘•É¥¹}Ù¥½±…Ñ¥½¹Ì‰t¹…ÁÁ•¹ (€€€€€€€€€€€€€€€€‰QÉ…¹Í¥Ñ¥½¹ÌÉ•™•É•¹”¹½¸µ…‘©…•¹Ð½ÈÕ¹­¹½Ý¸Í•¹•Ìˆ(€€€€€€€€€€€€¤(€€€€€€€É•ÑÕÉ¸…Ý…¥ÐÍ•±˜¹}É•Á½ÉÐ (€€€€€€€€€€€‘ˆ°(€€€€€€€€€€€ÁÉ½©•Ñ}¥õÁÉ½©•Ñ}¥°(€€€€€€€€€€€…É}¥õÍÑÈ¡‘É…™Ð¹•Ð ‰…É}¥ˆ¤½È€ˆˆ¤°(€€€€€€€€€€€¡…ÁÑ•É}Á±…¹}¥õÍÑÈ¡‘É…™Ð¹•Ð ‰¡…ÁÑ•É}Á±…¹}¥ˆ¤½È€ˆˆ¤°(€€€€€€€€€€€Í•¹•}¥õ9½¹”°(€€€€€€€€€€€ÍÕ‰©•Ñ}ÑåÁ”ô‰¡…ÁÑ•É}‘É…™Ðˆ°(€€€€€€€€€€€ÍÕ‰©•Ñ}¥õÍÑÈ¡‘É…™Ð¹•Ð ‰‘É…™Ñ}¥ˆ¤½È€ˆˆ¤°(€€€€€€€€€€€Ù•ÉÍ¥½¹}¹Õµ‰•Èõ¥¹Ð¡‘É…™Ð¹•Ð ‰Ù•ÉÍ¥½¹}¹Õµ‰•Èˆ¤½È€À¤°(€€€€€€€€€€€ÍÑ…”õÍÑ…”°(€€€€€€€€€€€Ù¥½±…Ñ¥½¹ÌõÙ¥½±…Ñ¥½¹Ì°(€€€€€€€€€€€Ý…É¹¥¹Ìõmt°(€€€€€€€€€€€•Ù¥‘•¹”õl(€€€€€€€€€€€€€€€˜‰Í½ÕÉ•}Í•¹•}½Õ¹Ðõí±•¸¡Í½ÕÉ•}¥‘Ì¥ôˆ°(€€€€€€€€€€€€€€€˜‰¡…ÁÑ•É}Í•¹•}½Õ¹Ðõí±•¸¡•áÁ•Ñ•‘}Í•¹•}¥‘Ì¥ôˆ°(€€€€€€€€€€€t°(€€€€€€€€€€€Á•ÉÍ¥ÍÐõÁ•ÉÍ¥ÍÐ°(€€€€€€€€¤(()‘É…™Ñ}Ù…±¥‘…Ñ¥½¹}Í•ÉÙ¥”€ôÉ…™ÑY…±¥‘…Ñ¥½¹M•ÉÙ¥” ¤(