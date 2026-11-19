# NovelForge V2 Comprehensive Product Audit

Date: 2026-07-19  
Audit gate: complete  
Implementation status: not started by this report

## Executive conclusion

NovelForge already has the correct architectural center: the incremental Narrative Analysis Engine, its persisted graph and findings, Story Health, Story Bible aggregation, governed canon, project events, agent memory, and the Interactive Narrative Studio. The requested product is not a new architecture.

The audit found:

- **Existing:** shared narrative graph, Story Health, canon registry/conflicts/proposals, timeline and plot findings, Story Auditor, editorial and dialogue reviewers, evidence-backed assistant, project events, Story Bible refresh, author-controlled approvals, arc readiness, and duplicate-question suppression.
- **Partial:** unified critique, canon transparency, proactive companion behavior, cross-agent structured memory, project completeness, beginner guidance, and milestone gates.
- **Missing as unified products:** Narrative Completeness Analyzer, authoritative Canon Explorer UX, persistent event-aware Workspace Companion, Shared Narrative Context router, guided creation pipeline, and explicit Concept/World/Draft/Revision/Publication milestone evaluation.

No new analysis graph, Story Health replacement, manual Story Bible, or parallel canon store is justified.

## Audit method

The audit traced live code paths across:

- `backend/app/services/narrative_analysis_engine.py`
- `story_health_service.py`, `story_auditor_service.py`, and `story_quality_service.py`
- `canon_governance_service.py`, `canon_service.py`, and the proposal workflow
- `story_bible_service.py`, `agent_memory_service.py`, and `memory_retrieval_service.py`
- `readiness_service.py`, planning/development APIs, and workspace context
- project events, background analysis, SSE refresh, and Project Assistant navigation
- current project workspace components, stores, APIs, unit tests, and Playwright journeys

Focused baseline validation passed:

- backend: 26 passed;
- frontend: 13 passed.

## Part 1 — Narrative Critique and improvement loop

Overall status: **PARTIAL**

Existing foundations:

- Narrative Analysis emits stable findings with severity, explanation, evidence, confidence, affected chapters/scenes/elements, and recommended actions.
- Story Health consumes the shared graph and exposes the same findings.
- Story Auditor performs a read-only AI review for pacing, repetition, emotional rhythm, structural weakness, continuity, unresolved threads, balance, and tension.
- EditorAgent and DialogueAgent produce evidence-backed review reports without mutating drafts.
- deterministic quality checks cover repetitive sentence, paragraph, dialogue, chapter shape/opening, exposition, emotional over-explanation, and overly uniform rhythm.

Incomplete behavior:

- there is no canonical `NarrativeCritique` projection joining Story Health, Story Auditor, editorial, and dialogue evidence;
- findings do not consistently identify `responsible_subsystem`;
- Story Auditor findings do not carry confidence consistently and are stored separately from shared `narrative_findings`;
- Story Auditor findings therefore do not directly affect the authoritative Story Health score;
- weak motivation, missing emotional payoff, worldbuilding inconsistency, weak foreshadowing, chapter hook/ending quality, and conflict escalation are not continuously evaluated across the project;
- proposed improvements are spread across `recommended_actions`, editorial recommendations, and agent prose rather than one governed workflow.

Required extension: a **Narrative Critique Service** that consumes Story Health and the current analysis graph, normalizes existing findings, invokes the existing StoryAuditorAgent only for uncovered qualitative lenses, and publishes stable critique findings back through the shared finding pipeline. It must propose only; it must never rewrite or apply changes.

## Part 2 — Canon transparency

Overall status: **PARTIAL**

Existing:

- full registry API with canon-type and active filters;
- active/inactive state and deactivation workflow;
- source collection, source ID/version, authority, value, evidence, timestamps, and promotion fingerprint;
- typed conflict evidence, affected locations, impact, acknowledgement, resolution, validation, review history, proposal queue, promotion history, and Story Bible refresh.

Missing or incomplete:

- the current UI shows only active facts, grouped and truncated to eight per type;
- no UI search, inactive view, record detail inspector, originating chapter, related entities, complete approval trail, or version comparison;
- no governed fact-edit workflow from the registry;
- confidence and relationship fields are not consistently present on registry records;
- promotion history exists as an API but is not an author-facing explorer.

Required extension: replace the limited registry panel with a **Canon Explorer** consuming Canon Governance. Edits must create a canon-change proposal with impact preview; direct untracked mutation remains prohibited.

## Part 3 — Narrative completeness

Overall status: **MISSING AS A PROJECT-WIDE CAPABILITY**

Existing foundations:

- arc-scoped readiness items and READY/PARTIALLY_READY/NOT_READY evaluation;
- arc maturity, drafting eligibility, Story Health metrics, AI `missing_story_areas`, unresolved questions, and Story Bible sections;
- structured data for characters, world, powers, relationships, mysteries, timeline, canon, arcs, chapters, scenes, editorial, and manuscript status.

Gap:

