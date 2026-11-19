# NovelForge Chat History Behavior Report

## Observed behavior

The current browser snapshot showed the five newest interactions immediately available under `Recent conversation`, while older saved turns were labeled `Historical conversation`. Each historical response exposed `Refresh against current story`, making the distinction between what was said then and what is true now explicit.

Historical planning and work entries were retained; they were not deleted or treated as current authority. Current answers are grounded through the current project services, not replayed blindly from old assistant text.

## Implemented behavior

`frontend/components/StoryStudioPanel.tsx` now limits the prominent conversation area to recent interactions and places older history behind progressive disclosure. The ordering remains chronological within each group, so collapsing history does not change the meaning of the conversation.

The composer also changes its prompt when Story Studio is waiting for clarification, and the follow-up carries `reply_to_job_id` so the answer remains attached to the original request.

## Acceptance

The current project no longer requires endless scrolling to reach the active composer or latest result. Full 10-15 interaction stress coverage was not repeated with a new provider run in this pass; the implementation is covered by focused tests and the live browser check.

