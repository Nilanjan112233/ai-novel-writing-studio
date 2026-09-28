# NovelForge Full Regression Report

## Backend

`pytest -q --ignore=test-output-focused.txt`

- 173 passed
- 7 skipped
- 441.72 seconds
- 180 tests collected

The normal `npm test` wrapper still attempts to collect the binary `test-output-focused.txt`; that is a repository test-discovery defect, so the complete run used the explicit ignore and completed successfully.

## Frontend

- 23 test files passed
- 87 tests passed

## Production build

`npm run build` passed with Next.js 15.5.22, including TypeScript/lint validation and static page generation.

## Browser sweep

The live browser exercised Story Studio, Writing, Characters, Relationships, World, Mysteries, Timeline, Plot Threads, Knowledge, Story Health, and Editorial. No application-error state was observed.

The browser also verified chapter-to-editor handoff, title separation, durable approval state, story context, post-approval change details, and readable evidence without raw IDs.

## Existing boundaries

No MongoDB authority, Canon Governance, Decision History, Story Bible authority model, Narrative Analysis Engine, graph, draft lineage, Writer's Room, revision architecture, Paragraph Editor, chronology, provider gateway, backup/recovery, or publication governance was replaced.
