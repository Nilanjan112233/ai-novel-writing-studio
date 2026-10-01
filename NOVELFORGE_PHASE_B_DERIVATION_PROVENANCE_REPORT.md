# NovelForge Phase B Derivation and Provenance Report

## Provenance guarantees

Every atomic memory links to logical and physical source identity, source version, source type, and derivation version. Equivalent facts preserve all evidence pointers. Episode projections point to the Chapter Intelligence ID, approved draft ID/version, and chapter number.

## Cost and provider routing

All Phase B derivation implemented in this pass is deterministic and provider-free. Provider extraction calls: 0. Provider extraction tokens: 0. The existing provider gateway remains the only path for pre-existing prose extraction; Phase B did not add a parallel model route.

## Incremental behavior

Phase A owner events invoke derivation only for the changed owner and then deterministically index affected atomic records. Duplicate delivery and unchanged processing remain idempotent. New owner versions close prior projections while preserving bounded history.

## Rebuild behavior

Project rebuild regenerates episodes and atomics from current owners, calculates a logical hash, records counts and a READY checkpoint, and does not mutate authority. Missing derived collections after restore are therefore recoverable.

## Failure posture

Malformed or absent derived evidence cannot become authority. Strict writing still relies on P0 eligibility and Phase A readiness/fallback. Tencent is not consulted for derivation, rebuild, or recall correctness.
