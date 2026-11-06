from fastapi import APIRouter

from app.config import settings
from app.services.ai import _get_api_config

router = APIRouter()


@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "devpilot-backend"}


@router.get("/health/ai")
async def ai_status():
    """Reports whether the Groq AI layer is configured. Never exposes secrets."""
    config = _get_api_config()
    embeddings = bool(settings.embedding_base_url and settings.embedding_api_key)
    return {
        "ai_configured": config is not None,
        "model": config["model"] if config else None,
        "embeddings_configured": embeddings,
    }
