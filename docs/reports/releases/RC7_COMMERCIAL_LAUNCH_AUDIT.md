# NovelForge RC7 Commercial Launch Audit

Audit date: 2026-08-01  
Verdict: **NO-GO for commercial launch**  
Scope: read-only product, architecture, UX, writing-quality, trust, performance, and test review. No product code or architecture was changed.

## Executive conclusion

NovelForge has a credible and unusually broad narrative-production foundation. Its core architecture does not need replacement, and several important protections work: reload during generation preserved the draft, repeated canon approval was rejected safely, publication export stayed locked for an invalid manuscript, timeline dependencies were readable, warm workspace bootstrap was fast, the production build passed, and backend/frontend regressions remained green.

It is nevertheless not ready for a commercial launch. Four defects directly break the promises on which an author must rely:

1. author-facing write failures can be silent;
2. Writer's Room can deactivate approved prose and select an unreviewed alternative despite saying it will not choose;
3. a Chapter 1 character conversation can disclose knowledge Story Bible explicitly says the character does not know;
4. real Gemini drafting is not reliable enough to complete either the sustained story or the current Playwright release gate.

These are bounded defects in existing services and UI state handling. None requires an architectural redesign or a new agent.

## What was actually tested

- Started the real Next.js, FastAPI, MongoDB, and configured Google AI Studio stack.
- Confirmed the configured provider/model was Gemini `gemini-3.1-flash-lite` in full execution mode.
- Created projects through the visible UI for fantasy, science fiction, romance, mystery, thriller, horror, slice of life, historical fiction, and a long-running epic concept. These were breadth probes, not nine finished novels.
- Completed a sustained speculative-mystery project with 11 chapters and 55 planned scenes, plus characters, world rules, an arc, 11 timeline anchors, an artifact, foreshadowing, knowledge evolution, canon review, Writer's Room alternatives, revision, chapter assembly, manuscript validation, and publication preflight.
- Made 55 real scene-generation attempts. Fifty-four produced Version A drafts; 42 passed review and approval. Total generated Version A prose was 13,368 words; approved prose was 10,348 words.
- Ran three real Writer's Room directions, a structured emotion revision, five chapter assembly attempts, a real Story Auditor pass, character conversation, project assistant questions, canon approval, Knowledge Graph inspection, and manuscript preflight.
- Exercised reload during generation, repeated approval, two browser tabs, a simultaneous duplicate request, and a 2,000-chapter live browser project.
- Benchmarked 100, 250, 500, 1,000, and 2,000 chapters. The exact 2,000-chapter synthetic fixture was removed afterward.
- Ran the current automated gates: backend, frontend, ESLint, production build, and all 48 Playwright tests.

Important boundary: the long-form trial met the requested 50-scene/10-chapter threshold, but it was not a market-length 80,000- to 100,000-word manuscript. Only one genre received sustained literary review.

## Critical findings

### C1. Author-facing write failures are silent

**Problem:** Draft generation, chapter assembly, approval, and similar store actions record an error but the project workspace never renders that store error.

**Evidence:** A beginner clicked Generate Draft. Gemini returned HTTP 200 twice, the application returned 409, no version appeared, and the UI showed no explanation or retry. Approving a failed long-form draft and assembling two chapters also returned 409 with no visible error. `projectStore.ts` sets `error` for these operations, while the workspace page does not select or render it.

**Why it matters:** An author cannot distinguish a slow operation from a rejected operation and will click again, leave the page, or assume prose was lost. Silent failure is incompatible with paid creative software.

**Suggested improvement:** Render the existing shared error state at the owning surface with the operation name, author-language reason, retry, and relevant destination. Clear it only after acknowledgement or a successful retry. Keep the existing API and store pattern.

**Estimated effort:** 1–2 engineering days plus focused UI/E2E coverage.

**Expected user impact:** Very high; restores basic trust and recoverability across all writing actions.

