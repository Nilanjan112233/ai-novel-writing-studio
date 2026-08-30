from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from app.core.config import settings
from app.core.database import Database
from app.api import projects, workflow, data, settings as settings_api, messages, planning, development, drafting, editorial, manuscript, intelligence, interactive, product_experience, rc6, operations
from app.api.intelligence import recover_narrative_analysis_jobs
import logging
import re
from uuid import uuid4
from app.core.version import APP_VERSION, SCHEMA_VERSION

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(_app: FastAPI):
    await Database.connect()
    resumed = await recover_narrative_analysis_jobs(Database.get_db())
    if resumed:
        logger.info("Resumed %s queued narrative analysis job(s)", resumed)
    try:
        yield
    finally:
        await Database.disconnect()


app = FastAPI(title="NovelForge API", version=APP_VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_host_list)


@app.middleware("http")
async def require_local_access_token(request: Request, call_next):
    supplied_reference = request.headers.get("X-Request-ID", "").strip()
    reference_id = supplied_reference if re.fullmatch(r"[A-Za-z0-9-]{8,80}", supplied_reference) else str(uuid4())
    request.state.reference_id = reference_id
    configured = settings.local_access_token.strip()
    if configured and request.url.path.startswith("/api/"):
        supplied = request.headers.get("X-NovelForge-Token", "")
        if supplied != configured:
            return JSONResponse(
                status_code=401,
                content={"detail": "Local access token required", "reference_id": reference_id},
                headers={"X-NovelForge-Reference": reference_id},
            )
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("Unhandled request failure. reference=%s path=%s", reference_id, request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "detail": "NovelForge could not complete this operation. Existing work is unchanged unless the screen already confirmed a save.",
                "reference_id": reference_id,
            },
            headers={"X-NovelForge-Reference": reference_id},
        )
    response.headers["X-NovelForge-Reference"] = reference_id
    return response

app.include_router(projects.router)
app.include_router(workflow.router)
app.include_router(data.router)
app.include_router(planning.router)
app.include_router(development.router)
app.include_router(drafting.router)
app.include_router(editorial.router)
app.include_router(manuscript.router)
app.include_router(intelligence.router)
app.include_router(interactive.router)
app.include_router(product_experience.router)
app.include_router(rc6.router)
app.include_router(rc6.library_router)
app.include_router(settings_api.router)
app.include_router(settings_api.ai_router)
app.include_router(messages.router)
app.include_router(operations.router)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "novelforge-api", "version": APP_VERSION}


@app.get("/health/live")
async def liveness_check():
    return {"status": "alive"}


@app.get("/health/ready")
async def readiness_check():
    try:
        await Database.get_db().command("ping")
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database is not ready") from exc
    return {
        "status": "ready",
        "database": settings.database_name,
        "version": APP_VERSION,
        "schema_version": SCHEMA_VERSION,
        "deployment": "local_private_beta",
    }
