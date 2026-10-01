# Subsystem Architecture: AI Assistant & Provider Gateway

The AI Assistant and Provider Gateway layer handles model registry, discovery, execution settings, retry fallback policies, and dynamic costing.

## Model Registry & Discovery

- **Model Registry**: Persists supported and verified models across all configured providers.
- **Model Discovery**: Dynamically queries active provider endpoints (e.g. Gemini, Groq, OpenRouter) to check model availability and features.
- **Verification Tests**: Discovers, registers, and validates settings by executing lightweight workflow runs.

## Provider Gateway

All LLM calls route through `ProviderGateway` (`backend/app/services/provider_gateway.py`).
- **Failover Routing**: Automatically routes calls to secondary providers/models during outages or 5xx responses.
- **Rate Limit & Cooldown**: Sets cool-down periods on providers encountering persistent rate limits.
- **Token telemetry**: Measures actual cost and token counts to record in execution traces.
- **Trace observability**: Every assistant cycle records latency, traces, and metadata.
