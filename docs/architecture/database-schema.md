# Subsystem Architecture: Database Schema

## Phase 6 Narrative Intelligence

The shared analysis graph uses five project-scoped collections:

- `narrative_nodes`: fingerprinted chapter, scene, character, relationship, event, canon, thread, mystery, artifact, world, faction, and continuity sources.
- `narrative_edges`: reusable reference/dependency relationships.
- `narrative_findings`: evidence-backed domain findings and acknowledgement/resolution lifecycle.
- `narrative_analysis_snapshots`: current scores, counts, cache/recomputation statistics, and graph version.
- `narrative_analysis_jobs`: queued/running/completed/failed background analysis state.

Identity indexes are unique within a project. Workspace indexes cover project/domain/status/severity, and latest-snapshot/job indexes use descending timestamps. Startup runs the idempotent Phase 6 migration after Phase 3C.

NovelForge utilizes MongoDB as its authoritative database. Collections represent distinct boundaries of planning, execution state, metadata, and drafting.

## Core Schema Registry

### Project Context
- **`projects`**: Top-level project details (title, premise, genre, tone).
- **`story_bibles`**: Aggregate story bible document representing the complete project state, rebuilt after planning updates.

### Planning Collections
- **`story_visions`**: Master project vision statement.
- **`character_bibles`**: List of characters and descriptions.
- **`character_journeys`**: Arc-level character goals, fears, and developments.
- **`world_bibles`**: Locations and world rules.
- **`factions`**: Group affiliations, descriptions, and territories.
- **`relationship_graphs`**: Character relationships and milestones.
- **`plot_threads`**: Main/sub plot details.
- **`theme_registry`**: Major themes and target realizations.
- **`mystery_registry`**: Plot mysteries, clues, red herrings, and truths.
- **`story_timelines`**: Chronological events and disclosures.
- **`story_arcs`**: Story arcs, estimated chapters, and goals.

### Drafting Collections
- **`scene_registry`**: List of planning outlines for chapters/scenes.
- **`scene_paragraphs`**: Paragraph-level planning skeletons.
- **`paragraph_content`**: Authoritative paragraph prose and editor state.
- **`paragraph_versions`**: Immutable history of manual and restoration commits.
- **`paragraph_suggestions`**: Dedicated storage for transient AI suggestions.
- **`manuscripts`**: Assembled manuscripts.
- **`manuscript_versions`**: Assembled manuscript chapter draft boundaries and source hashes.
- **`manuscript_reports`**: Validation reports for compiled manuscript versions.

### Orchestration & Governance
- **`canon_registry`**: Typed canon facts, sources, and active states.
- **`canon_conflicts`**: Active contradictions between active canon facts.
- **`decision_registry`**: Log of approved proposals and resolved questions.
- **`questions`**: Unresolved clarifications posed to the user.
- **`cycles` / `runs`**: Lifecycle and agent execution details.
- **`agent_outputs`**: Raw outputs, latency, tokens, cost, and traces per agent run.
- **`app_settings`**: Global configuration keys, provider preferences, and model details.
