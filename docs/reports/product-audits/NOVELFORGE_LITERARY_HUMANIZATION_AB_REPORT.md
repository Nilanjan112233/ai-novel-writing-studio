# NovelForge Literary Humanization A/B Report

Date: 2026-08-11

## Test

The same approved Chapter 1 and equivalent humanization instruction were sent through real providers. Neither revision was applied; all outputs remained protected Editorial alternatives.

## Results

| Route | Result | Cost/latency evidence |
|---|---|---|
| Gemini 3.1 Flash Lite | Fast, but reduced the 1,492-word source to 532 words; rejected by the new gate | 6,550 ms; about $0.003832 |
| DeepSeek V4 Flash | Preserved the chapter as a 1,392-word alternative with the same core mystery and ending | 34,461 ms; about $0.012077 |
| Gemini selected, guarded | Gemini produced a 404-word collapse; it was not persisted and escalated to DeepSeek, which produced a 1,205-word protected alternative | Gemini about $0.004522 plus DeepSeek about $0.016397; DeepSeek retry after an empty response |
| Auto after routing change | Directly selected DeepSeek for the full chapter and produced a 1,415-word protected alternative | 66,472 ms; about $0.018148 |

## Implementation decision

The quality gate rejects chapter-level humanization below 72% of the source word count (for sources of at least 500 words). Auto now routes full-chapter humanization directly through the strong editorial tier. Lightweight humanization remains available for short excerpts, while explicit lightweight choices are still guarded and escalated.

This is a literary-quality decision, not an AI-detector-evasion feature. The author must still review and apply any revision.
