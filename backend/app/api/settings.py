from fastapi import APIRouter, HTTPException
from datetime import datetime
from app.services.ai_provider import ai_provider
from app.core.database import Database
from app.core.config import settings as app_config
from app.services.orchestration_engine import orchestration_engine
from app.services.provider_gateway import ProviderError, provider_gateway
from app.services.model_registry_service import model_registry_service, normalize_provider
from app.services.provider_validation_service import ProviderValidationError, provider_validation_service
from app.services.provider_health_service import provider_health_service
from app.services.provider_recommendation_service import provider_recommendation_service
from app.services.observability_service import estimate_cost
from app.services.gemini_validation_service import gemini_validation_service
from app.services.model_health_service import model_health_service
from app.services.execution_trace_service import execution_trace_service
from app.services.narrative_studio import narrative_studio_service
from app.services.settings_service import settings_service
from app.services.memory_provider import memory_provider_service
from typing import Dict, Any
from bson import ObjectId

router = APIRouter(prefix="/api/settings", tags=["settings"])
ai_router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.get("/memory")
async def get_memory_settings():
    """Return safe, non-secret experimental memory-provider settings."""
    return await settings_service.get_memory_settings(runtime=False)


@router.put("/memory")
async def update_memory_settings(settings: Dict[str, Any]):
    """Save memory-provider selection without exposing credentials."""
    try:
        return await settings_service.save_memory_settings(settings)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/memory/test")
async def test_memory_provider():
    return await memory_provider_service.status(Database.get_db())


@router.post("/memory/smoke-test")
async def smoke_test_memory_provider():
    """Run the bounded developer-only Tencent retrieval gate with synthetic data."""
    return await memory_provider_service.smoke_test(Database.get_db(), str(ObjectId()))


@router.get("/ai")
async def get_ai_settings():
    """Get current AI provider settings."""
    return await settings_service.get_public_provider_settings()


@router.put("/ai")
async def update_ai_settings(settings: Dict[str, Any]):
    """Update AI provider settings."""
    for provider, config in (settings.get("providers") or {}).items():
        model = (config or {}).get("model")
        if model:
            try:
                await model_registry_service.validate_model(provider, model)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc))
    success = await ai_provider.update_settings(settings)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update settings")
    
    return {"message": "Settings updated"}


@router.post("/ai/test/{provider}")
async def test_ai_provider(provider: str, settings: Dict[str, Any] = None):
    """Test connection to an AI provider."""
    result = await ai_provider.test_connection(provider, settings)
    return result


@router.get("/execution")
async def get_execution_settings():
    db = Database.get_db()
    return (await orchestration_engine.get_settings(db)).model_dump()


@router.put("/execution")
async def update_execution_settings(settings: Dict[str, Any]):
    db = Database.get_db()
    try:
        return (await orchestration_engine.update_settings(db, settings)).model_dump()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/agents")
async def get_agent_model_assignments():
    db = Database.get_db()
    return [assignment.model_dump() for assignment in await orchestration_engine.get_assignments(db)]


@router.put("/agents")
async def update_agent_model_assignments(assignments: list[Dict[str, Any]]):
    db = Database.get_db()
    try:
        return [assignment.model_dump() for assignment in await orchestration_engine.update_assignments(db, assignments)]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/presets/{preset}")
async def apply_orchestration_preset(preset: str):
    db = Database.get_db()
    try:
        return (await orchestration_engine.apply_preset(db, preset)).model_dump()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/test-model")
@ai_router.post("/test-model")
async def test_model(payload: Dict[str, Any]):
    provider = payload.get("provider")
    model = payload.get("model")
    if not provider or not model:
        raise HTTPException(status_code=400, detail="provider and model are required")
    db = Database.get_db()
    result = await provider_gateway.test_model(provider, model, db=db)
    normalized_provider = normalize_provider(provider)
    await model_health_service.record_result(db, result)
    if result.get("success"):
        await provider_health_service.record_success(
            db,
            normalized_provider,
            model,
            int(result.get("latency_ms", 0)),
            int(result.get("tokens_used", 0)),
            estimate_cost(int(result.get("tokens_used", 0)), normalized_provider, model),
        )
    else:
        await provider_health_service.record_failure(
            db,
            normalized_provider,
            model,
            result.get("error_type", "PROVIDER_UNAVAILABLE"),
            result.get("error", "Provider test failed"),
        )
    return result


@router.get("/models")
async def get_models(provider: str | None = None, refresh: bool = False, verified_only: bool = False):
    service_call = model_registry_service.get_verified_models if verified_only else model_registry_service.get_models
    if verified_only:
        return [model.model_dump() for model in await service_call(provider)]
    return [model.model_dump() for model in await service_call(provider, refresh=refresh)]


