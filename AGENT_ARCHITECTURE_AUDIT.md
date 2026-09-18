# NovelForge Agent Architecture Audit

Audit date: 2026-06-13

Scope: every agent defined in current source, every active Narrative Studio agent
specification, the orchestration services that execute them, and historical
agent identities present in live execution data.

## Executive Result

Status: **FAIL**

NovelForge has 13 active Narrative Studio agent specifications and six retired
LangGraph agent classes. The active specifications have useful domain ownership
and structured outputs, but they are not independently orchestrated:

- 12 planning agents run every normal cycle.
- `ScenePlannerAgent` runs only through a separate endpoint.
- No `OrchestratorAgent` exists.
- No `KnowledgeAgent` exists.
- No readiness agent/system exists.
- Agent enable flags and cycle call budgets are ignored.
- Every active agent receives nearly the same broad context.
- Artifact overlap is resolved by last writer/upsert behavior rather than an
  explicit dependency or authority model.

## Agent Runtime Generations

### Generation 1: Retired LangGraph Workflow

Source:

- `backend/app/agents/*.py`
- `backend/app/graph/workflow.py`
- `backend/app/graph/state.py`

Fixed sequence:

`Intake -> Brainstorm -> Critic -> Story Architect -> Question -> optional Revision`

This path produces a whole-novel, three-act, chapter-oriented outline. It is not
called by current production workflow routes. Tests still instantiate it.

### Generation 2: Active Narrative Studio

Source:

- `backend/app/services/narrative_studio.py`

Fixed sequence:

1. NarrativeDirectorAgent
2. StoryArchitectAgent
3. CharacterJourneyAgent
4. WorldAgent
5. PowerSystemAgent
6. FactionAgent
7. RelationshipAgent
8. ThemeAgent
9. MysteryAgent
10. ArcArchitectAgent
11. PacingAgent
12. QuestionAgent

`ScenePlannerAgent` is excluded from normal cycles and invoked explicitly.

### Generation 2.5: Unused Adaptive Execution

Source:

- `backend/app/services/orchestration_engine.py`
- `backend/app/services/context_engine.py`

This service can accept selected agents, cap calls, estimate a budget, build
layered context, request delegated agents, compact memory, and record cognition.
No production route invokes `run_cycle_observability()`. It does not persist
Narrative Studio artifacts even if called.

It is not the requested Dynamic Orchestrator.

## Common Active Agent Contract

Every active Narrative Studio agent receives:

- project title and input fields;
- current cycle number;
- new user messages and queued task text;
- locked canon facts;
- decision registry summaries;
- rejected decisions;
- up to eight retrieved memory records;
- the current full Story Bible sections.

Every active agent is prompted to return strict JSON matching an example schema.

Every active execution can write:

- `context_packets`
- `execution_traces`
- provider health/quota records
- `discussion_messages`
- `agent_outputs` when a run ID exists
- `memory_embeddings`
- `story_bibles`
- `project_events`

The agent-specific artifact collections are listed below.

Configured output limit:

- assignment default: 4,096 tokens;
- active Narrative Studio hard cap: 3,000 output tokens;
- input context is truncated to 30,000 serialized characters in the prompt;
- provider trace totals include prompt estimates, so trace totals can exceed
  3,000.

## Active Agent Inventory

### NarrativeDirectorAgent

| Item | Audit |
| --- | --- |
| Purpose | Evaluate the story, coordinate the room, identify quality risks |
| Inputs | Full shared context; especially project vision, canon, decisions, Story Bible |
| Structured outputs | Summary, reasoning, concerns, recommendation, `story_vision`, `ai_insights` |
| Primary collections | `story_visions`, `ai_insights` |
| Memory use | Generic project retrieval; no director-specific memory |
| Observed historical trace usage | 19 calls, about 2,770 average trace tokens, about 8.8s average latency |
| Overlap | PacingAgent, QuestionAgent, StoryArchitectAgent, all domain risk analysis |
| Finding | Acts as coordinator in prose only; cannot choose or suppress agents |

### StoryArchitectAgent

