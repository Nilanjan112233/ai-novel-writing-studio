# NovelForge Episode Memory Redesign Report

## Decision

Chapter Intelligence was evolved instead of creating a generic L2 store. The existing chapter record now contains a deterministic, version-aware `episode_memory` projection.

## Episode contents

Episodes retain the chapter summary, material events, participants, state changes, knowledge changes, mystery progression, open obligations, source version, and an evidence pointer. Duplicate entries are removed exactly and individual values are bounded.

The complete Chapter Intelligence document remains stored and the existing author/API compatibility fields remain available. Retrieval uses a bounded episode text; Develop Story uses an even smaller specialist evidence projection. This preserves drill-down without preloading the verbose owner.

## Identity and revision behavior

Episode identity is derived from project, Chapter Intelligence identity, approved draft version, and derivation version. Older Chapter Intelligence versions remain stored as history; the active approved revision produces the current episode.

## Measured size

The controlled corpus stored about 1.29-1.31 KB of BSON episode data per chapter. The two-chapter real benchmark supplied 1,608 estimated episode tokens per specialist after prompt projection (about 804 per chapter), compared with the previously repeated broad evidence.

## Compatibility

An initial targeted test caught removal of the top-level `chapter_number` expected by the existing chapter-memory API. The API-compatible fields were restored, while specialist-only compaction stays at the packet boundary. The focused rerun and complete suite passed afterward.
