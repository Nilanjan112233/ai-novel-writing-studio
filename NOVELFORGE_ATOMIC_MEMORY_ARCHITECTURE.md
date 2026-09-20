# NovelForge Atomic Memory Architecture

## Authority boundary

Atomic memory is a disposable retrieval projection. It cannot approve, mutate, or supersede canon, decisions, confirmed planning, approved prose, or structured story owners.

## Record contract

Each atomic record carries:

- project and deterministic `memory_id`/`fact_key`;
- subject, predicate, compact value, and entity references;
- source owners, source versions, and all evidence pointers;
- authority class and confidence;
- source chapter/scene and valid-from/valid-to boundaries;
- `known_by`, `not_known_by`, and story-truth versus character-knowledge scope;
- active/historical/superseded status;
- derivation version and deterministic derivation hash.

Exact equivalent observations share one fact identity and aggregate provenance. The implementation intentionally does not perform fuzzy semantic merging.

## Derivation sources

Deterministic adapters cover canon, decisions, chapter plans, characters, relationships, world records, plot threads, timeline, knowledge, artifacts, mysteries, and Chapter Intelligence. Existing structured owners are projected rather than copied as competing truth.

Approved-prose nuance continues to arrive through the existing extraction and Chapter Intelligence path. Phase B adds no new provider call.

## Versioning and chronology

When a newer owner version appears, the prior atomic projection is closed. If the owners provide a later chapter boundary, the prior projection remains historically eligible through `valid_to_chapter`; otherwise it becomes inactive/superseded. Current writing receives only the valid current projection.

## Contradictions

For the same subject/predicate with different values, the highest-authority value is labelled `authority_supported`. Lower derived values are labelled `conflicts_with_authority` and are excluded from safe-writing retrieval. Equal-authority unresolved conflicts remain labelled rather than silently merged.

## Rebuild and backup

Phase A rebuild invokes deterministic Phase B reconstruction, validates a logical hash, and records a Phase B checkpoint. `atomic_memories` and its checkpoint are excluded from portable backup data, so restores remain usable with no memory index present.
