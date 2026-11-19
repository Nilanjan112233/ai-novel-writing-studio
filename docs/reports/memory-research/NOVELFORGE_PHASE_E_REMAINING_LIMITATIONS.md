# Phase E Remaining Limitations

## 1. The broad provider baseline did not complete

Two real providers/attempt sequences were tried. The final matched Gemini broad run completed Relationship and failed on Character Journey after transient availability/quota errors. Therefore:

- complete legacy prompt size is measured by deterministic replay;
- complete legacy cost is projected with the same model pricing;
- legacy full-workflow latency is unavailable;
- provider failure is reported, not hidden.

## 2. Provider retries remain variable

The compact real workflow completed but required three transient retries. Packet reduction improves cost and request feasibility, but does not eliminate upstream 503/429 variability.

## 3. Role projection relevance is deterministic, not learned

Phase E uses explicit section manifests, status filters, field projections, limits, and exact/high-confidence deduplication. It does not implement BM25, new embeddings, RRF, graph candidate generation, or semantic consolidation.

## 4. Chapter intelligence can contain conflicting derived evidence

The five-year/two-year Elias discrepancy remains visible in derived chapter evidence. This is intentional evidence preservation: the authority snapshot wins and the prompt labels chapter intelligence as derived. Phase E does not rewrite or consolidate chapter intelligence.

## 5. Evidence expansion is reference-first but not tool-driven

Handoffs carry evidence references, and the role packet supplies bounded evidence. Specialists do not yet have a general on-demand evidence-expansion tool. Adding progressive fact-to-episode-to-prose retrieval belongs to Phase D, not Phase E.

## 6. Fallback remains expensive

Broad fallback is safe and observable, but it intentionally retains the old large packet when mandatory authority cannot fit compact mode. This prioritizes correctness. Large-authority projects should be monitored for fallback frequency before adjusting manifests or budgets.

## 7. Human literary scoring is limited

The quality gate covers required facts, authority, chronology, safety, role usefulness, and cross-agent consistency. It does not replace multi-author blind literary evaluation across genres.

## 8. Derived handoff rebuild is not exposed as a command

Handoffs are durable and idempotent. Full specialist outputs remain available, but there is not yet a dedicated operator command to reconstruct all historical handoffs. This is not an authority or resume blocker for new Phase E runs.
