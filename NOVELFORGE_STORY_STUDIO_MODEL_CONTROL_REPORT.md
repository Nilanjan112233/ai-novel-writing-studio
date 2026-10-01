# NovelForge Story Studio Model Control Report

Date: 2026-08-11

## Result

Story Studio now exposes a clean response-model selector with `Auto (recommended)`, discovered configured models, and a per-message scope. The selector controls the primary conversational response only; extraction, validation, and other utility work remain task-routed.

## Evidence

- Browser acceptance showed `Auto (recommended)`, `Gemini 3.1 Flash Lite`, and `DeepSeek: DeepSeek V4 Flash 0423`.
- A real Story Studio request explicitly selected DeepSeek. The trace recorded OpenRouter/DeepSeek, task `story_studio`, a cheap tier, and the author-selection routing reason.
- A real Story Studio request explicitly selected Gemini. The trace recorded Gemini 3.1 Flash Lite, 3,472 ms latency, and $0.003892 estimated cost.
- A final real Auto full-chapter humanization request selected OpenRouter/DeepSeek directly after the routing refinement; the protected result was 1,415 words with no lightweight pre-call.
- The existing provider gateway and model registry remain the only provider path.

## Policy

`Auto` is still the default. Explicit model choice is an author preference, not a replacement for utility routing. Full-chapter humanization now routes Auto to the strong editorial tier after live evidence showed the lightweight model could collapse a chapter into a summary; an explicitly selected lightweight model remains allowed but is quality-gated and escalated safely.
