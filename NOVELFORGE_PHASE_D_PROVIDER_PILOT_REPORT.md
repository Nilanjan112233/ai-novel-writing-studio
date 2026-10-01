# NovelForge Phase D Develop Story Real-Provider Pilot

## Decision

**KEEP CURRENT PHASE C. Do not roll the tested Phase D packet into production.**

The deterministic progressive arm passed the efficiency, authority, safety, chronology, retry, fallback, and resume gates. It did not pass the required blinded quality non-inferiority gate. It recovered most of the quality lost by the fact-only control, but it removed useful Mystery-specific evidence and was less useful to an author than the current packet.

No production retrieval, Develop Story service, Discovery Writing, Story Studio, structured writing, schema, authority rule, or provider route was changed. The pilot ran through a process-local diagnostic wrapper and isolated restored project copies.

## Frozen experiment

- Source backup ID: `87b2e3b9-6047-4049-bde1-9fc5fdfbd8de`
- Authority snapshot hash: `1e686f2becbcdf61049728482b83d4b56a0f7bbe71e0a3003ff6c0f18934bc69`
- Provider/model for every arm: `gemini / gemini-3.1-flash-lite`
- Role order: Relationship, Character Journey, Mystery, Arc Architect, Pacing
- Provider calls: five per arm
- Retries/fallbacks during matched runs: zero/zero for every arm
- Each arm used a separate restored project; derived indexes rebuilt READY with 142 logical records.

The instruction, authority snapshot, role order, provider/model, starting handoff state, and project contents were held constant. Outputs and proposals created inside one restored copy could not affect another arm.

## Matched results

| Metric | Current Phase C | Fact only | Progressive |
| --- | ---: | ---: | ---: |
| Prompt tokens | 22,729 | 9,962 | 14,225 |
| Response tokens | 3,288 | 3,211 | 3,644 |
| Total tokens | 26,017 | 13,173 | 17,869 |
| Evidence tokens | 14,155 | 1,010 | 4,498 |
| Estimated normalized cost | $0.010407 | $0.005269 | $0.007147 |
| Provider-gateway recorded cost | $0.012696 | $0.005892 | $0.008113 |
| Wall latency | 34.514 s | 52.791 s | 29.494 s |
| Deterministic checks | 23/25 | 22/25 | 24/25 |
| Blind usefulness (1–5) | 4.5 | 3.0 | 4.0 |
| Blind overall mean (1–5) | 4.111 | 3.000 | 3.889 |

Progressive versus current:

- evidence: **-68.22%**;
- prompts: **-37.41%**;
- responses: **+10.83%**;
- total tokens: **-31.32%**;
- normalized estimated cost: **-31.33%**;
- provider-gateway recorded cost: **-36.10%**;
- wall latency: **-14.55%**, observational only because one provider sample is noisy.

## Quality result

Fact-only behaved as the expected negative control. It produced coherent but generic plans, lost prior-interaction and episode continuity, and replaced missing evidence with broad inventions such as generic shared threats and outsider dynamics.

Episodes recovered the labelled requirements: progressive scored 24/25 compared with current's 23/25. However, blind review found the progressive packet less specific and less useful. The largest loss was in Mystery: current evidence supported concrete references to the ledger, safe-deposit box, Lindon debt, mill, settlement, photograph, river, and other clue material; the tested progressive projection retained only a narrower subset. Progressive also over-focused several roles on correcting the two-year chronology conflict.

This is exactly why the acceptance policy required blind usefulness in addition to token and keyword checks.

## Safety and authority

All arms achieved 100% measured authority coverage. The progressive arm preserved the authoritative five-year disappearance, explicitly labelled the derived two-year observation as conflicting evidence, and never gave it equal authority.

| Leakage/risk | Current | Fact only | Progressive |
| --- | ---: | ---: | ---: |
| Candidate leakage | 0 | 0 | 0 |
| Rejected leakage | 0 | 0 | 0 |
| Future leakage | 0 | 0 | 0 |
| POV knowledge leakage | 0 | 0 | 0 |
| Duplicate logical hits | 0 | 0 | 0 |
| Authority coverage | 100% | 100% | 100% |

## Verification

- Real-provider matched arms: completed, 15 specialist calls.
- Optional raw-evidence test: completed, two real-provider calls.
- Manifest repeat/idempotency simulation: passed for five roles.
- Failure/fallback simulations: passed.
- Diagnostic scripts compiled.
- Focused P0/A/E/B/C/provider tests: **33 passed**, no timeout.
- Existing deprecation warnings were emitted; no test failed.
- Frontend/build were not rerun because no production or frontend/shared contract was changed.

Machine-readable evidence is under `artifacts/memory-phase-d-provider-pilot/`, led by `pilot-comparison.json`.

## Gate outcome

Efficiency, safety, authority, coherence, cost, raw-branch, and recovery gates passed. Blind usefulness and blind overall non-inferiority failed. The combined gate therefore failed.

