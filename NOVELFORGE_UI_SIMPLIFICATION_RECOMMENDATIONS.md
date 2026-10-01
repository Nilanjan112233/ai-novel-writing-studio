# NovelForge UI Simplification Recommendations

This is an audit recommendation list only. No UI or source changes were made.

## Priority 0: make the current writing state undeniable

- Put one state banner at the top of every project surface: current chapter, latest approved chapter, pending review count, active workflow, and the exact next safe action.
- Use the same health/milestone computation in Dashboard and Workspace Companion.
- Show “9 drafts waiting for review; Chapter 2 has a continuity warning” rather than only “Review Chapter 2.”
- Make refresh/persistence state explicit after approvals and long jobs.

## Priority 0: separate truth levels visually

Use a consistent four-state vocabulary everywhere:

| State | Author meaning |
|---|---|
| Confirmed | The author explicitly accepted it as planning intent |
| Candidate | NovelForge noticed it; author has not accepted it |
| Rejected | The author explicitly declined it; do not use in generation |
| Canon/approved prose | The governed story record that downstream writing may rely on |

Provisional Develop artifacts should never occupy the same visual tier as confirmed author intent or approved prose.

## Priority 0: choose one writing path

Explain Discovery Writing and controlled Drafting in one place. Either:

- present Discovery Writing as the default fast path and make Drafting an advanced alternative; or
- merge them behind one “Write next chapter” action with an advanced mode selector.

The current empty Drafting page is misleading after ten discovery chapters exist.

## Priority 1: simplify Story Studio

- Collapse older turns by default.
- Pin the latest assistant answer and current author decisions.
- Add explicit suggestion cards with Confirm, Keep candidate, Reject, and Ask why.
- Add a rejected-items drawer.
- Keep the composer fixed and visually primary.
- Explain model choice in plain language and show active jobs separately from conversation.

## Priority 1: make chapters safer

- Chapter cards should show approved/draft/protected branch status, word count, extraction status, continuity warnings, and active version in one row.
- A retry must name the exact chapter/draft it will regenerate.
- Disable retry while an earlier job is still running or show the existing job with a cancel/inspect action.
- Show a clear “This draft failed continuity; do not approve” warning when the provider output contradicts approved identity facts.

## Priority 1: make Toolbox pages author-oriented

Replace internal labels such as “provisional,” “candidate,” “persistence success,” and “workflow mode” with short explanations and an optional technical drawer. The author needs to know:

- what NovelForge believes;
- whether it is confirmed;
- where it came from;
- what action is available;
- what will change if they act.

## Priority 2: reduce assistant competition

Story Studio should own creative discussion. Workspace Companion should own brief next-action guidance. AI Narrative Companion should either become a mode inside Story Studio or be clearly framed as navigation/help. The current four-assistant vocabulary increases cognitive load.

## Priority 2: improve editorial confidence

- Replace browser `prompt()` branch naming with an in-page form.
- Show source and proposed revision side by side with protected hash/version metadata collapsed under “Details.”
- Make the failed provider path explain retry count, failure reason, and whether the source was untouched.
- Make selection rewrite discoverable from the chapter reader, not only from Editorial tooling.

