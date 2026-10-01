# NovelForge Product Audit Implementation Report

Date: 2026-08-08

## Outcome

NovelForge now presents the normal author journey around four stages: Shape the Story, Write the Story, Keep It Consistent, and Finish the Book. The advanced systems remain available through progressive disclosure. The implementation focused first on orchestration correctness, author authority, stale-state handling, failure recovery, and visible long-running work.

## Orchestration and automatic development

- Added a durable, atomic development lease so duplicate clicks and concurrent requests cannot start overlapping development runs.
- Development resumes safely after interruption; completed work remains persisted and the next run can continue from authoritative state.
- Automatic development is bounded to three passes, stops on genuine author gates, and does not let optional questions block progress.
- Same-pass downstream agents receive upstream results produced earlier in the pass.
- Progress records expose pass number, completed tasks, current author-facing role, next work, failures, and saved outcomes.
- Author decisions are compared with their prior effective authority, including a question's default recommendation. Meaningful changes create reconsideration/invalidation records instead of appending contradictory planning.
- Reconsideration is visible on the Dashboard and is resolved by targeted subsequent development.
- Agent memory is reindexed after applied outputs. Model-aware context budgets retain canon and approved decisions at highest priority.
- OpenRouter is not subject to the Google AI Studio application throttle; Gemini retains the configured rate control.

## Planning and readiness

- Arc draftability now depends on required core evidence, author-approved required checks, readiness, and authority—not optional depth dimensions.
- Required readiness items remain required even if an AI payload incorrectly marks them nonblocking.
- Arc character-growth evidence recognizes both arc-native growth and progression records.
- Arc checklist approval synchronizes the corresponding readiness requirement.
- The UI distinguishes required core readiness from an optional maturity-depth target.
- Authors can now approve generated chapter and scene plans directly in Drafting. This closes the former dead end between a draftable arc and approval-quality prose generation.
- Writing summaries refresh when plan status changes, eliminating stale readiness warnings.

## Writing, review, and provider compatibility

- Scene generation shows `Writing scene...` at both entry points and disables duplicate actions while work is active.
- Long AI actions use a four-minute client allowance, preventing the previous false 30-second failure while the backend was still working.
- Prose-producing agents use their configured output budget instead of the former 3,000-token cap.
- A narrow provider compatibility recovery can extract only reader-facing prose from a malformed structured envelope, or accept clearly unstructured prose. It never recovers or promotes canon claims, approvals, authority references, or planning mutations.
- A real DeepSeek v4 Flash/OpenRouter run produced and persisted a 679-word Version A after the compatibility change.
- The draft remained in author review, with three newly introduced facts placed in the Canon Proposal Queue.
- Old failure banners are cleared when retrying draft, editorial, manuscript, canon, and intelligence actions.
- Chapter and scene labels no longer duplicate names such as `Chapter 1: Chapter 1`.

## Navigation and author-facing language

- Primary navigation is limited to Dashboard, Continue Writing, AI Guidance, Toolbox, and Settings.
- Toolbox is organized by the four author stages. Seventeen specialist/detail surfaces remain under `More tools and project details`.
- Internal agent names are translated to author-facing team roles in normal activity views.
- Project Activity labels outputs as historical saved snapshots and explicitly says current authority lives in the owning workspace.
- Dashboard next actions now prioritize the active draft's review/revision state over generic scene-plan readiness.
- Narrative Intelligence banners use `Story guidance` for normal authors.
- Story Health labels its production metrics as approved chapters and approved chapter words.
- Canon rendering now tolerates legacy/provider records without a `field`; it displays `story fact` instead of crashing.

## Author control and frozen boundaries

The implementation preserves:

- Canon proposal/approval and provenance boundaries.
- Decision history and impact preview.
- Shared Narrative Intelligence graph authority.
- Story Bible as an approved, rebuildable projection.
- Scene-draft and revision lineage.
- Writer's Room source protection.
- Paragraph Editor content, versions, recovery, history, comments, locks, and approval boundaries.
- Character chronology validation.
- Backup checksum, preview, restore-as-copy, remapping, and rollback behavior.

No broad redesign was made to the frozen Paragraph Editor.

## Architecture impact

The existing authority model and collection ownership are unchanged. Changes are concentrated in orchestration state management, planning invalidation/reconsideration, provider execution handling, readiness semantics, author-facing navigation/status views, and defensive rendering. No new narrative graph or competing source of truth was introduced.
