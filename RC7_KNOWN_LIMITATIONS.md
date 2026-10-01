# NovelForge V2 RC7 — Known Limitations

## Provider latency and cancellation

Writing requests use the existing synchronous provider gateway. Request
identity prevents duplicate persistence and the UI prevents duplicate in-flight
actions, but cancellation does not terminate a provider request that has
already reached Gemini. On a high-demand response, the bounded retry path can
make a generation take more than two minutes. Existing prose remains safe
during retries.

## Quality remains bounded by the plan

RC7 supplies Story Bible, character, world, relationship, timeline, theme,
plot-thread, adjacent-scene, and decision context to the existing Scene Writer.
It also warns when scene plans repeat the same purpose, conflict, and outcome.
NovelForge does not silently replace an author's repetitive plan. A vague or
duplicated plan can therefore still produce competent but repetitive prose
until the author accepts the coaching and differentiates the scene.

## Writer's Room cost

Writer's Room generates three independent alternatives so the author can
compare real directions. With a remote provider this is intentionally more
expensive and slower than a single revision. The calls are bounded and
idempotent, but are not streamed.

## Large-project cold start

The measured 1,000-chapter synthetic project took 6.77 seconds for an uncached
workspace bootstrap. The same projection loaded in 33 milliseconds from the
persisted cache. A first open after broad invalidation is therefore noticeable;
normal return visits are fast.

## Frontend bundle

The final production build reports approximately 368 kB First Load JavaScript
for the project workspace. Major workspaces are progressively fetched, but
further code splitting would improve the first uncached desktop visit.

## Legacy warnings

Backend tests still report Pydantic v2 migration deprecation warnings from
older request/configuration models. They do not affect runtime correctness,
browser console cleanliness, or API compatibility, but should be removed in a
future non-breaking maintenance release.

## Acceptance-story scale

The live RC7 writing acceptance creates a bounded multi-chapter story path,
revises and approves scenes, assembles chapters, audits narrative quality, and
checks publication/export workflows. It is not a manually reviewed
market-length 100,000-word novel. Large-project behavior is covered separately
with 100, 250, 500, and 1,000-chapter performance fixtures.

## Agent scope

No new writing agent was added. The current Scene Writer, Editor, Dialogue,
Revision, Canon, Manuscript, and Story Auditor roles already cover RC7. The
identified problems were context, contract, validation, and workflow
integration defects; another agent would have duplicated responsibility.