### C2. Writer's Room violates author control and approved-draft safety

**Problem:** Generating three alternatives calls ordinary scene generation three times. Each generation changes the active version. The last unreviewed alternative becomes active and the previously approved source becomes inactive.

**Evidence:** The live approved Version A was deactivated; Versions C, D, and E were created; Version E became active even though the response contained `selected_draft_id: null`, `author_choice_required: true`, and the UI said no option would be chosen. The approved-scene count fell from 42 to 41. The implementation loops through `generate_scene` in `drafting_service.py:1069-1082`; the completion report claims the opposite behavior.

**Why it matters:** A brainstorming operation can silently change the authoritative draft and make an otherwise assemblable chapter ineligible. This is a direct data-governance and author-trust breach.

**Suggested improvement:** Use the existing draft lineage but persist Writer's Room outputs as inactive alternatives. Preserve the source's active and approved flags until the author explicitly selects, merges, or applies an option. Add an invariant test around active/approved counts.

**Estimated effort:** 2–3 engineering days including migration-safe repair for affected records and concurrency tests.

**Expected user impact:** Critical; prevents approved work from being displaced by exploration.

### C3. Character chronology/knowledge guardrail is not enforced

**Problem:** Character Conversation labels a response as bounded to Chapter 1 while allowing the model to infer future or explicitly unknown story truth.

**Evidence:** Story Bible said Anika Sen did not know that borrowed days avert disasters and create civic debt. At Chapter 1, asked about Dev and the Public Clock, she answered that the Clock harvests time and that the city was collecting a debt. The UI labeled this “Chapter 1 awareness” and “0 canon facts.” The context builder filters knowledge records, but also supplies the project premise and relies on a prompt instruction rather than validating response claims (`narrative_interaction_service.py:827-934`).

**Why it matters:** The defining promise of Character Conversations is that characters cannot know future or hidden information. A false awareness badge makes the breach worse because it tells the author the answer is safe.

**Suggested improvement:** Keep the existing context service, but remove future-bearing project fields from bounded conversation context and validate generated claims against allowed knowledge before persistence/display. Reject or regenerate out-of-bound claims and expose the actual evidence used.

**Estimated effort:** 3–5 engineering days with chronology, adversarial-question, and negative-knowledge tests.

**Expected user impact:** Critical; makes in-character exploration trustworthy for plotting and drafting.

### C4. Real drafting reliability fails launch acceptance

**Problem:** The provider/structured-output path frequently returns a transport-successful result that cannot satisfy the application contract, and recovery is not sufficient.

**Evidence:** In the sustained run, one of 55 scene generations failed after correction because `generated_text` was empty. Twelve more generated drafts could not be approved, leaving only 42/55 approved (76.4%). Five chapter assembly attempts produced only three approved chapters; two returned invalid transition links. The current full Playwright run independently failed `drafting-v2` with the same empty `generated_text` error.

**Why it matters:** At book scale, even a low single-call failure rate becomes routine interruption. A 76% approval yield and 60% chapter-assembly yield create substantial cleanup labor and make “less effort” untrue.

**Suggested improvement:** Harden the existing output adapter and correction loop: capture malformed-but-recoverable provider shapes, validate reference contracts before presenting approval, give one bounded repair path, and return an actionable author message without partial state. Do not loosen authority checks merely to improve pass rate.

**Estimated effort:** 4–7 engineering days plus a 50-scene real-provider soak gate.

**Expected user impact:** Critical; turns generation from a fragile experiment into a dependable workflow.

## High findings

### H1. Internal reference contracts reject otherwise usable prose

**Problem:** Twelve generated drafts stayed in review because model claims omitted exact internal UUID references for timeline, knowledge, artifact, or foreshadow records.

**Evidence:** Failures included “Missing planned references: <UUID>” and “References are not declared,” with raw UUIDs presented to the author.

**Why it matters:** The user cannot repair an internal identifier contract, and good prose becomes operationally stranded.

