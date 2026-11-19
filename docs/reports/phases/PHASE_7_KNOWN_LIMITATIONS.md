# Phase 7 Known Limitations

- Character knowledge boundaries depend on structured chapter, death, timeline, and `learned_chapter` metadata. Unstructured implications that were never extracted into Narrative Analysis cannot be enforced reliably.
- Character conversations preserve bounded memories in the Story Bible, but memory reconciliation remains author-governed; contradictory conversational opinions may coexist until a proposal or canon conflict is reviewed.
- Knowledge Graph layout is deterministic and lightweight. Very dense graphs should be filtered by entity kind or search; it is not a full force-directed graph editor.
- Navigation recognizes explicit workspace and chapter/scene requests. It does not execute arbitrary model-generated application commands.
- Conversational latency depends on the configured provider. Cached graph and recommendation reads remain local and do not call the provider.
- Workspace Intelligence reports existing analysis findings. It cannot warn about unsaved paragraph text because the frozen Paragraph Editor boundary only publishes approved project records to Narrative Analysis.
- AI responses are evidence-grounded but remain recommendations. Canon changes always require author approval, and high-impact changes require an additional explicit confirmation.

