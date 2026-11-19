# RC5 Project Timeline Walkthrough

Project Timeline records how the NovelForge project evolved. It is not the chronology inside the novel; that remains Story Timeline.

## Entry shape

Each entry presents:

- date;
- author or AI actor;
- author-readable action and outcome;
- affected systems;
- Story Health, Canon, and Story Timeline deltas where available;
- a related workspace destination;
- replay context.

## Walkthrough

1. Open **Toolbox → Review → Project Timeline**.
2. Scan the newest project decisions and milestones.
3. Expand an entry to replay what changed and which systems were affected.
4. Select **Open related workspace** to review the resulting state.

The service normalizes existing project events and milestone activity. It does not introduce a duplicate event store.

API: `GET /api/projects/{project_id}/project-timeline`.

