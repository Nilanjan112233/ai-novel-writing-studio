# RC9 Backup and Restore

## Backup scope

A project backup is an editable recovery archive, not a publication export. It
uses the same authoritative project-ownership registry as project lifecycle and
database integrity checks.

Included where present:

- project metadata and planning;
- decisions and guided-setup state;
- characters, world, factions, relationships, powers, themes, mysteries, arcs,
  timeline, knowledge, artifacts, and foreshadowing;
- canon registry/proposals/conflicts and Story Bible projections;
- chapter/scene plans, paragraph content and paragraph versions;
- scene/chapter drafts, alternative versions, revisions, editorial state,
  manuscripts, and publication metadata;
- Narrative Intelligence, completeness, Story Health, companion, project-event,
  and workspace cache records required for faithful recovery.

Provider credentials, global provider settings, tokens, and external publication
files are excluded. Derived projections may be rebuilt after restoration.

## Format and integrity

`.novelforge-backup` is a versioned ZIP containing Extended JSON newline records
and a manifest. The manifest identifies the source project, application and
schema versions, counts, excluded data, entry checksums, and format version. The
archive has a whole-file SHA-256 checksum in local backup metadata.

Validation rejects unknown entries, incompatible future format/schema versions,
missing project data, count differences, checksum differences, excessive
uncompressed size, and archives containing more than one project authority.

## Create a backup

- Current project: **Project → Settings → Back up and download**.
- All projects: **AI Settings → Back up all projects**. Archives are written to
  the protected backup folder shown on the same screen.
- Before update: double-click `Back Up Before Update.cmd`. This downloads a
  separate archive for every active or archived project into
  `NovelForge Update Backups`.

Backups rotate to the configured retention count per project (10 by default).
Pre-update downloaded copies are not deleted by rotation.

## Restore safely

1. In any project, open **Settings → Project backup and recovery**.
2. Select **Check for restore**, or use **Import backup** for a downloaded file.
3. Review compatibility, source release, record count, and integrity result.
4. Optionally name the recovery copy.
5. Select **Restore as new project**.
6. Open the restored project and compare it with the original.
7. Only after review, choose which copy to continue using. Archive the other copy
   from Projects if desired.

RC9 deliberately does not perform destructive in-place replacement. “Replacement”
is the author’s explicit decision to continue with the verified copy and archive
the prior project. Nothing is silently overwritten.

Restore assigns new machine identities and reconciles internal references. It
then rebuilds required Story Bible state and runs the project database integrity
audit. Any failure removes only the incomplete copy; the source project and
archive remain unchanged.

## Automatic recovery policy

RC9 does not add periodic whole-project snapshots on top of paragraph autosave
and version history. Automatic full copies would add hidden disk growth and
large-project write pressure. Instead, backups are bounded and explicit, the
update workflow refuses to proceed before project archives are downloaded, and
each project retains up to the configured number of protected local backups.

