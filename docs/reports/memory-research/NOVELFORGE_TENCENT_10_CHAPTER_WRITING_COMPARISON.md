# Ten-Chapter Real Writing Comparison

## Real corpus

The dedicated NovelForge project now contains ten approved chapters. Chapters 7–10 were generated through the actual Discovery Writing endpoint, reviewed, approved through the normal `review → approved` lifecycle, and enriched. Their word counts were 1,433, 1,337, 1,480, and 1,383; all met the 1,000-word floor. All four used OpenRouter DeepSeek V4 Flash for prose. The first six chapters were already real approved-provider output.

The ten approved texts were captured once into a clean Tencent test index. No MongoDB story authority was modified by the Tencent capture.

## Matched Chapter 11 observation

The same Chapter 11 instruction and the same DeepSeek V4 Flash writer were used. Only the retrieved memory arm changed.

| Arm | Memory tokens | Writer prompt tokens | Total tokens | Estimated cost | Latency | Words |
|---|---:|---:|---:|---:|---:|---:|
| Native | 4,972 | 5,249 | 7,248 | $0.007248 | 28.7 s | 1,464 |
| Tencent | 8,967 | 10,056 | 11,561 | $0.011561 | 61.1 s | 1,096 |
| Hybrid | 13,939 | 15,131 | 16,427 | $0.016427 | 54.1 s | 948 |

The application execution trace records the estimated costs. Tencent cost was 59.5% above Native for this matched call; Hybrid was 126.6% above Native. Hybrid also fell below NovelForge’s 1,000-word acceptance floor in this observational request. Callback checks were mixed: Native preserved the left-palm/Elias thread, Tencent surfaced Northglass/third-bell/Elias, and Hybrid surfaced all sampled terms but produced the shortest output. No arm is a demonstrated literary-quality winner.

This is a controlled memory/context comparison, not a claim of professional literary ranking; prose was not blind-rated by an independent panel.

