# NovelForge Current Memory Architecture Audit

**Audit date:** 2026-08-13  
**Scope:** current checkout, live local application, read-only MongoDB inspection, persisted execution traces, and existing benchmark artifacts. No provider generation, mutation endpoint, database write, configuration change, or test write was performed.

## Executive finding

NovelForge Native memory is not one database or one vector index. It is a governed stack:

1. **Authoritative story state** — approved prose, active canon, author decisions, and confirmed planning in the owning structured collections.
2. **Derived story understanding** — chapter intelligence, Story Bible sections, Narrative Analysis snapshots/findings, continuity reports, and shared-context projections.
3. **Retrieval infrastructure** — `memory_embeddings`, recent context, compressed cycle summaries, and bounded per-agent memory.
4. **Raw history and operations** — Story Studio jobs/messages, orchestration timeline, agent outputs, revision branches, execution traces, and optional Tencent observations.

Only the first layer may decide what is true. The other layers may retrieve, explain, summarize, or propose. This is the central advantage to preserve.

## Live system inspected

- Frontend: Next.js on `http://localhost:3000`; the project library rendered 628 active projects.
- Backend: FastAPI on `http://127.0.0.1:8005`; readiness reported NovelForge `2.0.0-rc9`, schema `9`, MongoDB database `novelforge`, private-beta mode.
- Persistence: MongoDB through Motor/PyMongo. The live database contained 117 collections.
- Representative project: `Memory Fantasy Experiment` (`6a788192066c6d634556c254`), two approved discovery chapters.
- Develop Story trace project: `Real Creative Workflow 2026-08-10` (`6a78d47d4f0c63bfcbcbc17f`).
- Optional Tencent gateway: healthy at port 8420, version `0.1.0`; its current store had 458 L0 rows, zero L1 records, zero L2 scene blocks, and embedding disabled.

The repository is not a Git worktree, so evidence was checked directly against files and live records rather than Git history.

## Current runtime architecture

```text
Author
  |
  +-- Story Studio question / planning / write / modify / develop
  |     |
  |     +-- intent classification and clarification
  |     +-- planning extraction -> candidate projections only
  |     +-- question -> Narrative Assistant over Narrative Analysis + confirmed state
  |     +-- write -> DiscoveryWritingService
  |     +-- develop -> DevelopmentStateService -> NarrativeStudio specialists
  |     +-- modify -> protected revision/canon proposal path
  |
  +-- Structured planning -> chapter plan -> scene plan -> DraftingService
  |
  +-- Approval boundary
        |
        +-- approved prose remains authoritative and versioned
        +-- extraction creates candidates
        +-- chapter intelligence derives episodic context
        +-- Narrative Analysis / Story Bible refresh projections
        +-- Native memory index derives retrieval documents
        +-- optional memory provider observes event, never changes authority

Next writing request
  |
  +-- Discovery writing: ContextEngine packet (authority + structured state
  |                    + Native hits + compressed cycle memory)
  |
  +-- Structured scene writing: NarrativeStudio context, then a bounded
                         writing-specific Story Bible projection
  |
  +-- provider routing/failover -> draft -> validation -> author review
```

## Ownership and authority map