@router.post("/providers/{provider}/validate")
async def validate_provider(provider: str, payload: Dict[str, Any] | None = None):
    try:
        api_key = (payload or {}).get("api_key")
        result = await provider_validation_service.validate(
            provider,
            api_key=api_key,
        )
        if api_key:
            settings = await provider_validation_service.settings_with_api_key(result["provider"], api_key)
            await provider_validation_service.save_settings(settings)
        return {"provider": result["provider"], "valid": True}
    except ProviderValidationError as exc:
        return {
            "provider": exc.provider,
            "valid": False,
            "error_type": exc.error_type,
            "error": str(exc),
        }


@router.post("/providers/{provider}/discover")
async def discover_provider_models(provider: str, payload: Dict[str, Any] | None = None):
    try:
        result = await model_registry_service.discover_models(
            provider,
            api_key=(payload or {}).get("api_key"),
        )
        return {
            **result,
            "models": [
                model.model_dump()
                for model in await model_registry_service.get_models(provider)
            ],
        }
    except ProviderValidationError as exc:
        cached_models = await model_registry_service.get_models(exc.provider)
        return {
            "provider": exc.provider,
            "status": "offline",
            "discovered_model_count": len(cached_models),
            "models": [model.model_dump() for model in cached_models],
            "error_type": exc.error_type,
            "error": str(exc),
        }


@router.get("/model-validations")
async def get_model_validations(provider: str | None = None):
    return await model_registry_service.get_validation_results(provider)


@router.get("/model-health")
async def get_model_health(provider: str | None = None):
    return await model_health_service.get_results(Database.get_db(), provider)


@router.post("/validate-models")
async def validate_models(payload: Dict[str, Any]):
    provider = normalize_provider(payload.get("provider", "gemini"))
    supported = {"gemini", "openrouter", "openai", "anthropic", "groq", "ollama"}
    if app_config.use_mock_llm:
        supported.add("mock")
    if provider not in supported:
        raise HTTPException(status_code=400, detail=f"Model validation is not supported for {provider}")
    db = Database.get_db()
    return await gemini_validation_service.validate_provider(db, provider=provider)


@router.get("/execution-traces")
async def get_execution_traces(limit: int = 50):
    db = Database.get_db()
    return await execution_trace_service.latest(db, limit=limit)


@router.post("/run-ai-workflow-test")
async def run_ai_workflow_test(payload: Dict[str, Any]):
    provider = normalize_provider(payload.get("provider", ""))
    model = payload.get("model", "")
    if not provider or not model:
        execution = (await orchestration_engine.get_settings(Database.get_db())).model_dump()
        provider = normalize_provider(execution.get("default_provider", "mock"))
        model = execution.get("default_model", "")
    if provider == "mock":
        return {
            "success": False,
            "mock_detected": True,
            "error_type": "MOCK_MODE",
            "error": "Run AI Workflow Test requires a real provider/model.",
        }
    db = Database.get_db()
    before = await db.execution_traces.count_documents({})
    try:
        result = await provider_gateway.generate_with_failover(
            db,
            [
                {"role": "system", "content": "You are NovelForge's provider execution smoke test."},
                {"role": "user", "content": "Reply ONLY:\nNOVELFORGE_TEST_OK"},
            ],
            provider=provider,
            model=model,
            fallbacks=[],
            temperature=0,
            max_tokens=96,
            agent_name="RealAIWorkflowTest",
        )
    except ProviderError as exc:
        return {
            "success": False,
            "mock_detected": False,
            "provider": exc.provider or provider,
            "model": exc.model or model,
            "error_type": exc.error_type,
            "error": str(exc),
            "execution_trace_saved": await db.execution_traces.count_documents({}) > before,
        }
    after = await db.execution_traces.count_documents({})
    content = result.get("content", "")
    return {
        "success": bool("NOVELFORGE_TEST_OK" in content and after > before and result.get("provider") != "mock"),
        "mock_detected": result.get("provider") == "mock",
        "provider": result.get("provider"),
        "model": result.get("model"),
        "tokens_used": result.get("tokens_used"),
        "latency_ms": result.get("latency_ms"),
        "execution_trace_saved": after > before,
        "response": content,
    }


