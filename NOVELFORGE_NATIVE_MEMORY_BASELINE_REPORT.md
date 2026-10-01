# NovelForge Native Memory Baseline

## Scope

The baseline used the existing six-chapter project `6a7765ab6873ed058569f36d` and the one-chapter real creative-workflow project `6a78d47d4f0c63bfcbcbc17f`. No production prose or authority records were changed.

Native retrieval remains the existing `MemoryRetrievalService` path: MongoDB `memory_embeddings`, deterministic project-local embeddings, narrative relevance scoring, source/quality priorities, deduplication, and Context Engine authority-first assembly. Context Engine still places canon, approved decisions, and timeline before retrieved memory.

## Matched live recall baseline

Eight continuity queries were run through the NovelForge provider comparison path against the one-chapter project:

| Metric | Native |
|---|---:|
| Queries | 8 |
| Non-empty recalls | 8/8 |
| Returned hits | 40 total, 5/query |
| Average recall latency | 218.8 ms |
| Average recorded context estimate | 1,613.2 tokens |

Queries covered Elias disappearance, funeral pressure, Northglass, Mara's promise, the old pumping station, body identification, the brass key/map, and unresolved mystery.

## Strengths

- already participates in the authority-first Context Engine;
- source IDs and source types remain tied to NovelForge records;
- current structured records and approved prose are available without an external service;
- Native fallback works when the optional service is unavailable;
- no additional operational dependency is required for opening, writing, review, export, or restore.

## Limitations to keep measuring

Native retrieval is still bounded by the quality and freshness of the native indexed records. It should continue to be measured for duplicate/stale candidate hygiene and long-horizon retrieval, but the present evidence does not justify replacing it with an unproven external path.
