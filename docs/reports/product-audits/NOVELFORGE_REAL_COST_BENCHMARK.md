# NovelForge Real Cost Benchmark

## Measured live baseline

The real one-chapter workflow in the dedicated validation project used the provider gateway and recorded these calls:

| Operation | Provider/model | Total tokens | Recorded cost |
|---|---|---:|---:|
| Chapter prose | OpenRouter / DeepSeek V4 Flash | 3,143 | 0.003143 |
| Range correction | OpenRouter / DeepSeek V4 Flash | 2,515 | 0.002515 |
| Range continuation | OpenRouter / DeepSeek V4 Flash | 2,367 | 0.002367 |
| Approved extraction after Gemini failure | OpenRouter / DeepSeek V4 Flash | 3,585 | 0.003585 |
| Gemini extraction attempt | Gemini 2.5 Flash | 2,368 | 0.000947 |
| Story planning fallback | OpenRouter / DeepSeek V4 Flash | 323 | 0.000323 |
| Story Studio answer | Gemini 2.5 Flash | 1,471 | 0.000588 |

The observed subtotal is approximately `0.013468` in the gateway's recorded USD field for those seven traces. It is a measured baseline, not a promise of provider billing equivalence.

## Routing change

The current source routes lightweight tasks to the configured Gemini model first and escalates when schema/quality validation fails. The live trace after configuration shows Gemini 3.1 succeeding for a Story Studio assistant task and a structured planning attempt safely escalating when JSON validation failed.

## Honest conclusion

This pass establishes the routing behavior and its safety, but it does not claim a percentage cost reduction because a matched before/after benchmark for extraction, humanization, brainstorming, and final prose was not rerun after the source restart. Final prose remains on the strong model; inexpensive tasks are eligible for cheaper routing without weakening validation.

