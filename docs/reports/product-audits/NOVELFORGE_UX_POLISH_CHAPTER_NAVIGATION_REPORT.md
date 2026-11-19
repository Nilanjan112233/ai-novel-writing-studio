# NovelForge UX Polish: Chapter Navigation and Editing

## Implemented

- Writing cards now say `Edit Chapter N` and preserve the selected draft ID.
- The selected chapter opens Editorial with a focused target rather than an unfiltered specialist page.
- Editorial explains that the protected source remains authoritative and that revision branches are alternatives until deliberately applied.
- Discovery-only chapter drafts without structured `chapter_plan_id` now display their real chapter number instead of `Chapter not linked`.
- Every chapter exposes `View versions (N)`; chapters with multiple versions expose `Compare versions`.
- Version comparison uses existing chapter draft lineage and returns a bounded human-readable diff. A one-version chapter explains how to create a revision before comparison is available.

## Live browser evidence

The real six-chapter project displayed Chapter 1–6. Selecting Chapter 3 and choosing `Edit Chapter 3` opened Editorial with:

- `Editing a selected chapter`;
- `Chapter 3 · Chapter draft · Version 1 · approved`;
- `New Revision Branch`.

No new editor or prose authority was introduced.

