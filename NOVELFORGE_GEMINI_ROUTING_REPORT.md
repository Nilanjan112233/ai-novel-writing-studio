# NovelForge Gemini and Lightweight Routing Report

## Current routing

Task routing remains inside the existing provider gateway. Deterministic application data is not sent to a model. Lightweight work uses the configured Gemini model when available; the current saved configuration is `gemini-3.1-flash-lite`. Humanization is now classified as a lightweight task with gateway fallback. Strong routing remains available for final prose, difficult continuity, and high-value revisions.

## Real provider evidence

The running application has a live Gemini configuration validated through the UI: the key validated, model discovery returned 20 models including `gemini-3.1-flash-lite`, and the selected-model test reported online/working with approximately 1.58 seconds latency.

Current execution traces also show a real `ProjectAssistant` call on `gemini-3.1-flash-lite` succeeding with 9,796 total tokens, 2,336 ms latency, and recorded cost `0.003918` in the gateway's accounting unit.

The same trace history records `StoryPlanningCapture` on Gemini 3.1 failing strict JSON validation after retries, then succeeding on OpenRouter DeepSeek V4 Flash with fallback marked true. This is safe escalation, not validation weakening. It means Gemini structured-output reliability is improved in model selection but not yet universally solved; schema/prompt simplification remains a follow-up.

## No credential exposure

Credentials were used through the existing AI settings/provider gateway and are not stored in source, logs, URLs, or this report.

