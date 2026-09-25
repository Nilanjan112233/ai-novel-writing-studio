# NovelForge Develop Story Real Workflow Audit

## Verdict

Develop Story did run through the real application and real provider path, and it incorporated several broad Story Studio themes. It also generated far more planning than the author asked for and promoted unconfirmed planning into the context used by writing. In this experiment it helped create a direction, but it did not preserve the author's authority boundaries well enough to be a safe pre-writing gate.

## Input state

The author had confirmed broad preferences only:

- young adult in a poor river settlement or river-working household;
- an opening local human problem around a dangerous river structure, debt, missing person, or seasonal threat;
- a choice to show up rather than repeat old-life avoidance;
- weak seam perception with a cost and no interface;
- mystery around crossing, world, and why the ability recognizes the protagonist;
- intimate, dangerous, dryly funny, and wondrous tone.

The exact protagonist name, settlement, supporting cast, and mechanics were explicitly left open. The three brainstorm options were requested as unconfirmed, and the author rejected drought, indentured labor, child companion, instant travel, and status window.

## Real run

- Start: approximately 12:41:03 local time.
- End: approximately 12:58:31 local time.
- Duration: more than 17 minutes.
- Provider: OpenRouter / `deepseek/deepseek-v4-flash`.
- Agent outputs: 18.
- Cycles: 3.
- Recorded project traces: 18 Develop calls.
- Recorded tokens: 730,627.
- Recorded cost: `$0.730627`.
- Retries: visible on CharacterJourney cycle 1, ArcArchitect cycle 1, Pacing cycle 2, and Readiness cycle 2; no provider fallback was recorded for these Develop calls.

## Specialist calls

| Cycle | Agent | Total tokens | Cost | Latency ms |
|---:|---|---:|---:|---:|
| 1 | NarrativeDirector | 4,822 | .004822 | 48,528 |
| 1 | StoryArchitect | 6,823 | .006823 | 35,157 |
| 1 | Question | 8,754 | .008754 | 35,485 |
| 1 | CharacterJourney | 11,616 | .011616 | 44,587 |
| 1 | Relationship | 13,574 | .013574 | 25,767 |
| 1 | World | 15,536 | .015536 | 49,663 |
| 1 | Faction | 16,299 | .016299 | 21,625 |
| 1 | Theme | 18,302 | .018302 | 18,628 |
| 1 | ArcArchitect | 21,195 | .021195 | 29,964 |
| 1 | Pacing | 22,429 | .022429 | 22,341 |
| 2 | PowerSystem | 69,974 | .069974 | 36,955 |
| 2 | CharacterJourney | 72,765 | .072765 | 143,828 |
| 2 | Mystery | 70,877 | .070877 | 43,630 |
| 2 | ArcArchitect | 75,549 | .075549 | 27,516 |
| 2 | StoryDevelopment | 74,553 | .074553 | 36,398 |
| 2 | Pacing | 74,547 | .074547 | 20,195 |
| 2 | Readiness | 75,831 | .075831 | 84,669 |
| 2 | Relationship | 77,181 | .077181 | 27,493 |

## What it produced

The run created a large provisional structure: one story arc, one world bible, one power system, one character journey, 12 mystery records, two factions, nine timeline entries, 17 arc checklists, 42 agent memories, one ten-chapter plan, 45 Story Bible sections, and extensive narrative-analysis material. The audit endpoint reported 18 agent outputs and `status=fail` because of invalid `cycle_generated` metadata in four character bibles, eight mysteries, and one relationship graph.

The central records repeatedly used:

- Kael as a provisional protagonist;
- a ten-year-old farm boy;
- an archivist/cartographer old life;
- Thornwick and Kael's family farm;
- the old well, buried sky, hidden fault, and suture-bearer system;
- a ten-chapter arc called “The Well and the Seam.”

These ideas are not merely harmless brainstorming in this run because later writing context retrieved them prominently. The character-bible and arc endpoints correctly marked persistence false/provisional, but the author-facing path did not stop them from steering generation.

## Did it incorporate Story Studio?

Yes, at the theme level: river-working life, local infrastructure, seams, cost, reincarnation mystery, and a slow progression direction appear in the plan and prose.

No, at the authority level: the run filled open slots with concrete names, ages, family structures, locations, and world history. The author had not approved those details. The system also did not present a manageable plan for confirmation before writing.

## Recommendation

Develop Story should return a small, reviewable “proposed foundation” first. A full specialist cycle should be optional and should remain isolated from writing retrieval until the author confirms the protagonist, opening situation, core relationships, and exclusions. The current run is over-planning, not because planning is inherently bad, but because its output is too large and too operationally influential for unconfirmed material.