| Item | Audit |
| --- | --- |
| Purpose | Develop open plot threads without chapter plans |
| Inputs | Full shared context |
| Structured outputs | `plot_threads` |
| Primary collections | `plot_threads` |
| Memory use | Generic retrieval, including existing plot threads |
| Observed historical trace usage | 109 calls, about 1,127 average trace tokens; identity is mixed with older executions |
| Overlap | ArcArchitectAgent, MysteryAgent, NarrativeDirectorAgent |
| Finding | “Architect” name is overloaded with the retired whole-novel architect |

### CharacterJourneyAgent

| Item | Audit |
| --- | --- |
| Purpose | Create/update characters and long-term journeys |
| Inputs | Full shared context |
| Structured outputs | Character identity, goals, fears, secrets, relationships, power, arc, beliefs, growth, plans |
| Primary collections | `character_bibles`, `character_journeys` |
| Memory use | Generic retrieval; character records are indexed |
| Observed historical trace usage | 16 calls, about 4,084 average total trace tokens, about 11.6s latency |
| Overlap | RelationshipAgent, ArcArchitectAgent, PowerSystemAgent |
| Finding | Progression is stored as loose arrays/strings, not arc/chapter/timeline state |

### WorldAgent

| Item | Audit |
| --- | --- |
| Purpose | Develop supported world details and unresolved areas |
| Inputs | Full shared context |
| Structured outputs | Rules, locations, races, history, religion, politics, technology, economy, academies, conflicts |
| Primary collections | `world_bibles` |
| Memory use | Generic retrieval; world records are indexed |
| Observed historical trace usage | 118 calls, about 4,410 average trace tokens; includes earlier architecture history |
| Overlap | PowerSystemAgent, FactionAgent, NarrativeDirectorAgent |
| Finding | No ownership boundaries for facts also emitted by power/faction agents |

### PowerSystemAgent

| Item | Audit |
| --- | --- |
| Purpose | Develop the power system while preserving locked decisions |
| Inputs | Full shared context |
| Structured outputs | Ranks, levels, cultivation, skills, classes, evolution paths, concept tree, limits, resources, costs, compatibility, progression |
| Primary collections | `power_systems` |
| Memory use | Generic retrieval; power records are indexed |
| Observed historical trace usage | 14 calls, about 4,123 average trace tokens, about 8.5s latency |
| Overlap | WorldAgent, CharacterJourneyAgent, ArcArchitectAgent |
| Finding | Runs even when no power-system input changed |

### FactionAgent

| Item | Audit |
| --- | --- |
| Purpose | Create factions grounded in world and conflict |
| Inputs | Full shared context |
| Structured outputs | Name, leader, goals, enemies, allies, influence, secrets, territory |
| Primary collections | `factions` |
| Memory use | Generic retrieval; factions are indexed |
| Observed historical trace usage | 13 calls, about 4,289 average trace tokens, about 7.3s latency |
| Overlap | WorldAgent, RelationshipAgent, StoryArchitectAgent |
| Finding | No stable faction references or validation against named entities |

### RelationshipAgent

| Item | Audit |
| --- | --- |
| Purpose | Create relationship edges between named characters |
| Inputs | Full shared context |
| Structured outputs | Character pair, type, strength, trust, history, payoff, status |
| Primary collections | `relationship_graphs` |
| Memory use | Generic retrieval; relationship records are not a dedicated retrieval source |
| Observed historical trace usage | 12 calls, about 4,317 average trace tokens, about 8.5s latency |
| Overlap | CharacterJourneyAgent, FactionAgent, ArcArchitectAgent |
| Finding | Character-name strings are not foreign keys; edge direction can duplicate a relationship |

### ThemeAgent

| Item | Audit |
| --- | --- |
| Purpose | Connect themes, motifs, and symbols to characters/arcs |
| Inputs | Full shared context |
| Structured outputs | Themes, motifs, symbols, payoffs, related characters/arcs |
| Primary collections | `theme_registry` |
| Memory use | Generic retrieval; theme records receive ranking boosts |
| Observed historical trace usage | 166 calls, about 4,203 average trace tokens; includes prior architecture history |
| Overlap | NarrativeDirectorAgent, ArcArchitectAgent, MysteryAgent |
| Finding | Theme work has no readiness status or approved thematic question |

