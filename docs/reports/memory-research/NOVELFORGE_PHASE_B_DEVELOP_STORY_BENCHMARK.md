# NovelForge Phase B Develop Story Benchmark

## Matched method

The Phase B run used the same source project, instruction, five specialists, provider (`gemini`), model (`gemini-3.1-flash-lite`), role manifests, and delta handoffs as the Phase E benchmark. It was run through the real provider.

## Results

| Metric | Phase E | Phase B |
|---|---:|---:|
| Prompt tokens | 33,551 | 23,622 |
| Response tokens | 4,267 | 3,472 |
| Estimated provider cost | $0.015127 | $0.010837 |
| Wall latency | 145.141 s | 56.676 s |
| Retries | 3 | 0 |
| Model fallbacks | 0 | 0 |

Evidence-layer reduction was 38.65%; total prompt reduction was 29.59%. All five role requirement checks passed, all five packets retained complete authority, Chapter 10 boundaries remained in all outputs, chronology authority was present in every packet, and same-cycle handoffs remained visible.

The first Phase B run is retained as `phase-b-provider-run-first-attempt.json`. It reduced total prompt to 29,935 but missed the evidence gate because the prompt still serialized the full episode object. The corrected run is the reported result.
