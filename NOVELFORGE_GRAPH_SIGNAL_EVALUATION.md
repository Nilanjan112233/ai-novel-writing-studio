# NovelForge Graph Signal Evaluation

## Existing graph only

The evaluation used existing Narrative Intelligence nodes and edges. No new graph database, duplicate node store, or graph authority was created. Query entities seed graph nodes; direct graph neighbours can boost matching memory records.

## Result

At 250 and 500 chapters, graph-augmented fusion produced exactly the same Recall@8 and MRR as the non-graph weighted winner:

- Recall@8: 1.0000 both;
- 500-chapter MRR: 0.8452 both;
- records scored: 1.93 both.

The labelled corpus did not show a rank improvement sufficient to justify an extra graph lookup and crosswalk during every query. Exact entity terms plus existing metadata already found the connected records.

## Decision

Do not enable graph ranking in production Phase C. Retain the evaluation helper. Reconsider only with a labelled multi-hop corpus where the relevant fact lacks lexical/entity overlap but is reachable through verified existing Narrative Intelligence edges. Graph relevance must remain a ranking signal after eligibility, never authority.
