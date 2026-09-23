# NovelForge Conversational Planning Precedence Report

## Result

Confirmed Story Studio planning is now projected into the existing persistent story state and included in writing/assistant context ahead of raw conversation and candidate memory.

## Context precedence

The effective order is:

1. approved canon;
2. approved decisions;
3. confirmed Story Studio planning;
4. confirmed Characters, World, Relationships, arcs, mysteries, timeline, and related owner records;
5. approved prose and relevant chapter intelligence;
6. relevant unresolved threads and suggestions;
7. current author instruction;
8. historical conversation only as explanation, never as authority.

`confirmed_story_studio_planning` is built from existing owner collections where the source is Story Studio planning and the authority status is confirmed. It is injected into the persistent workflow state, Narrative Studio context, and Narrative Interaction prompts.

## Safety

Brainstorming remains non-mutating. Concrete planning creates reviewable candidates. Confirmation uses existing owner services and does not automatically create canon. Superseded historical chat remains visible as history, but current saved state outranks it.