### MysteryAgent

| Item | Audit |
| --- | --- |
| Purpose | Track mysteries, clues, red herrings, reveal targets, resolution |
| Inputs | Full shared context |
| Structured outputs | Question, truth, known/hidden clues, red herrings, reveal target, status |
| Primary collections | `mystery_registry` |
| Memory use | Generic retrieval; mysteries are indexed |
| Observed historical trace usage | 12 calls, about 4,484 average trace tokens, about 5.9s latency |
| Overlap | ArcArchitectAgent, ThemeAgent, requested KnowledgeAgent and foreshadow system |
| Finding | “Known clues” does not model who knows what; no reader/character/world truth separation |

### ArcArchitectAgent

| Item | Audit |
| --- | --- |
| Purpose | Build story arcs and in-world timeline events |
| Inputs | Full shared context |
| Structured outputs | Multiple arcs and multiple timeline events |
| Primary collections | `story_arcs`, `story_timelines` |
| Memory use | Generic retrieval; arcs and timeline entries are indexed |
| Observed historical trace usage | 13 calls, about 4,481 average trace tokens, about 11.0s latency |
| Overlap | StoryArchitectAgent, MysteryAgent, CharacterJourneyAgent, PacingAgent |
| Finding | Generates/revises all arcs at once; no current arc, approval gate, or unknown future |

### PacingAgent

| Item | Audit |
| --- | --- |
| Purpose | Evaluate escalation, breathing room, dead zones, pacing risk |
| Inputs | Full shared context |
| Structured outputs | Weak pacing, dead zones, escalation risks, recommendations, score |
| Primary collections | `ai_insights` |
| Memory use | Generic retrieval |
| Observed historical trace usage | 9 calls, about 5,568 average trace tokens, about 13.5s latency |
| Overlap | NarrativeDirectorAgent, ArcArchitectAgent |
| Finding | Overwrites fields in the same `ai_insights` document owned by the director |

### QuestionAgent

| Item | Audit |
| --- | --- |
| Purpose | Ask unresolved, optional, high-value questions |
| Inputs | Full shared context and canon/decision heuristics |
| Structured outputs | Text, choices, default recommendation, story area |
| Primary collections | `questions` |
| Memory use | Generic retrieval plus overlap-based solved-question suppression |
| Observed historical trace usage | 100 calls, about 998 average trace tokens; mixed retired/active identity |
| Overlap | NarrativeDirectorAgent, every domain agent that emits concerns |
| Finding | Questions have no readiness-item linkage, priority, blocking status, or ownership |

### ScenePlannerAgent

| Item | Audit |
| --- | --- |
| Purpose | Create late-stage scene plans tied to arcs; no prose |
| Inputs | Full shared context |
| Structured outputs | Title, arc, summary, characters, emotional shift, purpose, foreshadowing, status |
| Primary collections | `scene_registry` |
| Memory use | Generic retrieval; scenes are indexed |
| Observed historical trace usage | 75 calls, about 4,101 average trace tokens; much data predates current active path |
| Overlap | ArcArchitectAgent and the absent drafting/writer agents |
| Finding | No approved-arc gate; endpoint name/UI imply drafting but only planning occurs |

## Retired Source Agent Inventory

### IntakeAgent

| Item | Audit |
| --- | --- |
| Purpose | Extract genre, themes, hooks, assumptions, premise candidates, character/world/plot seeds |
| Inputs | Project idea dump and all note fields |
| Outputs | Mutable LangGraph state fields |
| Collections | Indirectly `agent_outputs`, `timeline_messages` through legacy persistence |
| Memory | Full legacy timeline and previous artifacts in one prompt |
| Token limit | 4,000 output tokens by default |
| Overlap | NarrativeDirectorAgent, StoryArchitectAgent |
| Status | Retired from production, retained in tests |

### BrainstormAgent

| Item | Audit |
| --- | --- |
| Purpose | Generate possibilities, conflicts, twists, themes, scene ideas |
| Inputs | Intake fields plus full legacy context |
| Outputs | Mutable state lists |
| Collections | Indirect legacy output/timeline persistence |
| Memory | Full state prompt |
| Token limit | 4,000 |
| Overlap | StoryArchitectAgent, ArcArchitectAgent, ScenePlannerAgent |
| Status | Retired from production |