**Suggested improvement:** Resolve planned entities to stable machine references before/after generation inside the existing validator, and translate any remaining failure to story labels and one-click repair/navigation.

**Estimated effort:** 3–5 days.  
**Expected user impact:** High; materially raises approval yield and removes developer-facing repair work.

### H2. Beginner AI suggestion routing can return application help instead of story content

**Problem:** “Use AI suggestion” for Main Character populated details with an Arc Board help description and left the character name blank.

**Evidence:** The beginner service asks “Help me define my main character.” Application classification treats any token overlap as a surface match; `my main character` does not match the project phrase `my character`, so generic application surfaces win (`application_knowledge_service.py:160-195`).

**Why it matters:** The first AI-assisted creation interaction makes the system look incoherent to the exact audience RC6/RC7 targets.

**Suggested improvement:** Mark beginner-assistance calls explicitly as project-creation intent, or require stronger phrase scores before application routing. Add an end-to-end assertion on semantic result, not only button presence.

**Estimated effort:** 1–2 days.  
**Expected user impact:** High for first-run confidence.

### H3. The seven-step beginner flow overstates readiness and under-structures decisions

**Problem:** “7 of 7” and 100% does not mean the story is ready to draft, and First Decision is not recorded in the decision registry/history.

**Evidence:** The finished beginner project still had zero decision-registry entries, timeline events, plot threads, relationships, and themes, plus unresolved conflict/goal/stakes/growth blockers. `first_decision` writes only Shared Narrative Context (`beginner_experience_service.py:257-273`). “Open full First Decision workspace” opened an empty Questions page with no decision history or undo. Editing the decision did propagate and lowered consistency from 100 to 99 because the first scene contradicted it, which is a positive result.

**Why it matters:** Authors are told choices are editable/undoable but cannot find a governed history for the first foundational decision. Completion language conflates “steps answered” with “foundation sufficient.”

**Suggested improvement:** Keep step completion, but label it “setup answered.” Route First Decision through the existing decision-history service and show the remaining planning blockers before “Generate draft.”

**Estimated effort:** 2–4 days.  
**Expected user impact:** High; clearer expectations and real change-of-mind safety.

### H4. Scene ordering is not chapter ordering

**Problem:** Scene plans are sorted by `chapter_plan_id` UUID and then scene order, not by chapter number.

**Evidence:** The 55-scene Drafting view interleaved chapters and selected Chapter 11 as current while earlier chapters remained incomplete. The API sort is visible at `backend/app/api/development.py:567-568`.

**Why it matters:** A long-form author loses narrative sequence and may generate or revise the wrong scene.

**Suggested improvement:** Join/project chapter number in the existing query/service and sort by chapter number, then scene order. Add a shuffled-ID regression test.

**Estimated effort:** 1 day.  
**Expected user impact:** High for every multi-chapter project.

### H5. Drafting and Editorial do not scale as working lists

**Problem:** Drafting renders every scene, every version, and full prose; Editorial renders dozens of indistinguishable draft cards without scene/chapter names, search, or filters.

**Evidence:** `DraftingWorkspace.tsx:403-491` maps the entire arc and nested versions. At 55 scenes the page became a long multi-scroll surface. At 2,000 scenes, a request exceeded the 30-second client timeout and DOM inspection failed. Editorial showed 54 cards labeled only “scene draft · Version A,” plus truncated raw IDs, so the target revision could not be identified efficiently.

**Why it matters:** The core writing and editing workspaces degrade before a normal commercial novel is complete.

**Suggested improvement:** Preserve the current workspace but page/virtualize the existing list, collapse prose by default, and add chapter/scene labels plus search/status filters. Load prose/version details on demand.

**Estimated effort:** 4–7 days.  
**Expected user impact:** Very high for intermediate and professional authors.

### H6. Knowledge Graph exposes raw implementation metadata and incorrect reassurance

