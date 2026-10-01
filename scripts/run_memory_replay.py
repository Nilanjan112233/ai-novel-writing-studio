"""Provider-free Native memory replay and attribution CLI."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from motor.motor_asyncio import AsyncIOMotorClient


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.core.config import settings  # noqa: E402
from app.services.memory_replay_service import (  # noqa: E402
    ReplayRequest,
    memory_replay_service,
)


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--project-id")
    value.add_argument("--query", default="")
    value.add_argument("--consumer", default="discovery_writer")
    value.add_argument("--current-chapter", type=int)
    value.add_argument("--current-scene", type=int)
    value.add_argument("--pov-character")
    value.add_argument("--branch-id")
    value.add_argument("--top-k", type=int, default=8)
    value.add_argument("--expected-term", action="append", default=[])
    value.add_argument("--context-packet-id")
    value.add_argument("--label", default="")
    value.add_argument("--output", type=Path, required=True)
    value.add_argument("--compare-with", type=Path)
    value.add_argument("--develop-story", action="store_true")
    value.add_argument("--cycle", type=int, action="append")
    value.add_argument("--respect-index-readiness", action="store_true")
    return value


async def main() -> None:
    args = parser().parse_args()
    if not args.project_id:
        raise SystemExit("--project-id is required")
    client = AsyncIOMotorClient(
        settings.mongodb_url,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
    )
    db = client[settings.database_name]
    try:
        await db.command("ping")
        if args.develop_story:
            result = await memory_replay_service.develop_story_baseline(
                db, args.project_id, cycle_numbers=args.cycle,
            )
        else:
            result = await memory_replay_service.replay(
                db,
                ReplayRequest(
                    project_id=args.project_id,
                    query=args.query,
                    consumer=args.consumer,
                    current_chapter=args.current_chapter,
                    current_scene=args.current_scene,
                    pov_character=args.pov_character,
                    branch_id=args.branch_id,
                    top_k=args.top_k,
                    expected_terms=args.expected_term,
                    context_packet_id=args.context_packet_id,
                    label=args.label,
                    respect_index_readiness=args.respect_index_readiness,
                ),
            )
        if args.compare_with:
            baseline = json.loads(args.compare_with.read_text(encoding="utf-8"))
            result = {
                "baseline": baseline,
                "candidate": result,
                "comparison": memory_replay_service.compare(baseline, result),
            }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, indent=2, ensure_ascii=True),
            encoding="utf-8",
        )
        print(json.dumps({"output": str(args.output), "provider_calls": 0}, indent=2))
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
