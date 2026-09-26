# NovelForge Experience Completion — Implementation Report

Date: 2026-07-19  
Status: approved implementation design produced before significant additions

## Implementation boundary

This work extends the existing Narrative Analysis Engine, Story Health, Story Bible, Canon Governance, Project Assistant, project events, readiness, and memory services. The core architecture and Paragraph Editor remain frozen.

## Shared contracts

### Extended narrative finding

Add optional backward-compatible fields:

```text
finding_type: analysis | critique | completeness | editorial
responsible_subsystem: canon | timeline | character | dialogue | story_health | world | plot | editorial
suggested_improvement: string
source_service: string
source_finding_id: string
```

All evidence, confidence, chapters, scenes, elements, status, and stable fingerprints remain owned by the current shared finding model.

### Shared narrative context entry

```text
context_id, project_id, domain, subject, field, value
entity_refs, confidence, importance, status
source_type, source_id, source_excerpt, source_version
routed_subsystems, dedupe_fingerprint, supersedes_id
created_at, updated_at, approved_at
```

Confidence policy:

- explicit structured answer or direct author assertion: 0.95;
- accepted discussion decision: 0.90;
- clear preference/constraint: 0.80;
- inferred entity relationship: 0.65 and proposal/review required;
- question, navigation command, transient feedback, or ambiguous statement: do not persist as narrative fact.

## Services to add or extend

### 1. Project Intelligence Coordinator

Small orchestration service only. It calls existing incremental analysis, Story Bible rebuild, completeness refresh, and project event emission once after an approved mutation.

### 2. Shared Narrative Context Service

- classifies messages and answers;
- performs semantic and exact dedupe;
- stores provenance;
- routes structured facts to existing entity collections where safe;
- creates canon proposals for canon-changing or inferred facts;
- supplies one shared context packet to all agents;
- preserves legacy canon reads until migrated.

### 3. Narrative Critique Service

- consumes current Story Health, graph findings, Story Auditor, and editorial/dialogue reports;
- adds only missing qualitative lenses;
- normalizes responsibility and improvement fields;
- publishes stable critique findings into the shared finding pipeline;
- supports open, acknowledged, deferred, and resolved author workflow states;
- never applies improvements.

Routing map:

| Finding family | Responsible subsystem |
|---|---|
| canon contradiction/world fact conflict | Canon Intelligence |
| impossible chronology/travel/transition | Timeline Intelligence |
| motivation/personality/emotion/relationship drift | Character Intelligence |
| voice/exposition/speaker differentiation | Dialogue Coach |
| pacing/repetition/hook/ending/escalation | Story Health / Developmental Editor |
| mystery/foreshadow/thread payoff | Plot Thread Intelligence |
| world rule/location/organization consistency | Worldbuilding Consultant |

### 4. Narrative Completeness Service

- computes eight requested dimensions;
- returns criteria, evidence, blockers, optional improvements, and navigation target for every dimension;
- evaluates the five milestone gates;
- produces ranked next actions used by Dashboard, Companion, and Guide;
- persists versioned snapshots for delta/celebration history.

### 5. Canon Explorer projection

Extend Canon Governance with:

- server-side search and filters;
- record detail including graph relationships and originating locations;
- version lineage and comparison;
- joined approval/deactivation/conflict history;
- proposal-based edit endpoint with Change Impact.

No new canon database is introduced.

### 6. Workspace Companion projection

- converts project events, job completions, health/completeness deltas, milestone changes, and pending author actions into bounded companion messages;
- delegates conversational questions to Project Assistant;
- uses typed navigation actions;
- stores dismiss/read state only, not duplicate narrative knowledge.

### 7. Novel Creation Guide projection

Static step definitions:

1. Project Creation
2. Story Vision
3. Genre
4. Theme
5. Characters
6. Worldbuilding
7. Power System
8. Relationships
9. Timeline
10. Arcs
11. Scene Planning
12. Paragraph Drafting
13. Revision
14. Story Health
15. Canon Review
16. Publication Readiness

Dynamic status and percent come entirely from Completeness and milestone evidence. Each step provides why it matters, participating AI systems, required inputs, optional improvements, and a navigation action.

## API plan

Extend the existing project intelligence routers with:

- `GET /narrative-critique`
- `POST /narrative-critique/refresh`
- `PUT /narrative-critique/{finding_id}/status`
- `GET /narrative-completeness`
- `GET /production-milestones`
- `GET|POST /shared-narrative-context`
- `PUT /shared-narrative-context/{context_id}`
- `GET /canon/explorer`
- `GET /canon/explorer/{canon_id}`
- `POST /canon/explorer/{canon_id}/propose-edit`
- `GET /workspace-companion`
- `PUT /workspace-companion/messages/{message_id}`
- `GET /novel-creation-guide`

Routes are projections/actions over existing services, not independent domain logic.

## UI plan

Integrate into the current project workspace:

- Critique becomes an evidence/action view linked from Story Health.
- Canon Explorer replaces the truncated Active Canon section within the current Canon workspace.
- Completeness and milestone gates become the primary production pipeline strip on Dashboard/Readiness.
- Companion becomes a compact persistent workspace control and expandable feed; the existing assistant drawer handles free-form conversation.
- Creation Guide becomes a freely navigable drawer/panel using current section routes.

Do not add isolated top-level applications for each capability.

## Incremental implementation sequence

1. migration/index additions and shared typed contracts;
2. Project Intelligence Coordinator and Shared Narrative Context intake;
3. Critique normalization and missing critique lenses;
4. Completeness dimensions, milestones, and centralized next actions;
5. Canon Explorer query/detail/version/edit-proposal workflow;
6. Companion event projection and Creation Guide;
7. frontend integration and accessibility polish;
8. cross-system contract tests and performance benchmark;
9. RC1 implementation review;
10. RC2 full backend/frontend/build/Playwright regression;
11. RC3 product/UX/accessibility review;
12. RC4 documentation and cleanup;
13. phase/product completion only after all gates pass.

## Acceptance tests

- an explicit author answer creates one structured context entry with provenance, updates Story Bible, and is reused by later agents without a repeat question;
- a canon-changing assertion enters the governed proposal/version workflow;
- timeline change updates graph, critique, completeness, Story Health, Companion, and Guide from one refresh sequence;
- critique findings show responsibility, improvement, evidence, confidence, and navigation without applying changes;
- Canon Explorer can find active/inactive facts, compare versions, and inspect full history;
- milestone gates show criteria and blockers, not percentages alone;
- background analysis completion produces one accessible Companion notification;
- Dashboard, Companion, and Guide agree on the next action;
- 500-chapter cached reads remain bounded and no request rebuilds full context unnecessarily;
- frozen Paragraph Editor files remain unchanged unless a separately documented critical defect is proven.
