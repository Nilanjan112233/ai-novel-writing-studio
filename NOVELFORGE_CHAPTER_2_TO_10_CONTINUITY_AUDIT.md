# NovelForge Chapters 2–10 Continuity Audit

## Verdict

The sequence does not maintain acceptable continuity as generated. Chapter 2 is a hard identity and POV break: Chapter 1 establishes Renn as a fifteen-year-old girl in a river-working household, while Chapter 2 opens with “The smell woke him,” describes ten-year-old hands, and treats the protagonist as a boy in a farm-family setup. This chapter was left unapproved.

Chapters 3–10 mostly return to Renn/she and reuse the river, levy, seam, memory cost, missing Darin, blight, and well/other-world direction. That partial recovery is not enough to make the sequence safe: the broken Chapter 2 is still the official continuation, Chapter 4 has duplicate active records, and later context continues to retrieve provisional Kael/farm/well planning that was never author-confirmed.

## Chapter-by-chapter findings

| Chapter | Continuity result | Important observations |
|---:|---|---|
| 2 | Fail | He/him, ten-year-old boy, farm/father assumptions; the first continuation behaves as if a different novel is underway |
| 3 | Partial recovery | Renn/she, Lira, levy, memory cost, and seam language return; it is a correction rather than a natural continuation from Ch2 |
| 4 | Partial, with lineage failure | Two generated variants; one begins with the river dropping and Darin gone, another begins with the levy patched and introduces Corbin; raw active/version metadata is inconsistent |
| 5 | Partial | Missing Darin and Maren/alternate-space escalation create purpose; local relationships are thinner than the hook chain |
| 6 | Partial | Well/seam descent and Darin mystery continue; explanatory repetition increases |
| 7 | Partial | Blight and suture-bearer lore expand the system; new lore arrives faster than emotional grounding |
| 8 | Partial | Preserves blight, well, father, and alternate-world mystery; farm/Kael planning residue remains visible in context |
| 9 | Partial | Quiet levy-road chapter is a useful pause; “seam,” “preserves,” and threat language remain abstract and repetitive |
| 10 | Partial | Renn/she and early details are reused; stronger immediate hook, but escalation is another seam/voice/unknown-figure beat and the chapter remains unapproved |

## Failure modes observed

### Retry target corruption

The UI retry action described regeneration for Chapter 2. The backend then computed the next chapter from the latest raw chapter and created Chapter 3. The result is a workflow-level continuity defect, not a provider-only literary defect.

### Delayed completion and duplicate Chapter 4

One Chapter 4 provider call completed after the UI had timed out or appeared stale. A retry was then initiated, creating a second Chapter 4. The UI reports version count 2, but the raw documents are both active and both version 1. This makes it unclear which prose is authoritative, and it breaks reproducibility.

### Context contamination

Chapter context packets repeatedly carried provisional Develop artifacts such as “Kael,” the farm, the old well, “The Buried Sky,” “The One Who Notices,” and “A Gift, a Wound, or a Claim.” The packets label some material exploratory, but the writing model still sees it in a high-volume context. This is a practical authority leak even when the Mongo collections are formally non-canon.

### Extraction stops at the approved boundary

Chapter 1 has candidate extraction with 32 candidates. Chapters 2–10 have `extraction.status=not_started` and zero candidates because they were not approved. This is authority-safe in one sense, but the product gives the author no strong continuity warning that only one chapter is feeding structured memory while nine visible chapters are not.

## Memory/callback observations across the sequence

Correctly reused or naturally established:

- Renn's seam perception and physical/memory cost;
- the river and failing levy/Bleed;
- Lira and the household relationship;
- Darin's absence and the promise to send money;
- blight and the well/other-sky mystery;
- old-life observation and regret as broad themes.

Poorly retrieved or overwritten in practical generation context:

- Renn's age and gender in Chapter 2;
- the intended disaster-mapping/emergency-infrastructure old life, which was displaced by archivist/cartographer/farm planning;
- the exact river-household context, which was repeatedly mixed with a provisional farm;
- rejected drought, indentured-labor, child-companion, instant-travel, and status-window directions were not present in the prose, but the system gave no visible author-facing rejection ledger;
- later chapters did not acquire approved structured facts because the normal workflow treated them as drafts only.

## Continuation quality scores (1–10)

| Chapter | Opening | Readability | Naturalness | Voice | Dialogue | Emotion | Pacing | Purpose | Tension | Progression | Continuity | Ending | AI-pattern risk | Continue reading |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2 | 3 | 6 | 4 | 2 | 5 | 4 | 6 | 5 | 6 | 5 | 1 | 5 | 4 | 2 |
| 3 | 7 | 7 | 6 | 6 | 5 | 6 | 6 | 6 | 7 | 6 | 4 | 6 | 5 | 6 |
| 4 active | 6 | 6 | 5 | 6 | 5 | 5 | 6 | 7 | 7 | 7 | 4 | 6 | 4 | 5 |
| 5 | 6 | 6 | 5 | 6 | 5 | 5 | 6 | 7 | 7 | 7 | 5 | 6 | 4 | 5 |
| 6 | 6 | 6 | 5 | 6 | 5 | 5 | 6 | 7 | 7 | 7 | 5 | 6 | 4 | 5 |
| 7 | 6 | 6 | 5 | 6 | 5 | 5 | 6 | 7 | 7 | 7 | 5 | 5 | 4 | 5 |
| 8 | 6 | 6 | 5 | 6 | 5 | 5 | 6 | 6 | 7 | 7 | 4 | 6 | 4 | 5 |
| 9 | 6 | 7 | 5 | 6 | 5 | 6 | 6 | 6 | 6 | 6 | 5 | 5 | 4 | 5 |
| 10 | 7 | 7 | 5 | 6 | 5 | 6 | 6 | 7 | 8 | 7 | 5 | 6 | 4 | 6 |

These are auditor judgments, not automated scores. They are intentionally separated from the backend's `validation_result=PASS`, which only indicates structural/provider validation and does not establish literary continuity.

## Overall sequence assessment

The sequence feels like one premise being repeatedly reintroduced, not one novel steadily deepening. It has a recognizable escalation path—levy, seam, disappearance, well, blight, other space—but too few quiet relationship scenes and too much repeated mystery vocabulary. The protagonist's power progression is conceptually earned, but scenes often end because a new anomaly appears rather than because a choice produces a consequence.

Before real-novel use, NovelForge needs a continuation gate that compares a proposed chapter against approved facts and explicit exclusions, then blocks or clearly warns on identity, age, pronoun, household, POV, location, and active-goal mismatches. It also needs a durable draft target and idempotent job state so a user cannot accidentally create the next chapter while trying to repair the current one.

