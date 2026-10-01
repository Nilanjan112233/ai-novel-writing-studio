# NovelForge Native Memory V2 Migration Plan

**Status:** plan only; no migration or schema change performed.

## Migration goal

Introduce rebuildable Native Memory V2 without changing approved prose, canon, decisions, confirmed planning, revision lineage, backup semantics or old-project usability.

## Safety principles

1. Existing authority collections are read-only inputs to migration.
2. V2 is additive and derived.
3. Old Native remains available until shadow and canary gates pass.
4. Every V2 record points to an existing owner record/version and evidence.
5. Deleting V2 must never delete story data.
6. Backfill is resumable, idempotent and project-scoped.
7. Backup/restore remains valid without V2; derived memory can be rebuilt after restore.

## Proposed phases

### Phase 0 — acceptance corpus and observability

- Freeze labelled replay cases from current real packets and synthetic 10/25/50/100/250/500 projects.
- Record current recall outputs, context attribution, latency, cost and continuity results.
- Add an operation-level cost ledger design covering retries and auxiliary calls.
- Do not change runtime retrieval yet.

**Exit:** baseline is reproducible and includes the confirmed duplicate/chronology/POV cases.

### Phase 1 — additive derivation ledger

- Introduce V2 derived storage under a new versioned namespace/collection set.
- Project owner IDs, owner versions, evidence pointers, authority labels and story-time validity.
- Implement deterministic logical identity and derivation version.
- Add unique indexes that prevent the current `intelligence_id` versus `_id` duplication.

**Exit:** derived rows can be deleted and rebuilt identically without affecting owners.

### Phase 2 — project-scoped backfill

Order per project:

1. active canon and decision versions;
2. confirmed planning owners;
3. active approved prose/version pointers;
4. active chapter intelligence and structured episodes;
5. timeline, knowledge, relationship, mystery, thread and artifact validity;
6. optional explicit project preferences.

Use watermarks/checkpoints. Store source count, derived count, skipped invalid records, conflicts and hash. Never call paid providers for deterministic projections; queue optional extraction separately and only with approval/cost controls.

**Exit:** every derived item passes referential and authority validation.

### Phase 3 — shadow retrieval

- Execute V1 and V2 retrieval side by side for selected read requests.
- Only V1 reaches providers/authors.
- Compare recall, duplicates, authority leakage, chronology, source diversity, tokens and latency.
- Persist comparisons as non-authoritative telemetry.

**Exit:** acceptance corpus passes and V2 provides measurable benefit.

### Phase 4 — shadow context assembly

- Build consumer-specific V2 packets without sending them to paid models.
- Replay stored prompts offline where possible.
- Human/blind-review a sampled set before matched provider calls.
- Verify Story Studio rejection and preference governance.

**Exit:** packet quality non-inferior and token targets met.

### Phase 5 — reversible project canary

- Enable V2 for one explicitly selected test project behind a project flag.
- Preserve V1 fallback on error, timeout, incomplete authority coverage or unresolved migration.
- Log packet version and source ledger for every call.
- Never auto-enable Tencent or Hybrid.

**Exit:** real workflow passes generation, approval, revision, backup and restore tests.

### Phase 6 — gradual default and V1 retirement decision

- Expand by opt-in cohort, then default only after scale/quality gates.
- Keep V1 read compatibility for old projects through at least one full release/migration cycle.
- Retire duplicate V1 derived data only after verified backups and a rollback rehearsal.
- Tencent remains an independent experiment and is not required for V2.

## Invalidation and ongoing updates

Owner changes should emit or reuse project events:

- canon activation/deactivation;
- decision version change/undo/reopen;
- candidate confirm/reject/reconsider;
- chapter/scene version approval or archive;
- revision branch apply;
- structured owner edit;
- chapter intelligence regeneration.

A derivation worker marks dependent V2 records stale, writes replacements, then advances a project derivation watermark. Retrieval must reject records older than the authority watermark for strict writing calls or fall back to direct owners.

## Backup and restore

### Required

- Existing backups continue to include all authority and lineage data.
- Add V2 schema/derivation version and optional derived snapshot manifest.
- Restore validates authority first.
- If V2 is absent, incompatible or corrupt, discard it and rebuild.
- Preserve provenance IDs across restore where owner IDs are stable; otherwise build an explicit ID remap.

### Restore test

1. Back up a project with approved prose, canon, decisions, candidates, rejected ideas and revisions.
2. Restore into a clean database.
3. Compare authority hashes and lineage counts.
4. Rebuild V2.
5. Compare logical derived outputs and recall labels.
6. Confirm the project works with V2 disabled.

## Rollback

Rollback is a configuration/read-path switch:

- stop V2 workers for the project;
- route retrieval/context to V1;
- retain V2 telemetry for diagnosis;
- optionally delete only records in the explicitly resolved V2 collection namespace after backup;
- do not alter owner collections or external Tencent data.

Rollback triggers include authority leakage, missing provenance, chronology regression, higher important-memory miss rate, material latency regression, rebuild mismatch or backup/restore failure.

## Failure handling

| Failure | Safe behavior |
|---|---|
| V2 record lacks source version | Exclude it; use direct owner/V1 fallback |
| Derivation lag | Strict writer falls back to direct authority snapshot |
| Embedding service unavailable | Lexical + metadata + graph path; no blocking story mutation |
| Conflicting assertions | Include highest authority and conflict marker; request evidence expansion |
| Backfill interrupted | Resume from project/source watermark |
| Provider extraction fails | Keep deterministic/owner projection; retry separately |
| Tencent unavailable | No effect on V2 or authority |

## Migration acceptance criteria

- zero changes to authority hashes during backfill;
- 100% V2 rows have project, owner ID/type/version, derivation version and provenance;
- idempotent rerun creates zero duplicate logical records;
- old project opens and writes with V2 disabled;
- backup/restore authority counts, hashes and revision lineage match;
- V2 rebuild gives identical logical outputs for same source snapshot;
- rollback tested in a canary without data loss;
- no provider calls occur during deterministic backfill;
- all paid optional extraction is separately metered and resumable.

## What migration must not do

- rewrite approved prose or current revisions;
- promote candidate facts;
- copy Tencent memory into canon/owners;
- delete V1 indexes before canary completion;
- rely on Story Bible as the only source of truth;
- infer global author preferences from history during backfill;
- make restore depend on an external memory gateway.

