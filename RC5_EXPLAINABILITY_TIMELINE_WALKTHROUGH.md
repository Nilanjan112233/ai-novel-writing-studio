# RC5 Explainability Timeline Walkthrough

Story Health History explains how two Narrative Analysis snapshots differ. It compares stored analysis projections; it never recalculates or overrides Story Health.

## Walkthrough

1. Open **Toolbox → Review → Story Health History**.
2. Review the overall score movement, for example `82 → 86`.
3. Inspect category deltas for Canon, Timeline, Character, Plot, Pacing, Continuity, and Balance.
4. Read resolved and newly introduced findings in author language.
5. Select a reason or **Review supporting evidence** to open its owning workspace.

Every comparison answers what happened, why the author should care, and where to act. Compact snapshots are recorded for full analysis, cached analysis use, and finding-status rescoring.

API: `GET /api/projects/{project_id}/explainability-timeline`.

