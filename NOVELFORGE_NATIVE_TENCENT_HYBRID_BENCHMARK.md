# Native vs Tencent vs Hybrid Benchmark

## Matched recall

The same eight labeled queries were run against the ten-approved-chapter real project. The simple labeled relevance rule required a known story marker in at least one returned hit; all three modes recalled 8/8 labeled facts.

| Mode | Recall | Mean precision | Mean latency | Mean estimated context |
|---|---:|---:|---:|---:|
| Native | 8/8 | 0.90 | 84.1 ms | 4,198 tokens |
| Tencent | 8/8 | 0.90 | 413.1 ms | 9,331 tokens |
| Hybrid | 8/8 | 0.90 | 413.1 ms | 13,529 tokens |

Tencent hits had provenance on all 8 queries. MRR was not calculated in this pass; the run records first relevant rank and provider hit lists for later replay.

## Interpretation

Tencent is useful now in the narrow sense that it returns real, scoped evidence. It is not an efficiency improvement in this configuration. Its L0 fallback returns full prose messages, so the packet is roughly 2.2x Native for Tencent and 3.2x Native for Hybrid. Hybrid deduplication removes identical content hashes but cannot collapse semantically overlapping Native and Tencent representations.

Native remains the safer and faster writing context. Experimental Tencent comparison is retained, but no Tencent packet is allowed to replace Native authority.

