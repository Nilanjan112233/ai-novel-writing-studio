# NovelForge V2 RC5 Product Experience Audit

Date: 2026-07-19  
Audit status: complete before RC5 implementation

## Executive finding

NovelForge is functionally rich but still presents its architecture more clearly than it presents the author's workflow. The main shell exposes five primary controls and twenty-seven toolbox destinations, but the experience does not consistently explain why a surface exists, what the author should do there, or what happens next.

The audit confirms that RC5 does not require new narrative intelligence. It requires an application-knowledge projection, shared contextual guidance, author-language presentation, recommendation lifecycle state, and two history projections over existing events and analysis snapshots.

The Narrative Analysis Engine, Story Intelligence architecture, Story Bible, Canon Governance, Interactive Narrative Studio, Workspace Companion knowledge sources, Novel Creation Guide, and Paragraph Editor remain structurally frozen.

## Audit method and evidence

- traced every App Router page, project workspace section, assistant tab, major modal, card, table, graph, state, and navigation callback;
- rendered all current workspace destinations at 1280, 1440, 1920, and 2560 pixel widths;
- baseline Playwright desktop stability: 12 passed, 0 failed in 1.9 minutes;
- inspected Story Health, Canon, Interactive Studio, and companion screenshots;
- searched visible frontend paths for internal IDs, traces, graph terminology, raw serialization, technical metadata, duplicate-key risks, and non-actionable recommendations;
- reviewed Assistant and Companion context-selection logic.

## Severity summary

### Critical experience defects

1. **Continue Writing is a fabricated placeholder workspace.** It displays hard-coded chapter, scene, prose, character, and canon content rather than the selected project's governed drafting state. Navigation commands such as “Open Chapter 12” can land here.
2. **The Assistant has only story-first reasoning.** Every question first loads Narrative Analysis evidence and calls the narrative provider, even when the author asks what a page or button does.
3. **Normal author views expose raw technical data.** Visible examples include analysis identifiers, execution trace identifiers, cycle numbers, node/dependency/cache statistics, source identifiers, source collections, raw JSON evidence, raw node payloads, and serialized conflict objects.

### High-priority defects

1. The Companion can display repeated or near-identical recommendations because recommendation identity includes a changing completeness fingerprint.
2. Contextual recommendations explain themselves but do not consistently offer a destination.
3. Canon Queue is discoverable only as an Assistant tab; the main Canon workspace does not clearly lead the author through queue, review, approval, Story Bible refresh, and health impact.
4. Knowledge Graph inspection falls back to serialized payloads and lacks author-facing entity cards, neighborhood controls, direct actions, and progressive disclosure.
5. There is no Project Timeline and no score-change Explainability Timeline.
6. All twenty-seven toolbox destinations lack one shared “what/why/do/next” guidance contract.
7. The Assistant drawer consumes 480 pixels and overlays rather than coordinates with the main desktop workspace.

### Medium-priority defects

- inconsistent naming: Canon, Canon Governance, Canon Explorer, Canon Queue; Knowledge versus Story Bible; AI Guidance versus AI Narrative Companion versus Interactive Narrative Studio;
- toolbox is a long ungrouped list with no search or workflow grouping;
- icon-only primary navigation relies on browser title tooltips and lacks explicit accessible labels;
- graph keyboard nodes have no visible focus treatment;
- loading, empty, success, and error language varies substantially between surfaces;
- Settings presents cost, token, routing, model-health, and agent-assignment engineering controls to every author;
- run-cycle language does not explain scope, participants, expected results, or cost;
- assistant evidence badges expose analysis identifiers rather than human-readable sources;
- dashboard repeats Story Health information in several stacked panels before the author reaches the main next action.

## Visible surface coverage

