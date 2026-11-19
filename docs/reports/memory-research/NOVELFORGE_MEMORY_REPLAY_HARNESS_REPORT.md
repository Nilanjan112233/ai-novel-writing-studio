# NovelForge Memory Replay Harness Report

## Harness contract

`scripts/run_memory_replay.py` replays existing Native retrieval without refreshing the index and without calling a generation provider. `MemoryReplayService` emits JSON-safe records for:

- query/task, consumer, chapter/scene boundary, POV, branch, and top-k;
- physical embedding ID and physical owner ID;
- logical source ID and logical source/version identity;
- source type, status, authority, score, semantic score, and rank;
- estimated tokens, provenance, evidence pointers, validity interval, and knowledge scope;
- logical duplicates and their token cost;
- candidate/rejected/stale, future-chapter, and POV-knowledge leakage;
- relevant/irrelevant tokens, Recall@k, MRR, and elapsed retrieval time;
- recorded packet and tokens by packet section.

For post-change replay, the harness substitutes current retrieved hits into the stored packet in memory. It does not persist a new packet. This isolates retrieval changes while preserving the exact recorded authority and active-context sections.

The CLI supports `--compare-with` and produces a machine-readable `baseline`, `candidate`, and metric delta. It also supports `--develop-story` to inspect stored specialist packets.

## Permanent cases

`backend/tests/fixtures/memory_p0_cases.json` labels nine cases: duplicate intelligence, Elias chronology, POV shift, Mara/Lindon relationship extraction, rejected brainstorming, candidate leakage, superseded state, future knowledge, and character-specific knowledge. `backend/tests/test_memory_p0_foundation.py` executes these boundaries against real Mongo behavior in an isolated test database.

## Artifacts

- `memory-fantasy-baseline.json`: untouched pre-fix real-project capture.
- `memory-fantasy-before-after.json`: same request, baseline versus current retrieval.
- `memory-fantasy-after-safe.json`: correct pre-Chapter-2 chronology boundary.
- `real-duplicate-repair-dry-run.json`: read-only identification of the real alias pair.
- `long-scale-before-after.json`: same-corpus legacy-cap versus current-safe results at six scales.
- `develop-story-baseline.json`: cycles 2 and 3 from the real five-specialist project.
- `p0-regression.xml` and `backend-full.xml`: machine-readable test results.

## Determinism and mutation boundary

Hash embeddings, fixed queries, fixed labels, `refresh_index=False`, and no provider generation make normal replay deterministic for an unchanged database snapshot. Timing is observational and will vary. The scale runner uses an exact UUID-named temporary Mongo database, records `provider_calls: 0`, and removes only that database after the artifact is produced.

The harness does not approve, reject, supersede, delete, or rewrite authority. The real duplicate repair was run in dry-run mode only. Repair behavior itself is covered in an isolated database test.

## Example

```powershell
py -3.11 scripts/run_memory_replay.py `
  --project-id <id> `
  --query "Continue Mara's search" `
  --consumer discovery_writer `
  --current-chapter 5 `
  --pov-character Mara `
  --expected-term Elias `
  --output artifacts/memory-p0/replay.json
```

The answer to “Why did NovelForge include this?” is available through `why_selected`, logical identity, authority/validity, rank/score, chapter scope, provenance, and evidence pointers on each selected hit.

