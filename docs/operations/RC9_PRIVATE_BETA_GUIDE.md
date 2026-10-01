# RC9 Private Beta Guide

## Supported use

RC9 supports one trusted author running NovelForge locally on Windows. It is not
a hosted, shared, or multi-tenant service. Docker Desktop is the supported beta
runtime because it supplies the application, MongoDB, and persistent storage as
one bounded installation.

## Install and first launch

1. Install Docker Desktop for Windows and allow it to finish starting.
2. Extract the NovelForge beta folder to a location you control. Do not run it
   from inside a temporary ZIP preview.
3. Double-click `Start NovelForge.cmd`.
4. Wait for “NovelForge is ready,” then use the browser page that opens.
5. Review the readiness card. Project storage, data compatibility, backup
   storage, publication storage, and AI are reported independently.
6. Open **AI Settings**, enter the Google AI Studio key, select
   **Gemini 3.1 Flash Lite**, save, and use **Test Selected Model**. The saved key
   is never displayed again.
7. Open **Projects**, create the novel, and follow **Start Your Novel**.

If AI is not configured or temporarily unavailable, existing projects still
open. Manual writing, browsing, review, backup, and export of already-valid work
do not depend on an AI connection.

## Normal operation

- Start or resume: `Start NovelForge.cmd`
- Check problems: `Check NovelForge.cmd`
- Stop safely: `Stop NovelForge.cmd`
- Application: <http://localhost:3000>

The launcher never stops an unrelated process to obtain a port. A port conflict
is reported and the occupying application must be closed intentionally.

## Where data lives

In the supported Docker path:

- projects and application settings live in named Docker volumes;
- the credential encryption key, local backups, support bundles, and publication
  exports live in the persistent backend data volume;
- downloaded `.novelforge-backup` files and publication files live wherever the
  author saves them on Windows.

In the developer path, projects live in the configured local MongoDB database.
Backups default to `%USERPROFILE%\.novelforge\backups`, and diagnostics default
to `%USERPROFILE%\.novelforge\support` unless configured otherwise.

## What goes to an AI provider

When an author starts an AI generation, revision, conversation, or analysis
operation, NovelForge sends the relevant bounded story context to the configured
provider. Existing work is not uploaded merely by opening a project. Provider
credentials are not included in project backups or support bundles.

## Support and feedback

Open **AI Settings → NovelForge readiness**.

- **Download safe diagnostics** creates a local bundle with version, readiness,
  migration, provider/model status, sanitized errors, correlation references,
  and timings.
- **Private-beta feedback** records a categorized report locally. Attaching
  sanitized diagnostics is opt-in. Story content is never attached automatically.

Keep the support reference displayed with an error. It correlates the visible
failure with sanitized operational records.

## Uninstall and data preservation

Removing or replacing the extracted application folder does not itself delete
Docker named volumes. `Stop NovelForge.cmd` also preserves them. Before any
update or uninstall, run `Back Up Before Update.cmd` and move the downloaded
archives to a folder outside the NovelForge installation.

Never run `docker compose down --volumes` or delete Docker volumes unless you
intend to permanently remove the project database and encryption key. Deleting
the application folder can delete any downloaded backups stored inside it, so
store recovery archives separately.

