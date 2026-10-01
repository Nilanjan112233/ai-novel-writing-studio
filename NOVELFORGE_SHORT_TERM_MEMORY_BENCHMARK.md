# Short-Term Memory Benchmark

## Workload

The live Story Studio benchmark used repeated conversational/development activity on the one-chapter project, including current story constraints, Northglass atmosphere, the unresolved Elias question, funeral details, and planning-oriented follow-up. The provider layer recorded each capture and recall separately, preserving provider and source provenance.

## Observations

- Native captured and recalled through the established MongoDB memory path.
- Tencent accepted captures when the gateway was live.
- When Tencent was stopped, capture failures were recorded and did not block the Story Studio job; Native continued.
- In benchmark mode, Native stayed the primary answer path and Tencent was observational.
- In the matched eight-query recall run, Native returned 5 hits for every query; Tencent returned none.

## Supersession/rejection safety

The provider boundary itself does not promote conversational material. Current/superseded/rejected semantics remain governed by NovelForge shared narrative context, decisions, canon, and structured owner services. Tencent events are telemetry/derived recall only and therefore cannot outrank a current decision or enter writing context directly.

## Conclusion

Native is the only demonstrated short-term provider that supplied useful project context in this deployment. Tencent capture is operational but recall quality is unproven until indexing/embedding or supported FTS is configured.