**Problem:** Graph nodes and summaries display UUID-based labels and flattened payload metadata.

**Evidence:** A selected continuity node showed `continuity:<UUID>`, report/arc/chapter-plan/scene/subject IDs in Summary, “Project-wide,” and “0 warnings / No current Story Health concerns,” although the underlying continuity report blocked draft approval. The UI falls back to `valueText(selectedNode.payload)` (`InteractiveNarrativeStudio.tsx:476`).

**Why it matters:** This violates the product’s author-language promise and can falsely reassure users about a blocked story element.

**Suggested improvement:** Use existing node detail to map IDs to story labels, suppress unknown metadata outside Developer Mode, and derive warning/chapters from the same finding links used by Story Health.

**Estimated effort:** 3–5 days.  
**Expected user impact:** High for comprehension and trust.

### H7. Story Auditor misses major prose-quality defects and emits duplicates

**Problem:** The auditor did not detect a first-to-third-person discontinuity or repeated prose motifs, while duplicating an unresolved-promise finding.

**Evidence:** Of 54 Version A drafts, 48 were predominantly third-person and six first-person; Chapter 11 was entirely first-person after third-person chapters. Repeated phrases included “heart hammered,” “breath hitched,” ozone, rain, and several repeated five-word sequences. The audit returned six consolidated findings, including the exact same Chapter 11 unresolved promise twice, but no POV finding.

**Why it matters:** Authors may trust a good Story Health score while a reader-visible continuity defect remains undetected. Duplicate penalties also undermine score credibility.

**Suggested improvement:** Extend the existing critique/auditor rules with manuscript-level POV/style continuity and semantic finding identity. Do not add another agent; route results through the current Character/Continuity/Pacing owners.

**Estimated effort:** 4–6 days.  
**Expected user impact:** High for editorial confidence and score trust.

### H8. Canon proposal governance becomes a second job

**Problem:** 54 scene drafts created 47 pending proposals, including near-duplicate motivations and low-value microfacts. The queue has no search, grouping, or bulk triage.

**Evidence:** Proposal payload was about 136 KB. Similar Dev Sen motivation proposals appeared separately. The screen initially said no proposals for several seconds because modes, history, graph, proposals, and recommendations load in one `Promise.all` (`InteractiveNarrativeStudio.tsx:154-171`). Cards exposed raw scene UUIDs.

**Why it matters:** More generation creates disproportionate governance work, and a transient dependency can make the authoritative queue look empty.

**Suggested improvement:** Independently load the proposal resource, show a loading state, group semantic duplicates, and add existing-field filters/search. Keep approval individual for high-impact facts.

**Estimated effort:** 3–5 days.  
**Expected user impact:** High for sustained writing throughput.

### H9. Concurrent idempotent generation returns HTTP 500

**Problem:** Two simultaneous generation calls with the same request ID race while indexing memory.

**Evidence:** One call returned 200 and persisted one draft; the other returned 500 with `DuplicateKeyError` on the `memory_source_version` unique index. The current idempotency test sends the duplicate only after the first completes (`test_rc7_writing_experience.py:118-137`).

**Why it matters:** Double-clicks, multiple tabs, retries, or poor networks can produce scary server errors and may consume duplicate provider work even when final draft data is not duplicated.

**Suggested improvement:** Make memory indexing atomic/idempotent under the existing unique key and add a simultaneous-request test. Return the first request's result for the duplicate.

**Estimated effort:** 2–4 days.  
**Expected user impact:** High for trust under real network conditions.

### H10. Project Timeline is technically complete but operationally noisy

**Problem:** Each scene can create several generic events such as “Agent Completed,” “Scene Draft Changed,” “Scene draft created,” and “Canon proposal added,” without object names or filters.

**Evidence:** The long project produced a very long series of near-identical cards seconds apart. “Agent Completed” is implementation language and “the project changed” does not identify what changed.

