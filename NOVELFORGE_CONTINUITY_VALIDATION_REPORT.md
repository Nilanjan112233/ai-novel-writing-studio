# NovelForge Continuity Validation Report

## Why contradictions passed

Discovery validation previously enforced word range and one narrow duration check. POV/person detection existed in Narrative Analysis but was not part of the approval continuity gate. Confirmed relationship, ownership, knowledge, canon, decision, and confirmed-planning conflicts were not checked on this path. The duration check also accepted all draft durations if any one duration matched authority.

## P0 checks added

The Discovery approval validator now records evidence-backed findings for:

- predominant first-person versus third-person shift after dialogue removal;
- each conflicting “N years ago” claim against confirmed temporal authority;
- direct high-confidence polarity reversal of canon, approved decision, or confirmed Story Studio planning;
- unambiguous kinship conflict against a confirmed relationship owner;
- holder/owner conflict against the valid artifact state at that chapter;
- distinctive private/future knowledge presented as known by the POV character.

A failed finding is placed in the existing continuity report categories and also in `continuity_findings` as `{category, severity, message, evidence}`. Existing report consumers remain compatible.

## Creative evolution

The validator does not reject change merely because state evolves. An `intentional_pov_change` contract permits a declared POV switch. Explicit instructions containing change/transfer/heal/reveal/learn language prevent the matching high-confidence state rule from treating a planned transition as accidental drift.

This is conservative by design. It does not use an LLM, does not infer every paraphrase, and does not promote its finding to story authority. The author may revise the draft or explicitly plan the evolution.

## Regression case result

One seeded Discovery draft simultaneously contains the real failure shapes: third-to-first person, Elias two-versus-five years, Mara/Lindon brother extraction, Ivo holding Mara-owned Northglass, Mara knowing Ivo-only Elias truth, and reversal of “the river is not dry.” All six categories are detected. A separate explicitly planned POV switch is not flagged.

These tests run without persistence and without provider calls. The complete backend suite also passes, showing no regression to structured drafting validation.

## Limitations

High-confidence string/pattern checks trade recall for low false-positive risk. Semantic contradictions such as subtle motive changes, ambiguous possession, aliases, and indirect revelation remain outside P0. Those should be evaluated later with labelled evidence and authority-aware retrieval, not an unconstrained contradiction model.

