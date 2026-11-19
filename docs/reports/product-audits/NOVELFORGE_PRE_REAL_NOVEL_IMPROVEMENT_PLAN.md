# NovelForge Pre-Real-Novel Improvement Plan

This plan is evidence-based and implementation-free. It records what should happen after the author reviews this audit.

## Fix before starting a real novel

### P0 — Authority-safe continuation

- Ensure approved prose and confirmed author choices are the only high-priority drafting context.
- Exclude provisional Develop artifacts from writing retrieval unless explicitly requested as brainstorming.
- Store and expose rejected ideas so they cannot silently return as generation guidance.
- Add a continuation preflight for protagonist identity, age, pronouns, POV, location, household, active goal, and explicit exclusions.

### P0 — Chapter lifecycle and retry safety

- Bind every generation job to an explicit chapter target and source version.
- Make provider completion idempotent.
- Prevent a retry from advancing the chapter number.
- Resolve delayed completions before allowing a retry.
- Ensure only one raw active version exists for a chapter and that version numbers are authoritative.

### P0 — Chapter 1 opening quality

- Require first-scene grounding for present identity, immediate location, human want/need, and readable POV.
- Keep the old-life material, but reveal it through behavior, sensory memory, and a present choice.
- Delay system terminology until the reader understands the person and local stakes.
- Add a literary opening review that is separate from structural validation.

### P0 — Visible state consistency

- Make Dashboard, Writing, Companion, Story Health, Knowledge, Canon, and Toolbox derive their current chapter, milestone, health, and approval state from the same source.
- After approval or generation, refresh the visible state or show a clear persisted/refreshing status.
- Warn when nine visible chapters are still drafts and only one chapter feeds extraction/memory.

## Fix before scaling to a long novel

- Unify Discovery Writing and controlled Drafting or clearly define their intended order.
- Give Story Studio a current-decision panel, candidate/rejected controls, and a compact history.
- Let the author review a small Develop proposal before the expensive specialist cycle.
- Fix invalid `cycle_generated` metadata and make `/audit` actionable.
- Attach Story Studio and Discovery Writer calls to one project-level observability ledger.
- Make protected whole-chapter revision reliable and reviewable.
- Add a true continuity/story-health pass that compares prose, not only metadata.

## Can wait until after the authority pass

- Phase D progressive retrieval experiments;
- Tencent comparative retrieval as a writing default;
- advanced faction/academy expansion;
- broad visual redesign;
- cost optimization of strong-model drafting;
- publication/export polish.

## Recommended next implementation phase

“Authority-safe writing journey” should be the next phase. Its acceptance test should use a fresh real-provider project and deliberately exercise: author rejection, confirmation, Chapter 1 grounding, chapter retry, delayed provider completion, approval refresh, Chapter 2 continuation, and retrieval inspection by Chapter 8–10. The phase should preserve Native Phase C and require the old behavior to remain available as a safe fallback if any measured quality or authority check regresses.

