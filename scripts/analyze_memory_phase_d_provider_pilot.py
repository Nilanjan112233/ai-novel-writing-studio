"""Analyze the real-provider Phase D pilot without calling a model."""
from __future__ import annotations

import json
import math
import re
import statistics
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = ROOT / "artifacts" / "memory-phase-d-provider-pilot"
ARMS = ("current", "fact_only", "progressive")
AGENTS = ("RelationshipAgent", "CharacterJourneyAgent", "MysteryAgent", "ArcArchitectAgent", "PacingAgent")


def load(name: str) -> Any:
    return json.loads((ARTIFACT_DIR / name).read_text(encoding="utf-8"))


def text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str).lower()


def has(blob: str, *terms: str) -> bool:
    return any(term.lower() in blob for term in terms)


def output_for(artifact: dict[str, Any], agent: str) -> dict[str, Any]:
    return next((row.get("structured_output") or {} for row in artifact.get("agent_outputs") or [] if row.get("agent_name") == agent), {})


def quality_checks(agent: str, value: dict[str, Any]) -> dict[str, bool]:
    blob = text(value)
    story_detail = has(blob, "lindon", "ledger", "safe deposit", "funeral", "mill", "settlement", "photograph")
    if agent == "RelationshipAgent":
        return {
            "relationship_direction": has(blob, "ally", "cooperat", "partnership", "adversarial"),
            "conflict_trust_progression": has(blob, "trust", "distrust", "suspicion"),
            "relevant_characters": "mara" in blob and "ivo" in blob,
            "prior_interaction_continuity": story_detail,
            "chapter_10_boundary": "chapter 10" in blob,
        }
    if agent == "CharacterJourneyAgent":
        return {
            "character_state": "mara" in blob and has(blob, "current", "investigat", "search"),
            "progression": has(blob, "growth", "arc", "transition", "from "),
            "motivation": "elias" in blob and has(blob, "find", "search", "locate"),
            "consequences": has(blob, "risk", "fear", "stakes", "cost", "expos"),
            "episode_continuity": story_detail,
        }
    if agent == "MysteryAgent":
        truth = str(value.get("mysteries", [{}])[0].get("truth") if value.get("mysteries") else "").lower()
        possibility_only = not truth or has(truth, "unknown", "possible", "may ")
        return {
            "clue_progression": has(blob, "clue", "evidence", "investigat"),
            "unresolved_questions": has(blob, "open", "unresolved", "question", "mystery"),
            "reveal_timing": "chapter 10" in blob,
            "no_premature_answer": possibility_only,
            "five_year_chronology": "five years" in blob or "five-year" in blob,
        }
    if agent == "ArcArchitectAgent":
        return {
            "arc_objective": has(blob, "goal", "purpose", "objective"),
            "causal_progression": has(blob, "major_events", "dependencies", "catalyst", "pivot", "bridge"),
            "character_mystery_integration": all(term in blob for term in ("mara", "ivo", "elias")),
            "chapter_reveal_structure": "chapter 10" in blob or '"chapter_range": [10' in blob,
            "actionable_structure": has(blob, "chapter_range", "timeline_events", "major_events"),
        }
    return {
        "escalation": has(blob, "escalat", "rising stakes", "increasing"),
        "chapter_scene_rhythm": has(blob, "chapter", "sequence", "dead zone", "cadence"),
        "repetition_control": has(blob, "repet", "stagn", "dead zone", "stall"),
        "reveal_timing": "chapter 10" in blob,
        "pacing_consequences": has(blob, "risk", "consequence", "collapse", "dilute", "stakes"),
    }


