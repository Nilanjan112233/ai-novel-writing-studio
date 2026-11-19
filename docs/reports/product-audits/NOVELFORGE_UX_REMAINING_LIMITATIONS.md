# NovelForge UX Remaining Limitations

## Validation limitations

- Full backend validation completed: 171 passed, 7 skipped, 6m10s.
- Frontend validation completed: 23 test files, 86 tests passed.
- Production build completed successfully.
- Browser testing verified the live chapter-library and context experience and found the stale Story Studio answer defect. A post-build dev-harness restart did not expose the backend listener reliably, so a final post-fix real-provider browser answer was not claimed.

## Product limitations to address next

1. Add a selected-chapter handoff from Writing directly into the appropriate existing revision/editor target.
2. Make historical Story Studio answers visibly historical and add a “current story state” refresh affordance.
3. Render object-shaped evidence in the same expandable author-facing format as list evidence.
4. Persist and surface a compact activity/recovery panel for enrichment and Story Studio jobs across reloads.
5. Add a dedicated author-facing context comparison showing what changed in memory after approval, without exposing internal collections.

## Explicitly unchanged

MongoDB authority, Canon Governance, Canon Proposal Queue, Decision History, Story Bible authority, Narrative Analysis Engine, shared narrative graph, chapter/scene lineage, Writer's Room, revision branches, Paragraph Editor, chronology safeguards, backup/recovery, provider gateway, publication governance, and TencentDB status were not replaced or expanded into parallel systems.

