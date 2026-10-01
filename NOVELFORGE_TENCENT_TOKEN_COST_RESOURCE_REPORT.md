# Tencent Token, Cost, and Resource Comparison

## Matched writer call

The same DeepSeek V4 Flash writer call cost approximately `$0.007248` with Native context, `$0.011561` with Tencent context, and `$0.016427` with Hybrid context. The application trace recorded 5,249, 10,056, and 15,131 prompt tokens respectively. Tencent therefore increased prompt and total-token cost in the current L0 fallback configuration.

## Local operational sample

The isolated Node 22.16 gateway with the ten-chapter/scale benchmark data used approximately 676 MB working set, 754 MB private memory, and 4.95 MB on-disk data at inspection time. This is one local standalone sample, not a production service estimate. Native adds no separate process, port, or gateway startup requirement.

## Cost conclusion

Tencent capture/search itself used no external embedding/LLM calls in this configuration, but it increased downstream writer input. There is no measured provider-cost reduction.

