"""Create and validate a persistent production-scale Phase 3C story corpus."""
from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime
from uuid import uuid4

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.services.story_auditor_service import story_auditor_service
from app.services.story_bible_service import rebuild_story_bible
from app.services.story_health_service import story_health_service


def _chapter_text(number: int, arc: int) -> str:
    weather = ["hard rain", "dry snow", "river fog", "a wind smelling of iron"]
    mistakes = [
        "Mara mistook restraint for agreement",
        "Soren answered the question he wished she had asked",
        "the council chose pride over useful caution",
        "Mara withheld the kinder truth until it could no longer help",
    ]
    details = [
        "a cracked blue cup",
        "the bell rope's tarred fibers",
        "ink drying on an unsigned oath",
        "salt caught in the window frame",
        "a glove with one pearl button missing",
    ]
    paragraphs = []
    for beat in range(15):
        mistake = mistakes[(number + beat) % len(mistakes)]
        detail = details[(number * 2 + beat) % len(details)]
        sky = weather[(number + beat * 3) % len(weather)]
        paragraphs.append(
            (
                f"The morning brought {sky}, and {detail} sat where nobody "
                f"remembered leaving it. {mistake}. Mara noticed too late that "
                f"Soren had gone quiet, but she let the silence stand because an "
                f"apology would have admitted what she was still trying not to know. "
                f"The argument moved sideways: one person spoke about the city, "
                f"another about the dead, and neither named the promise between them. "
                f"By the time the bell sounded its {number + beat}th uncertain note, "
                f"their decision was practical, incomplete, and expensive. Nobody "
                f"felt certain enough to call it courage. They carried the consequence "
                f"forward anyway, each believing a different version of what had happened."
            )
        )
    paragraphs.append(
        (
            f"At the close of chapter {number}, Mara chose the narrower door. "
            f"It solved the immediate danger in arc {arc}, harmed someone who had "
            "trusted her, and left the founding oath open to a less comfortable answer."
        )
    )
    return "\n\n".join(paragraphs)


