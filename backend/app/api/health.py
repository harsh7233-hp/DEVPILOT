import os
import time
from typing import Any, Dict

from fastapi import APIRouter

from app.config import settings
from app.services.ai import _get_api_config, probe_llm
from app.services.search.embeddings import _get_config as _get_embedding_config

router = APIRouter()

_probe_cache: Dict[str, Any] = {"at": 0.0, "result": None}
_PROBE_TTL_SECONDS = 60


@router.get("/health")
async def health_check():
    commit = os.getenv("RENDER_GIT_COMMIT", "")[:7]
    return {
        "status": "ok",
        "service": "devpilot-backend",
        "commit": commit or "local",
        "graph_backend": (
            "neo4j"
            if settings.graph_backend == "neo4j" and settings.neo4j_password
            else "memory"
        ),
    }


@router.get("/health/ai")
async def ai_status(probe: bool = False):
    """Reports whether the Groq AI layer is configured. Never exposes secrets."""
    config = _get_api_config()
    embedding_config = _get_embedding_config()
    result: Dict[str, Any] = {
        "ai_configured": config is not None,
        "model": config["model"] if config else None,
        "embeddings_configured": embedding_config is not None,
        "embeddings_mode": "external" if embedding_config else "local",
    }

    if probe:
        if not config:
            result["probe"] = "not_configured"
            return result

        now = time.time()
        cached = _probe_cache["result"]
        if cached is not None and now - _probe_cache["at"] < _PROBE_TTL_SECONDS:
            result.update(cached)
            return result

        try:
            out = await probe_llm()
            probe_result = {"probe": "ok", "probe_response": out.strip()[:50]}
        except Exception as exc:
            probe_result = {
                "probe": "error",
                "probe_error": f"{exc.__class__.__name__}: {str(exc)[:300]}",
            }
        _probe_cache.update({"at": now, "result": probe_result})
        result.update(probe_result)

    return result
