# Develop Story Role Context Architecture

## Runtime flow

```text
Develop Story instruction
        |
        v
Shared authority snapshot
  - project/story identity
  - active canon
  - approved decisions
  - confirmed planning
  - rejected prohibitions
        |
        +--> role manifest --> bounded Story Bible projection
        |
        +--> safe Native retrieval
        |
        +--> bounded chapter/episode evidence when the role needs it
        |
        +--> workflow-only agent memory
        |
        +--> relevant upstream delta handoffs
        v
High-confidence deduplication
        |
        v
Authority coverage + role budget check
        |
        +--> pass: compact packet
        |
        +--> fail: broad legacy-safe fallback + telemetry reason
        v
Provider
```

## Active five-role manifests

| Role | Role projection | Chapter evidence | Upstream handoffs | Budget |
|---|---|---:|---|---:|
| Relationship | characters, relationships, journeys, progressions, knowledge, timeline | yes | none in tested order | 20k |
| Character Journey | characters, journeys, progressions, relationships, knowledge, arcs, threads, timeline | yes | Relationship | 22k |
| Mystery | mysteries, foreshadowing, knowledge, timeline, threads, artifacts | yes | Relationship, Character Journey | 22k |
| Arc Architect | arcs, arc development, threads, mysteries, journeys, progressions, relationships, timeline, drafting, readiness | yes | Relationship, Character Journey, Mystery, Theme, Knowledge | 30k |
| Pacing | arcs, arc development, threads, mysteries, timeline, drafting, progressions, readiness | yes | Character Journey, Mystery, Arc Architect | 30k |

The service also defines role manifests for the other existing planning specialists. It does not create new agents.

## Shared authority snapshot

Confirmed planning retains its typed `values` payload, source, and provenance. An attribution defect discovered during verification—source IDs without their planning meaning—was fixed before sign-off. The final benchmark recorded seven of seven unique confirmed-planning records in every packet, including:

- Elias disappeared five years ago;
- Elias's disappearance is the central mystery;
- Elias may be alive around Chapter 10;
- the current confirmed character and world framing.

Equivalent authority copies are removed only after unique-content accounting. Authority is never trimmed to meet a role budget.

## Role projection rules

- Only declared Story Bible sections are considered.
- Infrastructure fields, embeddings, timestamps, and Mongo IDs are omitted from provider context.
- Candidate, pending, rejected, stale, superseded, archived, and inactive records are ineligible.
- Long fields and child lists are bounded without changing the owner records.
- Raw discussion, editorial history, full story intelligence snapshots, workflow logs, and unrelated approved prose are not preloaded.

## Budgets and fallback

Budgets are internal packet targets, not user settings. Optional evidence is reduced in this order when needed:

1. workflow agent memory;
2. Native hits beyond the role allowance;
3. chapter evidence beyond the bounded set;
4. older handoffs.

Authority and mandatory role context are not silently removed. If they cannot fit, `mode=broad_fallback` is recorded and the existing model-safe broad budget is used. A complete-suite integration test exercised and verified this large-authority fallback.

## Attribution

Each planning packet records:

- instruction tokens;
- authority tokens and expected/actual authority counts;
- role-specific structured-context tokens;
- Native retrieval tokens;
- chapter/episode tokens;
- handoff tokens;
- workflow-memory tokens;
- workflow-metadata tokens;
- duplicate tokens removed;
- packet budget;
- final context tokens;
- mode and fallback reason.
