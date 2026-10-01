# Phase D Failure and Resume Report

## Resume/idempotency

Provider-free simulations verified:

- identical authority snapshot yields the same evidence-level decision;
- the same role yields the same manifest hash on repeat;
- selected evidence IDs are unique;
- exactly one handoff exists per completed specialist;
- exactly one specialist output exists per completed specialist;
- retry/resume alone does not duplicate handoffs or outputs.

All five specialist manifest checks passed.

## Fallback matrix

| Fault | Required fallback | Observed | Invented evidence |
| --- | --- | --- | ---: |
| Required episode missing | Current complete Phase C packet | Passed | 0 |
| Evidence pointer stale | Current complete Phase C packet | Passed | 0 |
| Progressive validation failure | Current complete Phase C packet | Passed | 0 |
| Phase C unavailable/incomplete | Existing complete Phase B/P0-safe path | Passed | 0 |
| Phase B complete-path fallback | Authority-first P0-safe retrieval | Passed | 0 |

Fallback reasons were explicit in the diagnostic artifact. No authority document was changed, and no evidence was invented to fill a missing pointer.

## Real-run behavior

The three matched provider runs had zero retries and zero packet fallbacks. The progressive arm therefore did not increase retry/fallback frequency in this bounded sample.

## Production implication

The recovery design is viable, but passing recovery does not authorize rollout. If a later tuned pilot passes quality, production implementation should retain:

1. a manifest hash tied to authority snapshot and role;
2. unique logical evidence IDs;
3. Phase C as the first complete fallback;
4. Phase B/P0-safe fallback if Phase C is incomplete;
5. explicit telemetry for fallback reason;
6. idempotent handoff/output persistence.

