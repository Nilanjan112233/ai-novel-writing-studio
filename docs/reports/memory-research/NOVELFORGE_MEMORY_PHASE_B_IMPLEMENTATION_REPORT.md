# NovelForge Memory Phase B Implementation Report

## Outcome

Phase B is implemented without starting Phase C or D. Atomic facts and compact episodes are derived, versioned, rebuildable projections. Mongo story owners, approved prose, canon, decisions, planning, and revision state remain the only authority.

The matched Develop Story evidence layer fell from 24,292 to 14,904 tokens (38.65%). Total prompt tokens fell from the Phase E baseline of 33,551 to 23,622 (29.59%), while the reduction against the 396,636-token legacy workflow remains 94.04%.

## Implemented

- `atomic_memories`: deterministic compact observations with logical identity, owner/source versions, evidence pointers, chapter/scene validity, knowledge scope, authority class, confidence, status, and derivation version.
- `episode_memory` inside the existing `chapter_intelligence` owner; no second episode store was created.
- Exact/high-confidence fact collapse with evidence-pointer aggregation.
- Authority-aware contradiction labels. Conflicting derived observations are excluded from safe-writing recall.
- Incremental derivation through Phase A owner events and provider-free project rebuild.
- Compact retrieval attribution in Discovery and Develop Story packets.
- Backup/restore independence: derived atomics and checkpoints are omitted and rebuilt from owners.
- A migration adding only derived-memory indexes and checkpoint indexes.

## Explicitly not implemented

No BM25, embedding-provider change, RRF, graph rank fusion, progressive tool retrieval, preference memory, Tencent dependency, new Story Bible, new agent, or destructive cleanup was added.

## Acceptance gates

| Gate | Result |
|---|---:|
| Evidence reduction >=30% | PASS: 38.65% |
| Overall reduction vs legacy >=50% | PASS: 94.04% |
| Authority coverage | PASS: 5/5 packets |
| Specialist requirements | PASS: 5/5 |
| P0 leakage | PASS: all zero |
| Duplicate logical hits | PASS: zero |
| Rebuildable/provider-free | PASS |
| Tencent required | No |

Artifacts are in `artifacts/memory-phase-b/`.