### CriticAgent

| Item | Audit |
| --- | --- |
| Purpose | Identify clichés, weak motivations, gaps, and missing elements |
| Inputs | Brainstorm output plus full context |
| Outputs | Critiques, weaknesses, suggestions, missing elements |
| Collections | Indirect legacy output/timeline persistence |
| Memory | Full state prompt |
| Token limit | 4,000 |
| Overlap | NarrativeDirectorAgent, PacingAgent |
| Status | Retired from production |

### Retired StoryArchitectAgent

| Item | Audit |
| --- | --- |
| Purpose | Create premise, three-act structure, and chapter roadmap |
| Inputs | Intake, brainstorm, critic, and project state |
| Outputs | Whole-novel `outline` with acts and chapters |
| Collections | `outlines`, `agent_outputs`, `timeline_messages` |
| Memory | Full previous outline and timeline |
| Token limit | 4,000 |
| Overlap | Active StoryArchitectAgent and ArcArchitectAgent |
| Status | Class name conflicts with active spec name |

### Retired QuestionAgent

| Item | Audit |
| --- | --- |
| Purpose | Ask 3-5 clarification questions |
| Inputs | Whole outline, weaknesses, canon-like state |
| Outputs | Question list |
| Collections | `questions` through legacy persistence |
| Memory | Full legacy state |
| Token limit | 4,000 |
| Overlap | Active QuestionAgent |
| Status | Class name conflicts with active spec name |

### RevisionAgent

| Item | Audit |
| --- | --- |
| Purpose | Revise whole-novel outline after answers |
| Inputs | Outline, questions, answers, prior state |
| Outputs | Revised acts and chapters |
| Collections | `outlines`, `agent_outputs`, `timeline_messages` |
| Memory | Full state |
| Token limit | 4,000 |
| Overlap | No active equivalent; behavior conflicts with arc-based target |
| Status | Retired from production |

## Historical Agent Identities Without Current Source Owners

Live execution traces also contain:

- `CharacterAgent`
- `ContinuityAgent`
- `PlotThreadAgent`
- `LiveJsonDiagnostic`

The first three have substantial historical traces but no current agent
definition. Their old artifacts remain mixed into current collections and
memory. This is evidence of a retired intermediate architecture.

## Token And Cost Audit

### Accounting Limitations

Token consumption cannot be audited precisely by project or cycle because:

- `execution_traces` has no `project_id`, `run_id`, or `cycle_number`;
- trace totals combine estimated prompt and estimated response tokens;
- provider-reported `tokens_used` is separately copied into output metadata;
- old and current agent generations share names;
- many tests mock the gateway and produce outputs without matching traces;
- model costs use provider-level constants.

Historical trace averages in this document are therefore directional, not
billing-grade.

### Agent Storm Cost Shape

A normal active cycle always attempts 12 provider calls. With roughly
4,000-5,500 total trace tokens per domain call in observed real executions, one
cycle can easily process tens of thousands of tokens before fallback retries,
Story Bible rebuilds, and repeated memory indexing are considered.

The requested default of five provider requests per minute would make a full
static cycle take at least about 2.4 minutes even with no retries. Demand-driven
selection is therefore required for both cost and user experience.

## Memory Audit By Agent

All active agents currently share the same memory mechanism:

1. Build a query from agent purpose and new messages.
2. Retrieve eight hash-vector-ranked records.
3. Include all canon and decision summaries.
4. Include the full current Story Bible.
5. Persist a context packet.

There is no:

- agent-specific memory collection;
- agent-specific retention;
- memory importance score;
- explicit unresolved-question memory;
- approved-only memory filter;
- stale-source filter;
- chapter/arc scope;
- memory access audit;
- automatic compression in the active path.

This makes the agents stateless consumers of a growing project snapshot rather
than long-running collaborators with bounded memory.

## Overlap And Ownership Audit

