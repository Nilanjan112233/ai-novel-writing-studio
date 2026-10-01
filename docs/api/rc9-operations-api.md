# RC9 Operations API

All responses include `X-NovelForge-Reference`. This API is bound to the local
private-beta deployment; it is not a multi-tenant security boundary.

| Method | Route | Purpose |
|---|---|---|
| GET | `/api/operations/readiness` | Author-language storage, migration, folder, and AI state |
| GET | `/api/operations/privacy` | Accurate local/provider/support data-flow summary and local folders |
| POST | `/api/operations/support-bundles` | Create a sanitized local diagnostic ZIP |
| GET | `/api/operations/support-bundles/{id}/download` | Download the exact diagnostic bundle |
| POST | `/api/operations/feedback` | Save categorized local beta feedback with optional diagnostics |
| POST | `/api/operations/backups` | Create a separate protected archive for every non-trashed project |
| POST | `/api/projects/{project_id}/backups` | Create one project backup |
| GET | `/api/projects/{project_id}/backups` | List that project’s backup metadata |
| POST | `/api/backups/import` | Stream and validate a downloaded archive; filename is supplied in `X-NovelForge-Filename` |
| POST | `/api/backups/{backup_id}/validate` | Validate compatibility, counts, entries, and checksums |
| POST | `/api/backups/{backup_id}/restore` | Restore as a new project, reconcile identities, and verify integrity |
| GET | `/api/backups/{backup_id}/download` | Download the exact archive |

Backup creation accepts `{ "reason": "..." }`. Restore accepts an optional
`{ "title": "..." }`. Feedback accepts category, message, and
`include_diagnostics`; `include_story_content` is retained as an explicit
declaration but RC9 never attaches story content.

