# NovelForge Retrieval Ranking Bake-Off

## Method

The replay-only bake-off used identical Phase B-derived records and 15 labelled queries at every scale. Cases cover exact names, artifacts, places, promises, quoted clues, three paraphrases, a Chapter 1 callback, unresolved mystery state, historical/current ownership, Ivo/Mara knowledge boundaries, and rejected Story Studio history. Eligibility was applied before comparison; no provider generation was used.

The expanded corpus intentionally differs from the earlier six-query Phase B scale corpus. Therefore within-bake-off scores compare methods against each other, while production acceptance compares Phase C against the published Phase B baseline.

## 500-chapter bake-off

| Method | Recall@8 | MRR | Mean records scored | Result |
|---|---:|---:|---:|---|
| Current Phase B ranker | 0.5714 | 0.4226 | 2,187.13 | poor expanded-corpus ranking |
| BM25 lexical | 1.0000 | 0.8238 | 2,187.13 | accurate, still linear in replay |
| Hash vector | 0.5000 | 0.3810 | 2,187.13 | inadequate alone |
| Story metadata | 0.5000 | 0.4286 | 2,187.13 | useful signal, inadequate alone |
| Lexical + metadata + hash | 1.0000 | **0.8452** | **1.93** | winner |
| Full RRF | 1.0000 | 0.7381 | 2,187.13 | worse and expensive |
| Winner + graph | 1.0000 | 0.8452 | 1.93 | no graph gain |
| MiniLM semantic | 1.0000 | 0.8333 | 2,187.13 | good recall, high operating cost |
| Lexical + semantic + metadata RRF | 1.0000 | 0.7500 | 2,187.13 | fusion regression |

The selected weighted fusion beat all single paths on combined MRR and candidate work. RRF was not selected merely for being a standard fusion technique.

## Query-family findings

At 500 chapters, BM25 exact-name Recall/MRR was 1.0/1.0 versus 0.8/0.8 for the current ranker. The selected fusion retained 1.0 paraphrase recall with 0.8333 paraphrase MRR. MiniLM also reached 1.0 paraphrase recall but only 0.4444 paraphrase MRR on these labelled cases.

Long-range facts were not recency-demoted: the Chapter 1 funeral-bell callback was recovered in a 500-chapter corpus. Temporal state and knowledge cases passed because P0 eligibility operates before ranking.

## Production gate

Production was switched only after the replay winner passed the gate. The Mongo production path then independently measured Recall@8 1.0, MRR 0.8111, and P95 61.175 ms at 500 chapters with zero leakage and duplicates. Machine evidence is in `artifacts/memory-phase-c/bakeoff.json` and `production-scale.json`.
