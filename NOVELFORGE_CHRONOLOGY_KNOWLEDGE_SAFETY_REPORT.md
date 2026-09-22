# NovelForge Chronology and Knowledge Safety Report

## Implemented boundary

Safe-writing retrieval now accepts `as_of_chapter`, optional `as_of_scene`, branch, and POV character. Eligibility reads `valid_from_*` and `valid_to_*` metadata and excludes evidence outside the requested boundary. Historical records remain stored; bounded versions are not erased or treated as current.

Discovery passes the state boundary immediately before the target chapter. Therefore:

- writing Chapter 5 can select a Chapter 3 ownership state valid through Chapter 7;
- writing Chapter 10 selects the Chapter 8 successor;
- the Chapter 3 record remains available for an as-of replay.

Superseded unbounded versions collapse to the highest current owner version. Candidate, rejected, reconsidered, stale, superseded, inactive, and abandoned statuses are ineligible for safe writing.

## Character knowledge

Knowledge entries retain story truth independently from `known_by` and `not_known_by`. With a POV character supplied, safe retrieval excludes a knowledge entry when that character is explicitly in `not_known_by` or when a non-empty `known_by` list does not contain the character. This is an eligibility rule, not prompt advice.

The continuity validator also checks high-confidence prose disclosure. A POV character cannot be written as knowing a distinctive ledger fact before the knowledge owner permits it. Story truth is not deleted; it is withheld from that character-context packet.

## Labelled results

- Elias five-year chronology conflict: detected and reported against confirmed authority.
- Northglass Mara-to-Ivo ownership interval: correct state at early and late boundaries.
- Later-chapter truth requested from an earlier chapter: excluded.
- Ivo-only knowledge requested from Mara POV: excluded.
- Explicit planned POV/knowledge evolution: not rejected merely because state changes.

The validator records category, severity, message, and source evidence. It does not claim open-ended semantic contradiction detection; chronology uses explicit temporal metadata plus high-confidence duration assertions.

## Remaining risk

Older projects may lack validity intervals and character knowledge lists. P0 handles available metadata safely but cannot infer missing historical boundaries without creating new derived facts. Backfilling those boundaries belongs to a later, reversible derivation phase with provenance and review.

Scene-level filtering exists when current records carry scene fields. Coverage is lower than chapter-level coverage because many current owners do not persist scene validity.

