# NovelForge V2 RC8 — Commercial Launch Audit

## Executive decision

**GO for a controlled local/private beta and commercial release candidate.**

**NO-GO for hosted multi-tenant SaaS.** Authentication, authorization, tenant
isolation, public API exposure, hosted secret custody, and rate limiting were
not brought into RC8 and require a separate security release.

The RC7 launch rejection is no longer supported by current evidence. All four
Critical findings and the mandatory High findings H1, H2, H4, H5, H9, and H11
are closed. The final adversarial review found no remaining Critical blocker for
the documented local/private deployment. This is a release-candidate verdict,
not a claim that AI output replaces professional editorial judgment.

## Critical findings

### C1 — Silent author-facing write failures: closed

- **Problem:** RC7 writes could fail while the owning workspace remained quiet.
- **Evidence:** RC8 uses one persistent author-language failure state across
  generation, approval, assembly, revision, canon, planning, workflow, and
  manuscript actions. Frontend banner tests and real Playwright failure/retry
  journeys passed.
- **Why it matters:** Authors can distinguish failure from delay and know that
  existing prose is safe.
- **Correction:** Failure names the operation, explanation, preservation state,
  retry, and destination; machine detail remains in Developer Mode.
- **Effort:** Medium, bounded store/UI correction.
- **User impact:** Very high trust and recovery improvement.

### C2 — Writer's Room author-control violation: closed

- **Problem:** Exploration could deactivate approved Version A and activate an
  alternative.
- **Evidence:** The 50-scene soak began with active/approved A, produced three
  inactive alternatives, and ended with A still active/approved. Concurrency,
  reload, retry, failure, and multi-request invariant tests passed.
- **Why it matters:** Brainstorming can no longer alter manuscript authority.
- **Correction:** Service invariants persist alternatives inactive and repair
  safely identifiable legacy state.
- **Effort:** Medium service/migration correction.
- **User impact:** Critical author-control promise restored.

### C3 — Character chronology leakage: closed

- **Problem:** A Chapter N conversation could expose future or hidden truth.
- **Evidence:** Direct and indirect deterministic tests passed. In the final real
  probe, the direct attack failed closed with no saved response/memory; the
  indirect attack returned a safe answer with five allowed evidence records.
- **Why it matters:** “Chapter awareness” is now an enforced boundary rather
  than a prompt label.
- **Correction:** Future-bearing context is excluded; output claims are checked,
  corrected once, then withheld if still unsafe.
- **Effort:** High, bounded context/output hardening.
- **User impact:** Very high continuity trust.

### C4 — Real drafting reliability: closed

- **Problem:** RC7 achieved only 76.4% approved scene yield and failed its real
  SceneWriter browser gate.
- **Evidence:** Final soak produced 50/50 usable, approved scenes and 10/10
  chapter drafts. Two consecutive complete real-stack Playwright runs passed.
- **Why it matters:** Book-scale generation no longer routinely strands prose.
- **Correction:** Provider normalization, contract parsing, semantic reference
  reconciliation, authority validation, one correction, and safe persistence.
- **Effort:** High adapter/service hardening.
- **User impact:** Very high writing reliability.

## High findings

### H1 — Internal reference burden: closed

Story labels now reconcile timeline, artifact, knowledge, foreshadowing,
character, scene, and chapter identities server-side. Tests intentionally shuffle
and omit UUIDs; ordinary author errors show narrative labels. Live Story Health
inspection found zero raw UUIDs after correction.

### H2 — Beginner AI routing: closed

All seven setup steps carry explicit narrative/project-creation intent.
Semantic backend tests and the novice real-Gemini browser journey verify that
character, world, conflict, decision, arc, and scene requests return the correct
kind of story material.

### H3 — Beginner readiness/decision clarity: closed for RC8 scope

Setup completion is kept separate from Arc Draft Readiness, Story Consistency,
Narrative Completeness, and publication gates. Empty 0/0 readiness displays
“Not evaluated.” Existing decision history/change/undo/reopen workflows remain
the authority; no duplicate decision store was added.

### H4 — Scene ordering: closed

API and UI order by chapter number, then scene order. Shuffled-ID fixtures and
the 10-chapter/50-scene soak agree on current scene, next action, Drafting,
Writing Desk, and chapter assembly order.

### H5 — Drafting and Editorial scale UX: closed at launch targets

Both workspaces use chapter/search/status filters, collapsed cards, bounded
rows, and lazy prose/version details. At 500 chapters, first-60 Drafting and
Editorial queries measured 3.80 ms and 4.45 ms. The 2,000-chapter run remains a
stress observation, not the primary UX target.

