# NovelForge Full Regression Report

Date: 2026-08-11

## Completed groups

The repository-wide direct command `py -3.11 -m pytest backend/tests -q` was allowed to run for 604 seconds but timed out without a completion result. It is not marked passed.

The same backend tests were then run in bounded groups:

- writing/Story Studio/Editorial/Drafting: 26 passed;
- Story Knowledge/Narrative Intelligence/Story Health: 16 passed;
- provider gateway/discovery/recovery: 15 passed, 6 skipped;
- orchestration/workflow/canon/regression: 31 passed, 1 skipped;
- API/manuscript/backup/RC8/RC9/paragraph and product groups: 88 passed.

Split total: 176 passed, 7 skipped. Focused post-change runs added 9 Story Studio tests and 14 Story Studio + Editorial tests, all passing. The skipped tests are provider/environment-gated tests already marked skipped by the suite.

Frontend validation: 23 test files and 87 tests passed. Production `next build` passed after the final frontend changes.

## Limitation

Because the one-shot backend command timed out and the final small routing/recovery edits were followed by focused rather than another 10-minute whole split, the strongest accurate status is “split regression passed; direct aggregate timeout,” not an unconditional full-suite pass.