**Why it matters:** The history cannot answer “what happened to my chapter?” and becomes notification fatigue rather than an audit trail.

**Suggested improvement:** Aggregate low-level events into author actions, attach chapter/scene/fact labels, and filter by system/action/date. Retain raw events only in Developer Mode.

**Estimated effort:** 3–5 days.  
**Expected user impact:** High for long-term orientation and recovery.

### H11. Current Playwright release gate is red

**Problem:** The repository's own full browser suite does not pass on the configured real stack.

**Evidence:** 43 passed, 3 failed, 2 skipped in 32.6 minutes. Failures were: real SceneWriter empty text after correction; RC7 amateur flow stuck seven minutes on a disabled Save button with empty Main Character fields; Paragraph Editor productivity setup returned a non-OK paragraph-generation response. The latter test does not print the response body, so its cause is not proven.

**Why it matters:** RC7's own completion rule says all gates must pass. A commercial release cannot waive failures in drafting and novice onboarding.

**Suggested improvement:** Fix the two proven RC7 failures, improve the paragraph test's error evidence, then require two consecutive full passes because real-provider variability is part of the product contract.

**Estimated effort:** Included in C4/H2 plus 1–2 days test hardening.  
**Expected user impact:** High; restores a meaningful release gate.

## Medium findings

### M1. Application Assistant mishandles compound page-help questions

**Problem:** On Timeline, “What does this Timeline page do, and what should I do next?” answered only with an unrelated Power System milestone.

**Evidence:** The same assistant answered a simpler “How does this page work?” well on Drafting, but duplicate copies of that prior answer appeared in history.

**Why it matters:** Beginners ask compound questions naturally. Ignoring the page question makes the assistant appear context-blind.

**Suggested improvement:** For combined intent, compose the existing application-surface explanation with the completeness-driven next action. Deduplicate message persistence.

**Estimated effort:** 2–3 days.  
**Expected user impact:** Medium to high for onboarding.

### M2. Character Intelligence contains contradictory structure

**Problem:** Anika's prose description explicitly states what she wants and fears, while structured Goals and Fears both display “None yet.”

**Evidence:** Live Character Intelligence showed the contradiction on one screen.

**Why it matters:** Completeness and character analysis may penalize information that already exists, and authors cannot tell which field is authoritative.

**Suggested improvement:** Reuse the existing extraction/Shared Narrative Context pipeline to normalize description facts into structured fields, retaining provenance and author approval.

**Estimated effort:** 2–4 days.  
**Expected user impact:** Medium; reduces duplicate entry and false incompleteness.

### M3. Canon provenance is incomplete in the visible explorer

**Problem:** The approved canon fact showed origin `canon proposals`, version, and status, but the “Evidence and approval history” region contained no visible evidence/history, and the review history list was empty.

**Evidence:** This followed a successful approval that propagated to the Story Bible and Knowledge Graph. Bible version moved from 281 to 284 for the single approval.

**Why it matters:** Canon is meant to be author-governed and fully transparent. The fact exists, but its audit trail is not inspectable.

**Suggested improvement:** Join the existing proposal decision/evidence records into the inspector and explain multiple Bible-version increments if intentional.

**Estimated effort:** 2–3 days.  
**Expected user impact:** Medium for governance trust.

### M4. Publication blockers are safe but opaque

**Problem:** Export correctly stayed disabled, but Manuscript showed only “1 findings” and a raw version UUID, not the chapter-gap explanation returned by the API.

**Evidence:** The API correctly reported a chapter sequence gap and publication preflight blockers; the live UI did not display the finding detail.

**Why it matters:** Blocking unsafe publication is good, but an author must know exactly how to unblock it.

**Suggested improvement:** Render existing report findings with chapter labels and direct navigation; hide immutable IDs outside Developer Mode.

**Estimated effort:** 1–2 days.  
**Expected user impact:** Medium to high near publication.

### M5. Mystery publication criterion can pass on absent registry data

