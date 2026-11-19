# Final TencentDB Agent Memory Recommendation

## Decision: KEEP NATIVE DEFAULT; TENCENT OPTIONAL/EXPERIMENTAL

Tencent retrieval is now genuinely operational and passes the 10/10 smoke gate. That is sufficient to keep the adapter and allow controlled developer experiments, but not sufficient to promote it:

- Native and Tencent both recalled 8/8 labeled facts in the ten-chapter comparison, but Tencent was about 4.9x slower and returned about 2.2x the estimated context tokens.
- Hybrid returned the most context and cost the most; it did not improve measured recall.
- The real matched DeepSeek writing call was cheapest with Native and produced an accepted-length result. Tencent and Hybrid increased cost; Hybrid fell below the 1,000-word floor.
- Tencent can surface stale and rejected L0 observations. NovelForge safe writing correctly keeps Native primary and prevents those observations from becoming authority.
- Chronology remained safe because NovelForge, not Tencent, enforced the primary packet boundary.
- Native remained available during a real Tencent outage.

Tencent should not become default or writing-primary. Reconsider only after enabling a supported semantic/L1 extraction path, adding compact provenance-preserving retrieval, and passing a new long-conversation plus 10/25/50/100 scale study with lower important-memory miss rate, no stale/rejected/chronology leakage, comparable prose continuity, and a measurable context-cost benefit.