### H6 — Knowledge Graph metadata/reassurance: closed

Normal mode shows author cards and story labels, not flattened payloads. Warning
reassurance derives from the same Narrative Analysis finding links as Story
Health. Raw identity is Developer Mode only.

### H7 — POV, repetition, and duplicate findings: closed

The existing Narrative Analysis/Story Auditor ownership now detects unexpected
first/third-person transitions and cross-scene repeated phrases, structures,
sensory motifs, and emotional gestures. Planned alternating POV, omniscient
narration, and thematic recurrence have exception/threshold tests. Semantic
identity ensures one issue is shown and scored once.

### H8 — Canon Queue burden: materially reduced

Independent loading, search, type/status filters, semantic grouping,
near-duplicate cues, story labels, evidence, and approval history are present.
Meaningful facts still require individual author approval; RC8 intentionally
does not auto-approve groups.

### H9 — Concurrent idempotency 500: closed

Atomic request identity plus unique persistence reuse handles 2/5 concurrent
calls, slow-provider retries, completion reuse, and recoverable failure without
DuplicateKeyError or duplicate scene versions.

### H10 — Project Timeline noise: closed

Author events identify scene/chapter/fact actions and can be filtered by chapter,
scene, action, system, and date. Low-level events remain available only for
debugging.

### H11 — Red Playwright gate: closed

The correction-contract, novice Save, and Paragraph Editor productivity paths
pass. The Paragraph Editor test preserves response status/body on failure.
Final consecutive full runs: 48 passed, 2 intentional skips in 24.6 minutes,
then 48 passed, 2 skipped in 23.3 minutes.

## Medium findings

### Closed or bounded

- **M1 Assistant compound intent:** page explanation and completeness-driven
  next action are composed; duplicate assistant persistence is prevented.
- **M2 Character structure:** goals/fears normalize to stable author fields with
  provenance.
- **M3 Canon provenance:** evidence and approval history are visible.
- **M4 Publication blockers:** seven preflight blockers in the soak each include
  explanation, why it matters, action, and destination.
- **M5 Mystery readiness:** absent registry data no longer means resolved.
- **M6 Companion:** constrained 1280×720 measurement was 336 px wide, with
  dismiss/complete/snooze memory, direct actions, stale-count refresh, docking,
  and reduced motion.
- **M8 Observability:** 68 soak traces record application outcomes in addition to
  provider transport, with correlation identity across the pipeline.
- **M9 Test pollution:** dedicated E2E database ends at 0 projects/0 models and
  exact cleanup; the normal database count remained 2,657.
- **M10 Deployment:** explicitly local/private; hosted remains NO-GO.

### Remaining, non-blocking

- **M7 Cold bootstrap:** 500 chapters measured 3.69 s cold and 24 ms warm;
  1,000 chapters measured 7.24 s cold. Staged readiness prevents a blank or
  falsely ready screen. Further Story Bible projection tuning is warranted.
  **Effort:** medium. **Impact:** primarily epic/series authors.
- **Legacy local test projects:** pre-RC8 data has no exact ownership manifest,
  so it was not bulk-deleted. **Effort:** user-reviewed cleanup. **Impact:** demo
  library clutter on this existing installation only.
- **Deprecation warnings:** 66 Pydantic/LangGraph compatibility warnings remain.
  **Effort:** medium before Pydantic v3. **Impact:** maintainability, not current
  author behavior.

## Low findings

- The dynamic project route is 221 kB with 373 kB first-load JavaScript. Lazy
  workspace modules mitigate use-time cost, but bundle reduction remains useful.
- Performance evidence does not include process working-set memory; no numeric
  memory claim is made.
- Semantic chronology and literary-quality analysis are conservative decision
  support, not mathematical proof or a replacement for human editing.

## Final adversarial attack result

The final audit re-attacked silent failures, Writer's Room state, future
knowledge, simultaneous idempotency, malformed/provider-variable output,
semantic references, reload/multi-tab behavior, long-project ordering, Canon
volume, POV/repetition, and publication blockers. No Critical launch blocker was
reproduced for the supported deployment.

## Release recommendation

Release RC8 as a controlled local/private beta or commercial release candidate,
with telemetry/support attention on provider failures and cold large-project
bootstrap. Do not market it as hosted multi-tenant SaaS. Reassess after beta
authors complete diverse full manuscripts; the current 50-scene soak proves
workflow reliability, not universal literary quality.
