# Develop Story Delta Handoff Report

## Result

Later specialists now receive compact structured deltas instead of replaying full prior specialist prose. Full output remains stored in `discussion_messages` and `agent_outputs` and can be inspected independently.

## Handoff contract

Each handoff contains:

- specialist and cycle;
- compact claims;
- recommendations;
- affected entities;
- constraints preserved;
- new conflicts;
- open questions;
- `accepted_state`, initially `pending`;
- evidence references to persisted artifacts, proposal, and run.

Handoffs are derived workflow coordination, never story authority.

## Same-cycle dependency behavior

| Consumer | Relevant upstream handoffs |
|---|---|
| Relationship | none in the tested order |
| Character Journey | Relationship |
| Mystery | Relationship, Character Journey |
| Arc Architect | Relationship, Character Journey, Mystery, plus Theme/Knowledge when present |
| Pacing | Character Journey, Mystery, Arc Architect |

The matched run recorded non-empty handoff context for all four specialists after Relationship. Handoff tokens rose gradually from 184 to 824 rather than replaying multi-thousand-token full outputs.

## Persistence and resume

`develop_story_handoffs` is project-scoped and has a unique identity over:

```text
project + run + cycle + specialist
```

Upsert processing is idempotent. At the start of a run/resume, existing handoffs for the same run and cycle are reloaded before specialist execution. Duplicate persistence was tested: two writes produced one record, and the record reloaded correctly.

The collection is included in the project ownership registry, so duplicate, backup, restore, and purge use the same lifecycle boundary as the rest of the project. Its absence does not affect authority; it can be regenerated from the retained full specialist outputs if a future repair tool is added.

## Cross-agent coherence

All five current real-provider outputs preserved the Chapter 10 reveal boundary. Labelled role checks passed 5/5, and the exact outputs were replayed through the legacy builder to isolate context cost from output quality. No handoff was accepted as canon, approved planning, or an author decision.