def safety(artifact: dict[str, Any]) -> dict[str, Any]:
    candidate = rejected = future = knowledge = duplicates = 0
    authority_complete = 0
    chronology_passes = 0
    for packet in artifact.get("context_packets") or []:
        attribution = packet.get("phase_e_attribution") or {}
        authority_complete += int(bool(attribution.get("authority_complete")))
        hits = ((packet.get("packet") or {}).get("retrieved_memory") or [])
        identities = []
        for hit in hits:
            metadata = hit.get("metadata") or {}
            status_blob = " ".join(str(metadata.get(key) or "").lower() for key in ("status", "candidate_status", "approval_status", "authority_status"))
            candidate += int("candidate" in status_blob or "pending" in status_blob)
            rejected += int("rejected" in status_blob)
            future += int(bool(metadata.get("future_chapter")))
            knowledge += int(bool(metadata.get("pov_knowledge_leak")))
            identities.append(str(metadata.get("logical_identity") or hit.get("logical_identity") or ""))
        duplicates += max(0, len([x for x in identities if x]) - len(set(x for x in identities if x)))
    for agent in AGENTS:
        blob = text(output_for(artifact, agent))
        good = "five years" in blob or "five-year" in blob or "5-year" in blob
        silently_two = bool(re.search(r"elias (?:had )?disappeared two years", blob)) and not has(blob, "conflict", "contradict", "five years", "five-year")
        chronology_passes += int(good and not silently_two)
    return {
        "authority_coverage": authority_complete,
        "authority_coverage_percent": round(100 * authority_complete / len(AGENTS), 2),
        "candidate_leakage": candidate,
        "rejected_leakage": rejected,
        "future_leakage": future,
        "pov_knowledge_leakage": knowledge,
        "duplicate_logical_hits": duplicates,
        "chronology_output_passes": chronology_passes,
    }


def evidence(artifact: dict[str, Any], arm: str) -> dict[str, Any]:
    rows = []
    for call in artifact.get("calls") or []:
        sources = call.get("prompt_tokens_by_source") or {}
        context = call.get("project_context") or {}
        manifest = context.get("phase_d_evidence_manifest") or {}
        if arm == "current":
            fact_tokens = int(sources.get("native_retrieval") or 0)
            episode_tokens = int(sources.get("chapter_episode_memory") or 0)
        else:
            fact_tokens = int(sources.get("native_retrieval") or 0)
            episode_tokens = int(sources.get("chapter_episode_memory") or 0)
        raw_tokens = int(sources.get("raw_evidence") or 0)
        rows.append({
            "specialist": call.get("agent_name"),
            "prompt_tokens": int(call.get("prompt_tokens") or 0),
            "response_tokens": int(call.get("response_tokens") or 0),
            "total_tokens": int(call.get("prompt_tokens") or 0) + int(call.get("response_tokens") or 0),
            "latency_ms": int(call.get("wall_latency_ms") or 0),
            "provider": call.get("provider"), "model": call.get("model"),
            "retries": int(call.get("retry_count") or 0), "fallback": bool(call.get("fallback_used")),
            "instruction_tokens": int(sources.get("instruction") or 0),
            "authority_tokens": int(sources.get("authority") or 0),
            "role_context_tokens": int(sources.get("role_specific_structured_context") or 0),
            "fact_tokens": fact_tokens,
            "episode_tokens": episode_tokens,
            "raw_tokens": raw_tokens,
            "handoff_tokens": int(sources.get("previous_agent_handoffs") or 0),
            "evidence_level": manifest.get("evidence_level") or "current_phase_c",
            "routing_reason": manifest.get("reason"),
            "manifest_hash": manifest.get("manifest_hash"),
        })
    return {
        "specialists": rows,
        "fact_tokens": sum(row["fact_tokens"] for row in rows),
        "episode_tokens": sum(row["episode_tokens"] for row in rows),
        "raw_tokens": sum(row["raw_tokens"] for row in rows),
        "evidence_tokens": sum(row["fact_tokens"] + row["episode_tokens"] + row["raw_tokens"] for row in rows),
        "authority_tokens": sum(row["authority_tokens"] for row in rows),
        "handoff_tokens": sum(row["handoff_tokens"] for row in rows),
    }


