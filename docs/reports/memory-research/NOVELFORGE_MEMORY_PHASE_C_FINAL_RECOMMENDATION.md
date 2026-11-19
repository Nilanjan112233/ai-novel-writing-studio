# NovelForge Memory Phase C Final Recommendation

## Decision

**KEEP PHASE C PRODUCTION RANKING. STOP BEFORE PHASE D.**

The selected metadata-narrowed lexical + existing-hash + story-metadata ranker meets the gates with substantially better 250/500 MRR and latency, non-inferior Recall@8 at every scale, zero safety leakage, zero logical duplicates, preserved Phase B compactness, preserved Phase E role quality, bounded Phase A mutation integration, and a tested complete Phase B fallback.

## Answers

1. **Which approach won?** Metadata/domain narrowing, Mongo lexical candidates, then weighted BM25 (`0.48`) + existing hash (`0.30`) + story metadata (`0.22`).
2. **Recall improvement?** At 500 chapters, 0.8333 to 1.0000: +0.1667 absolute, +20.0% relative.
3. **MRR improvement?** At 500 chapters, 0.6905 to 0.8111: +0.1206 absolute, +17.47% relative. At 250, 0.6944 to 0.8111: +0.1167.
4. **500-chapter P50/P95?** 47.115/61.175 ms cold; 7.727/8.812 ms warm. Phase B was 492.301/621.363 ms.
5. **Records scored?** 1.93 eligible records/query mean from 2.27 raw candidates out of 2,522 indexed rows.
6. **Index storage?** 1,214,800 bytes of lexical row payload at 500 chapters; clean benchmark Mongo index allocation 61,440 bytes (page-granular total-index figure).
7. **Does lexical help exact callbacks?** Yes. Exact-family Recall/MRR improved from 0.8/0.8 for the current replay ranker to 1.0/1.0.
8. **Does semantic help paraphrases?** It recovered them, but ranked them worse than the selected method and added ~92 MB plus 9.1 s startup and 11.9 s corpus encoding. It is not justified for production now.
9. **Does graph relevance justify complexity?** No. It changed neither Recall nor MRR in the labelled corpus.
10. **Does fusion beat a single path?** Weighted fusion delivered the best overall MRR. RRF did not.
11. **Discovery regression?** No. Recall/MRR stayed 1.0/1.0; tokens fell 917 to 316 and latency 48.7 to 27.209 ms.
12. **Develop Story regression?** Authority/role quality did not regress; prompt tokens fell 5.49% and latency fell 15.63%. The one real run cost 18.14% more because responses were longer, which is reported as a cost regression rather than hidden.
13. **Authority/chronology/knowledge leakage?** None measured. All P0 leakage metrics remain zero.
14. **Operational cost?** No provider/service/model dependency; ~1.21 MB row payload at 500 chapters, 186.903 ms one-time index build, 80.948/101.674 ms changed-row P50/P95, 2.321 ms unchanged no-op.
15. **Is Phase D justified?** Not yet as an automatic next step. Ranking is no longer the primary bottleneck, Discovery is already compact, and Develop Story evidence fell only another 7.34%. Phase D should begin only with a labelled evidence-expansion corpus proving that fact-first retrieval can reduce the remaining 13,810 Develop Story evidence tokens without lowering evidence quality.

## Recommended next pass

First run a read-only Phase D readiness study, not implementation. Label which specialist answers can be satisfied by atomic facts alone, which require episode context, and which require prose evidence. Measure evidence sufficiency, expansion frequency, hallucination/contradiction detection, and quality before adding progressive tool calls.

If the study supports Phase D, implement it behind the same Phase B fallback and Phase C attribution. Preserve current authority snapshots, role manifests, and deterministic compact memory. Do not add a semantic model, graph database, Tencent authority, new Story Bible, preference memory, or a destructive cleanup based on these results.

Tencent remains optional/experimental and has no production role in Phase C.
