"""Deterministic validation for derivative scene and chapter drafts."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable
from uuid import uuid4

from bson import ObjectId

from app.services.arc_development_service import arc_development_service
import json
import re


RESULTS = {"PASS", "WARNING", "FAIL"}


def _ids(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(value) for value in values if value]


def _unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if value))


_NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
_KINSHIP_TERMS = {
    "brother", "brothers", "sister", "sisters", "sibling", "siblings",
    "mother", "father", "parent", "parents", "son", "daughter", "cousin",
    "uncle", "aunt", "husband", "wife", "spouse",
}


def _duration_claims(text: str) -> list[tuple[int, str]]:
    claims: list[tuple[int, str]] = []
    for match in re.finditer(r"\b(one|two|three|four|five|six|seven|eight|nine|ten|\d+)\s+years?\s+ago\b", text or "", flags=re.IGNORECASE):
        raw = match.group(1).lower()
        claims.append((_NUMBER_WORDS.get(raw, int(raw) if raw.isdigit() else 0), match.group(0)))
    return [(value, phrase) for value, phrase in claims if value]


def _prose_without_dialogue(text: str) -> str:
    return re.sub(r'["\u201c][^"\u201d]*["\u201d]', " ", text or "")


def _narrative_person(text: str) -> str | None:
    """Return a high-confidence prose person signal, excluding dialogue."""
    prose = _prose_without_dialogue(text).lower()
    first = len(re.findall(r"\b(?:i|me|my|mine|myself)\b", prose))
    third = len(re.findall(r"\b(?:he|she|him|her|his|hers|himself|herself)\b", prose))
    if first >= 3 and first >= third * 1.5:
        return "first person"
    if third >= 3 and third >= first * 1.5:
        return "third person"
    return None


def _relationship_claims(text: str, name_a: str, name_b: str) -> set[str]:
    claims: set[str] = set()
    lowered = (text or "").lower()
    a = re.escape(str(name_a or "").split()[0].lower())
    b = re.escape(str(name_b or "").split()[0].lower())
    if not a or not b:
        return claims
    for sentence in re.split(r"(?<=[.!?])\s+|[;\n]", lowered):
        if not (re.search(rf"\b{a}\b", sentence) and re.search(rf"\b{b}\b", sentence)):
            continue
        claims.update(term for term in _KINSHIP_TERMS if re.search(rf"\b{re.escape(term)}\b", sentence))
    return claims


def _authority_text(document: Dict[str, Any]) -> str:
    for fields in (
        ("fact",),
        ("decision", "answer"),
        ("event", "summary"),
        ("content",),
        ("title", "summary"),
        ("relationship", "type"),
        ("item", "owner"),
    ):
        value = " ".join(str(document.get(field) or "") for field in fields).strip()
        if value:
            return value
    return ""


def _polarity_statements(text: str) -> Dict[str, bool]:
    """Map exact high-confidence assertions to whether they are negated."""
    statements: Dict[str, bool] = {}
    for sentence in re.split(r"[.!?;\n]+", text or ""):
        normalized = " ".join(re.findall(r"[a-z0-9'-]+", sentence.lower()))
        if len(normalized.split()) < 3:
            continue
        negated = bool(re.search(r"\b(?:not|never|cannot|can't|isn't|aren't|wasn't|weren't)\b", normalized))
        key = re.sub(
            r"\b(?:not|never|cannot|can't|isn't|aren't|wasn't|weren't)\b",
            "",
            normalized,
        )
        key = " ".join(key.split())
        if key:
            statements[key] = negated
    return statements


def _explicitly_planned_change(draft: Dict[str, Any], *terms: str) -> bool:
    metadata = draft.get("discovery_metadata") or {}
    if metadata.get("intentional_pov_change") and "pov" in terms:
        return True
    instruction = str(metadata.get("instruction") or draft.get("change_reason") or "").lower()
    change_words = {"switch", "change", "transfer", "give", "hand", "heal", "reveal", "learn"}
    return bool(change_words.intersection(set(re.findall(r"[a-z]+", instruction)))) and all(
        str(term).lower() in instruction for term in terms if term
    )


class DraftValidationService:
    async def _report(
        self,
        db,
        *,
        project_id: str,
        arc_id: str,
        chapter_plan_id: str,
        scene_id: str | None,
        subject_type: str,
        subject_id: str,
        version_number: int,
        stage: str,
        violations: Dict[str, list[str]],
        warnings: list[str] | None = None,
        evidence: list[str] | None = None,
        findings: list[Dict[str, Any]] | None = None,
        persist: bool = True,
    ) -> Dict[str, Any]:
        warnings = _unique(warnings or [])
        normalized = {
            key: _unique(value)
            for key, value in violations.items()
        }
        has_failures = any(normalized.values())
        result = "FAIL" if has_failures else ("WARNING" if warnings else "PASS")
        now = datetime.utcnow()
        report = {
            "project_id": ObjectId(project_id),
            "report_id": str(uuid4()),
            "arc_id": arc_id,
            "chapter_plan_id": chapter_plan_id,
            "scene_id": scene_id,
            "subject_type": subject_type,
            "subject_id": subject_id,
            "version_number": int(version_number),
            "validation_stage": stage,
            "result": result,
            "missing_knowledge": normalized.get("missing_knowledge", []),
            "contradictions": normalized.get("contradictions", []),
            "artifact_violations": normalized.get("artifact_violations", []),
            "timeline_violations": normalized.get("timeline_violations", []),
            "character_violations": normalized.get("character_violations", []),
            "power_violations": normalized.get("power_violations", []),
            "dependency_violations": normalized.get("dependency_violations", []),
            "foreshadow_violations": normalized.get("foreshadow_violations", []),
            "chapter_membership_violations": normalized.get(
                "chapter_membership_violations", []
            ),
            "scene_ordering_violations": normalized.get(
                "scene_ordering_violations", []
            ),
            "warnings": warnings,
            "evidence": _unique(evidence or []),
            "continuity_findings": findings or [],
            "created_at": now,
        }
        if persist:
            result_doc = await db.continuity_reports.insert_one(report)
            report["_id"] = result_doc.inserted_id
        return report

    async def preflight_scene(
        self,
        db,
        project_id: str,
        scene_id: str,
        *,
        persist: bool = True,
    ) -> Dict[str, Any]:
        pid = ObjectId(project_id)
        scene = await db.scene_plans.find_one(
            {"project_id": pid, "scene_id": scene_id}
        )
        if not scene:
            raise ValueError("Scene plan not found")
        chapter = await db.chapter_plans.find_one(
            {
                "project_id": pid,
                "chapter_plan_id": scene.get("chapter_plan_id"),
            }
        )
        arc = await db.story_arcs.find_one(
            {"project_id": pid, "arc_id": scene.get("arc_id")}
        )
        violations: Dict[str, list[str]] = {
            "missing_knowledge": [],
            "contradictions": [],
            "artifact_violations": [],
            "timeline_violations": [],
            "character_violations": [],
            "power_violations": [],
            "dependency_violations": [],
            "foreshadow_violations": [],
            "chapter_membership_violations": [],
            "scene_ordering_violations": [],
        }
        warnings: list[str] = []
        if not chapter:
            violations["chapter_membership_violations"].append(
                "Scene plan has no project-owned chapter plan"
            )
        elif chapter.get("arc_id") != scene.get("arc_id"):
            violations["chapter_membership_violations"].append(
                "Scene plan and chapter plan belong to different arcs"
            )
        elif str(chapter.get("status") or "").lower() != "approved":
            violations["chapter_membership_violations"].append(
                "Chapter plan is not approved"
            )
        if str(scene.get("status") or "").lower() != "approved":
            violations["chapter_membership_violations"].append(
                "Scene plan is not approved"
            )
        if not arc:
            violations["dependency_violations"].append("Arc does not exist")
            development = None
        else:
            development = await arc_development_service.evaluate(
                db, project_id, str(arc["arc_id"]), persist=False
            )
            if not development["draftable"]:
                violations["dependency_violations"].extend(
                    development.get("blockers") or ["Arc is not draftable"]
                )
        order = int(scene.get("order") or 0)
        if order <= 0:
            violations["scene_ordering_violations"].append(
                "Scene order must be positive"
            )
        duplicate_order = await db.scene_plans.count_documents(
            {
                "project_id": pid,
                "chapter_plan_id": scene.get("chapter_plan_id"),
                "order": order,
            }
        )
        if duplicate_order > 1:
            violations["scene_ordering_violations"].append(
                f"Scene order {order} is duplicated in the chapter"
            )
        linked = sum(
            len(_ids(scene.get(field)))
            for field in (
                "knowledge_changes",
                "artifact_interactions",
                "timeline_impacts",
                "foreshadow_links",
            )
        )
        if linked == 0:
            warnings.append("Scene plan has no continuity ledger links")
        return await self._report(
            db,
            project_id=project_id,
            arc_id=str(scene.get("arc_id") or ""),
            chapter_plan_id=str(scene.get("chapter_plan_id") or ""),
            scene_id=scene_id,
            subject_type="scene_plan",
            subject_id=scene_id,
            version_number=0,
            stage="pre_generation",
            violations=violations,
            warnings=warnings,
            evidence=[
                f"scene_status={scene.get('status')}",
                f"chapter_status={(chapter or {}).get('status')}",
                f"arc_maturity={(development or {}).get('maturity_score')}",
            ],
            persist=persist,
        )

    async def validate_scene_draft(
        self,
        db,
        project_id: str,
        draft: Dict[str, Any],
        *,
        stage: str = "post_generation",
        persist: bool = True,
    ) -> Dict[str, Any]:
        preflight = await self.preflight_scene(
            db, project_id, str(draft.get("scene_id") or ""), persist=False
        )
        pid = ObjectId(project_id)
        scene = await db.scene_plans.find_one(
            {"project_id": pid, "scene_id": draft.get("scene_id")}
        ) or {}
        claims = draft.get("continuity_claims") or {}
        violations = {
            "missing_knowledge": list(preflight.get("missing_knowledge") or []),
            "contradictions": list(preflight.get("contradictions") or []),
            "artifact_violations": list(preflight.get("artifact_violations") or []),
            "timeline_violations": list(preflight.get("timeline_violations") or []),
            "character_violations": list(preflight.get("character_violations") or []),
            "power_violations": list(preflight.get("power_violations") or []),
            "dependency_violations": list(preflight.get("dependency_violations") or []),
            "foreshadow_violations": list(preflight.get("foreshadow_violations") or []),
            "chapter_membership_violations": list(
                preflight.get("chapter_membership_violations") or []
            ),
            "scene_ordering_violations": list(
                preflight.get("scene_ordering_violations") or []
            ),
        }
        if not str(draft.get("generated_text") or "").strip():
            violations["contradictions"].append("Generated scene text is empty")

        mappings = [
            (
                "knowledge_entry_ids",
                "knowledge_changes",
                "knowledge_entries",
                "entry_id",
                "missing_knowledge",
                "knowledge fact",
                ("title", "content"),
            ),
            (
                "artifact_ids",
                "artifact_interactions",
                "artifact_registry",
                "artifact_id",
                "artifact_violations",
                "artifact",
                ("item", "name"),
            ),
            (
                "timeline_entry_ids",
                "timeline_impacts",
                "timeline_entries",
                "entry_id",
                "timeline_violations",
                "timeline event",
                ("title", "summary"),
            ),
            (
                "foreshadow_ids",
                "foreshadow_links",
                "foreshadow_registry_v2",
                "entry_id",
                "foreshadow_violations",
                "foreshadowing promise",
                ("seed", "payoff_target"),
            ),
        ]
        for claim_key, plan_key, collection, key, violation_key, entity_label, label_keys in mappings:
            claimed = set(_ids(claims.get(claim_key)))
            planned = set(_ids(scene.get(plan_key)))
            rows = await db[collection].find(
                {"project_id": pid, key: {"$in": list(claimed | planned)}},
                {key: 1, **{label_key: 1 for label_key in label_keys}},
            ).to_list(length=1000) if claimed or planned else []
            by_id = {str(item.get(key)): item for item in rows}

            def author_label(value: str) -> str:
                row = by_id.get(str(value)) or {}
                return next(
                    (
                        str(row.get(label_key))
                        for label_key in label_keys
                        if str(row.get(label_key) or "").strip()
                    ),
                    f"unmatched {entity_label}",
                )

            missing = sorted(planned - claimed)
            if missing:
                violations[violation_key].extend(
                    f"Missing planned {entity_label}: {author_label(value)}"
                    for value in missing
                )
            if claimed:
                found = {str(item.get(key)) for item in rows if item.get(key)}
                unknown = sorted(claimed - found)
                if unknown:
                    violations[violation_key].append(
                        f"An AI-supplied {entity_label} could not be matched to this project."
                    )
            undeclared = sorted(claimed - planned)
            if undeclared:
                violations[violation_key].append(
                    f"The draft references {entity_label} material not declared by the scene plan: "
                    + ", ".join(author_label(value) for value in undeclared)
                )

        claimed_characters = set(_ids(claims.get("characters")))
        allowed_characters = set(_ids(scene.get("character_focus")))
        unexpected_characters = sorted(claimed_characters - allowed_characters)
        if unexpected_characters:
            violations["character_violations"].append(
                "Characters outside scene focus: " + ", ".join(unexpected_characters)
            )
        claimed_power = _ids(claims.get("power_changes"))
        if claimed_power:
            progressions = await db.power_progressions.find(
                {"project_id": pid, "arc_id": scene.get("arc_id")}
            ).to_list(length=500)
            allowed_power = {
                str(value)
                for item in progressions
                for field in ("new_abilities", "mastered_abilities")
                for value in item.get(field) or []
            }
            unexpected_power = sorted(set(claimed_power) - allowed_power)
            if unexpected_power:
                violations["power_violations"].append(
                    "Undeclared power changes: " + ", ".join(unexpected_power)
                )
        claimed_dependencies = set(_ids(claims.get("dependency_ids")))
        if claimed_dependencies:
            allowed_dependencies = {
                item["dependency_id"]
                for item in await db.arc_dependencies.find(
                    {"project_id": pid, "arc_id": scene.get("arc_id")},
                    {"dependency_id": 1},
                ).to_list(length=500)
            }
            unknown_dependencies = sorted(
                claimed_dependencies - allowed_dependencies
            )
            if unknown_dependencies:
                violations["dependency_violations"].append(
                    "Unknown dependency claims: " + ", ".join(unknown_dependencies)
                )
        return await self._report(
            db,
            project_id=project_id,
            arc_id=str(draft.get("arc_id") or ""),
            chapter_plan_id=str(draft.get("chapter_plan_id") or ""),
            scene_id=str(draft.get("scene_id") or ""),
            subject_type="scene_draft",
            subject_id=str(draft.get("draft_id") or ""),
            version_number=int(draft.get("version_number") or 0),
            stage=stage,
            violations=violations,
            warnings=list(preflight.get("warnings") or []),
            evidence=[
                f"scene_id={draft.get('scene_id')}",
                f"version={draft.get('version_number')}",
            ],
            persist=persist,
        )

    async def validate_chapter_draft(
        self,
        db,
        project_id: str,
        draft: Dict[str, Any],
        *,
        stage: str = "post_generation",
        persist: bool = True,
    ) -> Dict[str, Any]:
        pid = ObjectId(project_id)
        if draft.get("workflow_mode") == "discovery":
            generated_text = str(draft.get("generated_text") or "").strip()
            violations: Dict[str, list[str]] = {key: [] for key in (
                "missing_knowledge", "contradictions", "artifact_violations", "timeline_violations",
                "character_violations", "power_violations", "dependency_violations",
                "foreshadow_violations", "chapter_membership_violations", "scene_ordering_violations",
            )}
            warnings: list[str] = []
            findings: list[Dict[str, Any]] = []

            def add_finding(
                category: str,
                message: str,
                *,
                violation_key: str = "contradictions",
                severity: str = "error",
                evidence: Dict[str, Any] | None = None,
            ) -> None:
                if severity == "warning":
                    warnings.append(message)
                else:
                    violations[violation_key].append(message)
                findings.append({
                    "category": category,
                    "severity": severity,
                    "message": message,
                    "evidence": evidence or {},
                })
            count = len(generated_text.split())
            minimum = int(draft.get("target_word_min") or 0)
            maximum = int(draft.get("target_word_max") or 0)
            if not generated_text:
                violations["chapter_membership_violations"].append("Discovery draft contains no prose")
            if minimum and count < minimum:
                warnings.append(f"The draft is {minimum - count} words below the requested minimum.")
            if maximum and count > maximum:
                warnings.append(f"The draft is {count - maximum} words above the requested maximum.")
            # Discovery prose has no scene-plan membership check, so explicitly
            # compare common high-impact duration claims against confirmed
            # planning/decision/timeline authority before approval.
            authority_documents: list[tuple[str, Dict[str, Any]]] = []
            authoritative_claims: list[tuple[int, str, str]] = []
            for collection, query in (
                ("canon_registry", {"project_id": pid, "active": {"$ne": False}}),
                ("decision_registry", {"project_id": pid, "status": {"$in": ["approved", "resolved"]}}),
                ("timeline_entries", {"project_id": pid, "status": {"$nin": ["rejected", "candidate"]}, "authority_status": {"$in": ["approved", "confirmed", "active"]}}),
            ):
                async for item in db[collection].find(query):
                    authority_documents.append((collection, item))
                    authoritative_claims.extend(
                        (value, phrase, collection)
                        for value, phrase in _duration_claims(
                            _authority_text(item) or json.dumps(item, default=str, ensure_ascii=True)
                        )
                    )
            confirmed_specs = (
                "character_bibles", "relationship_graphs", "plot_threads",
                "timeline_entries", "knowledge_entries", "artifact_registry",
                "mystery_registry", "story_arcs", "chapter_plans", "scene_plans",
            )
            for collection in confirmed_specs:
                async for item in db[collection].find({
                    "project_id": pid,
                    "source_type": "story_studio_planning",
                    "authority_status": "confirmed",
                }):
                    authority_documents.append((collection, item))
                    authoritative_claims.extend(
                        (value, phrase, collection)
                        for value, phrase in _duration_claims(
                            _authority_text(item) or json.dumps(item, default=str, ensure_ascii=True)
                        )
                    )
            draft_claims = _duration_claims(generated_text)
            if authoritative_claims and draft_claims:
                expected_values = {value for value, _, _ in authoritative_claims}
                conflicts = [(value, phrase) for value, phrase in draft_claims if value not in expected_values]
                if conflicts and not _explicitly_planned_change(draft, "chronology"):
                    expected = ", ".join(sorted({phrase for _, phrase, _ in authoritative_claims}))
                    actual = ", ".join(sorted({phrase for _, phrase in conflicts}))
                    add_finding(
                        "chronology_contradiction",
                        f"Confirmed story authority states {expected}, but this draft states {actual}. Review or correct the prose before approval.",
                        violation_key="timeline_violations",
                        evidence={"authority": expected, "draft": actual},
                    )

            draft_polarities = _polarity_statements(generated_text)
            for collection, authority_document in authority_documents:
                for assertion, authority_negated in _polarity_statements(
                    _authority_text(authority_document)
                ).items():
                    if assertion in draft_polarities and draft_polarities[assertion] != authority_negated:
                        if _explicitly_planned_change(draft, *assertion.split()[:2]):
                            continue
                        add_finding(
                            "authority_direct_conflict",
                            f"The draft directly reverses a confirmed {collection} assertion: {assertion}.",
                            evidence={
                                "source_collection": collection,
                                "source_id": str(authority_document.get("_id") or ""),
                                "authority_negated": authority_negated,
                                "draft_negated": draft_polarities[assertion],
                            },
                        )

            metadata = draft.get("discovery_metadata") or {}
            expected_person = str(metadata.get("pov_person") or "").strip().lower() or None
            previous = await db.chapter_drafts.find_one(
                {
                    "project_id": pid,
                    "workflow_mode": "discovery",
                    "chapter_number": {"$lt": int(draft.get("chapter_number") or 0)},
                    "status": "approved",
                    "active": {"$ne": False},
                },
                sort=[("chapter_number", -1), ("version_number", -1)],
            )
            previous_person = _narrative_person(str((previous or {}).get("generated_text") or ""))
            actual_person = _narrative_person(generated_text)
            required_person = expected_person or previous_person
            if (
                required_person
                and actual_person
                and required_person != actual_person
                and not _explicitly_planned_change(draft, "pov")
            ):
                add_finding(
                    "pov_person_shift",
                    f"The writing contract expects {required_person}, but the draft is predominantly {actual_person}.",
                    violation_key="character_violations",
                    evidence={
                        "expected_person": required_person,
                        "actual_person": actual_person,
                        "previous_chapter": (previous or {}).get("chapter_number"),
                    },
                )

            # Confirmed structured relationship state outranks prose-derived or
            # extracted relationship claims. This intentionally checks only
            # unambiguous kinship terms in this P0 pass.
            async for relationship in db.relationship_graphs.find({
                "project_id": pid,
                "authority_status": {"$in": ["approved", "confirmed", "active"]},
                "status": {"$nin": ["candidate", "rejected", "superseded", "stale"]},
            }):
                name_a = str(relationship.get("character_a") or relationship.get("from_character") or "")
                name_b = str(relationship.get("character_b") or relationship.get("to_character") or "")
                draft_relationships = _relationship_claims(generated_text, name_a, name_b)
                authoritative_relationships = {
                    term for term in _KINSHIP_TERMS
                    if re.search(rf"\b{re.escape(term)}\b", _authority_text(relationship).lower())
                }
                authority_negates_kinship = bool(re.search(
                    r"\b(?:not|never)\b.{0,24}\b(?:brother|sister|sibling|related)\b",
                    _authority_text(relationship).lower(),
                ))
                conflict = bool(draft_relationships) and (
                    authority_negates_kinship
                    or (
                        authoritative_relationships
                        and draft_relationships.isdisjoint(authoritative_relationships)
                    )
                )
                if conflict and not _explicitly_planned_change(draft, name_a.split()[0], name_b.split()[0]):
                    add_finding(
                        "relationship_contradiction",
                        f"The draft's {name_a}/{name_b} kinship claim conflicts with their confirmed structured relationship.",
                        violation_key="character_violations",
                        evidence={
                            "relationship_id": relationship.get("relationship_id"),
                            "authority": _authority_text(relationship),
                            "draft_terms": sorted(draft_relationships),
                        },
                    )

            # Ownership is historical state, so only the latest valid owner at
            # the draft's chapter boundary is checked.
            chapter_number = int(draft.get("chapter_number") or 0)
            async for artifact in db.artifact_registry.find({
                "project_id": pid,
                "authority_status": {"$in": ["approved", "confirmed", "active"]},
                "status": {"$nin": ["candidate", "rejected", "superseded", "stale"]},
                "$and": [
                    {"$or": [{"valid_from_chapter": {"$exists": False}}, {"valid_from_chapter": {"$lte": chapter_number}}]},
                    {"$or": [{"valid_to_chapter": {"$exists": False}}, {"valid_to_chapter": None}, {"valid_to_chapter": {"$gte": chapter_number}}]},
                ],
            }):
                item = str(artifact.get("item") or artifact.get("name") or "").strip()
                owner = str(artifact.get("owner") or "").strip()
                if not item or not owner or item.lower() not in generated_text.lower():
                    continue
                pattern = re.compile(
                    rf"\b([A-Z][A-Za-z'-]+)\b\s+(?:has|holds|carries|owns|possesses)\s+(?:the\s+)?{re.escape(item)}\b",
                    re.IGNORECASE,
                )
                holders = {match.group(1).lower() for match in pattern.finditer(generated_text)}
                invalid_holders = sorted(holder for holder in holders if holder not in owner.lower())
                if invalid_holders and not _explicitly_planned_change(draft, item.lower()):
                    add_finding(
                        "ownership_state_contradiction",
                        f"The draft gives {item} to {', '.join(invalid_holders)}, but confirmed state assigns it to {owner}.",
                        violation_key="artifact_violations",
                        evidence={"artifact_id": artifact.get("artifact_id"), "owner": owner},
                    )

            pov_character = str(metadata.get("pov_character") or "").strip()
            if pov_character:
                async for knowledge in db.knowledge_entries.find({
                    "project_id": pid,
                    "authority_status": {"$in": ["approved", "confirmed", "active"]},
                    "status": {"$nin": ["candidate", "rejected", "superseded", "stale"]},
                }):
                    known_by = {str(value).strip().lower() for value in knowledge.get("known_by") or []}
                    not_known_by = {str(value).strip().lower() for value in knowledge.get("not_known_by") or []}
                    pov = pov_character.lower()
                    unavailable = pov in not_known_by or (known_by and pov not in known_by)
                    if not unavailable:
                        continue
                    title = str(knowledge.get("title") or "").strip()
                    content = str(knowledge.get("content") or "").strip()
                    distinctive_terms = [
                        term.lower() for term in re.findall(r"[A-Za-z][A-Za-z'-]{4,}", f"{title} {content}")
                        if term.lower() not in {"about", "their", "there", "which", "story", "knows"}
                    ]
                    if not distinctive_terms or not any(term in generated_text.lower() for term in distinctive_terms[:8]):
                        continue
                    knowledge_verb = re.search(
                        rf"\b{re.escape(pov_character.split()[0])}\b.{{0,40}}\b(?:knew|knows|realized|remembered|understood|discovered|recognized)\b",
                        generated_text,
                        re.IGNORECASE,
                    )
                    first_person_leak = actual_person == "first person"
                    if (knowledge_verb or first_person_leak) and not _explicitly_planned_change(draft, "learn", title.lower()):
                        add_finding(
                            "character_knowledge_leakage",
                            f"The draft presents {title or 'restricted information'} as known by {pov_character} before the knowledge ledger permits it.",
                            violation_key="missing_knowledge",
                            evidence={
                                "entry_id": knowledge.get("entry_id"),
                                "known_by": sorted(known_by),
                                "not_known_by": sorted(not_known_by),
                            },
                        )
            return await self._report(
                db, project_id=project_id, arc_id="", chapter_plan_id="", scene_id=None,
                subject_type="chapter_draft", subject_id=str(draft.get("draft_id") or ""),
                version_number=int(draft.get("version_number") or 1), stage=stage,
                violations=violations, warnings=warnings, findings=findings,
                evidence=["workflow_mode=discovery", f"word_count={count}"], persist=persist,
            )
        chapter = await db.chapter_plans.find_one(
            {
                "project_id": pid,
                "chapter_plan_id": draft.get("chapter_plan_id"),
            }
        )
        violations: Dict[str, list[str]] = {
            "missing_knowledge": [],
            "contradictions": [],
            "artifact_violations": [],
            "timeline_violations": [],
            "character_violations": [],
            "power_violations": [],
            "dependency_violations": [],
            "foreshadow_violations": [],
            "chapter_membership_violations": [],
            "scene_ordering_violations": [],
        }
        if not chapter:
            violations["chapter_membership_violations"].append(
                "Chapter plan not found"
            )
            scenes = []
        else:
            if str(chapter.get("status") or "").lower() != "approved":
                violations["chapter_membership_violations"].append(
                    "Chapter plan is not approved"
                )
            development = await arc_development_service.evaluate(
                db, project_id, str(chapter.get("arc_id") or ""), persist=False
            )
            if not development["draftable"]:
                violations["dependency_violations"].extend(
                    development.get("blockers") or ["Arc is not draftable"]
                )
            scenes = await db.scene_plans.find(
                {
                    "project_id": pid,
                    "chapter_plan_id": chapter.get("chapter_plan_id"),
                }
            ).sort("order", 1).to_list(length=1000)
        expected_scene_ids = [scene["scene_id"] for scene in scenes]
        source_ids = _ids(draft.get("source_scene_draft_ids"))
        source_drafts = []
        for source_id in source_ids:
            source = await db.scene_drafts.find_one(
                {"project_id": pid, "draft_id": source_id}
            )
            if not source:
                violations["chapter_membership_violations"].append(
                    f"Unknown scene draft {source_id}"
                )
                continue
            source_drafts.append(source)
            if not source.get("active") or source.get("status") != "approved":
                violations["chapter_membership_violations"].append(
                    f"Scene draft {source_id} is not active and approved"
                )
        actual_scene_ids = [str(item.get("scene_id") or "") for item in source_drafts]
        if actual_scene_ids != expected_scene_ids:
            violations["scene_ordering_violations"].append(
                "Approved scene drafts do not exactly match chapter scene order"
            )
        generated_text = str(draft.get("generated_text") or "")
        cursor = 0
        for source in source_drafts:
            text = str(source.get("generated_text") or "")
            index = generated_text.find(text, cursor)
            if index < 0:
                violations["contradictions"].append(
                    f"Chapter does not preserve scene draft {source.get('draft_id')} verbatim"
                )
                continue
            cursor = index + len(text)
        transition_pairs = {
            (
                str(item.get("from_scene_draft_id") or ""),
                str(item.get("to_scene_draft_id") or ""),
            )
            for item in draft.get("transitions") or []
            if isinstance(item, dict)
        }
        allowed_pairs = set(zip(source_ids, source_ids[1:]))
        invalid_pairs = transition_pairs - allowed_pairs
        if invalid_pairs:
            violations["scene_ordering_violations"].append(
                "Transitions reference non-adjacent or unknown scenes"
            )
        return await self._report(
            db,
            project_id=project_id,
            arc_id=str(draft.get("arc_id") or ""),
            chapter_plan_id=str(draft.get("chapter_plan_id") or ""),
            scene_id=None,
            subject_type="chapter_draft",
            subject_id=str(draft.get("draft_id") or ""),
            version_number=int(draft.get("version_number") or 0),
            stage=stage,
            violations=violations,
            warnings=[],
            evidence=[
                f"source_scene_count={len(source_ids)}",
                f"chapter_scene_count={len(expected_scene_ids)}",
            ],
            persist=persist,
        )


draft_validation_service = DraftValidationService()
