# NovelForge Phase C Operational Cost Report

## Chosen production path

The production path adds no provider call, local ML runtime, service process, or network dependency. It reuses MongoDB and existing Phase A events. The only durable additions are lexical fields on rebuildable memory rows, one multikey index, and one project-scoped derived checkpoint.

## Measured storage

| Chapters | Records | Lexical BSON payload | Total indexed-document BSON | Mongo allocated indexes |
|---:|---:|---:|---:|---:|
| 100 | 522 | 245,597 B | 1,346,452 B | 8,192 B |
| 250 | 1,272 | 609,050 B | 3,308,908 B | 61,440 B |
| 500 | 2,522 | 1,214,800 B | 6,579,658 B | 61,440 B |

Mongo allocation is page-granular and includes collection indexes, so it is an operational allocation measurement rather than an exact incremental-index byte count. The lexical payload figure is the direct per-document addition.

## Runtime cost

- build the lexical index over 2,522 existing rows: 186.903 ms;
- single changed-row index update P50/P95: 80.948/101.674 ms;
- unchanged idempotent update: 2.321 ms and zero writes;
- 500-chapter retrieval cold P50/P95: 47.115/61.175 ms;
- 500-chapter retrieval warm P50/P95: 7.727/8.812 ms;
- mean eligible records scored/query: 1.93.

The changed-row cost is higher than the earlier Phase A-only mutation benchmark, because the same Mongo update now maintains a multikey term index and lexical payload. Work remains one-owner/one-derived-record scoped rather than novel-size scoped.

The candidate cache is bounded to 256 revision/query entries and invalidated by project mutation, rebuild, or failure. It stores rebuildable candidate documents only and is not authority.

## Rejected semantic operating cost

MiniLM would add a 91,578,407-byte model cache, 9.133-second cold import/model startup, and 11.873-second 500-chapter encoding pass. Because it did not beat the chosen MRR and required full-corpus scoring in this evaluation, it was not shipped.

Tencent remains optional and was not contacted. Phase C indexes are excluded from backup and rebuilt after restore.
