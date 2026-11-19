# NovelForge Phase B Cost Report

## Derivation cost

- Deterministic Phase B provider calls: 0.
- Deterministic Phase B provider tokens: 0.
- Rebuild provider cost: $0.
- Incremental re-derivation is scoped to the changed owner and its affected atomic/episode records.

Phase B relies on existing extraction/Chapter Intelligence when prose understanding has already required a model. It does not hide that pre-existing extraction cost, but it adds no new extraction call.

## Generation savings

The matched Develop Story run cost estimate fell from $0.015127 to $0.010837 (28.36%). Prompt tokens fell 29.59%; evidence tokens fell 38.65%. Retries fell from three to zero in the matched observed runs, although provider variance means this retry change should not be attributed solely to context size.

Discovery retrieval is provider-free. Its context shrank 38.29%.

## Storage cost

Controlled 500-chapter storage was about 2.60 MiB atomic plus 0.62 MiB episode BSON. Index/metadata overhead is additional and Mongo deployment-specific.
