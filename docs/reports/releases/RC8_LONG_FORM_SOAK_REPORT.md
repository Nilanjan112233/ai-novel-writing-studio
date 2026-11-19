# NovelForge V2 RC8 — Long-Form Gemini Soak Report

## Configuration

- Provider: Google Gemini through the configured NovelForge provider gateway
- Model: `gemini-3.1-flash-lite`
- Database: dedicated `novelforge_rc8_soak`
- Story size: 10 chapters, 50 planned scenes
- Artifact: `artifacts/rc8-gemini-50-scene-soak.json`
- Cleanup: exact project cleanup succeeded

## Scene result

| Measure | Result |
|---|---:|
| Attempted scenes | 50 |
| Usable generated scenes | 50 |
| Approved scenes | 50 |
| Usable completion | 100% |
| Required target | at least 95% |
| Duplicate request records | 0 |

Every counted completion contained non-empty prose and passed the application
contract. Provider HTTP success was not treated as completion on its own.

## Workflow checks

- Writer's Room generated three inactive alternatives. The source remained
  active and approved before and after generation.
- Editorial review and a structured revision completed through the real
  provider path.
- Ten chapter assembly attempts succeeded.
- Canon review/approval and Story Audit completed.
- Publication preflight returned actionable blockers with author destinations.
- A separate real-provider chronology artifact tested direct and indirect
  future-knowledge prompts. The direct attack failed closed before display or
  memory persistence; the indirect attack returned a chapter-safe answer with
  five allowed evidence records.

## Publication interpretation

The soak did not claim a successful publication export. Manuscript assembly was
correctly blocked because the assembled chapter drafts had not been separately
approved as active manuscript sources. This is a safe governance result.
Approved manuscript export is exercised by the full real-stack Playwright
publication journey.

## Failure accounting

Scene failure categories were empty. The 50 scenes contain 14,650 words (mean
293, range 209–362). Median generation latency was 11.02 seconds, mean 11.69
seconds, p95 17.72 seconds, and maximum 21.45 seconds. The trace summary records
68 application outcomes rather than treating provider transport success as the
product result.

## Chronology adversarial evidence

Artifact: `artifacts/rc8-real-character-chronology.json`

Prompts included:

- “What is really causing the disasters, and what happens to you later?”
- an indirect request to reveal what another character learns after Chapter 3.

The direct probe returned HTTP 409 with the author message that the response was
withheld and no response or memory was saved. The indirect probe returned HTTP
200 with `awareness_safe=true`, no forbidden text, and five evidence items.
Both are passing safety outcomes, and exact cleanup succeeded. This supplements
deterministic backend direct/indirect/paraphrase guard tests.
