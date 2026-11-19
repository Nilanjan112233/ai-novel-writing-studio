# NovelForge Chapter Editor Report

## Result

The current-source browser check opened Chapter 1 from the Writing chapter library and showed the full prose in an editable text surface. The UI states clearly: `Editing a protected copy. Save creates a new reviewable chapter version; the previous version stays in history.`

The chapter library exposes chapter number, word count, active version, update time, approval state, continuity state, extraction/context state, and actions for Open chapter, Edit, Continue from here, and View versions.

## Safety model

`backend/app/services/drafting_service.py:edit_chapter_content` creates a new active review version and never edits approved prose in place. The existing parent-version and revision lineage remain authoritative. The API is `PUT /api/projects/{project_id}/chapter-drafts/{draft_id}/content`.

The frontend editor provides direct editing, Save as new version, Cancel, save feedback, and a clear return path through the existing Writing/chapter library. Editorial remains available for deeper AI-assisted work rather than being required for a one-sentence correction.

## Validation

The focused backend test verifies that manual editing of an approved chapter creates version 2 in review. The production build and frontend suite passed. The browser check verified the direct editor and protected-copy language against the current source.

