# NovelForge V2 Phase 6 Implementation Plan

## Objective

Shift NovelForge's center of gravity from paragraph generation to whole-novel understanding while preserving the frozen Paragraph Editor architecture.

## Delivery slices

1. **6A — Shared engine:** persisted source graph, dependency edges, reusable evidence findings, scores, incremental fingerprints, cache, background jobs, and migration indexes.
2. **6B — Primary Story Health:** make Story Health the default project dashboard and expose all health dimensions with direct evidence and recommended actions.
3. **6C–6G — Intelligence consumers:** enrich Canon, Timeline, Character, Plot Thread, and Story Bible workflows from the shared graph without duplicate domain logic.
4. **6H — Change impact:** expose downstream chapters, scenes, characters, threads, canon, timeline, manuscripts, and narrative risk before structural decisions.
5. **6I — AI reviewer:** make the read-only StoryAuditorAgent consume the shared graph and require evidence-linked narrative recommendations.
6. **Scale and stabilization:** backend/frontend/Playwright coverage, 500-chapter benchmark, compatibility, architecture docs, and explicit limitations.

## Frozen boundary

No new paragraph capability is planned. Paragraph code may only be touched for a critical defect that blocks an existing regression gate. Phase 6 work is restricted to analysis, aggregation, governance, intelligence APIs, and consuming UI.

## Completion gates

- RC1: implementation complete.
- RC2: backend, frontend, build, Playwright, migration, integrity, and benchmark gates pass.
- RC3: product/UX and accessibility review complete; primary dashboard and evidence paths verified.
- RC4: architecture, walkthroughs, results, limitations, and cleanup complete.
- Phase Complete: only after RC1–RC4 all pass.
