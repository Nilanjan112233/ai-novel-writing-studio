# Known Limitations

1. Story Studio action confirmation is conservative: generic character/relationship changes produce governed proposal guidance, but a full natural-language action editor should be added only by routing each target through its existing owning service.
2. Story Studio progress is persisted and polled, not yet a full event-stream UI with retry controls for every stage.
3. Discovery generation currently performs one bounded prose call. Very large chapter requests need scene-sized continuation orchestration before production use.
4. Candidate extraction is stored and reusable but does not yet have a dedicated candidate-review panel; existing Canon Queue/structured inspectors remain the safe review surfaces.
5. The browser run used mock models for the repeatable 10-chapter soak and a real configured provider for the live prose check. It is not a statistically valid human reader study; human-feel assessment still requires editorial review and author feedback.
6. TencentDB Agent Memory has not been integrated because the requested order correctly requires native memory benchmarking first.

