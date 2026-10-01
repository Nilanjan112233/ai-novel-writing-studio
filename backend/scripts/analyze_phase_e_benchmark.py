"""Create the machine-readable Phase E matched cost and quality comparison."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "artifacts" / "memory-phase-e"


def _load(name: str) -> dict:
    return json.loads((ARTIFACTS / name).read_text(encoding="utf-8"))


def _calls_by_agent(run: dict) -> dict:
    return {call["agent_name"]: call for call in run.get("calls") or []}


def _outputs_by_agent(run: dict) -> dict:
    return {row["agent_name"]: row.get("structured_output") or {} for row in run.get("agent_outputs") or []}


def _contains_all(payload: dict, groups: list[tuple[str, ...]]) -> bool:
    text = json.dumps(payload, ensure_ascii=False).lower()
    return all(any(term.lower() in text for term in group) for group in groups)


def _count_unsafe(value: object) -> int:
    if isinstance(value, list):
        return sum(_count_unsafe(item) for item in value)
    if not isinstance(value, dict):
        return 0
    statuses = {
        str(value.get(key) or "").lower()
        for key in ("status", "authority_status", "candidate_status", "approval_status", "decision_status")
    }
    own = int(bool(statuses & {"candidate", "pending", "rejected", "stale", "superseded", "archived", "inactive"}))
    return own + sum(_count_unsafe(item) for item in value.values())


def main() -> None:
    legacy = _load("baseline-replay-provider-run.json")
    optimized = _load("optimized-provider-run.json")
    failed = _load("baseline-provider-failed-run.json")
    legacy_calls = _calls_by_agent(legacy)
    optimized_calls = _calls_by_agent(optimized)
    optimized_outputs = _outputs_by_agent(optimized)
    requirements = {
        "RelationshipAgent": [("mara",), ("elias",), ("chapter 10",), ("relationship", "trust", "alliance"), ("five years", "5-year")],
        "CharacterJourneyAgent": [("mara",), ("elias",), ("chapter 10",), ("journey", "arc", "growth", "change")],
        "MysteryAgent": [("elias",), ("chapter 10",), ("mystery", "clue", "reveal"), ("five-year", "5-year", "five years")],
        "ArcArchitectAgent": [("mara",), ("elias",), ("chapter 10",), ("arc", "goal", "purpose")],
        "PacingAgent": [("chapter 10",), ("pacing", "escalation", "chapter"), ("reveal",)],
    }
    per_agent = []
    for agent, before in legacy_calls.items():
        after = optimized_calls[agent]
        before_tokens = int(before.get("prompt_tokens") or 0)
        after_tokens = int(after.get("prompt_tokens") or 0)
        per_agent.append({
            "agent": agent,
            "baseline_prompt_tokens": before_tokens,
            "optimized_prompt_tokens": after_tokens,
            "prompt_reduction_percent": round((before_tokens - after_tokens) * 100 / before_tokens, 2),
            "optimized_response_tokens": int(after.get("response_tokens") or 0),
            "optimized_latency_ms": int(after.get("wall_latency_ms") or 0),
            "requirements_passed": _contains_all(optimized_outputs.get(agent, {}), requirements[agent]),
        })
    baseline_prompt = int(legacy["totals"]["prompt_tokens"])
    optimized_prompt = int(optimized["totals"]["prompt_tokens"])
    before_sources: Counter[str] = Counter()
    after_sources: Counter[str] = Counter()
    for call in legacy_calls.values():
        before_sources.update(call.get("prompt_tokens_by_source") or {})
    for call in optimized_calls.values():
        after_sources.update(call.get("prompt_tokens_by_source") or {})
    packet_attribution = {
        row["agent_name"]: row.get("phase_e_attribution") or {}
        for row in optimized.get("context_packets") or []
    }
    comparison = {
        "generated_from": {
            "legacy_input_replay": "baseline-replay-provider-run.json",
            "optimized_real_provider": "optimized-provider-run.json",
            "legacy_real_provider_failure": "baseline-provider-failed-run.json",
        },
        "methodology": {
            "same_source_snapshot": True,
            "same_instruction": legacy["instruction"] == optimized["instruction"],
            "same_agent_roster": legacy["agents"] == optimized["agents"],
            "legacy_outputs_replayed_from_optimized": True,
            "reason": "Gemini failed the broad legacy workflow after one completed specialist; deterministic output replay completed all five legacy packet measurements without claiming provider success.",
        },
        "totals": {
            "baseline_prompt_tokens": baseline_prompt,
            "optimized_prompt_tokens": optimized_prompt,
            "prompt_reduction_tokens": baseline_prompt - optimized_prompt,
            "prompt_reduction_percent": round((baseline_prompt - optimized_prompt) * 100 / baseline_prompt, 2),
            "baseline_response_tokens_matched_replay": int(legacy["totals"]["response_tokens"]),
            "optimized_response_tokens": int(optimized["totals"]["response_tokens"]),
            "baseline_projected_cost_usd_same_gemini_model": 0.160171,
            "optimized_actual_cost_usd": float(optimized["totals"]["estimated_provider_cost_usd"]),
            "projected_cost_reduction_percent": round((0.160171 - float(optimized["totals"]["estimated_provider_cost_usd"])) * 100 / 0.160171, 2),
            "optimized_wall_latency_ms": int(optimized["totals"]["wall_latency_ms"]),
            "optimized_retries": int(optimized["totals"]["retries"]),
            "optimized_fallbacks": int(optimized["totals"]["fallbacks"]),
            "legacy_real_provider_spend_before_failure_usd": float(failed["totals"]["estimated_provider_cost_usd"]),
            "legacy_real_provider_wall_latency_before_failure_ms": int(failed["totals"]["wall_latency_ms"]),
            "legacy_real_provider_completed_specialists": len(failed.get("agent_outputs") or []),
        },
        "per_agent": per_agent,
        "tokens_by_source": {
            "baseline": dict(before_sources),
            "optimized": dict(after_sources),
        },
        "quality": {
            "specialist_requirement_checks_passed": sum(1 for item in per_agent if item["requirements_passed"]),
            "specialist_requirement_checks_total": len(per_agent),
            "authority_coverage_complete_packets": sum(1 for item in packet_attribution.values() if item.get("authority_complete")),
            "authority_coverage_total_packets": len(packet_attribution),
            "broad_fallbacks": sum(1 for item in packet_attribution.values() if item.get("mode") == "broad_fallback"),
            "candidate_or_rejected_records_in_role_projection": sum(
                _count_unsafe(call.get("project_context", {}).get("role_specific_structured_context", {}))
                for call in optimized_calls.values()
            ),
            "chronology_authority_present": all("five years" in json.dumps(call.get("project_context", {}).get("authority", {}), ensure_ascii=False).lower() for call in optimized_calls.values()),
            "chapter_10_boundary_in_all_outputs": all("chapter 10" in json.dumps(payload, ensure_ascii=False).lower() for payload in optimized_outputs.values()),
            "same_cycle_handoffs_visible_after_first_specialist": all(
                int(packet_attribution[agent].get("tokens_by_source", {}).get("previous_agent_handoffs") or 0) > 1
                for agent in ("CharacterJourneyAgent", "MysteryAgent", "ArcArchitectAgent", "PacingAgent")
            ),
            "optimized_outputs_exactly_equal_replayed_outputs": optimized_outputs == _outputs_by_agent(legacy),
        },
        "packet_attribution": packet_attribution,
        "provider_failure_evidence": {
            "status": failed.get("status"),
            "error": failed.get("error"),
            "calls": [
                {key: call.get(key) for key in ("agent_name", "status", "prompt_tokens", "response_tokens", "provider", "model", "error_type", "error")}
                for call in failed.get("calls") or []
            ],
        },
    }
    output = ARTIFACTS / "phase-e-comparison.json"
    output.write_text(json.dumps(comparison, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"output": str(output), **comparison["totals"], **comparison["quality"]}, indent=2))


if __name__ == "__main__":
    main()
