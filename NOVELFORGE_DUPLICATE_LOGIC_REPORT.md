# NovelForge Duplicate Logic Report

Date: 2026-07-19

## Conclusion

The central Narrative Analysis graph is not duplicated. Phase 7 correctly consumes its nodes, edges, findings, and snapshots. Duplication exists around orchestration and compatibility edges, not the core intelligence model.

## Duplication requiring consolidation

### 1. Post-mutation refresh orchestration — high priority

Evidence:

- `_after_change` exists independently in Canon Governance, Drafting, Editorial, Manuscript, planning APIs, and development APIs;
- Story Bible rebuild is directly invoked from many additional API and service paths;
- event names/payloads and analysis refresh timing differ by path.

Risk: one mutation may refresh Story Bible but omit completeness, companion reaction, or a specific incremental invalidation.

Decision: centralize the sequence behind a small `ProjectIntelligenceCoordinator`; preserve each existing service as the owner of its mutation rules.

Completion update: implemented. Canon Governance, Drafting, Editorial, Manuscript, planning, and arc development now delegate the shared Story Bible rebuild and versioned project-event sequence to `ProjectIntelligenceCoordinator`. Subsystem-specific readiness and maturity evaluation remains with its owning subsystem.

### 2. Canon intake paths — high priority

Evidence:

- `canon_service.py` stores legacy free-text locked facts from messages/answers;
- `canon_governance_service.py` stores typed, sourced, versioned canon;
- Phase 7 canon proposals already enforce governance for AI facts.

Risk: invisible untyped facts can coexist with transparent typed canon and bypass the Explorer’s governance history.

Decision: Shared Narrative Context becomes the intake boundary. Keep compatibility reads during migration, but new facts route to typed knowledge and Canon Proposal/Promotion workflows.

### 3. Next-action selection — medium priority

Evidence:

- backend `WorkspaceContextService` derives `suggested_next_action`;
- frontend `Dashboard` independently derives a different `nextAction` ordering.

Risk: the dashboard and assistant can recommend different work.

Decision: Completeness/Milestone service owns ranked next actions; dashboard, companion, and guide consume the same result.

Completion update: implemented for the new production pipeline, companion, and creation guide. The older workspace-context compatibility field remains readable but is not extended with new decision logic.

### 4. Source inventories — medium priority

Evidence:

- Narrative Analysis `SOURCE_COLLECTIONS`;
- Story Bible section assembly;
- memory retrieval `source_specs`;
- database audit collection lists;
- project deletion cascade.

Risk: a new narrative entity can appear in one consumer but remain absent from memory, deletion, audit, or graph analysis.

Decision: introduce a shared narrative-source catalog or, at minimum, a contract test asserting coverage across these registries. Avoid a large repository abstraction rewrite.

### 5. Serialization helpers — low priority

Evidence: many API/service-local `_serialize` implementations convert ObjectId and datetime values.

Risk: inconsistent field naming and datetime conversion; low narrative-business risk.

Decision: use the existing utility serializer for newly touched code and consolidate opportunistically. Do not make this product audit a broad serialization rewrite.

### 6. Legacy Story Auditor logic — low priority

Evidence: `_legacy_deterministic_findings` duplicates several checks now owned by Narrative Analysis; current `deterministic_findings` already delegates to Narrative Analysis.

Decision: keep temporarily for compatibility/forensics but do not invoke or extend it. All new critique rules belong to the shared analysis/critique pipeline.

## Intentional separation to preserve

- **Story Health vs Narrative Critique:** Health is the scored project state; Critique is an actionable interpretation and improvement workflow.
- **Narrative Analysis graph vs UI graph projection:** the Phase 7 UI projection is a bounded view, not duplicate graph data.
- **Agent memory vs shared project knowledge:** bounded agent execution memory is a cache/projection; Shared Narrative Context is authoritative project knowledge.
- **Readiness vs Completeness:** readiness can retain arc-specific execution gates; Completeness provides project dimensions and production milestones.
- **Canon proposals vs canon registry:** proposals are governed pending changes; the registry is approved truth.
- **Workspace Companion vs Project Assistant:** Companion selects proactive event/status messages; Project Assistant remains the conversational reasoning and navigation interface.

## Guardrail tests required

1. every new narrative source participates in analysis, Story Bible, memory, audit, and deletion;
2. every mutation uses the shared refresh coordinator exactly once;
3. every user fact has one dedupe fingerprint and provenance chain;
4. every critique references a shared finding/evidence source;
5. dashboard, companion, and guide receive the same next-action ID;
6. canon edits create versions and proposals rather than overwriting registry history.
