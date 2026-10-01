# NovelForge Narrative Studio V2 - Phase 3A Migration Guide

Migration date: 2026-06-14

## Scope

Phase 3A is an additive migration. It adds editorial reports, scores, revision
branches, revision versions, and their indexes. Existing Phase 2B planning
and approved draft data is preserved.

## Command

From `backend`:

```powershell
py -3.11 scripts\run_phase_3a_migration.py
```

The application startup path also runs registered migrations.

## Collections

The migration creates or normalizes:

- `editorial_reports`
- `revision_branches`
- `revision_versions`
- `editorial_scores`

Compatible legacy editorial records receive stable IDs, project ownership,
status defaults, timestamps, and normalized subject fields where possible.

## Indexes

Installed indexes:

| Collection | Index |
| --- | --- |
| `editorial_reports` | `editorial_reports_project_subject` |
| `editorial_reports` | `editorial_reports_type_score` |
| `revision_branches` | `revision_branches_project_branch` |
| `revision_branches` | `revision_branches_source` |
| `revision_versions` | `revision_versions_branch_version` |
| `editorial_scores` | `editorial_scores_subject` |
| `editorial_scores` | `editorial_scores_project_type` |

## Verified Result

The final rerun returned:

```json
{
  "editorial_reports_normalized": 0,
  "revision_branches_normalized": 0,
  "revision_versions_normalized": 0,
  "editorial_scores_normalized": 0,
  "indexes_installed": true
}
```

This confirms the migration is idempotent.

## Deployment Order

1. Back up the MongoDB database.
2. Deploy the Phase 3A backend.
3. Run the migration command.
4. Verify all seven named indexes.
5. Deploy the Phase 3A frontend.
6. Confirm `/api/settings/ai` contains no `api_key` fields.
7. Run backend, frontend, build, and Playwright validation.
8. Enable the three editorial agents for intended providers/models.

Existing approved drafts require no conversion.

## Rollback

1. Stop new editorial and revision requests.
2. Disable `EditorAgent`, `DialogueAgent`, and `RevisionAgent`.
3. Redeploy the Phase 2B application.
4. Retain all four additive collections and seven indexes.

Do not delete editorial or revision collections during rollback. They do not
change Phase 2B authority and preserve audit history for a future redeploy.

No approved scene or chapter draft is modified by migration or rollback.

## Verification Queries

Confirm index installation:

```javascript
db.editorial_reports.getIndexes()
db.revision_branches.getIndexes()
db.revision_versions.getIndexes()
db.editorial_scores.getIndexes()
```

Confirm approved sources remain present:

```javascript
db.scene_drafts.countDocuments({ status: "approved", active: true })
db.chapter_drafts.countDocuments({ status: "approved", active: true })
```

Confirm revision lineage uniqueness:

```javascript
db.revision_versions.aggregate([
  {
    $group: {
      _id: { project_id: "$project_id", branch_id: "$branch_id", version_number: "$version_number" },
      count: { $sum: 1 }
    }
  },
  { $match: { count: { $gt: 1 } } }
])
```

The final query must return no records.
