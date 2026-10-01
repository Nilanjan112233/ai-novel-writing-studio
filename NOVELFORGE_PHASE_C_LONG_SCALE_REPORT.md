# NovelForge Phase C Long-Scale Report

The provider-free production-path corpus used the same 10/25/50/100/250/500 scale progression plus exact, paraphrase, long-range, mystery, temporal, knowledge, and Story Studio rejection cases.

| Chapters | Records | Recall@8 | MRR | Precision@returned≤8 | Cold P50 | Cold P95 | Warm P50 | Warm P95 | Raw candidates | Eligible scored |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 | 72 | 1.0000 | 0.7778 | 0.4806 | 8.747 ms | 10.462 ms | 4.325 ms | 5.082 ms | 3.60 | 3.33 |
| 25 | 147 | 1.0000 | 0.8111 | 0.5722 | 9.669 ms | 10.726 ms | 3.255 ms | 4.795 ms | 2.27 | 1.93 |
| 50 | 272 | 1.0000 | 0.8111 | 0.5722 | 10.138 ms | 11.813 ms | 4.578 ms | 5.080 ms | 2.27 | 1.93 |
| 100 | 522 | 1.0000 | 0.8111 | 0.5722 | 13.304 ms | 18.486 ms | 3.831 ms | 4.898 ms | 2.27 | 1.93 |
| 250 | 1,272 | 1.0000 | 0.8111 | 0.5722 | 31.602 ms | 41.499 ms | 6.536 ms | 7.932 ms | 2.27 | 1.93 |
| 500 | 2,522 | 1.0000 | 0.8111 | 0.5722 | 47.115 ms | 61.175 ms | 7.727 ms | 8.812 ms | 2.27 | 1.93 |

The benchmark was refreshed after final filtering/cache changes. Cold latency includes Mongo checkpoint and candidate work; warm latency uses the revision-keyed bounded candidate cache. No provider call occurred.

## Baseline comparison

At 250 chapters, MRR rises from 0.6944 to 0.8111 and P95 falls from 140.512 to 41.499 ms. At 500 chapters, MRR rises from 0.6905 to 0.8111 and P95 falls from 621.363 to 61.175 ms. Recall rises from 0.8333 to 1.0 at both scales.

Small synthetic MRR is not claimed as improved: the old Phase B 10-chapter MRR was 1.0, whereas the expanded Phase C corpus is 0.7778. This reflects equivalent atomic/owner representations ahead of the labelled logical owner in a very small corpus. Recall remains 1.0, and the real Discovery case remains rank-perfect.

## Safety and long-range behavior

Every scale had zero unsafe leakage and zero duplicate logical hits. The Mara knowledge query scored zero eligible rows; the Ivo query retrieved his private fact. Historical/current Northglass ownership selected the correct temporal value. The Chapter 1 callback remained retrievable at Chapter 500.

Machine-readable evidence: `artifacts/memory-phase-c/production-scale.json`.
