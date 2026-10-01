# TencentDB Agent Memory Benchmark

## Result

The Tencent local gateway was started from the official npm package in standalone mode on `127.0.0.1:8420` with embedding/extraction disabled and keyword configuration. The gateway health endpoint reported `status: ok`, `vectorStore: true`, `embeddingService: false`, and a healthy pipeline worker.

It accepted all six approved chapters from the dedicated six-chapter project as derived capture records (`l0_recorded: 2` per chapter; 6/6 successful). It also accepted Story Studio conversation/development captures while benchmark mode was enabled.

However, six direct Tencent recall queries returned `code: 0`, `memory_count: 0`, and empty context. The search endpoint tested for conversations returned 404 in this local gateway configuration. This means capture reachability was successful, but useful recall was not.

## Matched recall comparison

| Metric | Native | Tencent |
|---|---:|---:|
| Queries | 8 | 8 |
| Non-empty recalls | 8 | 0 |
| Hits | 40 | 0 |
| Average latency | 218.8 ms | 303.1 ms |
| Average context estimate | 1,613.2 tokens | 0 |

The zero Tencent context is not a cost win: it is a retrieval failure for the tested deployment. It cannot support a writing-quality comparison because it supplied no story facts.

## Interpretation

Tencent is not recommended as the default or as a writing-context primary. The integration is retained as an experimental adapter so a supported embedding/FTS configuration can be evaluated without touching authority systems. The next Tencent benchmark must repeat the same labeled query set after retrieval is genuinely populated.
