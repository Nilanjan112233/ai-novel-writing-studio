# NovelForge Memory and Retrieval Report

## Context evidence

Before backfill, a live context packet was approximately 2,949 tokens and was dominated by older prompt-shaped chapter intelligence. After using the existing chapter-intelligence backfill and candidate extraction, a task-specific packet was approximately 4,820 tokens and included candidate-derived Chapter 5 facts such as Northglass, the third bell, Vale, the marsh, and Elias evidence. The packet did not include the entire project.

The sparse Chapter 6 continuation then used those facts without the author restating them. This is evidence that native context assembly is working and that large context capacity is not being filled indiscriminately.

## Authority behavior

Canon and decisions remain separate from candidate extraction. Approved prose, Story Bible, Narrative Intelligence, chapter intelligence, and recent context are assembled through existing services. The known issue is stale legacy intelligence: weak records can coexist with richer later records and leak noise into retrieval.

## TencentDB decision

Do not integrate TencentDB Agent Memory in this phase. No measured blocker requires it. Native retrieval already supports the demonstrated continuity; the measurable shortcomings are extraction quality, stale-record handling, relevance ranking, and canonical-change invalidation. A future adapter should be evaluated only after those native benchmarks are fixed and compared.