@router.post("/run-full-workflow-test")
async def run_full_workflow_test(payload: Dict[str, Any]):
    db = Database.get_db()
    execution = await orchestration_engine.get_settings(db)
    provider = normalize_provider(payload.get("provider") or execution.default_provider)
    model = payload.get("model") or execution.default_model
    if execution.execution_mode != "full":
        raise HTTPException(status_code=400, detail="Run Full Workflow Test requires execution mode FULL")
    if provider == "mock":
        raise HTTPException(status_code=400, detail="Run Full Workflow Test requires a real provider/model")

    project_doc = {
        "title": "NovelForge Full Workflow Test",
        "idea_dump": "A prince discovers dead gods beneath his kingdom.",
        "genre": "Fantasy",
        "tone": "Mythic",
        "status": "testing",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    project_result = await db.projects.insert_one(project_doc)
    project_id = str(project_result.inserted_id)
    run_doc = {
        "project_id": project_result.inserted_id,
        "status": "running",
        "current_agent": "real_ai_test",
        "started_at": datetime.utcnow(),
        "finished_at": None,
        "metadata": {"real_ai_workflow_test": True},
    }
    run_result = await db.runs.insert_one(run_doc)
    run_id = str(run_result.inserted_id)
    agents = [
        "NarrativeDirectorAgent",
        "ArcArchitectAgent",
        "PowerSystemAgent",
        "CharacterJourneyAgent",
        "MysteryAgent",
        "PacingAgent",
        "RelationshipAgent",
        "FactionAgent",
        "ThemeAgent",
    ]
    before_traces = await db.execution_traces.count_documents({})
    outputs = 0
    total_tokens = 0
    traces = []

    try:
        state = {
            "project_id": project_id,
            "cycle_number": 1,
            "timeline_messages": [{"role": "user", "content": project_doc["idea_dump"]}],
            "outputs": [],
            "new_messages": [{"role": "user", "content": project_doc["idea_dump"]}],
        }
        await narrative_studio_service.run(
            db,
            project_id=project_id,
            state=state,
            run_id=run_id,
            agent_names=agents,
            max_agent_calls=len(agents),
        )
        outputs = await db.agent_outputs.count_documents({"project_id": ObjectId(project_id), "run_id": ObjectId(run_id)})
        await db.runs.update_one({"_id": ObjectId(run_id)}, {"$set": {"status": "completed", "current_agent": "completed", "finished_at": datetime.utcnow()}})
    except ProviderError as exc:
        await db.runs.update_one({"_id": ObjectId(run_id)}, {"$set": {"status": "failed", "current_agent": "failed", "finished_at": datetime.utcnow(), "error": str(exc)}})
        return {
            "success": False,
            "message": "Workflow Test Failed",
            "provider": exc.provider or provider,
            "model": exc.model or model,
            "error_type": exc.error_type,
            "error": str(exc),
            "tokens": total_tokens,
            "outputs": outputs,
            "project_id": project_id,
            "run_id": run_id,
            "mock_used": False,
        }
    except Exception as exc:
        await db.runs.update_one({"_id": ObjectId(run_id)}, {"$set": {"status": "failed", "current_agent": "failed", "finished_at": datetime.utcnow(), "error": str(exc)}})
        raise

    trace_docs = await db.execution_traces.find({"created_at": {"$gte": run_doc["started_at"]}}).sort("created_at", -1).to_list(length=20)
    traces = [
        {
            "provider": trace.get("provider"),
            "model": trace.get("model"),
            "agent_name": trace.get("agent_name"),
            "tokens": trace.get("total_tokens"),
            "latency_ms": trace.get("latency_ms"),
            "status": trace.get("status"),
        }
        for trace in trace_docs
    ]
    total_tokens = sum(int(trace.get("tokens") or 0) for trace in traces)
    after_traces = await db.execution_traces.count_documents({})
    artifact_counts = {
        "discussion_messages": await db.discussion_messages.count_documents({"project_id": ObjectId(project_id)}),
        "story_visions": await db.story_visions.count_documents({"project_id": ObjectId(project_id)}),
        "story_arcs": await db.story_arcs.count_documents({"project_id": ObjectId(project_id)}),
        "power_systems": await db.power_systems.count_documents({"project_id": ObjectId(project_id)}),
        "character_journeys": await db.character_journeys.count_documents({"project_id": ObjectId(project_id)}),
        "mystery_registry": await db.mystery_registry.count_documents({"project_id": ObjectId(project_id)}),
        "ai_insights": await db.ai_insights.count_documents({"project_id": ObjectId(project_id)}),
    }
    passed = (
        outputs >= 5
        and after_traces > before_traces
        and all(trace["provider"] != "mock" for trace in traces if trace.get("agent_name") in agents)
        and all(count > 0 for count in artifact_counts.values())
    )
    return {
        "success": passed,
        "message": "Workflow Test Passed" if passed else "Workflow Test Failed",
        "provider": provider,
        "model": model,
        "tokens": total_tokens,
        "outputs": outputs,
        "artifacts": artifact_counts,
        "project_id": project_id,
        "run_id": run_id,
        "mock_used": any(trace["provider"] == "mock" for trace in traces),
        "traces": traces,
    }


@router.get("/health")
async def get_provider_health():
    db = Database.get_db()
    return await provider_health_service.health_snapshot(db)


@router.get("/recommendations")
async def get_provider_recommendation(
    task_type: str = "routing",
    budget_preference: str = "balanced",
    quality_preference: str = "balanced",
    latency_preference: str = "balanced",
    context_tokens: int = 0,
):
    return await provider_recommendation_service.recommend(
        task_type=task_type,
        budget_preference=budget_preference,
        quality_preference=quality_preference,
        latency_preference=latency_preference,
        context_tokens=context_tokens,
    )
