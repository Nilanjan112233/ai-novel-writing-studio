# NovelForge Lexical Retrieval Report

## Design

Each existing derived `memory_embeddings` row now carries normalized unigrams/bigrams, bounded term frequencies, document length, and ranker version. Mongo's compound multikey index on project, active state, ranker version, and search term provides candidate generation. BM25 then scores the complete returned candidate set in process.

This is real lexical retrieval without Elasticsearch/OpenSearch or a second authoritative store. The fields are disposable projections, produced by the same Phase A idempotent upsert and rebuilt from owners.

Candidate generation selects up to six discriminative terms based on project/domain document frequency. It does not cap matching records: every record matching the selected terms is returned and diagnostics report population, selected terms, coverage, raw candidates, and eligible records scored. A general query without an indexed term falls back to complete Phase B; a domain-specific empty knowledge result can return a labelled complete empty set.

## Exact callback evidence

On the expanded 500-chapter replay:

- current Phase B exact-family Recall/MRR: 0.8/0.8;
- BM25 exact-family Recall/MRR: 1.0/1.0;
- selected fusion exact-family Recall/MRR: 1.0/1.0.

Rare character, artifact, Virelai Observatory, broken-bell promise, and quoted-clue cases all passed. Lexical search therefore materially improves the exact callback class common in novels.

## Safety and explainability

Lexical matching never establishes truth. P0 eligibility filters candidates before BM25/hash/metadata scoring. Selected hits expose the lexical, hash, and metadata components, strategy, logical identity, authority, validity, evidence pointers, and rank. Rejected material remains available only to broader Story Studio retrieval, not safe writing.

## Storage

At 500 chapters / 2,522 rows, measured added lexical document payload was 1,214,800 BSON bytes. The clean benchmark collection's total allocated index space was 61,440 bytes after index build; this includes Mongo index allocation and should not be treated as a byte-perfect incremental index-only figure. No model files or external index service are required.
