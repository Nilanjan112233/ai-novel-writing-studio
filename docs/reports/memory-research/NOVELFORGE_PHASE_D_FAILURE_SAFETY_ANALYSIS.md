# NovelForge Phase D Failure and Safety Analysis

## Authority invariant

Expansion is read-only. Approved prose, active canon, approved decisions, confirmed planning, and the current approved revision remain authoritative. Atomic memory, episodes, Narrative Analysis, agent output, candidates, and rejected material remain derived or ineligible.

## Failure matrix

| Failure | Required behavior |
|---|---|
| Episode unavailable | use authority + current Phase C facts; if why/how cannot be supported, mark evidence incomplete or use the current broad safe packet |
| Evidence pointer stale | do not quote or infer missing evidence; record pointer failure and fall back |
| Raw prose unavailable | give only supported fact/episode result and state exact wording cannot be verified |
| Derived memory rebuilding | use Phase A authority-safe fallback; never call stale derived memory complete |
| Phase C incomplete | use existing complete Phase B scan/fallback with P0 eligibility |
| Unresolved derived conflict | return the authoritative value and a labelled conflict; expand only for explanation |
| Knowledge scope missing | omit private truth from POV context and use structured knowledge/authority fallback |
| Revision mismatch | validate the current approved version before expanding; older prose remains historical |

## Conflict ordering

For Elias chronology, the packet must show five years as confirmed planning. A contradictory derived episode may be attached as a conflict note, but “two years” must never rank or serialize as an equal current fact. The same rule applies to ownership, relationship, injury/healing, mystery state, and revision transitions.

## Fallback recommendation

The fallback is the existing current Phase C packet. If Phase C readiness is not proven, use the existing Phase B/P0-safe path. Never invent a missing excerpt and never use Tencent as a recovery dependency.

## Audit result

No production path, schema, authority owner, provider route, or index was changed. The benchmark performed zero Mongo writes and zero provider calls. Machine evidence: `artifacts/memory-phase-d/failure-matrix.json` and `manifest.json`.