**Problem:** “Mysteries resolved or intentionally deferred” was satisfied even though the planned arc had three named unresolved mysteries and foreshadowing.

**Evidence:** The formal mystery registry was empty, so the criterion treated absence as success. Other blockers still prevented export.

**Why it matters:** The shared readiness policy is only as trustworthy as its source coverage; planning data must not disappear from publication evaluation.

**Suggested improvement:** Have the existing readiness projection distinguish “no mystery data” from “all mysteries resolved” and reconcile planned arc mysteries into the shared graph.

**Estimated effort:** 2–4 days.  
**Expected user impact:** Medium; prevents false readiness later.

### M6. Workspace Companion is helpful but too large and sometimes stale

**Problem:** At 1280×720, Toolbox plus expanded Companion left roughly 524 px for the workspace. It showed vague/duplicate “Workspace update” cards and a stale canon-proposal count.

**Evidence:** The companion did stop flooding during 55 generations and provides collapse, docking, reduced-motion, and distinct animation states—strong foundations. But “Ask how this page works” merely opened a blank assistant, and “Tomorrow” snooze was ambiguous.

**Why it matters:** The guide can become the distraction it is intended to avoid, especially during writing.

**Suggested improvement:** Keep the visual design and animation state model; reduce expanded default width/height, name affected story objects, make suggested prompts one-click executable, and refresh counts from the owning resource.

**Estimated effort:** 2–4 days.  
**Expected user impact:** Medium to high for focus and guidance.

### M7. Cold-start performance exceeds a comfortable desktop threshold

**Problem:** Warm bootstrap scales well, but broad invalidation/cold load becomes slow.

**Evidence:** Measured cold bootstrap: 100 chapters 1.41 s; 250 2.54 s; 500 4.06 s; 1,000 7.36 s; 2,000 20.36 s. Warm bootstrap remained 11.7–57.1 ms. A second 2,000 run was 14.76 s. The live 2,000-project dashboard took 26.16 s to become author-ready.

**Why it matters:** Cache misses, upgrades, or large changes feel broken unless progress is explicit. The original 500+ target is mostly acceptable; 1,000–2,000 is a stress boundary.

**Suggested improvement:** Profile and bound the existing bootstrap projection, keep expensive panels lazy, and expose staged readiness. Avoid rebuilding invalidated domains that are not needed for the first screen.

**Estimated effort:** 4–7 days.  
**Expected user impact:** Medium for epic/series authors; low for small novels.

### M8. Execution observability reports transport success, not usable product success

**Problem:** All 72 SceneWriter traces were marked success even though one generation failed and 12 drafts could not pass approval.

**Evidence:** 577,987 tokens, about $0.2312 estimated cost, average provider latency 8.38 s, and zero trace retries were recorded, while application validation failed downstream. Logs also repeatedly print settings-load messages without a visible correlation ID joining provider call, validation, persistence, and UI action.

**Why it matters:** Operators can see a healthy provider while authors see failed work, delaying incident diagnosis.

**Suggested improvement:** Preserve provider status but add an application outcome/status to the existing trace, plus request/correlation ID through validation and persistence.

**Estimated effort:** 2–4 days.  
**Expected user impact:** Medium indirectly through faster support and recovery.

### M9. Validation/test data pollutes the visible project library

**Problem:** The live Projects page contained 2,621 active projects across 110 pages, dominated by test fixtures.

**Evidence:** Backend pytest correctly uses an isolated database, but multiple Playwright files use the default `novelforge` database and cleanup is inconsistent.

**Why it matters:** Reusing this environment for demos or release verification makes the commercial product look broken and can hide real projects.

**Suggested improvement:** Give Playwright a dedicated database namespace and guaranteed cleanup by project ID. Do not use title-prefix bulk deletion.

**Estimated effort:** 1–2 days.  
**Expected user impact:** Medium in QA/demo deployments; low in a fresh customer database.

