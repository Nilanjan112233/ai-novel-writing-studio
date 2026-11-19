# RC9 Troubleshooting

Run `scripts/windows/check-novelforge.cmd` first. It reports whether the local services, project
storage, data format, backup folder, publication folder, and AI connection are
ready. A failed AI check does not mean the project database is unavailable.

## Docker Desktop is not running

Start Docker Desktop, wait until it reports that its engine is ready, then run
`scripts/windows/start-novelforge.cmd` again. No NovelForge data is changed by this failure.

## Port 3000, 8000, or 27017 is occupied

NovelForge will not terminate the occupying process. Close the known application
using that port or stop an older NovelForge instance. Do not kill an unknown
process merely to make startup pass.

## Project storage unavailable

Do not continue editing in a screen that reports a failed save. Keep the error
visible and retain its support reference. Check Docker Desktop and
`scripts/windows/check-novelforge.cmd`; restart NovelForge after storage is healthy. If the
database volume cannot be recovered, install a clean instance and import a
downloaded `.novelforge-backup`.

## Gemini unavailable or invalid key

Existing projects remain readable and manually editable. Open **AI Settings**,
replace the credential, select a supported model, and run **Test Selected Model**.
Provider timeouts and temporary rate limits are recoverable; retry only after the
current operation reports failure. NovelForge does not persist partial provider
output as a valid draft.

## Disk space or backup failure

NovelForge checks its backup and publication destinations and reserves a minimum
free-space threshold. A failed backup leaves the project unchanged. Free space,
confirm the folder is writable, then retry. Keep important downloaded backups on
a second drive or another storage location you control.

## Interrupted generation, revision, approval, or analysis

Restart the application and reopen the project. Approved prose remains
authoritative; Writer’s Room alternatives remain inactive; idempotent retries
reuse an established operation where possible; queued Narrative Analysis work is
recovered during backend startup. Retry from the visible failure banner.

## Interrupted backup or restore

Temporary backup files are not registered as valid archives. Restore writes a
separate project copy and rolls that copy back if integrity verification fails.
Validate the backup again after restart. Never delete the original project until
the restored copy has opened and been reviewed.

## Create diagnostics

Open **AI Settings → Download safe diagnostics**. The archive excludes prose,
prompts, provider responses, Story Bible content, notes, credentials, tokens,
and database connection strings. It includes correlation references useful for
matching an author-facing failure to sanitized logs.

