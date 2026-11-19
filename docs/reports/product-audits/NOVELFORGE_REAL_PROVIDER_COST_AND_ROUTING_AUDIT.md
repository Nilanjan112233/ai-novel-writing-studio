# NovelForge Real Provider Cost and Routing Audit

## Scope and accounting note

All core calls used the real NovelForge gateway. No mocked AI responses were used for the main journey. Costs below use the application's recorded `cost_usd` where a central execution trace exists. Discovery writing stores a separate `tokens_used` field in chapter metadata but its provider traces were not attached to the project in the central trace listing, so writing costs are labeled estimated.

## Provider/model breakdown

| Workflow | Calls | Provider/model | Tokens | Recorded/estimated cost | Retries/fallback |
|---|---:|---|---:|---:|---|
| Story Studio provider turns | 3 real AI + 1 deterministic review | Gemini / `gemini-3.1-flash-lite` | 5,598 real AI tokens | estimated .005598 | no fallback in job metadata |
| Develop Story | 18 | OpenRouter / `deepseek/deepseek-v4-flash` | 730,627 | recorded .730627 | retries on several agents; no fallback |
| Unique Chapters 1–10 | 10 | OpenRouter / `deepseek/deepseek-v4-flash` | 167,087 | estimated .167087 | no central trace; chapter metadata has latency/tokens |
| Raw chapter calls including duplicate Ch4 | 11 | OpenRouter / `deepseek/deepseek-v4-flash` | 185,262 | estimated .185262 | duplicate caused by delayed completion/retry |
| Editorial review | 2 | OpenRouter / `deepseek/deepseek-v4-flash` | 12,870 trace tokens | recorded .012870 | one call recorded retry 1 |
| Whole-chapter revision failure | 1 | OpenRouter / `deepseek/deepseek-v4-flash` | 5,960 prompt-only tokens | recorded .005960 | retry count 2; invalid JSON; no output |
| Selection revision | 1 | OpenRouter / `deepseek/deepseek-v4-flash` | 7,531 trace tokens | recorded .007531 | successful |

The editorial/revision central trace total is `$0.026361`. The unique-path experiment estimate is approximately `$0.929673` (`.005598 + .730627 + .167087 + .026361`). Including the duplicate Chapter 4 generation, the estimate is approximately `$0.947848`.

The chapter metadata's `tokens_used` differs from central trace `total_tokens` conventions on some editorial calls. This is why the report preserves both recorded and estimated labels rather than presenting a false single precision total.

## Routing assessment

Story Studio correctly routed the conversational work to the lightweight Gemini model, and its job metadata recorded the task tier as cheap. Develop Story routed all specialist work to DeepSeek V4 Flash, including very large context-heavy planning agents. Chapter drafting, editorial, and revision also used DeepSeek V4 Flash.

The audit does not support changing routing blindly. The primary problem was not that writing used a strong model; it was that the context was wrong and the lifecycle allowed unsafe drafts. Safe routing opportunities are:

- deterministic state/approval/duplicate detection should remain code, not an AI call;
- Story Studio intent classification and simple confirmation bookkeeping should be deterministic or lightweight;
- large specialist cycles should be opt-in after the author confirms a foundation;
- continuity preflight can be a small structured check before spending a full drafting call;
- full literary revision should remain a strong-model task only after the protected path is reliable.

## Observability defects

The Story Studio jobs expose real provider metadata and execution trace IDs, but the central project trace endpoint did not return those job traces. Chapter drafts expose real writer provider metadata, but their calls were also absent from the project-filtered central execution trace list. This makes cost/retry/fallback accounting harder than it should be.

The application therefore passed through real calls but did not provide one auditable trace ledger for the full experiment. That is a product observability defect, not evidence that the calls were mocked.

