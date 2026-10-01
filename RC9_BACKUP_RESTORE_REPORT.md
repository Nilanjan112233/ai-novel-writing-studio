# NovelForge V2 RC9 — Backup and Restore Report

## Recovery contract

NovelForge backups protect editable project state. Publication exports protect reader-facing manuscript output; Paragraph versions protect prose history. These are intentionally separate responsibilities.

The backup service reads the same project-owned collection registry used by lifecycle deletion and database integrity. It does not create a second source of truth. The archive manifest records product, application, schema and backup-format versions, project identity/title, timestamp, collection counts, rebuildable data, exclusions and SHA-256 checksums.

## Included and excluded data

The archive covers the project record and all authoritative project-owned records: planning, decisions, characters, worldbuilding, relationships, timeline, canon, Story Bible, scenes, paragraphs, versions, revisions, editorial/manuscript state and project-scoped Narrative Intelligence. Rebuildable projections are included where present and can be refreshed after restore.

Excluded by design: provider API keys, provider/global settings, encryption material, support bundles and publication files outside the project database.

## Restore sequence

1. Select or import an archive.
2. Validate archive checksum, manifest, allowed collections, per-entry checksums, record counts and compatibility.
3. Preview title, source version, created date, record counts, warnings, exclusions and rebuildable information.
4. Restore as a new project identity; remap internal project/entity references deterministically.
5. Rebuild Story Bible if absent and run the project database-integrity audit.
6. Publish the new copy only after verification succeeds.

The original project is never overwritten. A failed verification removes only the partial copy. A stable request identity makes lost-response retries and concurrent browser calls idempotent.

## Evidence

- Unit/integration: complete copy, checksum, corrupt archive, rollback, import after metadata loss, backup-all partial failure and concurrent/retried restore.
- Live browser: created and downloaded a project backup, changed the working project, previewed the archive, restored a separate copy, opened it and verified the original remained present.
- Packaged API concurrency: two simultaneous requests and a retry produced one project (`copies: 1`) and one restore operation (`operations: 1`).
- Database integrity passed after backup/restore testing.
- 50-chapter archive: 67,144 bytes, create 800 ms, validate 141 ms.
- 500-chapter archive: 282,031 bytes, create 1,843 ms, validate 823 ms.

## Recovery and retention

The UI supports current-project and all-project backups. `Back Up Before Update.cmd` creates the explicit recovery boundary used by the update workflow. Retention is bounded to ten available backups per project. Downloaded archives should be copied to another disk or trusted storage if the author needs protection from complete machine loss.

Automatic timer-based backups were evaluated but not added: opaque background archives would consume storage and create false reassurance unless external-copy policy is also solved. RC9 instead makes explicit and pre-update backups visible and bounded. This is a known private-beta limitation, not Paragraph Editor versioning duplication.
