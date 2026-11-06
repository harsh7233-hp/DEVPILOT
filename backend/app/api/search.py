from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.services.analysis import get_job, get_jobs_for_repo
from app.services.search.chunker import chunk_all_files
from app.services.search.embeddings import generate_embeddings
from app.services.search.store import get_store, delete_store
from app.services.session import SESSION_COOKIE, decode_session

router = APIRouter(prefix="/search", tags=["search"])


def _get_token(request: Request) -> str:
    cookie = request.cookies.get(SESSION_COOKIE)
    if not cookie:
        raise HTTPException(status_code=401, detail="Not authenticated")
    session = decode_session(cookie)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return session["token"]


def _repo_id(owner: str, repo: str) -> str:
    raw = f"{owner}/{repo}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


class SemanticSearchRequest(BaseModel):
    owner: str
    repo: str
    query: str
    top_k: int = 10


class IndexRequest(BaseModel):
    owner: str
    repo: str


@router.post("/semantic")
async def semantic_search(request: Request, body: SemanticSearchRequest):
    _get_token(request)

    if not body.query or len(body.query) > 2000:
        raise HTTPException(status_code=400, detail="Query must be 1-2000 characters")
    if not re.match(r'^[a-zA-Z0-9._-]+$', body.owner) or len(body.owner) > 100:
        raise HTTPException(status_code=400, detail="Invalid owner format")
    if not re.match(r'^[a-zA-Z0-9._-]+$', body.repo) or len(body.repo) > 100:
        raise HTTPException(status_code=400, detail="Invalid repo format")

    rid = _repo_id(body.owner, body.repo)
    store = get_store(rid)

    if not store.is_indexed:
        _build_index_from_jobs(rid, body.owner, body.repo)
        store = get_store(rid)

    if not store.is_indexed:
        raise HTTPException(
            status_code=404,
            detail="No indexed code found. Run an analysis first.",
        )

    try:
        query_embeddings = await generate_embeddings([body.query])
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    query_vec = query_embeddings[0]
    results = store.search(query_vec, top_k=body.top_k, min_score=0.15)

    return {
        "results": [
            {
                "file": chunk.get("file_path", ""),
                "entity": chunk.get("entity_name", ""),
                "kind": chunk.get("entity_kind", ""),
                "snippet": chunk.get("snippet", ""),
                "start_line": chunk.get("start_line", 0),
                "end_line": chunk.get("end_line", 0),
                "score": round(score, 4),
            }
            for chunk, score in results
        ],
        "total_indexed": store.count,
        "query": body.query,
    }


@router.post("/index")
async def index_repository(request: Request, body: IndexRequest):
    _get_token(request)
    rid = _repo_id(body.owner, body.repo)
    store = get_store(rid)
    store.clear()

    count = _build_index_from_jobs(rid, body.owner, body.repo)
    if count == 0:
        raise HTTPException(
            status_code=404,
            detail="No parsed files found. Run an analysis first.",
        )

    return {"status": "indexed", "chunks": count, "repo_id": rid}


@router.delete("/{owner}/{repo}/index")
async def delete_index(request: Request, owner: str, repo: str):
    _get_token(request)
    rid = _repo_id(owner, repo)
    delete_store(rid)
    return {"status": "deleted"}


def _build_index_from_jobs(rid: str, owner: str, repo: str) -> int:
    jobs = get_jobs_for_repo(owner, repo)
    completed = [j for j in jobs if j.status == "completed" and j.parsed_files]
    if not completed:
        return 0

    latest = max(completed, key=lambda j: j.id)
    sources: Dict[str, str] = {}
    for f in latest.files:
        fp = f.get("path", "")
        content = f.get("content", "")
        if fp and content:
            sources[fp] = content

    chunks = chunk_all_files(latest.parsed_files, sources)
    if not chunks:
        return 0

    chunk_dicts = [c.to_dict() for c in chunks]
    texts = [
        f"{c.entity_name} ({c.entity_kind}) in {c.file_path}\n{c.snippet}"
        for c in chunks
    ]

    import asyncio

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                embeddings = pool.submit(
                    asyncio.run, generate_embeddings(texts)
                ).result()
        else:
            embeddings = loop.run_until_complete(generate_embeddings(texts))
    except RuntimeError:
        return 0

    store = get_store(rid)
    store.add(embeddings, chunk_dicts)
    return len(chunks)
