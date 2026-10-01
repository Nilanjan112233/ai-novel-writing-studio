# TencentDB Agent Memory Recommendation

## Recommendation: KEEP NATIVE DEFAULT; TENCENT OPTIONAL/EXPERIMENTAL

Tencent should not become NovelForge’s default memory provider based on this run. The official local gateway was integrated cleanly and accepted derived captures, but it returned zero memories for all six long-horizon queries and all eight matched recall queries. Native returned relevant hits for 8/8 matched queries, five per query, at lower average latency (218.8 ms vs 303.1 ms).

## Answers to the requested questions

1. **Old story details better?** Not demonstrated; Native was useful, Tencent was empty.
2. **Less irrelevant context?** Not measurable because Tencent supplied no context.
3. **Lower tokens?** Not proven; zero tokens represented zero recall, not compression.
4. **Lower provider cost?** Not proven; capture and gateway overhead still exist, and useful Tencent context was absent.
5. **Better Story Studio discussion memory?** Capture works, useful recall is unproven.
6. **Rejected brainstorming leakage?** No leakage was introduced; full comparative rate is deferred until Tencent recall works.
7. **Superseded facts?** NovelForge authority ordering remains safe; Tencent was not allowed to override it.
8. **Chronology safe?** Yes in the tested path because Tencent is untrusted and writing remains Native-primary; Tencent-specific recall safety still requires a populated test.
9. **Better chapter continuity?** Not demonstrated.
10. **Less recap/repetition?** Not demonstrated.
11. **10/25/50/100 chapters?** Native six-chapter evidence exists; Tencent long-horizon comparison is blocked by empty recall and must not be fabricated.
12. **Latency?** Tencent recall averaged 303.1 ms in the matched run; Native 218.8 ms.
13. **RAM/disk?** One local gateway sample was ~434 MB working set/~470 MB private memory; small local SQLite/WAL files were observed. This is not a production estimate.
14. **Develop Story?** Dual capture is wired; improvement is unproven.
15. **Narrative or workflow memory?** Tencent is currently a better candidate for future workflow/history experiments than narrative authority, but even that needs populated recall evidence.
16. **Hybrid better?** Not demonstrated.
17. **Can it fail safely?** Yes; real failure recorded and Native continued.
18. **Default/optional/hybrid/remove?** Keep Native default, Tencent optional experimental, with Native fallback; do not remove the adapter yet.

## What is required before reconsidering the default

Upgrade the local runtime to the documented Node version, configure a supported FTS or embedding retrieval path, repeat the labeled 10-chapter comparison, then add 25/50/100 synthetic scale tests and matched prose review. Adoption requires measured continuity parity or improvement, lower important-memory misses, no stale/rejected/chronology regressions, and a meaningful efficiency benefit.
