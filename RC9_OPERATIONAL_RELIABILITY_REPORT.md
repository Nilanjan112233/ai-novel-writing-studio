# NovelForge V2 RC9 — Operational Reliability Report

## Failure-mode matrix

| Scenario | Observed behavior | Result |
|---|---|---:|
| MongoDB unavailable | Frontend stays reachable; readiness returns structured `blocked`, preservation statement and restart action in 5.09 s. | PASS |
| MongoDB restart | Readiness recovers to `offline_ready` in 0.067 s; packaged project count remains five. | PASS |
| AI not configured | Existing projects remain listable; readiness explains AI setup separately. | PASS |
| Invalid/corrupt backup | Archive rejected before any restored project exists. | PASS |
| Restore verification fails | Partial copy removed; original remains; operation records `failed` and `rolled_back`. | PASS |
| Lost restore response / retry | Stable request ID returns the same completed copy. | PASS |
| Concurrent restore from two tabs | One logical restore, one copy, no duplicate-key 500. | PASS |
| Backup destination partial failure | Successful project archives remain available; failed project and recovery guidance are named. | PASS |
| Stop and restart | Docker volumes preserve project state; all test projects returned. | PASS |
| Provider transport success but app failure | Existing RC8 outcome telemetry retains parse/validation/reference/persistence/final outcome and support identity. | PASS (regression) |
| Writer's Room exploration | Existing approved/active source invariant remains covered by RC8 regression and Playwright. | PASS (regression) |
| Paragraph Editor save/recovery | Frozen behavior and productivity journey remain covered; no RC9 editor capability change. | PASS (regression) |

## Migration reliability

RC9 startup records application/schema version, runs migrations under a leased lock, stores run status, and clears/recovers abandoned ownership. Migration operations are additive and idempotent. Synthetic pre-RC6, RC6, RC7 and RC8 project fixtures retained their existing fields while receiving RC9 metadata; a second RC9 migration changed zero legacy projects.

The update launcher treats a failed backup, build, health check or readiness check as a stop condition. It does not remove the prior data volumes.

## Long-session and scale observations

The operational benchmark covers 50, 100, 250, 500 and 1,000 chapters. Warm bootstrap remains 12.98–71.90 ms and dashboard readiness 121–265 ms across the measured range. Working set rose with loaded project size (57.55 MB at 50 chapters to 100.96 MB at 1,000) rather than unbounded elapsed time; the cleanup sample retained 0 MB.

The full 28.6-minute browser regression exercises project switching, planning, writing, generation, Writer's Room, revisions, canon, Story Bible, Narrative Intelligence, assistant/companion, backup/restore, export, reload and recovery paths against FastAPI, MongoDB and configured Gemini where applicable.

## Observability

Every API response receives `X-NovelForge-Reference`. Provider transport and application outcomes remain separately traceable through request/correlation identity. Support bundles provide sanitized readiness, migration and outcome summaries. Raw story content, prompts, responses, credentials and database addresses are excluded.

## Residual reliability risks

- A safe full-disk exhaustion was not forced on the host. Write probes, free-space reporting and unavailable/read-only destination handling are tested instead.
- Docker and process crashes are covered through persisted-state restart and existing operation invariants, not hardware power-cut testing.
- Timer-based automatic whole-project backups are not included; explicit and pre-update backups are the supported contract.
- Provider availability and latency remain external dependencies for AI operations, though existing/manual work is independent.