| Knowledge | Primary storage / owner | Authority | Source and lifecycle | Retrieval / invalidation | Enters future writing? | Author inspection / correction |
|---|---|---|---|---|---|---|
| Approved chapter prose | `chapter_drafts`; Drafting/Discovery services | Authoritative after approval | Generated or edited draft -> review -> approved; versions retained | Active approved version; revision/rollback lineage | Yes: recent evidence, chapter intelligence, Story Bible projection | Writing and Editorial; edit saves a new version |
| Approved scene prose | `scene_drafts`; Drafting service | Authoritative after approval | Scene plan -> draft -> approval | Active approved draft; bounded adjacent-scene excerpt | Yes in structured writing | Writing, Writer's Room, Editorial, rollback |
| Canon | `canon_registry`; canon governance | Highest story authority | Explicit proposal/promotion/activation | Active-state filtering; history retained | Yes | Canon surfaces and proposals |
| Decisions | `questions`, `decision_registry`; Decision History | Authoritative author answer | Answer/version/change/undo/reopen | Decision change invalidates matching planning and rebuilds projections | Yes | Decision history and impact UI |
| Confirmed planning | Owning character, relationship, world, mystery, plot, timeline, knowledge, artifact and arc collections | Authoritative planning, below canon/approved prose | Story Studio candidate -> explicit confirm, or structured author workflow | `authority_status`; stale/rejected excluded by governed readers | Yes | Knowledge Suggestions and specialist pages |
| Candidate planning | Same owning collections plus `discovery_extractions` | Non-authoritative proposal | Brainstorm/extraction -> pending -> confirm/reject/reconsider | Candidate status; confirmation integrates with owner | Should not, except derived chapter intelligence can reflect it | Knowledge Suggestions |
| Chapter intelligence | `chapter_intelligence`; Chapter Intelligence service | Derived | Approved chapter -> provider/deterministic extraction -> active version | Version active flag; indexed in Native | Yes, heavily | Writing state exposes readiness, but detailed correction is indirect |
| Story Bible | `story_bibles`, `story_bible_sections`; Story Bible service | Projection, not authority | Rebuilt from owners, analysis, workflow and editorial material | Section replacement on rebuild | Yes; full for planners, bounded for scene writer | Visible through specialist/product surfaces; correct owners, not projection |
| Narrative Intelligence | Narrative Analysis snapshots/history/nodes/edges/findings | Derived projection | Project events and approved/structured records -> incremental analysis | Snapshot/hash/cache and finding status | Yes for Story Studio and bounded writing projection | Story Health/finding explanations; source correction is indirect |
| Continuity reports | `continuity_reports` | Derived diagnostic | Draft validation | New reports accumulate | Yes in ContextEngine working memory | Visible in review surfaces |
| Native retrieval documents | `memory_embeddings`; Memory Retrieval service | Derived index | Materialized from many source collections | content hash/version, `active`, limited stale cleanup | Yes | Search endpoint only; no dedicated correction UI |
| Character knowledge | `knowledge_entries` and character/story records | Confirmed rows can be authoritative; candidates are not | Structured planning or extraction candidate | Authority status; confirmed context filtering | Yes | Knowledge Suggestions and Story Bible-derived UI |
| Shared narrative context | `shared_narrative_context`; Shared Context service | Structured author-context projection | Classifies meaningful workspace input into subject/field/value | Same-field entries supersede older entries; active toggle | Indirectly through Narrative Analysis/Story Bible | API/UI support exists, but not a central author workflow |
| Agent memory | `agent_memories`; Agent Memory service | Derived workflow memory | Recent output/concerns; canon/decisions copied into core | Tier limits and compaction; archived source pointers | Yes for the same specialist | Not directly author-facing |
| Compressed cycle memory | `compressed_memories`; Memory Compaction service | Derived workflow summary | Counts/titles/agent names from earlier cycles | Latest five in ContextEngine | Yes in orchestration contexts | No direct correction UI |
| Raw Story Studio history | `story_studio_jobs`, `narrative_assistant_messages` | Raw interaction history | Requests, responses, statuses | Job lifecycle; no semantic invalidation | Not directly in Native writer packets | Job history visible |
| Workspace Companion | companion message/state collections | UI projection | Workspace state -> recommendations | Read/refresh state | No direct writing authority | Visible and dismissible/readable |
| Revision alternatives | `revision_branches`, `revision_versions`; Editorial service | Non-authoritative until explicitly applied | Immutable branch/version lineage | Branch status and apply operation | Only applied/current prose should influence writing | Full compare/lineage/status workflow |
| Provider and orchestration traces | `execution_traces`, provider traces, timeline/agent outputs | Operational evidence | Every model/agent call | Retention, cycle/run identifiers | Some agent outputs enter later agent contexts; provider traces do not | Operational/admin surfaces, not story correction |
| Tencent memory | External L0/L1/L2/L3 store via adapter | Derived observation only | Capture from selected conversations/events | Provider-local; no NovelForge authority invalidation | Never primary when `safe_for_writing=True` | Settings/telemetry, not story editing |

## Actual flow: Story Studio to next chapter

1. `StoryStudioService.request` classifies the request and may ask for clarification.
2. Planning-like statements are extracted into no more than 30 candidate projections. The extraction prompt explicitly forbids treating ideas as canon (`story_studio_service.py:155-204`).
3. Candidates are stored in the existing owner collections with provenance and `authority_status=candidate`; confirmation/rejection/reconsideration changes those statuses (`story_knowledge_projection_service.py:137-253,335-388`).
4. A write request calls `DiscoveryWritingService.generate`, which constructs a 24,000-token ContextEngine packet, generates, and may call Range Editor/continuation/compression when length misses (`discovery_writing_service.py:110-230`).
5. Approval is the meaningful state transition. It protects prose, then triggers candidate extraction, chapter intelligence, analysis/Story Bible refresh, and optional memory capture (`drafting_service.py:1199-1280`).
6. The next request repeats context construction from current authority and derived state. Raw Story Studio chat is not replayed into the Native writer packet.

