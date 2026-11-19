# NovelForge Continuity Soak Report

## Scenario

The dedicated story introduced deliberate dependencies: Mara Venn’s left-palm injury, Elias’s ferry promise, Ivo’s changing trust relationship, Councillor Vale’s investigation, a brass compass later called Northglass, a third-bell rule, an impossible river path, a water-stained map, a blue cloth, a secret known by Ivo but not Mara, and a missing-brother mystery.

## Observations

Chapters 2–6 reused names, locations, injuries, objects, promises, relationships, and unresolved danger. Chapter 6 is the strongest test because the instruction asked for immediate continuation and explicitly prohibited a reset. The model retrieved the marsh, Northglass, map, scar, Ivo, and Elias threads and converted them into new causality rather than a recap.

The run also exposed a retrieval-quality problem: older chapter-intelligence records created before the extraction hardening contain prompt-shaped or polluted character entries. After backfill, Chapter 5 produced rich candidate-derived intelligence, but stale legacy entries were still present in the packet.

## Author-change test

Story Studio correctly gated an ambiguous request to rename the compass and change its behavior. An explicit mutation request produced no authoritative mutation and no proposal because the new project had no owning canonical record to modify. This confirms safety, but does not yet prove downstream propagation from an established canonical fact. That remains a required next test on a project containing approved canon.

## Judgment

Native retrieval is sufficient to support continuity across the live six-chapter sample, but stale-record deduplication and migration of weak legacy intelligence must be improved before continuity can be called robust for long novels. TencentDB is not justified by this evidence; the immediate bottleneck is native extraction and retrieval hygiene.

