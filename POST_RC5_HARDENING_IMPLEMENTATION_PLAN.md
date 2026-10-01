# NovelForge V2 — Post-RC5 Product Hardening Plan

Date: 2026-07-23  
Status: approved implementation boundary derived from the full-project audit

## Objective

Close verified correctness, scalability, security, publication, navigation, and product-experience gaps without redesigning the frozen Narrative Analysis Engine architecture or adding Paragraph Editor capabilities.

## Preserved boundaries

- Narrative Analysis remains the shared source for Story Health, Canon, Timeline, Character, Plot Thread, Story Bible, Assistant, and Companion projections.
- Canon and manuscript mutations remain author governed.
- Paragraph Editor capability remains frozen; only project ownership, migration, lifecycle, and integration defects may be corrected.
- Application Knowledge remains separate from project knowledge.
- Local-first operation remains the default deployment model. Hosted multi-tenant identity is documented as a separate deployment requirement rather than being inferred into this release.

## Implementation workstreams

1. **Data integrity**
   - normalize project ownership identifiers;
   - replace obsolete workspace collection lookups;
   - centralize project-owned collection cleanup;
   - add recoverable archive/restore and explicit duplication modes;
   - require confirmation for permanent deletion.
2. **Workspace Companion**
   - consume real analysis and workflow job state;
   - emit and react to completion/failure events;
   - mark opened messages read;
   - add docked layout, persisted preferences, quiet motion controls, and live-region status.
3. **Analysis and projection performance**
   - add source manifests and domain-scoped dirty analysis;
   - coalesce no-change history;
   - segment large Story Bible sections while preserving the public response contract;
   - make Companion reads projection based;
   - deduplicate refresh and background work.
4. **Product completion**
   - add governed manuscript export packages;
   - add publication preflight;
   - complete Application Knowledge publication/lifecycle intents;
   - add refresh-safe workspace deep links and global navigation.
5. **Safety and operations**
   - configurable CORS and optional local session-token protection;
   - protected provider settings/test endpoints when a token is configured;
   - persistent encryption-key guidance and safer Docker defaults;
   - meaningful liveness/readiness endpoints;
   - retention/index updates for high-volume operational records.
6. **Quality**
   - structured chronology parsing and evidence-coverage scoring;
   - explicit insufficient-evidence Story Health state;
   - typed mutation contracts for new/changed endpoints;
   - targeted regression, accessibility, visual, lifecycle, migration, and performance coverage.

## Validation gates

1. migration idempotency and project data-integrity audit;
2. focused backend and frontend tests;
3. focused Playwright for project lifecycle, Companion, publication, navigation, and application knowledge;
4. full backend regression;
5. full frontend regression and production build;
6. full Playwright desktop matrix with console capture;
7. real database-configured Gemini 3.1 Flash Lite smoke validation;
8. large-novel incremental/cache benchmark;
9. RC1 implementation, RC2 regression, RC3 product/UX, and RC4 documentation closeout.

## Explicit non-goals

- no new paragraph editing feature;
- no independent analysis engine or duplicate recommendation engine;
- no speculative cloud billing, team collaboration, or hosted tenancy architecture;
- no automatic canon or manuscript approval.
