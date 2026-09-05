"""Deterministic, arc-scoped story readiness evaluation."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from bson import ObjectId


SATISFIED_STATUSES = {"approved", "ready"}
VALID_STATUSES = {"missing", "discussed", "proposed", "approved", "ready"}
VALID_PRIORITIES = {"required", "recommended", "optional"}
DRAFTABLE_ARC_STATUSES = {"approved", "active"}


def _public_item(item: Dict[str, Any]) -> Dict[str, Any]:
    result = {}
    for key, value in item.items():
        if key == "_id":
            result["id"] = str(value)
        elif isinstance(value, ObjectId):
            result[key] = str(value)
        elif isinstance(value, datetime):
            result[key] = value.isoformat()
        else:
            result[key] = value
    return result


class ReadinessService:
    def normalize_item(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        priority = str(payload.get("priority") or "recommended").lower()
        status = str(payload.get("status") or "missing").lower()
        if priority not in VALID_PRIORITIES:
            raise ValueError(f"Unsupported readiness priority: {priority}")
        if status not in VALID_STATUSES:
            raise ValueError(f"Unsupported readiness status: {status}")
        evidence = payload.get("evidence") or []
        if not isinstance(evidence, list):
            raise ValueError("Readiness evidence must be a list")
        if status == "missing" and evidence:
            status = "discussed"
        return {
            **payload,
            "category": str(payload.get("category") or "Uncategorized").strip(),
            "title": str(payload.get("title") or "Untitled requirement").strip(),
            "description": str(payload.get("description") or "").strip(),
            "priority": priority,
            "status": status,
            "evidence": evidence,
            "blocking": bool(payload.get("blocking", priority == "required")),
        }

    async def evaluate(
        self,
        db,
        project_id: str,
        *,
        arc_id: str | None = None,
        persist: bool = True,
    ) -> Dict[str, Any]:
        pid = ObjectId(project_id)
        project = await db.projects.find_one({"_id": pid}, {"_id": 1})
        if not project:
            raise ValueError("Project not found")

        query: Dict[str, Any] = {"project_id": pid}
        arc = None
        if arc_id:
            arc = await db.story_arcs.find_one(
                {"project_id": pid, "arc_id": arc_id}
            )
            if not arc:
                raise ValueError("Arc not found")
            query["$or"] = [
                {"arc_id": arc_id},
                {"arc_id": {"$exists": False}},
                {"arc_id": None},
                {"arc_id": ""},
            ]

        items = await db.story_readiness.find(query).sort(
            [("priority", 1), ("category", 1), ("title", 1)]
        ).to_list(length=1000)
        required = [
            item
            for item in items
            if item.get("priority") == "required"
        ]
        blockers = [
            item
            for item in required
            if str(item.get("status") or "missing") not in SATISFIED_STATUSES
        ]
        satisfied = [
            item
            for item in items
            if str(item.get("status") or "missing") in SATISFIED_STATUSES
        ]
        has_progress = bool(
            satisfied
            or any(item.get("evidence") for item in items)
            or any(
                str(item.get("status") or "missing")
                in {"discussed", "proposed"}
                for item in items
            )
        )

        if required and not blockers:
            status = "READY"
        elif has_progress:
            status = "PARTIALLY_READY"
        else:
            status = "NOT_READY"

        arc_status = str((arc or {}).get("approval_status") or "draft").lower()
        drafting_eligible = bool(
            arc_id
            and status == "READY"
            and arc_status in DRAFTABLE_ARC_STATUSES
        )
        counts = {
            readiness_status: sum(
                1
                for item in items
                if str(item.get("status") or "missing") == readiness_status
            )
            for readiness_status in sorted(VALID_STATUSES)
        }
        report = {
            "project_id": project_id,
            "arc_id": arc_id,
            "status": status,
            "drafting_eligible": drafting_eligible,
            "arc_approval_status": arc_status if arc_id else None,
            "counts": counts,
            "total_items": len(items),
            "required_items": len(required),
            "satisfied_required_items": len(required) - len(blockers),
            "blockers": [_public_item(item) for item in blockers],
            "missing": [
                _public_item(item)
                for item in items
                if str(item.get("status") or "missing") == "missing"
            ],
            "recommended": [
                _public_item(item)
                for item in items
                if item.get("priority") == "recommended"
                and str(item.get("status") or "missing")
                not in SATISFIED_STATUSES
            ],
            "ready": [_public_item(item) for item in satisfied],
            "evaluated_at": datetime.utcnow().isoformat(),
        }
        if persist and arc:
            await db.story_arcs.update_one(
                {"_id": arc["_id"]},
                {
                    "$set": {
                        "readiness_status": status,
                        "drafting_eligible": drafting_eligible,
                        "readiness_evaluated_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow(),
                    }
                },
            )
        return report

    async def evaluate_all_arcs(self, db, project_id: str) -> List[Dict[str, Any]]:
        arcs = await db.story_arcs.find(
            {"project_id": ObjectId(project_id)}, {"arc_id": 1}
        ).to_list(length=500)
        return [
            await self.evaluate(db, project_id, arc_id=arc["arc_id"])
            for arc in arcs
            if arc.get("arc_id")
        ]


readiness_service = ReadinessService()
