# NovelForge UX Polish: Activity and Post-Approval Context

## Implemented

- Added a compact `writing-activity` projection over durable Story Studio jobs, Narrative Analysis jobs, and approved-chapter enrichment states.
- Writing surfaces show running or failed activity with author language and explicitly state when approved prose is safe.
- Added `What changed after approval` to chapter context.
- The comparison shows prior derived context, new candidate information, candidate status, canon-change status, open threads, and next-chapter influence.
- Existing extraction, chapter intelligence, context packets, and canon proposal records remain the data sources.

## Safety

The projection never promotes candidates to canon and does not expose MongoDB IDs or internal collections. A failed enrichment record cannot make already-approved prose appear unsafe.

## Known limitation

The current project has no active background job at validation time, so the browser could verify the projection endpoint and normal idle state but did not force a costly real chapter approval solely to manufacture a failure state.