| Area | Overlapping agents | Risk |
| --- | --- | --- |
| Story quality | Narrative Director, Pacing, Question | Repeated analysis and questions |
| Plot structure | Story Architect, Arc Architect, Mystery | Conflicting thread/arc/reveal plans |
| Character change | Character Journey, Arc Architect, Relationship | Duplicate progression authority |
| World politics | World, Faction, Relationship | String-based cross-entity drift |
| Power progression | Power System, Character Journey, Arc Architect | No typed progression ledger |
| Theme/payoff | Theme, Mystery, Arc Architect | Payoff duplication |
| AI insights | Narrative Director, Pacing | Shared mutable document |
| Foreshadowing | Mystery, Arc Architect, Scene Planner | No active registry owner |

The current “one agent writes one top-level collection” rule is not sufficient
because narrative concepts cross collection boundaries.

## Missing Requested Agents And Capabilities

### OrchestratorAgent

Absent.

The target agent must:

- inspect typed changes and readiness;
- calculate impacted artifacts and agents;
- skip unaffected work;
- persist reasons for run/skip/block decisions;
- enforce call, cost, rate, and loop budgets;
- distinguish discussion, planning, continuity, and drafting tasks;
- stop when no meaningful work remains.

It should produce an execution plan, not narrative artifacts.

### KnowledgeAgent

Absent.

Mystery records contain known and hidden clues but do not model:

- world truth;
- reader knowledge;
- individual character knowledge;
- source event/chapter;
- confidence;
- misinformation;
- knowledge transfer.

### Readiness Evaluation

Absent.

Question generation is not readiness. Required/recommended/drafting-stage items,
evidence, status transitions, blockers, and arc drafting gates do not exist.

### Drafting Agents

No active prose writer exists. Historical traces/settings mention
`SceneWriterAgent`, `DialogueAgent`, and `EditorAgent` in task mappings, but
there are no current implementations.

## Agent Execution Risks

| Severity | Finding |
| --- | --- |
| Critical | All planning agents run regardless of change impact |
| Critical | Disabled assignment flag is ignored |
| Critical | Generated artifacts become active before approval |
| High | No workflow lease, idempotency, or durable task queue |
| High | No rate limiter or global provider concurrency control |
| High | Context includes unbounded aggregate data with silent truncation |
| High | Memory reindexing repeats full-project work after every agent |
| High | Contradiction findings do not prevent persistence |
| High | Agent schemas are examples, not validated Pydantic/JSON schemas |
| Medium | Exact names/titles are used as entity identity |
| Medium | One agent failure fails the full cycle after prior partial writes |
| Medium | No compensation or rollback |
| Medium | No per-agent timeout/cancellation state in workflow records |

## Recommended V2 Agent Boundaries

| Agent/system | Owned responsibility |
| --- | --- |
| `OrchestratorAgent` | Change impact, readiness, execution planning, skip/block/stop |
| `ReadinessService` | Deterministic checklist status and drafting gates |
| Narrative Director | Cross-domain creative direction and discussion prioritization |
| Story Architect | Story spine and open conflict/thread structure |
| Arc Architect | One requested arc at a time |
| Character Journey | Character identity and progression proposals |
| KnowledgeAgent | Reader/character/world knowledge ledger |
| Continuity service/agent | Typed consistency checks against approved data |
| Foreshadow agent/service | Seed/payoff lifecycle |
| Artifact agent/service | Item ownership, powers, hidden powers, relevance |
| Scene Planner | Approved current arc to scene plan |
| Scene Writer | Scene plan to prose draft |
| Editor | Draft review without mutating canon |

Deterministic services should own status calculations, identity, transitions,
rate limits, and persistence. Agents should propose creative content.

## Agent Audit Exit Criteria

Agent architecture is not complete until:

- `OrchestratorAgent` controls the real production execution path;
- run/skip/block reasons are persisted;
- unaffected agents are demonstrably skipped;
- agent schemas are validated;
- artifacts are staged until approval;
- memory is bounded and agent-aware;
- knowledge, progression, foreshadow, and artifact ownership are explicit;
- provider rate limits and workflow call budgets are enforced;
- drafting is gated by required readiness and approved current arc;
- legacy agents and historical identities are migrated or retired cleanly.
