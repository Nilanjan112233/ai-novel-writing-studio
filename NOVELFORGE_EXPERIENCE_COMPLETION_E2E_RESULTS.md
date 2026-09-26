# Experience Completion E2E Results

Date: 2026-07-19

## Full Playwright regression

Command: `npx playwright test --project=chromium`

Result: **37 passed, 2 skipped, 0 failed in 23.0 minutes**.

The run covered:

- real Gemini story planning, drafting, editorial review, manuscript governance, project lifecycle, Story Auditor, and Phase 7 interactive narrative workflows;
- shared Phase 6 Narrative Analysis graph and Story Health evidence;
- the milestone pipeline, critique, Canon Explorer, creation guide, and Workspace Companion in one project workspace;
- frozen Paragraph Editor suggestions, versions, comments, productivity, visual QA, pipeline filters, and performance;
- project/workspace/settings stability at 1280, 1440, 1920, and 2560 pixels;
- mobile Story Intelligence usability and a clean new-project workspace.

The two skipped cases are the suite's intentionally conditional provider/lifecycle cases, not failures.

## Final focused browser gate

Command: `npx playwright test e2e/product-experience-completion.spec.ts --project=chromium`

Result after the final coordinator and guide cleanup: **1 passed, 0 failed in 36.0 seconds**.

## Real Google AI Studio validation

The encrypted/stored database credential was used through the application provider gateway; the key was never printed.

- Provider: Gemini
- Model: `gemini-3.1-flash-lite`
- Direct stored-credential probe: successful, 1.562 seconds, 6 output tokens
- Narrative Intelligence smoke probe: successful, 1.642 seconds, 68 output tokens, required marker present
- Full Playwright provider calls: HTTP 200 throughout the configured live workflows

