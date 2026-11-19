# NovelForge V2 RC9 — Private Beta UX Report

## Amateur-author acceptance

The visible packaged application was tested from a clean library rather than only through APIs. First Run separates three concepts an amateur author otherwise confuses: whether local work is safe, whether AI is available, and what to do next. It leads to Projects even when AI is not configured and links AI setup to the relevant Settings area.

The test author created a fantasy mystery, “The Lanterns Below,” entered premise/genre/tone, reached the guided project dashboard, created a project backup, downloaded it, validated and previewed it, restored a separate copy and reopened the copy. The original remained visible. After application stop/start, the projects returned without manual refresh or recovery action.

## What improved

- First-launch status uses author language instead of database/provider internals.
- AI being unavailable no longer makes the product look wholly broken.
- Project Settings makes backup ownership and restore safety visible near the project.
- Global Settings provides readiness, privacy, backup-all, diagnostics and feedback in one operational area.
- Restore preview states what is included, excluded, rebuildable and unchanged.
- Backup creation and archive download failures are distinguished; a failed download does not imply that a successfully stored archive was lost.
- Failures persist until acknowledged/retried and include a support reference.
- Empty Story Health/question states no longer claim conflicts or warnings before analysis has run.

## Remaining friction observed

### First install

Docker Desktop is still a prerequisite and the first build took about nine minutes on the test host. The launcher explains progress/failure, but this is less approachable than a signed native installer.

### First project

The guided dashboard and Companion can recommend different adjacent next actions. Both destinations are valid, but a beginner may interpret the mismatch as disagreement. This is a medium-priority polish issue, not lost state or a dead end.

### Backup mental model

“Create backup” stores an application copy and “Download” creates portability. The UI explains both, but an author protecting against computer loss must still remember to download/copy the archive elsewhere. There is no scheduled external backup.

### Operational Settings density

Readiness, privacy, support, backup-all and feedback form a long panel. It remained usable at tested desktop sizes, but progressive disclosure could be refined after private-beta observation without changing the architecture.

## Navigation and accessibility

The tested desktop matrix covered 1280×720 with Toolbox and Companion plus 1366×768, 1440×900, 1920×1080 and 2560×1440. Existing keyboard, focus, ARIA, reduced-motion, error-announcement, dialog and frozen Paragraph Editor assertions passed. Companion did not block the core backup/restore or writing journeys.

## Private-beta usability judgment

A non-technical author can create/open local work, understand why AI is unavailable, make a safety copy, recover as a separate project, obtain a support reference and restart without developer intervention after the initial Docker prerequisite is satisfied. Private-beta onboarding should explicitly verify Docker Desktop and require one successful downloaded backup during orientation.
