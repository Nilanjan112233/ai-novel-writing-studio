# NovelForge Story Studio UX Audit

## Verdict

Story Studio is useful as an exploration surface but is not yet good enough to be the primary author interface. It has the right proposal-based intent and the conversation is visible, but the interaction model is closer to a long activity log than a modern conversational workspace.

## What was tested

The isolated project received four real conversational turns:

1. The application asked useful questions about old-life reflex, regret, local stakes, and moral conflict.
2. The author answered with disaster mapping, emergency infrastructure, sibling regret, a river-household problem, and a costly seam perception.
3. The author requested three explicitly unconfirmed foundations. The application produced three options and recommended the rejected drought/indentured-labor option.
4. The author explicitly rejected those directions and stated broad preferences to confirm. The application acknowledged the constraints but did not present an actionable confirmation ledger.

## Strengths

- Conversation is persisted and inspectable.
- The first and third provider responses were useful and appropriately scoped to brainstorming/questions.
- Brainstorming was stored as non-mutating in job metadata, which is consistent with proposal-based authority.
- The model selector is visible.
- The assistant can surface navigation actions and story references.
- The UI provides a path to chapter actions and Develop Story.

## Problems

### Message ordering and history

The newest message is not visually primary after several long turns. Old messages remain expanded, each with both user and assistant text, making the current conversational state hard to find. There is no strong “current decision” strip, pinned summary, or compact history mode.

### Confirmed versus candidate state

The author explicitly asked for a restatement of confirmed, candidate, and rejected material. The response said the foundation was set, but there was no visible confirmation queue, rejection ledger, or per-item status. Later Toolbox pages showed candidate labels in some places but the author had to know which pages to inspect.

### Intent classification

The answer describing what was distinctive and what remained generic was classified as `review` and returned “I did not find a current genericness warning,” rather than answering the creative question. This is a conversation-quality failure even though the technical job completed.

### Composer and context

The composer is at the bottom of a long history. The current conversation is visually diluted by old turns and multiple companion surfaces. The author cannot easily see what NovelForge currently believes before sending the next message.

### Multiple assistants

Story Studio, AI Narrative Companion, Workspace Companion, and Interactive Narrative Studio appear as overlapping assistant concepts. A novice cannot easily tell which assistant mutates nothing, which can navigate, which surfaces suggestions, and which is the place to continue writing.

### Long-running operations

Develop Story ran for more than seventeen minutes. The visible completion state did not make the amount of generated planning or its provisional status obvious. Long chapter jobs also left the composer/button in a stale generating state until refresh, contributing to the duplicate Chapter 4.

### Actions after generation

The author needs one obvious path from discussion to “review this plan,” “confirm these items,” “start Chapter 1,” and “return to current writing.” Those actions are distributed across the conversation, Dashboard, Writing, and Toolbox.

## Better interaction model, without redesigning now

The next UX design should preserve the proposal-based architecture but add:

- a compact, collapsible conversation history;
- a pinned “Current author decisions” panel;
- explicit Confirm, Keep as candidate, Reject, and Revisit controls for suggestions;
- a visible rejected-items ledger used by future generation;
- a single current composer with a clear model/task explanation;
- job cards that show active, completed, failed, retrying, and persisted states;
- a single “Continue writing” action that opens the correct chapter and state;
- an evidence drawer for why a suggestion is shown;
- a clear handoff from Story Studio to Develop Story that previews context and warns about unconfirmed planning.

## Acceptance conclusion

Story Studio is good enough for exploratory testing and for authors who understand the internal architecture. It is not good enough as the default author home for a novice writing a real novel.

