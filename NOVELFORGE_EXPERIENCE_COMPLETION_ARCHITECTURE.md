# NovelForge V2 Experience Completion Architecture

## Architectural decision

The completion work is a projection layer over the frozen Narrative Analysis Engine. It does not create a second story graph, a second health calculation, or a second editor. The Paragraph Editor was not changed.

```text
Approved project content + structured author answers
                         |
                         v
              Narrative Analysis Engine
                         |
       +-----------------+------------------+
       |                 |                  |
       v                 v                  v
 Shared findings    Analysis graph     Story Bible
       |                 |                  |
       +--------+--------+---------+--------+
                |                  |
                v                  v
        Critique projection   Completeness projection
                |                  |
                +---------+--------+
                          |
                          v
       Story Health + milestone gates + companion
```

## Services and ownership

| Service | Responsibility | Reuses |
|---|---|---|
| `NarrativeAnalysisEngine` | Incremental nodes, edges, findings, shared scores | Approved project collections |
| `ProjectIntelligenceCoordinator` | One Story Bible rebuild and one versioned project event after governed mutations | Existing mutation owners |
| `SharedNarrativeContextService` | Classify, deduplicate, preserve provenance, and route meaningful author input | Canon Proposal and Story Bible workflows |
| `NarrativeCritiqueService` | Convert health and analysis evidence into actionable, subsystem-owned critique | Story Health and `narrative_findings` |
| `NarrativeCompletenessService` | Evaluate eight completeness dimensions and five production gates | Analysis, canon, Story Bible, project artifacts |
| `CanonGovernanceService` | Searchable authoritative registry, history, comparison, activation, governed edits | Existing canon and proposal stores |
| `WorkspaceCompanionService` | Present quiet, event-driven guidance and navigation | Health, completeness, proposals, project events |
| `StoryBibleService` | Publish approved and attributable shared knowledge | Existing Story Bible build pipeline |

## Shared persistence

- `narrative_nodes`, `narrative_edges`, `narrative_findings`, and analysis snapshots remain the common intelligence substrate.
- `shared_narrative_context` stores structured author answers with confidence, provenance, fingerprint, status, and routing targets.
- `narrative_completeness_snapshots` stores current and historical projection results.
- `workspace_companion_messages` stores stable, dismissible companion events.
- Canon remains authoritative in `canon_registry`; edits create proposals and cannot bypass author approval.

## Incremental and concurrent behavior

Source fingerprints determine which nodes must be recomputed. A cache hit performs no node recomputation. Graph edges use idempotent bulk upserts followed by stale-edge cleanup, so simultaneous dashboard consumers cannot violate the project/edge unique identity. Critique and completeness reuse the graph snapshot and do not submit the novel to a second analyzer.

## Cross-system refresh rules

1. Meaningful author input is structured and deduplicated.
2. The context record retains its source and routes to relevant systems.
3. Canon-changing input creates a proposal instead of changing official canon.
4. Approved mutations pass through the coordinator, which rebuilds the Story Bible once and emits one project event.
5. Narrative Analysis refreshes shared graph state and scores.
6. Critique, completeness, milestones, Knowledge Graph, and companion read those shared results.

## Compatibility boundaries

- Existing Phase 6 and Phase 7 API contracts remain available.
- Legacy canon facts are normalized for display without destructive migration.
- No automatic narrative improvement is applied.
- No Paragraph Editor capability was added or modified.
