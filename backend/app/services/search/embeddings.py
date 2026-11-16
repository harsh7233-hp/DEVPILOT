from __future__ import annotations

import hashlib
import math
import re
from typing import List, Optional

import httpx

from app.config import settings

DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536
MAX_BATCH_SIZE = 20
MAX_TEXT_CHARS = 8000


def _get_config() -> Optional[dict]:
    api_key = settings.embedding_api_key or settings.groq_api_key
    if not api_key:
        return None
    base_url = settings.embedding_base_url or ""
    if not base_url:
        return None
    return {
        "api_key": api_key,
        "base_url": base_url,
        "model": settings.embedding_model or DEFAULT_EMBEDDING_MODEL,
    }


def _truncate(text: str) -> str:
    if len(text) > MAX_TEXT_CHARS:
        return text[:MAX_TEXT_CHARS]
    return text


def _local_embedding(text: str) -> List[float]:
    """Deterministic hashing vectorizer used when no embedding provider is set.

    It is lexical rather than semantic, but keeps Code Explorer search usable
    without requiring a second paid API.
    """
    vec = [0.0] * EMBEDDING_DIM
    tokens = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]{1,}", text.lower())
    for token in tokens:
        h = int.from_bytes(
            hashlib.blake2b(token.encode(), digest_size=8).digest(), "big"
        )
        vec[h % EMBEDDING_DIM] += 2.0
        for i in range(max(1, len(token) - 2)):
            gram = token[i : i + 3]
            h = int.from_bytes(
                hashlib.blake2b(gram.encode(), digest_size=8).digest(), "big"
            )
            vec[h % EMBEDDING_DIM] += 1.0
    norm = math.sqrt(sum(v * v for v in vec))
    if norm:
        vec = [v / norm for v in vec]
    return vec


async def _call_embedding_api(texts: List[str]) -> List[List[float]]:
    config = _get_config()
    if not config:
        raise RuntimeError(
            "Embedding API not configured. Set EMBEDDING_API_KEY and EMBEDDING_BASE_URL "
            "(Groq does not support embeddings — use OpenAI, Cohere, or another provider)."
        )

    url = f"{config['base_url']}/embeddings"
    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": config["model"],
        "input": texts,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code != 200:
            raise RuntimeError(f"Embedding API error {resp.status_code}: {resp.text[:300]}")
        data = resp.json()
        sorted_data = sorted(data["data"], key=lambda x: x["index"])
        return [item["embedding"] for item in sorted_data]


async def generate_embeddings(texts: List[str]) -> List[List[float]]:
    truncated = [_truncate(t) for t in texts]
    if not _get_config():
        return [_local_embedding(t) for t in truncated]

    all_embeddings: List[List[float]] = []

    for i in range(0, len(truncated), MAX_BATCH_SIZE):
        batch = truncated[i : i + MAX_BATCH_SIZE]
        batch_embeddings = await _call_embedding_api(batch)
        all_embeddings.extend(batch_embeddings)

    return all_embeddings


def cosine_similarity(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