No service derives project-wide completion dimensions or remaining work from those authoritative sources. Current readiness is mostly authored checklist state and is arc-focused. It does not calculate Story, Character, World, Power, Relationship, Mystery, Timeline, and Canon completeness, nor publication milestones.

Required extension: a **Narrative Completeness Service** that reads the Story Bible, Narrative Analysis findings, Canon Governance, readiness, editorial, and manuscript state. Its output is a projection, not a second source of truth.

## Part 4 — Intelligent Workspace Companion

Overall status: **PARTIAL**

Existing:

- persistent project workspace and assistant drawer;
- evidence-grounded answers, six modes, typed navigation, contextual recommendations, dashboard next action, live agent/run status, SSE project events, and background analysis jobs;
- backend workspace context containing current chapter/scene, approvals, health, warnings, and a suggested action.

Missing:

- no persistent companion persona/state separate from opening the assistant drawer;
- no event-aware celebrations or background-completion notifications;
- no unobtrusive animation, attention queue, milestone reactions, or onboarding explanations;
- navigation answers exist, but page-help and creation-process guidance are not backed by a structured guide;
- next-action logic is duplicated between the backend workspace context and frontend dashboard.

Required extension: a lightweight **Workspace Companion projection and component** driven by project events, completeness milestones, current workspace context, and the existing Project Assistant. It must be dismissible, motion-reduced, keyboard accessible, and non-blocking.

## Part 5 — Global user memory

Overall status: **PARTIAL**

Existing:

- user messages and question answers become durable decisions and locked facts;
- Story Bible rebuild occurs after meaningful user interactions;
- future questions are suppressed using canon/decision overlap;
- canonical decisions are synchronized into bounded per-agent memory;
- project memory indexes characters, world, plot, timeline, questions, canon, decisions, readiness, and other structured sources with version/provenance metadata.

Critical gaps:

- every user message with two meaningful tokens is treated as approved locked canon, which is too broad;
- stored facts are frequently untyped free text and are not routed to character, world, power, timeline, or relationship domains;
- confidence, extraction rationale, affected entities, and routing decisions are absent;
- agent memory is synchronized per agent rather than exposed as one authoritative shared context projection;
- semantic duplicate prevention exists for questions, not for all structured knowledge;
- provenance is basic source/source ID rather than a full transformation and approval chain.

Required extension: a **Shared Narrative Context Service** that classifies meaningful user assertions, applies explicit confidence rules, deduplicates them, preserves provenance, and routes them through existing authoritative collections or Canon Proposal governance.

## Part 6 — Guided novel creation workflow

Overall status: **PARTIAL UI, MISSING UNIFIED GUIDE**

Existing:

- project creation collects title, genre, tone, and story seed;
- the workspace exposes every required destination;
- Dashboard offers one suggested next action;
- Story Vision, readiness, arc development, drafting, editorial, Story Health, Canon, and manuscript workflows exist independently.

Missing:

- no interactive ordered/free-jump guide;
- no explanation of why each step matters, participating AI systems, required inputs, or optional improvements;
- no central completion state tied to authoritative project data;
- no project-level milestones or gate criteria.

Required extension: a **Novel Creation Guide** whose steps and percentages are derived from Narrative Completeness. The guide must navigate existing pages and must not own duplicate completion state.

## Part 7 — Cross-system validation

| Validation requirement | Current status | Audit conclusion |
|---|---|---|
| User answers propagate | Partial | Durable decisions/canon and Bible rebuild exist; typed routing is missing. |
| Story Bible triggers downstream refresh | Exists | Mutation paths rebuild and emit events; refresh orchestration is duplicated. |
| Canon approval updates Character Intelligence | Partial | Bible/graph refresh occurs, but no explicit character-impact projection or test. |
| Timeline updates Story Health | Exists | Timeline mutation rebuilds analysis; timeline findings feed Story Health. |
| Knowledge Graph refreshes after changes | Exists | Graph is rebuilt from shared sources during Narrative Analysis. |
| Companion reacts to analysis | Missing | SSE exists; no companion event interpretation. |
| Critique findings update Story Health | Missing | audit reports remain outside scored shared findings. |
| No duplicate business logic | Partial | shared graph is sound, but refresh, serialization, canon intake, and next-action logic are duplicated. |
| No repeated questions | Partial | question overlap suppression exists; structured-context dedupe is incomplete. |

## Architectural decision

All implementation must remain a consumer/coordination layer around the current platform:

```text
Approved project content and user knowledge
                    │
                    ▼
        Narrative Analysis Engine
                    │
     Story Health + Shared Findings
                    │
       ┌────────────┼────────────┐
       ▼            ▼            ▼
   Critique     Completeness   Canon Explorer
       │            │            │
       └──────┬─────┴─────┬──────┘
              ▼           ▼
      Workspace Companion  Creation Guide
```

The Shared Narrative Context service feeds approved structured project content before analysis; it does not create an alternate Story Bible or graph.