## Actual flow: structured writing and Develop Story

`DraftingService.generate_scene` requires approved plans, gathers linked domain records and a bounded excerpt of the preceding approved scene, and creates persistent orchestration state (`drafting_service.py:198-338,426-762`). `NarrativeStudioService._run_agent` then:

1. recalls Native memory with the safe-writing boundary;
2. synchronizes canon/decisions into per-agent core memory;
3. loads agent memory, confirmed planning, canon, decisions, Story Bible and earlier cycle outputs;
4. trims only when the model-specific context budget is exceeded;
5. for a scene-writing agent, sends a bounded writing projection rather than the full Bible;
6. for planning specialists, sends the full reconstructed Story Bible plus up to 20 retrieved hits and prior outputs;
7. records the output and refreshes structured live context for the next agent.

Relevant implementation: `narrative_studio.py:902-1075,1174-1250,2145-2172`.

## What is stored but rarely or inconsistently used

- Raw Narrative Assistant messages and Story Studio jobs are history, not Native writer memory.
- Candidate knowledge is visible and governable but is intentionally excluded from authority queries. It may still be echoed through chapter-intelligence summaries, which is a correctness gap.
- `shared_narrative_context` is structured and supersedable, but it is not a primary direct source in the two observed writer paths.
- Workspace Companion is product guidance, not a writing-context source.
- Provider/execution traces are useful for audit and cost, not for prose continuity.
- Tencent L0 is populated, but L1/L2 are empty in the current local deployment and the safe writer path remains Native.
- General Native `retrieved_memory` is constructed for all NarrativeStudio agents, but the final scene-writing prompt does not include it; planners do. This is an inconsistency rather than proof it is unnecessary.

## Confirmed defects and risks

### Confirmed defects

1. **Duplicate logical chapter-intelligence embeddings.** Chapter Intelligence indexes by `intelligence_id`; project refresh later indexes the same Mongo document by `_id`. The real Chapter 2 packet retrieved two near-identical Chapter 1 intelligence hits. See `chapter_intelligence_service.py:81-137` and `memory_retrieval_service.py:259-370`.
2. **Continuity false negatives.** The inspected two-chapter project changed third-person to first-person and conflicted on the disappearance chronology, while two highly similar continuity reports both passed.

### Likely integration gaps

- Native source filters are inconsistent. Several indexed source types have explicit authority filters, while timeline messages, agent outputs, legacy timeline, AI insights, chapter/scene plans, canon and decisions are not consistently status-filtered before indexing.
- Planning invalidation is content/regex-based rather than dependency-based. It can miss paraphrases or supersede an accidental match.
- Chapter intelligence is derived from approved prose but can preserve extraction errors and candidate interpretations; its large weight lets those errors dominate recall.
- Derived projections lack a uniform, inspectable `derived_from -> superseded_by -> evidence` contract.

### Intentional design

- Memory providers cannot change canon, decisions, approved prose, or Story Bible ownership.
- Safe writing always uses Native as primary (`memory_provider.py:487-522`).
- Revisions are immutable alternatives until explicitly applied (`editorial_service.py:852-1168`).
- Candidate planning is not automatically canon.

## Current architecture verdict

The authority architecture is sound and should remain. The retrieval and context-delivery architecture is not yet sufficient for long-novel correctness or cost. The highest-value work is to improve Native derivation, filtering, ranking, provenance, and progressive delivery—not to replace MongoDB authority with a generic memory provider.

## Evidence index

- Native index and retrieval: `backend/app/services/memory_retrieval_service.py:259-395`
- Context packet: `backend/app/services/context_engine.py:33-113`
- NarrativeStudio context: `backend/app/services/narrative_studio.py:902-1250`
- Provider authority boundary: `backend/app/services/memory_provider.py:487-522`
- Candidate governance: `backend/app/services/story_knowledge_projection_service.py:137-388`
- Story Bible authority filtering: `backend/app/services/story_bible_service.py:36-169,352-389`
- Immutable revisions: `backend/app/services/editorial_service.py:852-1168`
- Frontend product surfaces: `frontend/app/project/[projectId]/page.tsx`, `frontend/components/StoryStudioPanel.tsx`, `WritingWorkspace.tsx`, `EditorialWorkspace.tsx`, and `WorkspaceCompanion.tsx`

