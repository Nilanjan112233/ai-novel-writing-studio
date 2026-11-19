# NovelForge Narrative Studio V2 - Phase 3C Memory Audit

Audit date: 2026-06-14

## Result

Passed.

## Memory Layers

NovelForge now separates:

- recent active context;
- deterministic working memory;
- retrieved indexed memory;
- compressed agent memory;
- important agent memory;
- recent agent memory;
- chapter intelligence;
- old unresolved chapter obligations;
- active canon authority.

Agents no longer need unrestricted historical chapter prose to recall story
state.

## Long-Range Assertions

The 50-chapter validation corpus verified:

- Chapter 45 is present in current chapter intelligence.
- Chapter 50 is present in current chapter intelligence.
- Chapter 4 still carries the obligation to return the broken bell clapper
  before the thaw vote.
- Chapter 9 still carries the obligation to tell Soren who ordered the
  dockworkers' oath erased.
- Both old obligations remain visible after more than 40 later chapters.

## Bounded Context

The default chapter memory packet uses:

- up to 10 recent chapter-intelligence records;
- up to 12 unresolved long-range obligations.

Story Auditor requests a larger but still bounded packet. Serialized prompt
context is rejected above 30,000 characters.

## Compression

Chapter intelligence preserves explicit facts and obligations before prose
compression occurs. This reduces the risk that summarization removes a small
but important promise.

The tests verified retention of selected obligations, not perfect semantic
retention of every possible detail. Compression should remain subordinate to
canon and structured intelligence.

## Retrieval Quality

Chapter intelligence is indexed with source type and project ownership.
Agents receive records relevant to their current task plus recent and
important memory.

Current retrieval remains primarily lexical and structured. It is reliable for
stable names, IDs, and explicit obligations, but paraphrased thematic recall
needs a human-rated retrieval benchmark.

## Canon Memory

Active canon records remain separate from chapter summaries and are supplied
as binding context. The production corpus reported:

- canon conflicts: 0;
- continuity warnings: 0.

## Failure Modes Checked

- old obligation dropped after many chapters: not observed;
- recent chapter missing: not observed;
- project ID omitted from memory query: not observed;
- full historical prose copied into every prompt: prevented;
- Story Auditor writing agent memory: prevented;
- chapter approval without intelligence: covered by regression and backfill.

## Residual Risks

- vague promises that are never represented as explicit obligations can still
  be missed;
- aliases and renamed characters need stronger entity resolution;
- semantic retrieval quality is not yet scored against a gold set;
- direct database imports used by the scale script do not exercise every
  normal approval event, although API and service regressions cover that path.

## Recommendation

Create a permanent 100-question memory benchmark across multiple genres. Each
question should identify the expected chapter-intelligence record, canon
record, and evidence span, then measure precision, recall, token cost, and
cross-project false positives.