async def main():
    client = AsyncIOMotorClient(settings.mongodb_url)
    db = client[settings.database_name]
    now = datetime.utcnow()
    project_id = ObjectId()
    isolation_project_id = ObjectId()
    project = {
        "_id": project_id,
        "title": "Phase 3C Validation: The Bell Beneath Winter",
        "premise": (
            "A civic archivist discovers that her city's bell erases promises "
            "whenever leaders agree too easily."
        ),
        "idea_dump": (
            "Mara distrusts consensus, Soren hides his role in the founding oath, "
            "and the bell may be protecting the city from a worse memory."
        ),
        "genre": "Literary fantasy",
        "tone": "Intimate, fallible, and politically uncertain",
        "themes": ["Memory", "Consent", "The cost of certainty"],
        "validation_key": f"phase-3c-{uuid4()}",
        "created_at": now,
        "updated_at": now,
    }
    await db.projects.insert_one(project)
    await db.projects.insert_one(
        {
            "_id": isolation_project_id,
            "title": "Phase 3C Isolation Control: The Noon Orchard",
            "premise": "An orchard grows fruit from abandoned futures.",
            "genre": "Fantasy",
            "validation_key": f"phase-3c-isolation-{uuid4()}",
            "created_at": now,
            "updated_at": now,
        }
    )

    arcs = [
        {
            "project_id": project_id,
            "arc_id": "winter-bell",
            "title": "Arc 1: The Winter Bell",
            "purpose": "Expose the bell's political use without proving its origin.",
            "goal": "Keep the thaw council from erasing the dockworkers' pact.",
            "conflict": "Mara needs allies she does not trust.",
            "stakes": "The city loses the memory of collective ownership.",
            "chapter_range": [1, 22],
            "estimated_chapters": 22,
            "major_events": ["The bell misnames the dead", "Mara breaks the council seal"],
            "mysteries": ["Who taught the bell to erase agreement?"],
            "approval_status": "approved",
            "development_status": "completed",
            "focus_role": "completed",
            "order": 1,
            "created_at": now,
            "updated_at": now,
        },
        {
            "project_id": project_id,
            "arc_id": "erased-oath",
            "title": "Arc 2: The Erased Oath",
            "purpose": "Force Mara and Soren to choose which imperfect history survives.",
            "goal": "Recover the founding oath without restoring its coercive clause.",
            "conflict": "The true oath incriminates both families.",
            "stakes": "Truth may preserve the city and destroy its fragile peace.",
            "chapter_range": [23, 50],
            "estimated_chapters": 28,
            "major_events": ["Soren confesses partially", "The bell refuses a clean ending"],
            "mysteries": ["Why did Mara's mother preserve the missing clause?"],
            "approval_status": "approved",
            "development_status": "draftable",
            "focus_role": "current",
            "order": 2,
            "created_at": now,
            "updated_at": now,
        },
    ]
    await db.story_arcs.insert_many(arcs)
    await db.story_visions.insert_one(
        {
            "project_id": project_id,
            "premise": project["premise"],
            "genre": project["genre"],
            "themes": project["themes"],
            "target_length": "80,000-90,000 words",
            "audience": "Adult fantasy readers",
            "narrative_goals": [
                "Preserve ambiguity",
                "Let characters make costly mistakes",
                "Avoid structurally identical chapters",
            ],
            "created_at": now,
            "updated_at": now,
        }
    )
    await db.character_bibles.insert_many(
        [
            {
                "project_id": project_id,
                "name": "Mara Venn",
                "role": "archivist and reluctant civic witness",
                "description": "Observant, defensive, and often wrong about silence.",
                "goals": ["Preserve the dockworkers' pact", "Avoid becoming her mother"],
                "fears": ["Public certainty", "Being forgiven too easily"],
                "current_status": "active",
                "created_at": now,
                "updated_at": now,
            },
            {
                "project_id": project_id,
                "name": "Soren Vale",
                "role": "bell keeper",
                "description": "Loyal in practice, evasive in speech.",
                "goals": ["Keep Mara alive", "Hide his family clause in the oath"],
                "fears": ["A truthful history with no room for mercy"],
                "current_status": "active",
                "created_at": now,
                "updated_at": now,
            },
        ]
    )
    await db.relationship_graphs.insert_one(
        {
            "project_id": project_id,
            "relationship_id": "mara-soren",
            "character_a": "Mara Venn",
            "character_b": "Soren Vale",
            "status": "mutual loyalty damaged by strategic omissions",
            "future_payoff": "They must choose whether partial truth can still be consent.",
            "created_at": now,
            "updated_at": now,
        }
    )
    await db.mystery_registry.insert_many(
        [
            {
                "project_id": project_id,
                "mystery_id": "bell-teacher",
                "question": "Who taught the bell to erase agreement?",
                "truth": "The first council encoded the ritual together.",
                "status": "open",
                "arc_id": "winter-bell",
                "reveal_target": "Chapter 46",
                "created_at": now,
                "updated_at": now,
            },
            {
                "project_id": project_id,
                "mystery_id": "missing-clause",
                "question": "Why did Mara's mother preserve the missing clause?",
                "truth": "She wanted a later generation to refuse it knowingly.",
                "status": "open",
                "arc_id": "erased-oath",
                "reveal_target": "Chapter 49",
                "created_at": now,
                "updated_at": now,
            },
        ]
    )
    await db.artifact_registry.insert_many(
        [
            {
                "project_id": project_id,
                "artifact_id": "winter-bell",
                "item": "The Winter Bell",
                "owner": "The city",
                "future_relevance": "Must ring after a deliberately imperfect vote.",
                "status": "active",
                "created_at": now,
                "updated_at": now,
            },
            {
                "project_id": project_id,
                "artifact_id": "blue-cup",
                "item": "Mara's cracked blue cup",
                "owner": "Mara Venn",
                "future_relevance": "Contains ash from the first oath fire.",
                "status": "active",
                "created_at": now,
                "updated_at": now,
            },
        ]
    )
    await db.foreshadow_registry_v2.insert_many(
        [
            {
                "project_id": project_id,
                "entry_id": "third-note",
                "seed": "The bell's third note is always missing in official recordings.",
                "payoff_target": "Chapter 44",
                "status": "advanced",
                "created_at": now,
                "updated_at": now,
            },
            {
                "project_id": project_id,
                "entry_id": "pearl-button",
                "seed": "A pearl button appears near every altered oath.",
                "payoff_target": "Chapter 48",
                "status": "seeded",
                "created_at": now,
                "updated_at": now,
            },
        ]
    )

    chapter_plans = []
    chapter_drafts = []
    intelligence = []
    total_words = 0
    for number in range(1, 51):
        arc_id = "winter-bell" if number <= 22 else "erased-oath"
        text = _chapter_text(number, 1 if number <= 22 else 2)
        word_count = len(text.split())
        total_words += word_count
        plan_id = f"validation-plan-{number:02d}"
        draft_id = f"validation-draft-{number:02d}"
        obligations = []
        if number == 4:
            obligations.append("Return the broken bell clapper before the thaw vote")
        if number == 9:
            obligations.append("Tell Soren who ordered the dockworkers' oath erased")
        chapter_plans.append(
            {
                "project_id": project_id,
                "chapter_plan_id": plan_id,
                "arc_id": arc_id,
                "chapter_number": number,
                "title": f"Chapter {number}: The {number}th Uncertain Note",
                "purpose": f"Complicate Mara's understanding of the oath in chapter {number}.",
                "conflict": "A useful decision requires an admission nobody is ready to make.",
                "character_focus": ["Mara Venn", "Soren Vale"],
                "status": "approved",
                "created_at": now,
                "updated_at": now,
            }
        )
        chapter_drafts.append(
            {
                "project_id": project_id,
                "draft_id": draft_id,
                "chapter_plan_id": plan_id,
                "arc_id": arc_id,
                "version_number": 1,
                "status": "approved",
                "active": True,
                "generated_text": text,
                "source_scene_draft_ids": [],
                "generated_by": "phase_3c_validation_corpus",
                "validation_result": "PASS",
                "created_at": now,
                "updated_at": now,
            }
        )
        intelligence.append(
            {
                "project_id": project_id,
                "intelligence_id": f"validation-intelligence-{number:02d}",
                "chapter_plan_id": plan_id,
                "chapter_draft_id": draft_id,
                "chapter_draft_version": 1,
                "chapter_number": number,
                "arc_id": arc_id,
                "title": f"Chapter {number}: The {number}th Uncertain Note",
                "active": True,
                "chapter_summary": (
                    f"Mara misreads a civic signal, chooses an incomplete answer, "
                    f"and carries a personal cost into chapter {number + 1}."
                ),
                "important_events": [
                    f"Mara makes costly choice {number}",
                    f"Soren withholds part of the oath in chapter {number}",
                ],
                "characters_present": ["Mara Venn", "Soren Vale"],
                "character_changes": [
                    {"character": "Mara Venn", "change": f"Certainty weakens at beat {number}"}
                ],
                "knowledge_revealed": [],
                "mysteries_introduced": [],
                "mysteries_advanced": [],
                "mysteries_resolved": [],
                "foreshadowing_introduced": [],
                "foreshadowing_advanced": [],
                "foreshadowing_resolved": [],
                "artifact_usage": (
                    [{"artifact_id": "winter-bell", "name": "The Winter Bell"}]
                    if number % 3 == 0
                    else []
                ),
                "relationship_changes": [
                    {
                        "relationship_id": "mara-soren",
                        "status": "trust changes without becoming cleanly better",
                    }
                ],
                "timeline_impact": [],
                "canon_impact": [],
                "unresolved_questions": obligations,
                "future_obligations": obligations,
                "word_count": word_count,
                "quality_findings": [],
                "created_at": now,
                "updated_at": now,
            }
        )
    await db.chapter_plans.insert_many(chapter_plans)
    await db.chapter_drafts.insert_many(chapter_drafts)
    await db.chapter_intelligence.insert_many(intelligence)

    manuscript_id = "validation-manuscript"
    version_id = "validation-manuscript-v1"
    await db.manuscripts.insert_one(
        {
            "project_id": project_id,
            "manuscript_id": manuscript_id,
            "title": project["title"],
            "status": "review",
            "active": True,
            "version": 1,
            "created_at": now,
            "updated_at": now,
        }
    )
    await db.manuscript_versions.insert_one(
        {
            "project_id": project_id,
            "manuscript_id": manuscript_id,
            "version_id": version_id,
            "version_number": 1,
            "status": "review",
            "source_chapters": [
                {
                    "chapter_draft_id": item["draft_id"],
                    "chapter_plan_id": item["chapter_plan_id"],
                    "chapter_number": index + 1,
                }
                for index, item in enumerate(chapter_drafts)
            ],
            "word_count": total_words,
            "active": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    await db.editorial_reports.insert_one(
        {
            "project_id": project_id,
            "report_id": "validation-editorial",
            "subject_type": "arc",
            "subject_id": "erased-oath",
            "report_type": "editorial",
            "score": 74,
            "findings": [
                {
                    "category": "repetitive_chapter_structure",
                    "severity": "warning",
                    "message": "Several chapters use the same consequence cadence.",
                },
                {
                    "category": "overly_clean_resolution",
                    "severity": "info",
                    "message": "The ending currently resists a clean resolution.",
                },
            ],
            "blockers": [],
            "generated_by": "deterministic_validation",
            "created_at": now,
        }
    )
    await db.canon_registry.insert_many(
        [
            {
                "project_id": project_id,
                "canon_id": "canon-bell-cost",
                "canon_type": "artifact",
                "subject": "The Winter Bell",
                "field": "cost",
                "value": "It erases remembered consensus, not disagreement.",
                "active": True,
                "authority_level": "locked",
                "created_at": now,
                "updated_at": now,
            },
            {
                "project_id": project_id,
                "canon_id": "canon-mara-flaw",
                "canon_type": "character",
                "subject": "Mara Venn",
                "field": "flaw",
                "value": "She often interprets silence as consent or judgment.",
                "active": True,
                "authority_level": "locked",
                "created_at": now,
                "updated_at": now,
            },
        ]
    )

    await db.chapter_intelligence.insert_one(
        {
            **intelligence[0],
            "_id": ObjectId(),
            "project_id": isolation_project_id,
            "intelligence_id": "isolation-intelligence-1",
            "chapter_plan_id": "isolation-plan-1",
            "chapter_draft_id": "isolation-draft-1",
            "chapter_number": 1,
            "chapter_summary": "Nia waits for blue fruit beneath an unfamiliar noon.",
            "characters_present": ["Nia"],
            "future_obligations": ["Harvest the blue fruit after noon"],
        }
    )

    audit = await story_auditor_service.run(
        db,
        str(project_id),
        include_agent=False,
    )
    health = await story_health_service.calculate(db, str(project_id))
    bible = await rebuild_story_bible(db, str(project_id))
    isolated_leaks = await db.chapter_intelligence.count_documents(
        {
            "project_id": isolation_project_id,
            "$or": [
                {"characters_present": {"$in": ["Mara Venn", "Soren Vale"]}},
                {"chapter_summary": {"$regex": "bell|oath", "$options": "i"}},
            ],
        }
    )
    result = {
        "project_id": str(project_id),
        "isolation_project_id": str(isolation_project_id),
        "arcs": 2,
        "chapters": 50,
        "words": total_words,
        "health_score": health["story_health_score"],
        "audit_result": audit["result"],
        "audit_findings": len(audit["findings"]),
        "story_bible_version": bible["version"],
        "isolation_leaks": isolated_leaks,
        "chapter_45_present": any(
            item["chapter_number"] == 45
            for item in bible["sections"]["chapter_intelligence"]
        ),
        "chapter_50_present": any(
            item["chapter_number"] == 50
            for item in bible["sections"]["chapter_intelligence"]
        ),
    }
    print(json.dumps(result, indent=2, default=str))
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
