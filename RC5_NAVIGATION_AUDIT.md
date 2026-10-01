# RC5 Navigation Audit

## Post-RC5 verification — 2026-07-23

All workspace destinations now persist as `?section=` deep links. Direct loads, assistant actions, Companion actions, the desktop Ctrl/Cmd+K navigator, sidebar/toolbox actions, and browser Back/Forward converge on the same destination registry. Invalid targets fall back to Dashboard.

New verified destinations include recoverable project lifecycle views and the governed Manuscript publication surface. The Project Assistant answer to “How do I publish?” explains approved-version preflight, supported formats, and navigates to Manuscript.

The E2E audit verifies Canon Queue → Timeline → browser Back, Assistant → Manuscript, Companion actions, and project Active/Archived/Trash transitions. No recommendation in the audited feeds is emitted without a valid destination.

## Current hierarchy

Primary rail:

1. Dashboard
2. Continue Writing
3. AI Guidance
4. Toolbox
5. Settings

Toolbox: twenty-seven destinations presented as one ungrouped list.

Assistant tabs: Assistant, Characters, Graph, Canon Queue, Context.

## Confirmed working paths

- primary rail destinations open;
- every toolbox button renders its target without page-level horizontal overflow;
- Novel Creation Guide steps navigate to workspace sections;
- Companion messages contain a `Show me` action;
- Assistant supports explicit chapter, scene, Story Health, Timeline, Canon, Character Intelligence, Story Bible, Knowledge Graph, Plot Threads, and Mystery destinations;
- Critique findings can route to their responsible subsystem;
- Canon registry records can be inspected from Canon.

## Dead ends and ambiguous paths

1. **Open Chapter routes to the hard-coded Continue Writing placeholder**, not a selected governed chapter.
2. Workspace Context recommendations offer “Why was this generated?” but no open/navigate action.
3. The top intelligence banner offers Explain only.
4. Canon Queue has no persistent direct entry from the Canon workspace or toolbox.
5. Story Bible is called Knowledge in navigation and Story Bible in Assistant language.
6. Characters is the destination for Character Intelligence, but the page title says Character Journey.
7. Timeline does not distinguish Story Timeline from the requested Project Timeline.
8. Run Cycle does not preview what will happen or where results will appear.
9. Section state is not represented in the URL; refresh returns to Dashboard and cannot preserve a shared/deep-linked workspace destination.
10. Several empty states do not contain a creation or navigation action.

## Required navigation contract

Every recommendation/action must provide:

```text
label
destination section
optional entity/chapter/scene focus
reason for navigation
completion condition
fallback destination
```

Destinations must be validated against one shared application catalog. Dashboard, Assistant, Companion, Creation Guide, critique, Canon, and workspace recommendations must not invent section names independently.

## Proposed workflow grouping

- **Start:** Dashboard, Creation Guide, Story Vision, Questions
- **Design:** Characters, World, Power System, Factions, Relationships, Themes
- **Structure:** Arcs, Arc Development, Plot Threads, Mysteries, Story Timeline, Readiness
- **Write and revise:** Drafting, Editorial, Manuscript
- **Understand:** Story Health, Story Bible, Knowledge Graph, AI Insights
- **Govern:** Canon, Canon Queue, Discussion Room, Workflow

The grouping changes discoverability only; it does not change ownership or architecture.

## RC5 resolution

The shared Application Knowledge catalog now validates every guidance and Assistant destination. The toolbox exposes 31 surfaces in workflow groups rather than a flat list.

| Source | Direct destination behavior |
|---|---|
| Dashboard next action | Opens the Narrative Completeness owner |
| Page Guidance | Opens the current surface’s approved downstream action |
| Application Assistant | Opens the explained surface first, then optional downstream workflows |
| Project Assistant | Opens the chapter, scene, or responsible intelligence workspace |
| Workspace Companion | `Show me` opens the recommendation target |
| Workspace Intelligence | `Review now` opens the finding owner |
| Critique | Opens the responsible subsystem |
| Canon | Visible `Review Canon Queue` action opens the proposal queue |
| Project Timeline | Opens the affected workspace |
| Story Health History | Opens the finding/evidence owner |
| Knowledge Graph | Opens the selected entity’s owning workspace |

The fabricated Continue Writing destination was removed. Continue Writing and chapter navigation now use governed Drafting. Story Timeline, Project Timeline, and Story Health History are distinct destinations with distinct page guidance.

One limitation remains: section state is not encoded in the URL, so a full route refresh returns to Dashboard. This is documented rather than hidden.
