# NovelForge Matched Cost Before/After Report

Date: 2026-08-11

## Matched live sample

The same Chapter 1 humanization instruction was run against equivalent source prose.

- Gemini lightweight: approximately $0.003832, 6.55 seconds, but failed the chapter-preservation quality gate at 532 words.
- DeepSeek strong: approximately $0.012077, 34.46 seconds, and produced a 1,392-word reviewable alternative.
- Guarded Gemini plus escalation: approximately $0.020919 combined, with a 404-word Gemini candidate rejected and a 1,205-word DeepSeek result accepted after one provider empty-response retry.

The raw lightweight path is about 68% cheaper than the direct strong call, but it is not an acceptable Auto choice for this full-chapter task. The guarded two-call path is more expensive than direct strong generation. Therefore Auto was changed to use the strong editorial tier directly for full-chapter humanization; lightweight remains appropriate for short excerpts and routine structured tasks.

## Other live routing

- A real Gemini Story Studio response was about $0.003892.
- A real DeepSeek Story Studio response recorded about $0.007032.
- After the routing change, a real Auto full-chapter humanization trace selected OpenRouter/DeepSeek directly and produced 1,415 words at about $0.018148, without a lightweight pre-call.
- The real targeted development run used five DeepSeek specialists with roughly 68k–75k billed tokens per call, confirming context duplication as the largest current cost opportunity.

This is measured evidence from the local execution traces, not a universal provider price claim.

## Measured provider mix in the live audit window

Across 37 relevant traces after 09:00, 28 used OpenRouter/DeepSeek (75.7%) and 9 used Gemini 3.1 Flash Lite (24.3%). The aggregate estimated trace cost was $0.685111, dominated by the five-agent development run; this is an audit-window total, not a per-chapter price.
