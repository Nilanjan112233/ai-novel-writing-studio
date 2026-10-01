# Chronology and Character-Knowledge Report

The synthetic chronology test stored a Chapter 8-only “fourth gate” fact and a Chapter 3 bounded context. A safe NovelForge recall for a Chapter 3 query:

- used Native as the primary provider;
- returned the Chapter 3 bounded record;
- did not leak the Chapter 8-only fact into the primary packet;
- kept Tencent comparison marked non-authoritative.

Tencent itself is not trusted to enforce chronology. All future-context retrieval must continue through NovelForge’s existing chronology, knowledge-boundary, canon, and decision filters.

