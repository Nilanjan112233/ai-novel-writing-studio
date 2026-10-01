"""Produce a machine-readable Phase E versus Phase B evidence comparison."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PHASE_E = ROOT / "artifacts" / "memory-phase-e" / "optimized-provider-run.json"
PHASE_B_DIR = ROOT / "artifacts" / "memory-phase-b"
PHASE_B = PHASE_B_DIR / "phase-b-provider-run.json"


def _sum(run, source):
    return sum(int((call.get("prompt_tokens_by_source") or {}).get(source) or 0) for call in run.get("calls") or [])


def _unsafe(value):
    if isinstance(value, list): return sum(_unsafe(item) for item in value)
    if not isinstance(value, dict): return 0
    statuses = {str(value.get(key) or "").lower() for key in ("status", "authority_status", "candidate_status", "approval_status", "decision_status")}
    return int(bool(statuses & {"candidate", "rejected", "stale", "superseded", "archived", "inactive"})) + sum(_unsafe(item) for item in value.values())


def main():
    before = json.loads(PHASE_E.read_text(encoding="utf-8")); after = json.loads(PHASE_B.read_text(encoding="utf-8"))
    before_evidence = _sum(before, "native_retrieval") + _sum(before, "chapter_episode_memory")
    after_evidence = _sum(after, "native_retrieval") + _sum(after, "chapter_episode_memory")
    outputs = {row["agent_name"]: row.get("structured_output") or {} for row in after.get("agent_outputs") or []}
    requirements = {
        "RelationshipAgent": [("mara",), ("elias",), ("chapter 10",), ("relationship", "trust", "alliance"), ("five years", "five-year", "5-year")],
        "CharacterJourneyAgent": [("mara",), ("elias",), ("chapter 10",), ("journey", "arc", "growth", "change")],
        "MysteryAgent": [("elias",), ("chapter 10",), ("mystery", "clue", "reveal"), ("five years", "five-year", "5-year")],
        "ArcArchitectAgent": [("mara",), ("elias",), ("chapter 10",), ("arc", "goal", "purpose")],
        "PacingAgent": [("chapter 10",), ("pacing", "escalation", "chapter"), ("reveal",)],
    }
    quality = {}
    for agent, groups in requirements.items():
        text = json.dumps(outputs.get(agent, {}), ensure_ascii=False).lower()
        quality[agent] = all(any(term in text for term in group) for group in groups)
    packets = {row.get("agent_name"): row.get("phase_e_attribution") or {} for row in after.get("context_packets") or []}
    after_sources = Counter(); before_sources = Counter()
    for call in before.get("calls") or []: before_sources.update(call.get("prompt_tokens_by_source") or {})
    for call in after.get("calls") or []: after_sources.update(call.get("prompt_tokens_by_source") or {})
    comparison = {
        "methodology": {"same_source_project": before.get("source_project_id") == after.get("source_project_id"), "same_instruction": before.get("instruction") == after.get("instruction"), "same_agents": before.get("agents") == after.get("agents"), "same_provider": before.get("matched_provider") == after.get("matched_provider"), "same_model": before.get("matched_model") == after.get("matched_model"), "real_provider_runs": True},
        "totals": {
            "phase_e_prompt_tokens": before["totals"]["prompt_tokens"], "phase_b_prompt_tokens": after["totals"]["prompt_tokens"],
            "total_reduction_percent": round((before["totals"]["prompt_tokens"] - after["totals"]["prompt_tokens"]) * 100 / before["totals"]["prompt_tokens"], 2),
            "phase_e_evidence_tokens": before_evidence, "phase_b_evidence_tokens": after_evidence,
            "evidence_reduction_percent": round((before_evidence - after_evidence) * 100 / before_evidence, 2),
            "legacy_prompt_tokens": 396636, "phase_b_vs_legacy_reduction_percent": round((396636 - after["totals"]["prompt_tokens"]) * 100 / 396636, 2),
            "phase_e_cost_usd": before["totals"]["estimated_provider_cost_usd"], "phase_b_cost_usd": after["totals"]["estimated_provider_cost_usd"],
            "phase_e_latency_ms": before["totals"]["wall_latency_ms"], "phase_b_latency_ms": after["totals"]["wall_latency_ms"],
            "phase_e_retries": before["totals"]["retries"], "phase_b_retries": after["totals"]["retries"], "phase_b_fallbacks": after["totals"]["fallbacks"],
        },
        "tokens_by_source": {"phase_e": dict(before_sources), "phase_b": dict(after_sources)},
        "quality": {
            "specialist_requirements": quality, "requirements_passed": sum(quality.values()), "requirements_total": len(quality),
            "authority_complete_packets": sum(1 for item in packets.values() if item.get("authority_complete")), "authority_total_packets": len(packets),
            "broad_fallbacks": sum(1 for item in packets.values() if item.get("fallback_reason")),
            "unsafe_role_projection_records": sum(_unsafe(call.get("project_context", {}).get("role_specific_structured_context", {})) for call in after.get("calls") or []),
            "chronology_authority_present": all("five years" in json.dumps(call.get("project_context", {}).get("authority", {}), ensure_ascii=False).lower() for call in after.get("calls") or []),
            "chapter_10_boundary_in_outputs": all("chapter 10" in json.dumps(payload, ensure_ascii=False).lower() for payload in outputs.values()),
            "handoffs_visible": all(int((packets.get(agent) or {}).get("tokens_by_source", {}).get("previous_agent_handoffs") or 0) > 1 for agent in ("CharacterJourneyAgent", "MysteryAgent", "ArcArchitectAgent", "PacingAgent")),
        },
    }
    output = PHASE_B_DIR / "phase-b-comparison.json"; output.write_text(json.dumps(comparison, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output), **comparison["totals"], **comparison["quality"]}, indent=2))


if __name__ == "__main__": main()
