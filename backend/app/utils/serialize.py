"""Serialize MongoDB documents for API responses."""
from typing import Any, Dict, List
from bson import ObjectId


def _str_id(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, ObjectId):
        return str(value)
    return str(value)


def _mongo_value(value: Any) -> Any:
    """Recursively make nested response metadata safe for JSON/Pydantic."""
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, list):
        return [_mongo_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _mongo_value(item) for key, item in value.items()}
    return value


def serialize_run(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": _str_id(doc.get("_id")),
        "project_id": _str_id(doc.get("project_id")),
        "status": doc.get("status", "running"),
        "current_agent": doc.get("current_agent", ""),
        "started_at": doc.get("started_at"),
        "finished_at": doc.get("finished_at"),
        "cycle_number": int((doc.get("metadata") or {}).get("cycle_number") or doc.get("cycle_number") or 0),
        "metadata": _mongo_value(doc.get("metadata") or {}),
        "error": doc.get("error"),
        "error_code": doc.get("error_code"),
    }


def serialize_agent_output(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": _str_id(doc.get("_id")),
        "run_id": _str_id(doc.get("run_id")),
        "agent_name": doc.get("agent_name", ""),
        "content": doc.get("content", ""),
        "metadata": _mongo_value(doc.get("metadata") or {}),
        "created_at": doc.get("created_at"),
    }


def serialize_question(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": _str_id(doc.get("_id")),
        "project_id": _str_id(doc.get("project_id")),
        "text": doc.get("text", ""),
        "choices": doc.get("choices") or [],
        "answered": doc.get("answered", False),
        "answer": doc.get("answer"),
        "cycle_number": int(doc.get("cycle_number") or 0),
        "default_recommendation": doc.get("default_recommendation"),
        "story_area": doc.get("story_area"),
        "blocking": bool(doc.get("blocking", False)),
        "created_at": doc.get("created_at"),
    }


def serialize_outline(doc: Dict[str, Any], project_id: str) -> Dict[str, Any]:
    return {
        "id": _str_id(doc.get("_id")) if doc.get("_id") else "",
        "project_id": _str_id(doc.get("project_id")) or project_id,
        "premise": doc.get("premise", ""),
        "themes": doc.get("themes") or [],
        "acts": doc.get("acts") or [],
        "chapters": doc.get("chapters") or [],
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
    }


def serialize_timeline_message(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": _str_id(doc.get("_id")),
        "project_id": _str_id(doc.get("project_id")),
        "cycle_number": doc.get("cycle_number", 1),
        "role": doc.get("role", "system"),
        "agent_name": doc.get("agent_name"),
        "message_type": doc.get("message_type", "summary"),
        "content": doc.get("content", ""),
        "created_at": doc.get("created_at"),
    }


def serialize_cycle(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": _str_id(doc.get("_id")),
        "project_id": _str_id(doc.get("project_id")),
        "cycle_number": doc.get("cycle_number", 1),
        "trigger_message_ids": [_str_id(mid) for mid in doc.get("trigger_message_ids", [])],
        "agents_run": doc.get("agents_run") or [],
        "started_at": doc.get("started_at"),
        "finished_at": doc.get("finished_at"),
        "status": doc.get("status", "running"),
    }
