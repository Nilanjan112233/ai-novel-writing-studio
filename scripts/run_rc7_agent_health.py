"""Summarize real-provider execution health for the final RC7 acceptance window."""
from __future__ import annotations

import asyncio
import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.core.database import Database  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--since",
        help="UTC ISO timestamp for the first trace to include; defaults to 24 hours ago.",
    )
    return parser.parse_args()


async def main(window_start_utc: datetime) -> None:
    await Database.connect()
    db = Database.get_db()
    traces = await db.execution_traces.find(
        {
            "created_at": {"$gte": window_start_utc},
            "provider": "gemini",
            "model": "gemini-3.1-flash-lite",
        },
        {
            "agent_name": 1,
            "status": 1,
            "retry_count": 1,
            "fallback_used": 1,
            "latency_ms": 1,
            "prompt_tokens": 1,
            "response_tokens": 1,
            "created_at": 1,
            "error_type": 1,
        },
    ).sort("created_at", 1).to_list(length=5000)

    by_agent: dict[str, Counter[str]] = defaultdict(Counter)
    agent_latency: dict[str, list[int]] = defaultdict(list)
    statuses: Counter[str] = Counter()
    retries = 0
    fallback_count = 0
    errors: list[dict[str, Any]] = []

    for trace in traces:
        agent = str(trace.get("agent_name") or "Unassigned")
        status = str(trace.get("status") or "unknown")
        statuses[status] += 1
        by_agent[agent][status] += 1
        agent_latency[agent].append(int(trace.get("latency_ms") or 0))
        retries += int(trace.get("retry_count") or 0)
        fallback_count += int(bool(trace.get("fallback_used")))
        if status not in {"success", "completed"}:
            errors.append(
                {
                    "agent": agent,
                    "status": status,
                    "error_type": trace.get("error_type"),
                    "created_at": trace.get("created_at").isoformat(),
                }
            )

    agents = []
    for agent in sorted(by_agent):
        latencies = agent_latency[agent]
        agents.append(
            {
                "agent": agent,
                "calls": sum(by_agent[agent].values()),
                "statuses": dict(sorted(by_agent[agent].items())),
                "average_latency_ms": round(sum(latencies) / len(latencies), 2),
                "maximum_latency_ms": max(latencies),
            }
        )

    result = {
        "window_start_utc": window_start_utc.isoformat(),
        "generated_at_utc": datetime.utcnow().isoformat(),
        "provider": "gemini",
        "model": "gemini-3.1-flash-lite",
        "total_traces": len(traces),
        "statuses": dict(sorted(statuses.items())),
        "retry_count": retries,
        "fallback_count": fallback_count,
        "errors": errors,
        "agents": agents,
        "status": "pass" if traces and not errors and not fallback_count else "fail",
    }
    output = ROOT / "artifacts" / "rc7-agent-health.json"
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    await Database.disconnect()


if __name__ == "__main__":
    args = parse_args()
    window_start = (
        datetime.fromisoformat(args.since.rstrip("Z"))
        if args.since
        else datetime.utcnow() - timedelta(hours=24)
    )
    asyncio.run(main(window_start))
