from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.ai import router as ai_router
from app.api.analysis import router as analysis_router
from app.api.auth import router as auth_router
from app.api.code_review import router as code_review_router
from app.api.dashboard import router as dashboard_router
from app.api.graph import router as graph_router
from app.api.health import router as health_router
from app.api.impact import router as impact_router
from app.api.intelligence import router as intelligence_router
from app.api.repositories import router as repos_router
from app.api.search import router as search_router
from app.api.notifications import router as notifications_router
from app.api.security import router as security_router

app = FastAPI(
    title="DevPilot API",
    description="AI-powered developer platform for codebase analysis and change impact",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(repos_router, prefix="/api")
app.include_router(analysis_router, prefix="/api")
app.include_router(graph_router, prefix="/api")
app.include_router(impact_router, prefix="/api")
app.include_router(ai_router, prefix="/api")
app.include_router(search_router, prefix="/api")
app.include_router(code_review_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(intelligence_router, prefix="/api")
app.include_router(security_router, prefix="/api")
app.include_router(notifications_router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "DevPilot API", "version": "0.1.0"}
