# RC8 Author Safety Workflow

## When generation succeeds

1. NovelForge reuses cached Narrative Intelligence and assembles bounded scene
   context.
2. Gemini returns a candidate using story labels.
3. The server normalizes the provider shape, parses the contract, reconciles
   references, and validates narrative authority.
4. One new immutable review version is persisted.
5. The author compares, edits, approves, discards, or restores it.

## When generation fails

1. No partial candidate becomes active or approved.
2. Existing prose remains unchanged.
3. The owning workspace announces what failed and why.
4. The author can retry with the same request ID or navigate to the named
   blocker.
5. Debug detail is available only in Developer Mode.

## Writer's Room

1. The approved/active source remains untouched.
2. Emotional, action, and mystery alternatives are generated independently.
3. Every alternative is inactive and reviewable.
4. Refresh, retry, failure, or a second browser tab cannot promote one.
5. Only an explicit author selection, merge, or promotion changes the active
   review version.

## Character conversation

1. The author chooses a character and chapter boundary.
2. NovelForge projects only knowledge available to that character by then.
3. The response is checked for direct and indirect future/hidden facts.
4. Unsafe output is corrected once or withheld with a visible explanation.
5. New stable facts remain Canon Proposals until the author approves them.

## Publication blockers

Preflight blockers are expressed as an explanation, why it matters, an action,
and a one-click destination. Publication remains conservative: NovelForge does
not silently approve chapters, manuscripts, canon, mysteries, or milestones to
make the gate pass.