def coherence(artifact: dict[str, Any]) -> dict[str, Any]:
    calls = artifact.get("calls") or []
    expected = {"RelationshipAgent": 0, "CharacterJourneyAgent": 1, "MysteryAgent": 2, "ArcArchitectAgent": 3, "PacingAgent": 3}
    handoffs = {}
    integration = {}
    recommendations = []
    for call in calls:
        agent = str(call.get("agent_name"))
        count = len((call.get("project_context") or {}).get("previous_agent_handoffs") or [])
        handoffs[agent] = {"expected": expected[agent], "actual": count, "pass": count >= expected[agent]}
        out = output_for(artifact, agent)
        blob = text(out)
        integration[agent] = {
            "mara": "mara" in blob,
            "elias": "elias" in blob,
            "chapter_10": "chapter 10" in blob,
            "ivo_where_relevant": (agent == "MysteryAgent" and "ivo" in blob) or agent not in {"MysteryAgent"},
        }
        recommendations.append(str(out.get("recommendation") or ""))
    similarities = []
    for index, left in enumerate(recommendations):
        a = set(re.findall(r"[a-z]{4,}", left.lower()))
        for right in recommendations[index + 1:]:
            b = set(re.findall(r"[a-z]{4,}", right.lower()))
            similarities.append(len(a & b) / max(1, len(a | b)))
    return {
        "handoff_passes": sum(row["pass"] for row in handoffs.values()),
        "handoffs": handoffs,
        "integration_passes": sum(all(row.values()) for row in integration.values()),
        "integration": integration,
        "mean_recommendation_jaccard": round(statistics.mean(similarities), 4) if similarities else 0.0,
    }


