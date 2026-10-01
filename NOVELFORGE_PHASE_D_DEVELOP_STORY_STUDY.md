# NovelForge Phase D Develop Story Study

## Matched baseline

The stored Phase C run used the five active specialists, the same Memory Fantasy state, Gemini `gemini-3.1-flash-lite`, and role-specific Phase E packets.

| Metric | Current Phase C | Progressive shadow |
|---|---:|---:|
| Native + episode evidence | 13,810 | 3,890 |
| Total prompt tokens | 22,326 | 12,406 |
| Evidence reduction | — | 71.83% |
| Total prompt reduction | — | 44.43% |
| Labelled authority coverage | 5/5 | 5/5 |
| Labelled role-depth sufficiency | 5/5 current | 5/5 shadow |
| Fact-only role-depth sufficiency | — | 0/5 |
| Raw expansions for this instruction | current episodes only | 0 |

The shadow used the stored matched packet contents and exact Phase C per-source token attribution. It compacted redundant Native fact representations and projected only the episode fields each role needs. It did not call a provider.

## Per specialist

| Specialist | Current evidence | Fact | Selected episodes | Shadow evidence |
|---|---:|---:|---:|---:|
| Relationship | 2,619 | 64 | 540 | 604 |
| Character Journey | 2,618 | 64 | 577 | 641 |
| Mystery | 2,618 | 322 | 489 | 811 |
| Arc Architect | 2,979 | 322 | 676 | 998 |
| Pacing | 2,976 | 322 | 514 | 836 |

## Why fact-only failed

The matched instruction asked the agents to strengthen relationship progression, character journey, mystery escalation, arc coherence, and pacing. Current-state facts preserve hard constraints but do not explain the causal transition from funeral mistrust to conditional cooperation or the evolution of clues. Every role therefore needed at least one bounded episode projection.

## Cross-agent coherence

Authority snapshots, role projections, and Phase E handoffs are unchanged in the simulation. The compact evidence retains the five-year chronology, central mystery, Chapter 10 boundary, Mara/Ivo state, and Northglass relevance. This proves packet coverage, not that stochastic outputs remain equally useful.

## Recommended Develop Story policy

- Route by role deterministically.
- Always keep the Phase E authority snapshot and handoffs.
- Relationship/Character/Mystery/Arc/Pacing receive bounded relevant episodes directly.
- Raw prose is not preloaded for normal planning; allow a bounded exact-evidence escape hatch for a specialist explicitly assigned wording or scene-level analysis.
- Fall back to the complete current Phase C packet when coverage validation fails.

## Unmet acceptance gate

No matched provider output was generated in this read-only audit. Specialist usefulness, retries, output length, and cross-agent coherence are therefore not measured after ablation. Production Phase D should wait for that A/B/C validation.

Machine evidence: `artifacts/memory-phase-d/develop-story-shadow.json`.
