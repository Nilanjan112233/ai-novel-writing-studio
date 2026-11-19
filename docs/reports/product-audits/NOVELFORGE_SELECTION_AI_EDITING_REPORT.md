# NovelForge Selection-Based AI Editing Report

## Design

The chapter editor captures selected text and exposes focused actions for rewrite, naturalization, shortening, dialogue improvement, and a custom instruction. The selection plus tightly bounded surrounding prose is sent to the existing Editorial review/branch/revision path through `POST /api/projects/{project_id}/chapter-drafts/{draft_id}/selection-revision`.

The result is a protected suggestion. It does not silently replace text. The author can review the revision in the existing Editorial/version workflow and accept, reject, regenerate, or keep the original.

## Safety

The selected passage, surrounding context, chapter facts, POV, chronology, and continuity constraints are preserved as revision guidance. Existing draft lineage, Writer's Room protections, Paragraph Editor authority, and approved-source immutability are unchanged.

## Evidence and limitation

The current-source browser check selected text with the normal editor keyboard interaction and showed `Focused AI edit` with Rewrite naturally, Shorten, Improve dialogue, and Custom instruction. The API, focused tests, TypeScript build, and direct editor surface are validated. A real provider selection-revision call was not made in this final pass because it would create an unnecessary paid revision in the existing validation project; the normal chat-based revision path was exercised with a real provider call earlier in the same project.