def main() -> None:
    artifacts = {arm: load(f"{arm.replace('_', '-')}-provider-run.json") for arm in ARMS}
    blind = load("blind-manual-review.json")
    mapping = load("blind-map.json")["mapping"]
    blind_by_arm = {}
    for review in blind["reviews"]:
        arm = mapping[review["code"]]
        blind_by_arm[arm] = {
            "code": review["code"],
            "scores": review["scores"],
            "mean": round(statistics.mean(review["scores"].values()), 3),
            "notes": review["notes"],
        }

    arms = {}
    for arm, artifact in artifacts.items():
        per_agent = {}
        for agent in AGENTS:
            checks = quality_checks(agent, output_for(artifact, agent))
            per_agent[agent] = {"checks": checks, "passed": sum(checks.values()), "total": len(checks), "percent": round(100 * sum(checks.values()) / len(checks), 2)}
        ev = evidence(artifact, arm)
        arms[arm] = {
            "totals": artifact["totals"],
            "evidence": ev,
            "quality": {"specialists": per_agent, "passed": sum(row["passed"] for row in per_agent.values()), "total": sum(row["total"] for row in per_agent.values())},
            "blind_review": blind_by_arm[arm],
            "coherence": coherence(artifact),
            "safety": safety(artifact),
        }

    current = arms["current"]
    progressive = arms["progressive"]
    fact = arms["fact_only"]
    current_prompt = current["totals"]["prompt_tokens"]
    progressive_prompt = progressive["totals"]["prompt_tokens"]
    current_evidence = current["evidence"]["evidence_tokens"]
    progressive_evidence = progressive["evidence"]["evidence_tokens"]
    comparisons = {
        "progressive_prompt_reduction_percent": round(100 * (current_prompt - progressive_prompt) / current_prompt, 2),
        "progressive_evidence_reduction_percent": round(100 * (current_evidence - progressive_evidence) / current_evidence, 2),
        "progressive_response_change_percent": round(100 * (progressive["totals"]["response_tokens"] - current["totals"]["response_tokens"]) / current["totals"]["response_tokens"], 2),
        "progressive_total_token_reduction_percent": round(100 * ((current_prompt + current["totals"]["response_tokens"]) - (progressive_prompt + progressive["totals"]["response_tokens"])) / (current_prompt + current["totals"]["response_tokens"]), 2),
        "progressive_cost_reduction_percent": round(100 * (current["totals"]["estimated_provider_cost_usd"] - progressive["totals"]["estimated_provider_cost_usd"]) / current["totals"]["estimated_provider_cost_usd"], 2),
        "fact_prompt_reduction_percent": round(100 * (current_prompt - fact["totals"]["prompt_tokens"]) / current_prompt, 2),
        "fact_cost_reduction_percent": round(100 * (current["totals"]["estimated_provider_cost_usd"] - fact["totals"]["estimated_provider_cost_usd"]) / current["totals"]["estimated_provider_cost_usd"], 2),
    }
    failure = load("failure-resume.json")
    raw = load("raw-evidence-provider-test.json")
    raw_episode = raw["results"][0]["parsed"]
    raw_exact = raw["results"][1]["parsed"]
    gates = {
        "evidence_reduction_at_least_30": comparisons["progressive_evidence_reduction_percent"] >= 30,
        "prompt_reduction_at_least_20": comparisons["progressive_prompt_reduction_percent"] >= 20,
        "labelled_quality_non_inferior": progressive["quality"]["passed"] >= current["quality"]["passed"],
        "blind_usefulness_non_inferior": progressive["blind_review"]["scores"]["usefulness"] >= current["blind_review"]["scores"]["usefulness"],
        "blind_overall_non_inferior": progressive["blind_review"]["mean"] >= current["blind_review"]["mean"],
        "cross_agent_coherence_non_inferior": progressive["coherence"]["handoff_passes"] >= current["coherence"]["handoff_passes"] and progressive["coherence"]["integration_passes"] >= current["coherence"]["integration_passes"],
        "authority_coverage_100": progressive["safety"]["authority_coverage_percent"] == 100,
        "zero_safety_leakage": all(progressive["safety"][key] == 0 for key in ("candidate_leakage", "rejected_leakage", "future_leakage", "pov_knowledge_leakage", "duplicate_logical_hits")),
        "no_retry_fallback_regression": progressive["totals"]["retries"] <= current["totals"]["retries"] and progressive["totals"]["fallbacks"] <= current["totals"]["fallbacks"],
        "total_cost_lower_or_equal": progressive["totals"]["estimated_provider_cost_usd"] <= current["totals"]["estimated_provider_cost_usd"],
        "deterministic_resume_failure": failure["all_manifests_repeat_identically"] and failure["no_duplicate_handoffs"] and failure["no_duplicate_outputs"] and all(not row["invented_evidence"] for row in failure["failure_cases"]),
        "raw_branch_validated": raw_episode.get("assessment") == "insufficient_evidence" and raw_exact.get("assessment") in {"subtle", "explicit"},
    }
    accepted = all(gates.values())
    payload = {
        "schema_version": 1,
        "provider": phase_provider(artifacts),
        "arms": arms,
        "comparisons": comparisons,
        "raw_evidence_test": raw,
        "failure_resume": failure,
        "acceptance_gates": gates,
        "accepted": accepted,
        "recommendation": "KEEP_CURRENT_PHASE_C" if not accepted else "RECOMMEND_SEPARATE_DEVELOP_STORY_PHASE_D_IMPLEMENTATION",
        "principal_quality_finding": "Progressive preserved deterministic requirements and coherence but blind usefulness/overall scores were below current Phase C; Mystery lost the most episode-specific clue detail.",
    }
    (ARTIFACT_DIR / "pilot-comparison.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"comparisons": comparisons, "quality": {arm: arms[arm]["quality"] for arm in ARMS}, "blind": blind_by_arm, "gates": gates, "accepted": accepted, "recommendation": payload["recommendation"]}, indent=2, ensure_ascii=False))


def phase_provider(artifacts: dict[str, Any]) -> dict[str, Any]:
    pairs = {(value.get("matched_provider"), value.get("matched_model")) for value in artifacts.values()}
    return {"constant": len(pairs) == 1, "pairs": [list(pair) for pair in sorted(pairs)]}


if __name__ == "__main__":
    main()
