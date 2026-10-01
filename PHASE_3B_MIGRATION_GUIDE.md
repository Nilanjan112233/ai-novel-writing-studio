# NovelForge Narrative Studio V2 - Phase 3B Migration Guide

Migration date: 2026-06-14

## Scope

Phase 3B is additive. It introduces manuscript records, immutable manuscript
versions, manuscript reports, canon conflicts, and typed fields on the
existing canon registry.

All Phase 1A through Phase 3A data is preserved.

## Command

From `backend`:

```powershell
py -3.11 scripts\run_phase_3b_migration.py
```

The registered application startup path also runs the migration.

## Collections

Created or normalized:

- `manuscripts`
- `manuscript_versions`
- `manuscript_reports`
- `canon_conflicts`
- `canon_registry`

Legacy canon records retain their locked-fact fields. The migration adds
stable canon IDs, typed domains, source collection and version, authority,
active state, evidence, subject, field, value, and timestamps.

On its first run, the migration can build typed canon records from approved:

- character bibles;
- power progressions;
- artifacts;
- timeline entries;
- knowledge entries;
- factions;
- world bibles;
- mysteries;
- relationships.

## Indexes

| Collection | Index | Keys |
| --- | --- | --- |
| `manuscripts` | `manuscripts_project_version` | project, version, manuscript |
| `manuscript_versions` | `manuscript_versions_manuscript_version` | project, manuscript, version |
| `manuscript_reports` | `manuscript_reports_subject` | project, manuscript, version, type, time |
| `canon_registry` | `canon_registry_project_type` | project, type, subject, field |
| `canon_registry` | `canon_registry_active` | project, active, authority, time |
| `canon_conflicts` | `canon_conflicts_project_status` | project, status, severity, time |

`manuscript_versions_manuscript_version` is unique.

## Idempotency

The migration records:

```text
migrations.phase_3b_version = 1
```

Expensive normalization and canon backfill run once. Later application starts
still verify all required indexes.

Two consecutive final reruns both returned:

```json
{
  "canon_records_normalized": 0,
  "canon_records_created": 0,
  "manuscripts_normalized": 0,
  "indexes_installed": true
}
```

## Post-Migration Checks

Verify:

1. All six named indexes exist.
2. Existing locked canon facts remain available.
3. Manuscript versions have unique project/manuscript/version numbers.
4. Every Phase 3B record has a valid `project_id`.
5. Every manuscript `current_version_id` resolves to its manuscript.
6. Every manuscript source chapter resolves to an approved chapter draft.
7. No provider secret appears in API responses or migration logs.

The final production E2E project passed these checks and the project-scoped
database audit with zero findings.

## Rollback

1. Stop new manuscript and canon operations.
2. Disable `ManuscriptAgent`.
3. Disable `CanonAgent`.
4. Redeploy the Phase 3A application.
5. Retain the additive Phase 3B collections and indexes.

Do not delete:

- manuscripts;
- manuscript versions;
- manuscript reports;
- canon registry history;
- canon conflicts.

Rollback requires no mutation of approved chapters, scenes, editorial
records, or revision history.