| Surface | Exists | First-time-author status | Primary RC5 action |
|---|---:|---|---|
| Projects library | Yes | Partial | Explain creation, archive, duplicate, and next step; improve empty/success states. |
| Dashboard | Yes | Partial | Establish one hierarchy: milestone, health, next action, recent evolution. |
| Continue Writing | Yes | Defective | Remove placeholder destination and route to governed drafting/editor state. |
| AI Guidance | Yes | Partial | Add application/story query routing and page-aware prompts. |
| Toolbox | Yes | Partial | Group by workflow, add labels/help, preserve direct access. |
| Story Vision | Yes | Partial | Add purpose, required inputs, consequence, next action; remove trace metadata. |
| Story Room | Yes | Partial | Clarify difference from Discussion Room and Assistant. |
| Story Health | Yes | Partial | Translate cache/graph data and raw evidence into author language. |
| Creation Guide | Yes | Good foundation | Make current step and next action more prominent. |
| Discussion Room | Yes | Partial | Replace cycles/traces with sessions and author-facing outcomes. |
| Characters | Yes | Partial | Rename/position as Character Intelligence and explain evidence/actions. |
| World | Yes | Partial | Add missing-work guidance and clear empty states. |
| Power System | Yes | Partial | Add not-applicable path and remove provider/trace details. |
| Factions | Yes | Partial | Add purpose and relationship/navigation actions. |
| Relationships | Yes | Partial | Improve graph legend, focus, empty state, and navigation. |
| Plot Threads | Yes | Partial | Show lifecycle, affected chapters, and direct resolution work. |
| Themes | Yes | Partial | Explain theme tracking and evidence. |
| Mysteries | Yes | Partial | Explain setup/development/resolution status and next action. |
| Readiness | Yes | Partial | Reconcile arc readiness with project milestones in author language. |
| Knowledge | Yes | Partial | Identify this explicitly as the Story Bible knowledge view. |
| Knowledge Graph | Yes | Defective presentation | Replace payloads with typed cards and graph controls. |
| Story Timeline | Yes | Partial | Rename to distinguish it from Project Timeline. |
| Arcs | Yes | Partial | Explain Arc Board columns, progression, and next action. |
| Arc Development | Yes | Partial | Explain maturity, dependencies, drafting eligibility, and consequences. |
| Questions | Yes | Partial | Clarify persistence and Canon Proposal behavior before submission. |
| AI Insights | Yes | Partial | Remove trace metadata and route every suggestion. |
| Drafting | Yes | Functional | Preserve; add contextual help outside the frozen editor. |
| Editorial | Yes | Functional | Explain review types, non-destructive branches, and next action. |
| Manuscript | Yes | Functional | Explain governance states and publication path. |
| Canon | Yes | Partial | Add obvious queue and workflow explanation. |
| Workflow | Yes | Engineering-led | Present author progress by default; retain internals only in Developer Mode. |
| Settings | Yes | Engineering-led | Add an author-safe default view and explicit Developer Mode. |

## Assistant and companion audit

The Project Assistant currently cannot reliably answer application questions because its prompt requires Narrative Analysis evidence. Application queries therefore incur unnecessary story lookup/provider work and can receive story-first answers.

The Companion persists dismissals but does not maintain a complete recommendation lifecycle. It lacks cooldown, completion, dependency, last-presented, interaction memory, daily recap, and working/idle/sleeping state. Its frontend animation is a permanent pulse, not behavior tied to real companion state.

## Architecture decision

RC5 will add projections only:

- a typed Application Knowledge catalog independent from story knowledge;
- an Assistant query router that selects application, project, or combined context;
- contextual page guidance consuming the same catalog;
- recommendation lifecycle state over Narrative Completeness actions;
- Project Timeline over existing project events;
- Explainability Timeline over existing analysis snapshots/findings;
- author-facing graph and evidence presenters;
- a Developer Mode boundary for technical information.

No analysis rules, canon authority, Story Bible ownership, Character Conversation reasoning, or Paragraph Editor behavior will be redesigned.

## Post-implementation audit outcome

All three critical findings were resolved without changing frozen architecture:

1. Continue Writing now opens governed Drafting and the fabricated project content was removed.
2. The Assistant selects application, project, or combined reasoning before loading context; application help consumes no story search or provider tokens.
3. Normal author surfaces use shared value/evidence cards, with technical diagnostics available only in explicit Developer Mode.

The high-priority gaps were also closed: stable Companion recommendation lifecycle, direct recommendation navigation, persistent Canon Queue entry, structured Knowledge Graph inspection, Project Timeline, Story Health History, and page guidance across the complete workspace catalog.

The final evidence, dependency notices, and remaining bounded limitations are recorded in the RC5 completion, test, console, and known-limitations reports.
