# NovelForge Semantic Retrieval Report

## Evaluation

The existing hash vector is not semantic. A real local `sentence-transformers/all-MiniLM-L6-v2` path was evaluated offline against the same eligible Phase B records. It was bake-off only and was not added to application requirements or production startup.

Measured costs on the local machine:

- Python/model startup: 9,133.36 ms;
- cached model size: 91,578,407 bytes;
- encoding 2,522 records at 500 chapters: 11,872.995 ms;
- records semantically scored/query in the replay: about 2,187 eligible rows.

At 500 chapters semantic retrieval reached Recall@8 1.0 and MRR 0.8333. It helped paraphrase recall, but the selected lexical/metadata/hash approach reached the same overall recall, higher MRR in the bake-off (0.8452), and bounded candidate work without a model runtime.

Lexical + semantic + metadata RRF reduced MRR to 0.7500. More signals did not improve ranking.

## Decision

Do not ship a semantic model in Phase C. The local model adds about 92 MB, multi-second cold startup/encoding, dependency complexity, RAM pressure, and mutation-time encoding without beating the simpler winner. No paid Gemini/DeepSeek embedding path was used.

Semantic retrieval remains a possible later experiment only if a broader paraphrase corpus demonstrates misses that lexical expansion and story metadata cannot solve. Such a future experiment must use bounded candidates, not full-corpus semantic scoring.