### M10. Hosted commercial security boundary is unspecified

**Problem:** API authentication is enforced only when a local token is configured; defaults are appropriate for a local desktop stack but not a multi-user hosted product.

**Evidence:** Trusted hosts and CORS are local by default, which is good. No evidence was found that this build is intended to provide tenant/user isolation when internet-exposed.

**Why it matters:** “Commercial launch” can mean local desktop or hosted SaaS; the latter would be unsafe without an explicit identity/tenant boundary.

**Suggested improvement:** Document the supported deployment model. If launch is local-only, keep it local and say so. If hosted, make the existing token/auth boundary mandatory and validate per-project authorization before release.

**Estimated effort:** Documentation 0.5 day; hosted hardening is a separate release gate.  
**Expected user impact:** Medium to critical depending on deployment; not a defect for strictly local use.

## Low findings

### L1. Author-facing wording still leaks identifiers and grammar defects

**Evidence:** Raw UUIDs appeared in Story Health, Knowledge Graph, Editorial, Canon Queue, and Manuscript. Text included “1 new story fact need your decision.”

**Suggested improvement:** Centralize existing story-label resolution and run a terminology/copy pass.  
**Effort:** 1–2 days.  
**Impact:** Low individually, cumulative polish gain.

### L2. Project workspace bundle remains large

**Evidence:** Production build passed, but `/project/[projectId]` is 217 kB route code and 368 kB first-load JavaScript.

**Suggested improvement:** Lazy-load existing heavy workspaces such as graph/editorial/manuscript without changing boundaries.  
**Effort:** 2–3 days.  
**Impact:** Low to medium on cold desktop visits.

### L3. Backend deprecation warnings are accumulating

**Evidence:** Backend passed with 81 warnings: Pydantic class config, `__get_validators__`, `json_encoders`, and a LangGraph pending default change.

**Suggested improvement:** Migrate models incrementally and pin/declare the LangGraph serializer behavior.  
**Effort:** 2–4 days.  
**Impact:** Low now; reduces upgrade risk.

### L4. Some status language is ambiguous

**Evidence:** “Readiness” showed Ready for the arc while publication was not ready; Companion showed “0 new messages” alongside five existing items; “Tomorrow” did not state a time.

**Suggested improvement:** Qualify labels as Arc Drafting Readiness, unread messages, and a concrete snooze time.  
**Effort:** 1 day.  
**Impact:** Low to medium for novice comprehension.

## Wishlist

No wishlist features are recommended. New agents, new dashboards, and a Paragraph Editor expansion would add complexity without addressing the verified launch blockers. The existing services and agent roles are sufficient once their contracts, state transitions, and author-facing recovery paths are corrected.

## Writing-quality assessment

### What helped

- Most scenes had a concrete immediate goal, obstacle, decision, and forward handoff.
- Hooks were readable and the central sibling/civic-debt conflict generated clear stakes.
- Physical detail often carried emotion instead of relying only on abstract explanation.
- The planning inputs materially shaped named events, artifacts, the protagonist's dilemma, and later chapter turns.

### What did not reach professional-novel quality

- Average Version A scene length was about 248 words (182–358), so the result read as linked vignettes rather than fully dramatized commercial-novel scenes.
- Sensory motifs and emotional gestures repeated across scenes: rain, ozone, hammered hearts, hitched breath, white knuckles, fingers/hands, and similar sentence frames.
- Emotional meaning was sometimes stated through explanatory metaphors immediately after the action had already conveyed it, reducing reader space.
- POV shifted to first person in the final two chapters without an intentional plan or warning.
- The Story Auditor caught broad continuity/structure concerns but not the most reader-visible POV drift or prose repetition.
- Canon proposals multiplied incidental inventions, raising governance cost.

Bottom line: the workflow encourages more structured writing than an ungrounded generator, but currently guarantees neither sustained scene depth nor reliable professional editing. It helps create more usable material; it does not yet reliably turn that material into a better novel with less effort.

