# NovelForge V2 RC7 — Amateur Author UX and Story Quality Report

## Acceptance perspective

The live acceptance was performed as a first-time author who had a premise but
did not know NovelForge's architecture or terminology. The journey created a
new project, completed the beginner foundation, planned a first scene, entered
Drafting, asked the Assistant and Companion for help, generated with the real
Gemini configuration, inspected the result, and verified persisted narrative
knowledge. A separate real-provider journey created and approved six scenes
across three chapters and assembled all three chapter drafts.

## Problems found before RC7

| Novice experience | Why it was a problem | RC7 result |
|---|---|---|
| Guided setup ended at a scene plan, but Drafting only said “blocked” | The author could not tell which approval or readiness step was missing | Writing Desk lists the exact blockers and a direct next action; exploratory drafts are clearly labelled |
| Assistant answered a writing-state question with generic page help | It sent the author back to the page they already occupied | Writing-state questions use the live writing projection before application or story retrieval |
| Companion recommended unrelated foundation tasks while Drafting was blocked | It felt like a notification feed, not a writing coach | Writing surfaces prioritize prepare, generate, review, revise, approve, and continue actions with existing cooldown memory |
| Scene Writer output was converted into planning-summary placeholders | The result did not feel like prose | The existing Scene Writer now returns full reader-facing prose plus an explanation |
| Regeneration recreated paragraph skeletons | Existing editor work could be lost | Whole-scene alternatives preserve all Paragraph Editor records and versions |
| Existing versions looked like technical history | An amateur could not confidently explore alternatives | Versions are labelled A/B/C and support preview, compare, favorite, merge, discard, and restore without replacement |
| Planning context was invisible and partly omitted | The author could not trust that earlier work mattered | Writing Desk reports reused context; generation receives the bounded Story Bible, decisions, theme, world, relationships, plot threads, timeline, and adjacent scenes |
| Repetitive plans could generate repetitive chapters without an early signal | More generation could amplify a planning mistake | Non-blocking “Before final prose” coaching detects identical purpose/conflict/outcome plans |

## Live novice result

The novice story concerned a father trying to collect a magical memory fare
while protecting his daughter. The generated scene was 186 words and made the
contract visible:

- **Goal:** collect the memory fare.
- **Trouble:** a silent child refuses, and the river exposes the father's
  hidden past.
- **Stakes:** his standing and his daughter's stolen memories.
- **Handoff:** a Council lantern forces a choice between hiding the child and
  facing the authorities.

The prose used action and sensory detail to carry emotion rather than explaining
every feeling. It established an immediate goal, personal stakes, a
character-driven dilemma, and a forward hook without an information dump. The
provider introduced one new proper name; NovelForge routed it to the existing
Canon Proposal Queue instead of making it official.

The draft remained exploratory because the novice intentionally left planning
gates unresolved. That is correct: NovelForge allowed low-risk experimentation
but did not pretend the scene was ready for approval.

## Story-quality evaluation

| Quality | Live observation | Assessment |
|---|---|---|
| Character-driven conflict | The father's public duty conflicts with protecting a vulnerable child and recovering his daughter's memories | Strong in the novice scene |
| Clear stakes | Personal loss and social consequence are both explicit in the scene contract | Strong |
| Emotional subtext | Gesture, silence, river imagery, and the Council lantern carry pressure | Good; a longer revision could deepen specificity |
| Room for readers to feel | The compact scene generally dramatizes emotion instead of naming it | Good, with occasional familiar fantasy phrasing |
| Goal and real trouble | Both are visible before the prose and enacted in it | Strong |
| Pacing | The novice scene enters conflict quickly and exits on a decision | Strong for a short scene |
| Information load | No long lore explanation was required to understand the choice | Good |
| Scene-to-scene causality | RC7 now supplies prior approved prose and next-scene pressure | Structurally improved and visible |
| Planning reuse | Character, world, relationships, themes, mysteries, plot threads, decisions, and timeline are included in bounded context | Verified in stored context and UI counts |

## Honest multi-chapter result

The three-chapter acceptance story successfully generated and approved six
real-provider scenes, assembled three chapter drafts, and passed final
per-scene authority validation after one corrective retry. Gemini also returned
one temporary high-demand response; the existing provider retry recovered
without duplicate prose or data loss.

The Story Auditor rejected the resulting story with 27 raw issues represented
by 20 consolidated findings:

- 1 high continuity warning;
- 11 repetitive-scene findings;
- 1 repetitive chapter-opening finding;
- 6 unresolved-promise findings;
- 1 unresolved-thread finding.

This failure is expected and valuable. The acceptance fixture deliberately
gave several scenes the same generic purpose, conflict, and outcome. The
generated prose connected sequentially, but it repeated the same discovery
shape. RC7 now detects that condition before final prose, asks the author to
differentiate the plan, and uses each scene's timeline event as its distinct
progression. It does not override the author's repeated plan.

## Can a novice change their mind?

Yes. The tested product exposes four protected layers:

1. planning decisions retain the existing edit, history, undo, reopen, and
   impact-preview workflow;
2. paragraph content retains autosave, undo/redo, checkpoints, and immutable
   versions;
3. scenes retain Version A/B/C alternatives, comparison, favorite, merge,
   discard, and restore;
4. structured revisions remain proposals until the author approves the branch
   and separately promotes it as a new review draft.

Approved prose and canon are never silently replaced.

## Companion and Assistant assessment

The Companion is materially more useful while writing because it is driven by
the current Writing Desk state and offers one action at a time. Existing
recommendation identity, cooldown, dismiss, completed memory, and snooze
persistence prevent constant interruption. Its compact animated UI retains
idle, thinking, working, celebration, and reduced-motion states from the frozen
RC6 architecture.

The Assistant now correctly separates:

- **application knowledge** — what a page, control, or workflow does;
- **writing state** — why this draft is blocked and what comes next;
- **project knowledge** — canon, characters, timeline, and story evidence.

In the novice journey, “why is writing blocked?” returned the real blockers and
a usable destination rather than generic documentation.

## Agent decision

No new agent is needed. The existing Scene Writer, Editor, Dialogue, Revision,
Canon, Manuscript, and Story Auditor roles are sufficient. RC7's defects were
caused by an incorrect Scene Writer contract, incomplete context projection,
and weak workflow integration. Adding another agent would duplicate
responsibility and make author control harder to understand.

## Final browser conclusion

The final Chromium suite completed with 46 passes and two
environment-conditional skips. The novice journey produced no console warning,
console error, or page error. Desktop stability passed at 1366x768, 1440x900,
1920x1080, and 2560x1440. The exact latest novice and multi-chapter projects
also passed the post-run database integrity audit with no findings.
