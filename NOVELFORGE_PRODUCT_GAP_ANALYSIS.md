# NovelForge Product Gap Analysis

Date: 2026-07-19

## Priority model

- **P0 — knowledge and finding contracts:** required before new UX, because every requested feature depends on consistent provenance, routing, and refresh behavior.
- **P1 — author truth and quality:** Critique, Completeness, milestones, and Canon Explorer.
- **P2 — cohesive experience:** Companion and Creation Guide consuming P0/P1 data.
- **P3 — closure:** cross-system tests, large-project benchmark, accessibility, Playwright, and documentation.

## P0 gaps

### Shared finding contract

Current shared findings already carry most evidence fields but lack:

- `responsible_subsystem`;
- `suggested_improvement` as a normalized author-facing field;
- `source_service` / `source_finding_id`;
- explicit `finding_type` for analysis, critique, completeness, or editorial findings;
- stable workflow status beyond open/acknowledged/resolved.

Close by extending the existing narrative finding schema and score ingestion. Do not create a separate unlinked critique store.

### Shared user knowledge contract

Current user messages become untyped locked facts using a two-token rule. Replace that intake rule with structured context entries containing:

- subject, predicate/field, value, domain, entity references;
- confidence and importance;
- source type, source ID, source excerpt, user identity, timestamps, and version;
- target routes and approval state;
- dedupe fingerprint and supersession relationship.

Explicit structured question answers receive high confidence. Suggestions, preferences, questions, and transient commands must not become official canon automatically.

### Refresh coordination

At least six `_after_change` implementations and numerous direct Story Bible rebuild calls repeat refresh behavior. Introduce one small coordinator used by existing mutation paths to:

1. rebuild or incrementally refresh Narrative Analysis;
2. rebuild Story Bible;
3. update completeness/milestones;
4. emit one typed project event.

This is consolidation, not an architecture redesign.

## P1 gaps

### Narrative Critique

Add missing qualitative lenses using existing evidence:

- motivation/action alignment;
- dialogue voice drift across approved scenes;
- emotional setup/payoff;
- world-rule contradictions;
- foreshadow setup/development/payoff strength;
- scene-purpose similarity and redundant exposition;
- chapter opening hook and ending turn;
- tension/conflict escalation curve.

Critiques remain proposals. The author can acknowledge, defer, resolve, or navigate to evidence; no automatic prose edits.

### Narrative Completeness and milestones

Calculate dimensions from existing authoritative records. Empty optional fields must not be treated as blockers unless the selected genre/project configuration requires them.

Initial gate criteria:

- **Concept Complete:** premise, genre, themes, target audience/length, protagonist, primary goal, and central conflict are present.
- **World Ready:** required world/location/organization/power rules are defined; no critical world/canon conflicts; world and power completeness meet threshold.
- **Draft Ready:** Concept Complete and World Ready; at least one approved/draftable arc; major character motivations, relationships, timeline anchors, mysteries/payoffs, chapter plan, and scene plan criteria pass.
- **Revision Ready:** planned manuscript scope is drafted; editorial review exists; critical structural and continuity issues are zero; no required arc remains incomplete.
- **Publication Ready:** manuscript approved; Canon and Timeline Health meet threshold; no critical/high unresolved Story Health findings; required mysteries/payoffs resolved or explicitly deferred; completeness dimensions meet threshold.

Gate criteria must be returned individually with evidence, blockers, and target navigation—not as opaque percentages.

### Canon Explorer

Use the current registry, proposal, conflict, graph, and audit collections. Add a query/detail projection joining:

- active and inactive versions;
- source and originating location;
- evidence/confidence;
- related graph nodes;
- proposal, approval, promotion, deactivation, and conflict history.

“Edit” creates a governed proposal with Change Impact preview. Approval promotes a new version and supersedes the old active fact.

## P2 gaps

### Workspace Companion

Create an event-aware companion state from:

- latest project events/background jobs;
- health deltas;
- critique and completeness changes;
- milestones reached/lost;
- pending canon proposals;
- current page and authoritative next action.

UX constraints:

- compact persistent control, expandable feed;
- no random movement over author content;
- subtle CSS state animation only, disabled by `prefers-reduced-motion`;
- dismissible messages and quiet mode;
- keyboard, screen-reader, and mobile support;
- navigation actions remain typed and deterministic.

### Novel Creation Guide

Guide steps are a static definition paired with dynamic completeness evidence. It must not store a second set of checkboxes. Manual acknowledgement may be stored only for optional education tips, never for narrative completion.

## P3 gaps

- cross-system contract tests for every propagation requirement;
- 500-chapter benchmark covering critique, completeness, guide, companion state, and Canon Explorer queries;
- Playwright journeys for first-time creation, canon governance, knowledge reuse, milestone progression, and companion reactions;
- architecture, operator walkthroughs, limitations, and RC1-RC4 completion artifacts.

## Explicit non-goals

- no new Narrative Analysis Engine architecture;
- no replacement Story Health score;
- no second Knowledge Graph;
- no direct AI canon mutation;
- no automatic application of critique improvements;
- no manual duplicate Story Bible data-entry system;
- no Paragraph Editor changes except a separately proven critical defect.

