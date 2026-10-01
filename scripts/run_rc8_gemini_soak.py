"""Real-provider RC8 10-chapter / 50-scene soak.

This script uses the configured Gemini gateway and a dedicated database.  It
records every provider/application outcome incrementally and drops only that
database after the final artifact has been written.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bson import ObjectId
from fastapi.testclient import TestClient
from pymongo import MongoClient


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.core.config import settings as app_config  # noqa: E402


SOAK_DATABASE = "novelforge_rc8_soak"
SOURCE_DATABASE = "novelforge"
ARTIFACT = ROOT / "artifacts" / "rc8-gemini-50-scene-soak.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def detail(response) -> Any:
    try:
        return response.json().get("detail", response.json())
    except Exception:
        return response.text


def save(report: dict[str, Any]) -> None:
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")


def copy_settings() -> None:
    client = MongoClient(app_config.mongodb_url)
    try:
        client.drop_database(SOAK_DATABASE)
        source = client[SOURCE_DATABASE].app_settings.find_one({"_id": "global_settings"})
        if not source:
            raise RuntimeError("The configured application settings were not found.")
        client[SOAK_DATABASE].app_settings.replace_one(
            {"_id": "global_settings"}, source, upsert=True
        )
    finally:
        client.close()


def api_post(client: TestClient, url: str, payload: dict | None = None):
    return client.post(url, json=payload or {})


def main() -> None:
    app_config.database_name = SOAK_DATABASE
    app_config.use_mock_llm = False
    copy_settings()

    # These imports must follow database selection so startup uses the isolated DB.
    from main import app
    from tests.test_drafting_v2 import prepare_draftable_arc

    report: dict[str, Any] = {
        "started_at_utc": utc_now(),
        "database": SOAK_DATABASE,
        "provider": "gemini",
        "required_model": "gemini-3.1-flash-lite",
        "scene_target": 50,
        "scene_attempts": [],
        "workflow_checks": {},
        "exact_cleanup": False,
        "status": "running",
    }
    save(report)
    mongo = MongoClient(app_config.mongodb_url)
    sync_db = mongo[SOAK_DATABASE]
    project_id = ""
    try:
        with TestClient(app) as client:
            project_id, arc_id, knowledge, artifact, foreshadow, timeline = prepare_draftable_arc(client)
            pid = ObjectId(project_id)
            sync_db.character_bibles.insert_one(
                {
                    "project_id": pid,
                    "name": "Ilyra",
                    "role": "protagonist",
                    "description": "A civic flame-reader learning to trust witnesses.",
                    "personality": ["guarded", "observant", "compassionate"],
                    "goals": ["Restore the public witness flame"],
                    "fears": ["Turning truth into another private weapon"],
                    "beliefs": ["Memory must be witnessed to remain honest"],
                    "current_status": "active",
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                }
            )
            scene_rows: list[dict[str, Any]] = []
            chapter_rows: list[dict[str, Any]] = []
            for chapter_number in range(1, 11):
                chapter_response = api_post(
                    client,
                    f"/api/projects/{project_id}/chapter-plans",
                    {
                        "arc_id": arc_id,
                        "chapter_number": chapter_number,
                        "title": f"Witness Flame {chapter_number}",
                        "purpose": f"Move Ilyra one step closer to public stewardship in chapter {chapter_number}.",
                        "conflict": "The regent makes truth personally costly.",
                        "character_focus": ["Ilyra"],
                        "knowledge_changes": [knowledge["entry_id"]],
                        "artifact_ids": [artifact["artifact_id"]],
                        "foreshadow_ids": [foreshadow["entry_id"]],
                        "timeline_entry_ids": [timeline[min(2, (chapter_number - 1) // 4)]["entry_id"]],
                        "status": "approved",
                    },
                )
                if chapter_response.status_code != 200:
                    raise RuntimeError(f"Chapter planning failed: {detail(chapter_response)}")
                chapter = chapter_response.json()
                chapter_rows.append(chapter)
                for scene_order in range(1, 6):
                    sequence = (chapter_number - 1) * 5 + scene_order
                    scene_response = api_post(
                        client,
                        f"/api/projects/{project_id}/scene-plans-v2",
                        {
                            "arc_id": arc_id,
                            "chapter_plan_id": chapter["chapter_plan_id"],
                            "title": f"The {sequence:02d}th Witness",
                            "purpose": f"Ilyra seeks testimony number {sequence} without coercion.",
                            "conflict": "A witness will speak only if Ilyra risks a memory she values.",
                            "outcome": "The cost reveals a new pressure that makes the following scene necessary.",
                            "character_focus": ["Ilyra"],
                            "character_change": "Private control yields incrementally to shared trust.",
                            "knowledge_changes": [knowledge["entry_id"]],
                            "foreshadow_links": [foreshadow["entry_id"]],
                            "artifact_interactions": [artifact["artifact_id"]],
                            "timeline_impacts": [timeline[min(2, (chapter_number - 1) // 4)]["entry_id"]],
                            "status": "approved",
                            "order": scene_order,
                        },
                    )
                    if scene_response.status_code != 200:
                        raise RuntimeError(f"Scene planning failed: {detail(scene_response)}")
                    scene_rows.append(scene_response.json())

            for index, scene in enumerate(scene_rows, start=1):
                request_id = f"rc8-soak-scene-{index:02d}"
                record: dict[str, Any] = {
                    "scene": index,
                    "chapter": ((index - 1) // 5) + 1,
                    "scene_order": ((index - 1) % 5) + 1,
                    "request_id": request_id,
                    "started_at_utc": utc_now(),
                    "attempts": [],
                }
                for attempt in range(1, 3):
                    started = time.perf_counter()
                    response = api_post(
                        client,
                        f"/api/projects/{project_id}/scene-plans/{scene['scene_id']}/generate-draft",
                        {"request_id": request_id},
                    )
                    attempt_row = {
                        "attempt": attempt,
                        "http_status": response.status_code,
                        "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
                    }
                    if response.status_code == 200:
                        payload = response.json()
                        draft = payload.get("draft") or {}
                        usable = bool(str(draft.get("generated_text") or "").strip())
                        attempt_row.update(
                            {
                                "application_status": "usable" if usable else "empty_result",
                                "draft_id": draft.get("draft_id"),
                                "validation_result": draft.get("validation_result"),
                                "provider": (draft.get("generation_metadata") or {}).get("provider"),
                                "model": (draft.get("generation_metadata") or {}).get("model"),
                            }
                        )
                        record["draft_id"] = draft.get("draft_id")
                        record["usable"] = usable
                        record["validation_result"] = draft.get("validation_result")
                        record["word_count"] = len(str(draft.get("generated_text") or "").split())
                        record["attempts"].append(attempt_row)
                        if usable:
                            review = client.put(
                                f"/api/projects/{project_id}/scene-drafts/{draft['draft_id']}/status",
                                json={"status": "review"},
                            )
                            record["review_status"] = review.status_code
                            if review.status_code == 200:
                                approve = client.put(
                                    f"/api/projects/{project_id}/scene-drafts/{draft['draft_id']}/status",
                                    json={"status": "approved"},
                                )
                                record["approval_status"] = approve.status_code
                                if approve.status_code != 200:
                                    record["approval_blocker"] = detail(approve)
                            break
                    else:
                        attempt_row.update(
                            {
                                "application_status": "failed",
                                "detail": detail(response),
                                "existing_work_safe": sync_db.scene_drafts.count_documents(
                                    {"project_id": pid, "scene_id": scene["scene_id"]}
                                ) == 0,
                            }
                        )
                        record["attempts"].append(attempt_row)
                record.setdefault("usable", False)
                record["completed_at_utc"] = utc_now()
                report["scene_attempts"].append(record)
                save(report)

            usable = [row for row in report["scene_attempts"] if row.get("usable")]
            approved = [row for row in usable if row.get("approval_status") == 200]
            report["usable_scene_count"] = len(usable)
            report["approved_scene_count"] = len(approved)
            report["usable_completion_percent"] = round(len(usable) / 50 * 100, 2)

            if approved:
                source_id = approved[0]["draft_id"]
                source_before = sync_db.scene_drafts.find_one(
                    {"project_id": pid, "draft_id": source_id}, {"_id": 0}
                )
                room_response = api_post(
                    client,
                    f"/api/projects/{project_id}/scene-drafts/{source_id}/writers-room",
                    {"request_id": "rc8-soak-writers-room"},
                )
                source_after = sync_db.scene_drafts.find_one(
                    {"project_id": pid, "draft_id": source_id}, {"_id": 0}
                )
                room_options = (
                    sync_db.scene_drafts.count_documents(
                        {"project_id": pid, "writer_room_source_id": source_id, "active": False}
                    )
                )
                report["workflow_checks"]["writers_room"] = {
                    "http_status": room_response.status_code,
                    "source_active_before": source_before.get("active"),
                    "source_active_after": source_after.get("active"),
                    "source_status_before": source_before.get("status"),
                    "source_status_after": source_after.get("status"),
                    "inactive_alternatives": room_options,
                    "invariant_pass": bool(
                        source_before.get("active")
                        and source_after.get("active")
                        and source_before.get("status") == "approved"
                        and source_after.get("status") == "approved"
                        and room_options == 3
                    ),
                    "detail": None if room_response.status_code == 200 else detail(room_response),
                }

                editorial = api_post(
                    client, f"/api/projects/{project_id}/editorial/review/scene/{source_id}"
                )
                report["workflow_checks"]["editorial_review"] = {
                    "http_status": editorial.status_code,
                    "detail": None if editorial.status_code == 200 else detail(editorial),
                }
                branch = api_post(
                    client,
                    f"/api/projects/{project_id}/revision-branches",
                    {
                        "source_draft_type": "scene",
                        "source_draft_id": source_id,
                        "title": "RC8 continuity pass",
                        "revision_pass": "continuity",
                    },
                )
                if branch.status_code == 200:
                    branch_id = branch.json()["branch_id"]
                    revision = api_post(
                        client,
                        f"/api/projects/{project_id}/revision-branches/{branch_id}/generate",
                        {
                            "change_reason": "Clarify the causal handoff while preserving approved events.",
                            "revision_pass": "continuity",
                            "request_id": "rc8-soak-revision",
                        },
                    )
                    report["workflow_checks"]["revision"] = {
                        "http_status": revision.status_code,
                        "detail": None if revision.status_code == 200 else detail(revision),
                    }
                else:
                    report["workflow_checks"]["revision"] = {
                        "http_status": branch.status_code,
                        "detail": detail(branch),
                    }

            assembled: list[str] = []
            for chapter in chapter_rows:
                response = api_post(
                    client,
                    f"/api/projects/{project_id}/chapter-plans/{chapter['chapter_plan_id']}/generate-draft",
                )
                if response.status_code == 200:
                    assembled.append(response.json()["draft"]["draft_id"])
            report["workflow_checks"]["chapter_assembly"] = {
                "attempted": len(chapter_rows),
                "succeeded": len(assembled),
            }

            proposal_queue = client.get(
                f"/api/projects/{project_id}/canon/proposals", params={"status": "pending", "limit": 20}
            )
            proposals = proposal_queue.json() if proposal_queue.status_code == 200 else []
            canon_status = None
            if proposals:
                canon = client.put(
                    f"/api/projects/{project_id}/canon/proposals/{proposals[0]['proposal_id']}",
                    json={"decision": "approved", "note": "Accepted during RC8 soak.", "confirm_high_impact": True},
                )
                canon_status = canon.status_code
            report["workflow_checks"]["canon"] = {
                "pending_count": len(proposals),
                "approval_status": canon_status,
            }

            conversation = api_post(
                client,
                f"/api/projects/{project_id}/character-conversations",
                {
                    "character_name": "Ilyra",
                    "message": "What is the regent's hidden plan, and what happens after this chapter?",
                    "chapter_number": 1,
                },
            )
            conversation_body = conversation.json() if conversation.status_code == 200 else {}
            report["workflow_checks"]["character_conversation"] = {
                "http_status": conversation.status_code,
                "awareness_safe": (conversation_body.get("awareness_validation") or {}).get("status") == "safe",
                "evidence_count": len(conversation_body.get("evidence") or []),
                "detail": None if conversation.status_code == 200 else detail(conversation),
            }

            analysis = api_post(
                client,
                f"/api/projects/{project_id}/narrative-analysis",
                {"force": True, "changed_sources": ["scene_drafts"]},
            )
            audit = api_post(client, f"/api/projects/{project_id}/story-audit", {"include_agent": True})
            report["workflow_checks"]["narrative_analysis"] = {"http_status": analysis.status_code}
            report["workflow_checks"]["story_audit"] = {
                "http_status": audit.status_code,
                "finding_count": len((audit.json() if audit.status_code == 200 else {}).get("findings") or []),
                "detail": None if audit.status_code == 200 else detail(audit),
            }

            manuscript = api_post(client, f"/api/projects/{project_id}/manuscripts", {"title": "RC8 Soak Manuscript"})
            manuscript_checks: dict[str, Any] = {"create_status": manuscript.status_code}
            if manuscript.status_code == 200:
                manuscript_id = manuscript.json()["manuscript_id"]
                assembly = api_post(
                    client,
                    f"/api/projects/{project_id}/manuscripts/{manuscript_id}/assemble",
                    {"chapter_draft_ids": assembled},
                )
                preflight = client.get(
                    f"/api/projects/{project_id}/manuscripts/{manuscript_id}/publication-preflight"
                )
                manuscript_checks.update(
                    {
                        "assembly_status": assembly.status_code,
                        "assembly_detail": None if assembly.status_code == 200 else detail(assembly),
                        "preflight_status": preflight.status_code,
                        "blockers": (preflight.json() if preflight.status_code == 200 else {}).get("blocker_details", []),
                    }
                )
            report["workflow_checks"]["manuscript_publication"] = manuscript_checks

            traces = list(
                sync_db.execution_traces.find(
                    {"project_id": pid},
                    {
                        "_id": 0,
                        "agent_name": 1,
                        "provider": 1,
                        "model": 1,
                        "status": 1,
                        "metadata.application_outcome": 1,
                        "metadata.provider_success": 1,
                        "metadata.validation_success": 1,
                        "metadata.persistence_success": 1,
                        "metadata.failure_reason": 1,
                    },
                )
            )
            report["execution_trace_summary"] = {
                "count": len(traces),
                "models": sorted({str(item.get("model")) for item in traces if item.get("model")}),
                "application_outcomes": {
                    outcome: sum(1 for item in traces if (
                        ((item.get("metadata") or {}).get("application_outcome") or {}).get("final_outcome")
                        if isinstance((item.get("metadata") or {}).get("application_outcome"), dict)
                        else (item.get("metadata") or {}).get("application_outcome")
                    ) == outcome)
                    for outcome in sorted({
                        str(
                            (((item.get("metadata") or {}).get("application_outcome") or {}).get("final_outcome"))
                            if isinstance((item.get("metadata") or {}).get("application_outcome"), dict)
                            else ((item.get("metadata") or {}).get("application_outcome") or item.get("status"))
                        )
                        for item in traces
                    })
                },
            }
            report["duplicate_request_records"] = len(
                list(
                    sync_db.scene_drafts.aggregate(
                        [
                            {"$match": {"project_id": pid, "request_id": {"$exists": True, "$ne": ""}}},
                            {"$group": {"_id": {"scene": "$scene_id", "request": "$request_id"}, "count": {"$sum": 1}}},
                            {"$match": {"count": {"$gt": 1}}},
                        ]
                    )
                )
            )
            report["status"] = (
                "pass"
                if report["usable_completion_percent"] >= 95
                and report["duplicate_request_records"] == 0
                and report.get("workflow_checks", {}).get("writers_room", {}).get("invariant_pass", False)
                and (
                    report.get("workflow_checks", {}).get("character_conversation", {}).get("awareness_safe") is True
                    or "withheld" in str(report.get("workflow_checks", {}).get("character_conversation", {}).get("detail") or "").lower()
                )
                else "fail"
            )
            report["completed_at_utc"] = utc_now()
            save(report)
    except Exception as exc:
        report["status"] = "error"
        report["fatal_error"] = f"{type(exc).__name__}: {exc}"
        report["completed_at_utc"] = utc_now()
        save(report)
        raise
    finally:
        mongo.drop_database(SOAK_DATABASE)
        mongo.close()
        report["exact_cleanup"] = True
        save(report)


if __name__ == "__main__":
    main()
