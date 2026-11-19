# NovelForge Real Model Routing and Cost Report

## Live routing

All 16 measured real-provider requests in the validation window used OpenRouter / `deepseek/deepseek-v4-flash`: six writer calls, two range editors, six extraction calls, and two Story Studio assistant calls. Gemini was configured but was not needed because the selected OpenRouter route succeeded; no strong-model downgrade was made for final prose.

| Operation | Requests | Tokens | Estimated cost |
|---|---:|---:|---:|
| Discovery writing | 6 | 28,744 | $0.028744 |
| Range correction | 2 | 7,393 | $0.007393 |
| Approved-prose extraction | 6 | 22,007 | $0.022007 |
| Story Studio | 2 | 1,960 | $0.001960 |
| **Total** | **16** | **60,104** | **$0.060104** |

There were three recorded retries, including a real empty-response/timeout-style extraction retry that later succeeded. The largest measured call was 6,812 tokens. The measured average across the six approved chapters, including Story Studio, was about $0.010 per chapter under the application’s current estimate.

## Routing judgment

The existing gateway, task metadata, validation, and failover path are reusable. The next cost optimization should route deterministic work to code, extraction/classification to a verified lightweight model, ordinary brainstorming to a cheap capable model, and final prose/complex continuity to a strong model. Validation and escalation must remain mandatory. This live run did not provide comparative Gemini evidence, so savings from a cheaper extraction route are a recommendation, not a measured result.

