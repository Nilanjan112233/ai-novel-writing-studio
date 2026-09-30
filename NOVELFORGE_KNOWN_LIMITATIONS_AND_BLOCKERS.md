# NovelForge Known Limitations and Remaining Blockers

Date: 2026-08-08

## Remaining private-beta/commercial blockers

1. **Long provider latency remains visible but coarse.** Scene generation can take several minutes and may include a correction pass. The user now sees an honest busy state and eventual outcome, but not token streaming or per-stage provider progress.
2. **Provider structured output varies by model.** The new recovery safely preserves prose only, but provider-specific malformed metadata can be lost. Canon and authority metadata are intentionally not guessed.
3. **Generated plan prose can be too analytical.** One pre-fix scene plan in the validation project contains a long explanation beginning with project analysis rather than concise author-facing scene direction. The creation prompt was tightened, but that existing record was not rewritten and the improvement was not recharged in a second live creation test.
4. **Generated prose can introduce facts requiring author judgment.** The live draft mentioned family details and a passenger description. Governance worked: three facts remained pending. This is a quality/review cost, not silent canon corruption.
5. **Continuity links can be incomplete.** The live draft reported that its scene plan had no continuity-ledger links. It remained a warning and did not silently pass into approval.
6. **Advanced Toolbox remains large.** Seventeen specialist/detail destinations are progressively disclosed. This is substantially calmer than top-level exposure, but further contextual surfacing should be evaluated with novice usability sessions before removing any capability.
7. **Historical summaries can contain superseded conclusions.** They are now labeled saved snapshots; their text is retained for provenance and can mention an older readiness state.
8. **Global Settings navigation could not be fully exercised in the in-app browser.** The project Settings page and provider-backed calls worked, but direct `/settings` navigation was intermittently blocked by the browser surface. Provider configuration was independently exercised by the real call and automated tests.
9. **Restore execution was intentionally not performed.** Backup generation and restore preview/integrity passed. Restore-as-copy, remapping, idempotency, and rollback are covered by automated tests, but the live project was not duplicated during this validation.
10. **No SaaS or multi-tenant claim is made.** The validated boundary remains a local/private desktop-style deployment.

## Confirmed issues fixed during validation

- No author control to approve generated chapter/scene plans.
- Stale Writing Dashboard blockers after plan approval.
- False 30-second failure while backend provider work continued.
- Duplicate live generation entry points not visibly disabled.
- SceneWriter output budget truncated/strained structured responses.
- DeepSeek/OpenRouter prose shape not accepted despite provider success.
- Retry left the old failure banner visible.
- Canon Registry crashed when a record lacked `field`.
- Arc maturity threshold looked like a blocker despite optional dimensions.
- Historical workflow outputs looked like current authoritative truth.
- Story Health chapter/word labels did not reveal that they count approved chapter intelligence.
- Dashboard recommended starting a scene even after its active draft had reached review.

## Not simplified because it protects trust

- Canon proposals, high-impact confirmations, approval history, and provenance.
- Decision history, reopen/undo behavior, and change-impact preview.
- Draft review/approval states and immutable version lineage.
- Writer's Room inactive alternatives and source protection.
- Paragraph Editor versions, recovery, locks, comments, and approval.
- Revision branches and explicit application into a new review version.
- Chronology-aware character conversations.
- Shared Narrative Intelligence evidence and one-graph authority.
- Backup checksum, restore preview, restore-as-copy, remapping, and rollback.

## Acceptance answer

For the validated local/private-beta path, the answer is now **yes, with known beta limitations**: a new author can provide a high-level idea, let the story team develop connected planning, see progress and meaningful gates, approve plans, generate and review prose, keep AI-introduced facts outside canon until decided, inspect consistency, and reach manuscript/backup workflows without learning agent or graph internals. The largest remaining experience risk is multi-minute provider work with coarse progress and variable generated-content quality—not loss of author authority or silent state mutation.
