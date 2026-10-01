# NovelForge Narrative Studio V2 - Phase 3C Agent Audit

Audit date: 2026-06-14

## Method

The audit reviewed agent definitions, authority instructions, orchestration
selection, bounded context, provider traces, deterministic validators, and the
final real-Gemini E2E runs.

## Authority Findings

- `StoryAuditorAgent` is read-only and produces findings only.
- `SceneWriterAgent` writes derivative scene prose but cannot change planning
  or approve drafts.
- `EditorAgent` and `DialogueAgent` analyze without rewriting.
- `RevisionAgent` creates an alternative branch and cannot replace approved
  source.
- `ManuscriptAgent` and `CanonAgent` review immutable records only.
- Deterministic services retain approval, validation, canon, manuscript,
  impact, and mutation authority.

No tested agent modified authoritative content outside its role.

## Recent Trace Sample

The latest 100 successful traces for the most relevant agents contained:

| Agent | Calls | Avg latency | Tokens | Cost | Retries | Fallbacks |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| SceneWriterAgent | 52 | 8,976 ms | 224,112 | $0.089644 | 0 | 0 |
| EditorAgent | 35 | 7,945 ms | 157,459 | $0.062983 | 0 | 0 |
| ManuscriptAgent | 5 | 4,414 ms | 5,815 | $0.002326 | 0 | 0 |
| CanonAgent | 5 | 4,143 ms | 7,339 | $0.002936 | 0 | 0 |
| StoryAuditorAgent | 3 | 5,325 ms | 23,676 | $0.009471 | 0 | 0 |

These measurements cover multiple validation projects and are operational
evidence, not a controlled model benchmark.

## Usefulness

`StoryAuditorAgent` added contextual observations to deterministic findings
without taking action. Editor, Manuscript, and Canon agents continued to
provide domain-specific review while deterministic services enforced truth.

## Hallucination And Schema Reliability

A statistically meaningful hallucination rate is not available from the
current sample. The system therefore uses measurable proxies:

- unsupported IDs fail deterministic continuity checks;
- cross-project IDs fail ownership checks;
- agents cannot directly mutate authority records;
- one real SceneWriter response omitted required prose despite valid JSON.

The empty-prose incident is now handled by one corrective retry. If the retry
also fails, the operation still fails visibly rather than saving an empty
draft.

## Redundancy

The strongest overlap is between deterministic story-quality findings and
agent editorial observations. This is acceptable when the UI clearly labels
the source. It becomes noise when both repeat the same warning without added
evidence.

Recommendation: deduplicate by category, subject, and evidence fingerprint
while retaining both deterministic and AI provenance.

## Token And Memory Efficiency

- Chapter intelligence replaces large historical prose blocks.
- Prompt context is capped at 30,000 serialized characters.
- Recent chapter memory and long-range obligations have separate limits.
- Explicit actions select one required agent and skip unrelated agents.
- Story Auditor does not write agent memory.

SceneWriter and Editor remain the largest token consumers. Their prompts
should be profiled against chapter length and report usefulness.

## Degradation Over Time

No context corruption or provider-output degradation was detected between the
early and late chapters in deterministic memory tests. The validation corpus
did expose repeated structural patterns, which is a story-generation quality
risk rather than a memory failure.

## Recommendations

- Add a human-rated agent benchmark set with usefulness, factuality, voice,
  and recommendation-novelty scores.
- Track corrected-schema responses as a first-class reliability metric.
- Deduplicate repeated recommendations across adjacent audit runs.
- Compare token cost against accepted findings, not raw output length.
- Add chapter-specific evidence links to every agent finding.
- Keep deterministic authority checks mandatory even when model confidence is
  high.
