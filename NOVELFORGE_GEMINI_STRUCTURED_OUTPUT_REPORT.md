# NovelForge Gemini Structured Output Report

## Live evidence

Gemini 3.1 Flash Lite successfully returned a structured RevisionAgent response for the humanization route in 6,550 ms. It also successfully returned an ordinary Story Studio response. Earlier lightweight planning-capture traces include a Gemini failure that safely used the existing OpenRouter fallback.

## Interpretation

Gemini is usable for simple validated responses, but reliability is task- and schema-dependent. The provider gateway continues to validate parsing and schema before acceptance. No schema weakening or bypass was added.

## Policy

Keep lightweight extraction/classification on the cheapest validated route. Escalate malformed, empty, low-confidence, or content-quality failures. Full-chapter humanization now uses strong Auto routing because the live quality result—not JSON compliance—was the limiting factor.

