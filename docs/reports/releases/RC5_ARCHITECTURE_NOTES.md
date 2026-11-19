# RC5 Architecture Notes

## Post-RC5 production hardening — 2026-07-23

- `ProjectLifecycleService` is the single ownership catalog for archive, trash, restore, guarded purge, shell duplication, story duplication, and integrity queries. The UI never calls permanent deletion as its primary action.
- The existing Narrative Analysis Engine remains authoritative. A lightweight source manifest and project-event cursor avoid loading full chapter/scene payloads for unchanged runs; per-project locks coalesce concurrent requests; a cache hit reuses the same analysis identity and does not create false history.
- Story Bible persistence is segmented by section while its assembled API contract remains backward compatible.
- Narrative job recovery marks interrupted work safely on startup, and the Companion reads cached projections plus job state instead of initiating analysis.
- Publication is a governed projection of the approved current manuscript version. Every export records source version, generated formats, hashes, and a manifest; no Paragraph Editor or analysis architecture is involved.
- Workspace deep links use the existing section registry as the single destination source. Browser history and the command navigator consume that registry rather than defining a second navigation model.
- Local deployment security now uses explicit CORS origins, trusted hosts, loopback container bindings, optional token authentication, durable settings encryption, and separate liveness/readiness checks.
- The Paragraph Editor remains frozen. The only production change was a critical persistence compatibility fix: paragraph-owned documents now use canonical ObjectId project ownership and serialize those identifiers at the API boundary.

## Bounded additions

RC5 adds projections around the frozen Narrative Analysis platform:

```text
Application catalog ─┬─ Page guidance
                     ├─ Assistant application reasoning
                     └─ Navigation validation

Narrative Analysis history ── Story Health History
Existing project events ───── Project Timeline
Narrative Completeness ─────── Companion recommendation lifecycle
Narrative graph ────────────── Knowledge Graph cards and controls
```

## Backend modules

- `ApplicationKnowledgeService`: author-facing product catalog and query classification.
- `ProjectEvolutionService`: Project Timeline and analysis-snapshot comparison.
- `WorkspaceCompanionService`: stable lifecycle, cooldown, recap, and state projection.
- `NarrativeAnalysisEngine`: compact history recording added at existing completion/cache/rescore points.
- RC5 migration: indexes only; backward-compatible and idempotent.

## Frontend modules

- `PageGuidance`: one shared what/why/do/next contract.
- `AuthorValue`: safe author-facing values and evidence.
- `ProjectTimelines`: evolution and score-change views.
- `WorkspaceCompanion`: state-aware, reduced-motion-safe companion UI.
- existing Interactive Narrative Studio: application-layer badges, graph cards, direct actions, and explainability presentation.

## Preserved boundaries

- no new story-analysis rules;
- no duplicate graph or canon store;
- no Canon authority change;
- no Story Health scoring redesign;
- no Paragraph Editor capability addition;
- no mobile redesign;
- no automatic application of AI narrative changes.
