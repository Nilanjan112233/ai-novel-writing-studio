# NovelForge UX Polish: Story Studio History and Evidence

## Implemented

- Saved responses are labeled `Historical conversation · saved response`.
- Current results are labeled `Current grounded answer`.
- Historical cards have `Refresh against current story`, which creates a new current answer and preserves the old response.
- Unapplied proposals are labeled as requiring an author decision.
- Evidence accepts arrays, objects, scalar fields, and nested records and renders readable labels rather than raw payloads.
- Chapter evidence is displayed as `Story source · Chapter N`.
- Provider answers are presentation-sanitized so internal finding IDs are not shown in normal author mode.
- Story Studio story-state questions now route through current project evidence when they mention chapters, characters, injuries, mysteries, canon, relationships, or remembered facts.

## Real-provider browser evidence

Using the actual running Story Studio and configured provider gateway, the question:

> What does NovelForge remember about Mara’s injury, and what happened in Chapter 3?

returned specific continuity facts: Mara’s healing left-palm injury, its status in Chapter 2, the satchel and compass events in Chapter 3, the hidden compartment, the old-ferry promise, the map, and the Elias clue.

Refreshing an older “what should I work on next?” response produced a new current answer while retaining the original response as history.

