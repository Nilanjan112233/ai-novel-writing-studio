# NovelForge Extraction Quality Report

## Live findings

Approved prose created candidate extraction records without automatic canon promotion. Chapter 1 had an empty legacy extraction record. Chapters 2–4 had candidates, but many were polluted character labels such as sentence fragments and stopwords. Chapter 5 produced 37 candidates across characters, relationships, world facts, timeline events, knowledge changes, mysteries, promises, plot threads, foreshadowing, artifacts, POV/style, and unresolved elements. Chapter 6 produced 26 candidates.

Chapter 5 is evidence that the strengthened extraction contract can produce useful structured context. It captured the Northglass, blood/path rule, third bell, Vale’s knowledge, Elias evidence, Mara/Ivo tension, the marsh destination, and unresolved questions.

## Changes made

Extraction now records provider/model/tokens/trace/fallback/attempt metadata, requests concrete story facts instead of vague summaries, and uses a bounded deterministic fallback when provider output is empty or malformed. The fallback recognizes the project’s meaningful artifact, injury, promise, mystery, and world-rule signals. Existing candidates remain candidates; no candidate is silently promoted to canon.

## Remaining quality gap

Legacy weak records remain in the native memory path and need an explicit re-extraction/cleanup migration with provenance. The live evidence supports improving deduplication, confidence, and relevance filtering before considering an external memory system.

