# Phase D Provider Pilot Final Recommendation

## Recommendation

**KEEP CURRENT PHASE C for Develop Story. Do not implement the tested Phase D packet in production.**

The pilot demonstrated that deterministic facts-plus-episodes can materially reduce tokens and cost without weakening authority or safety. It did not demonstrate non-inferior author usefulness. The acceptance gates explicitly require both.

## Gate table

| Gate | Result |
| --- | --- |
| Progressive evidence reduction ≥30% | PASS: 68.22% |
| Total prompt reduction ≥20% | PASS: 37.41% |
| Labelled specialist quality non-inferior | PASS: 24/25 vs 23/25 |
| Blind usefulness non-inferior | **FAIL: 4.0 vs 4.5** |
| Blind overall non-inferior | **FAIL: 3.889 vs 4.111** |
| Cross-agent coherence non-inferior | PASS |
| Authority coverage 100% | PASS |
| Zero safety leakage | PASS |
| No retry/fallback regression | PASS |
| Total provider cost lower/equal | PASS: 36.10% lower gateway cost |
| Deterministic resume/failure behavior | PASS |
| Raw evidence branch validated | PASS |

## Answers to the final questions

1. **Did progressive retrieval reduce prompt tokens?** Yes: 22,729 to 14,225, a 37.41% reduction.
2. **Did total provider cost fall?** Yes: gateway-recorded cost fell from $0.012696 to $0.008113, 36.10%. Normalized estimated cost fell 31.33%.
3. **Did response length change?** Yes: 3,288 to 3,644 tokens, an increase of 10.83%. Total tokens still fell 31.32%.
4. **Did specialist usefulness change?** Yes. Progressive blind usefulness was 4.0 versus current 4.5, so it was inferior despite better deterministic coverage.
5. **Which specialist lost the most information?** Mystery. The compact projection omitted several concrete clue and evidence details present in current Phase C.
6. **Did fact-only fail as expected?** Yes. It lost episode/prior-interaction continuity, scored 3.0 blind mean, and produced more generic/invented connective planning.
7. **Did episodes recover the missing quality?** They recovered the labelled depth checks and most blind quality, but not all specificity/usefulness.
8. **Was raw evidence necessary for the wording test?** Yes. Episode-only correctly could not judge subtlety; the bounded prose enabled a specific, grounded answer.
9. **Did cross-agent coherence change?** No meaningful degradation. Handoff counts and integration checks passed; blind coherence was 4.0 for both current and progressive.
10. **Were authority or chronology facts lost?** No. Authority coverage was 100%; five years remained authoritative; the two-year derived conflict was explicitly subordinate.
11. **Did retries/fallbacks change?** No. All matched arms had zero retries/fallbacks. Simulated fallbacks selected Phase C, then Phase B/P0-safe paths as required.
12. **Is deterministic routing sufficient?** The mechanism is sufficient and deterministic; the tested evidence contents are not yet quality-sufficient. Model-requested tools are not justified.
13. **Should Develop Story Phase D be implemented?** No, not from this pilot. Tune role projections and repeat a blinded matched pilot first.
14. **Should Discovery remain unchanged?** Yes. It was not modified or exercised by this pilot.
15. **Should writing/editorial remain unchanged?** Yes. Wording and prose work needs raw evidence more often and was out of scope.

## Next bounded experiment—not implementation

1. Keep Phase C production behavior unchanged.
2. Enrich the Mystery episode projection with high-value clue, obligation, location, ownership, and evidence-reference fields.
3. Retain similar specificity for Relationship/Character roles where prior interactions matter.
4. Put the chronology conflict in one compact shared conflict block; expand it only for roles that need it.
5. Ensure outputs label invented mystery explanations and Elias-alive claims as proposals, not story facts.
6. Repeat the same frozen three-arm pilot and blind review.
7. Require progressive blind usefulness and overall mean to meet or exceed current before preparing a production implementation plan.

No production Phase D implementation plan is recommended yet because the “if and only if the pilot passes” condition was not met.