## Performance results

| Chapters | Dashboard | Bootstrap cold | Bootstrap warm median |
|---:|---:|---:|---:|
| 100 | 112 ms | 1,409 ms | 11.7 ms |
| 250 | 147 ms | 2,540 ms | 13.0 ms |
| 500 | 140 ms | 4,058 ms | 17.8 ms |
| 1,000 | 175 ms | 7,363 ms | 33.2 ms |
| 2,000 | 563 ms | 20,361 ms | 57.1 ms |

The 2,000-chapter benchmark process peaked at about 82.3 MB working set and 17.3 seconds total CPU across the full benchmark script. These are service-process measurements, not whole-machine totals. Cache effectiveness is excellent; cold projection and front-end list rendering are the scale risks.

## Automated validation results

| Gate | Current result | Interpretation |
|---|---|---|
| Backend | **118 passed, 7 skipped** in 10:32 | Green, with 81 warnings; primary provider tests are not all live |
| Frontend | **63 passed** across 17 files | Green; mostly component/API mocks |
| ESLint | **Pass** | No warnings/errors |
| Production build | **Pass** | Next.js compiled/type-checked; project first load 368 kB |
| Playwright | **43 passed, 3 failed, 2 skipped** in 32.6 min | Release gate failed on real drafting, novice flow, and paragraph setup |
| Database integrity | **Pass** for sustained and beginner audit projects | Referential/storage consistency only, not semantic correctness |

## Test-suite weaknesses

- The RC7 amateur E2E stops after reviewing one exploratory draft; it does not revise, approve, continue, assemble, or publish (`e2e/rc7-amateur-writing.spec.ts:49-87`).
- Backend provider behavior is normally replaced with a deterministic fake in `backend/tests/conftest.py`; those tests validate orchestration contracts, not Gemini variability.
- Idempotency coverage is sequential, not simultaneous.
- No automated invariant proves Writer's Room leaves approved/active source state untouched.
- No long-form E2E asserts chapter ordering, list scalability, canon proposal volume, POV consistency, or semantic finding deduplication.
- No adversarial Character Conversation test asks directly about known future/unknown facts and validates the response claims.
- The Paragraph Editor productivity setup asserts only `response.ok()` and omits the response body, reducing failure diagnosability.
- UI stability tests validate fixed viewports but do not prove the usable center width with both Toolbox and Companion expanded.

## Verified strengths that should be preserved

- Architecture boundaries and shared Narrative Analysis graph are coherent enough to fix in place.
- Reload during an in-flight real generation preserved the eventual draft.
- Repeated canon approval was rejected with no duplicate canon record.
- Canon approval propagated to Canon Registry, Story Bible, and Knowledge Graph without manual refresh.
- Publication export remained disabled for an invalid/gapped manuscript.
- Story Timeline presented the 11-event dependency chain clearly in author language.
- Warm bootstrap cache scaled well through 2,000 chapters.
- Companion recommendation memory prevented a 55-generation notification flood and honors reduced motion/collapse.
- Frontend unit tests, backend regressions, lint, production build, and database referential audit all passed.

## Release recommendation

Do not launch commercially until all Critical items and H1, H2, H4, H5, H9, and H11 are closed. Then require:

1. two consecutive full Playwright passes on the real configured provider;
2. a repeat 50-scene soak with at least 95% generation completion and no silent failures;
3. Writer's Room active/approved invariants under normal and concurrent calls;
4. adversarial character-awareness tests;
5. a 100–500 chapter live UI check with ordered, bounded lists;
6. a publication journey where every blocker is visible and actionable;
7. a clean dedicated E2E database.

At that point NovelForge could be a strong private beta candidate. Today it is an impressive, functionally broad RC with real author value, but the remaining failures affect the exact promises—control, continuity, reliability, and explainability—that distinguish it from an ordinary AI text generator.
