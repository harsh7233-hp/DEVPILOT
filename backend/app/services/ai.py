from __future__ import annotations

import hashlib
import json
import re
import time
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings

# ── Provider abstraction ──────────────────────────────────────────

DEFAULT_MODEL = "openai/gpt-oss-20b"
MAX_CONTEXT_CHARS = 40_000
MAX_HISTORY_TURNS = 10
ANSWER_MAX_TOKENS = 2048


def _get_api_config() -> Optional[Dict[str, str]]:
    api_key = settings.groq_api_key
    if not api_key:
        return None
    return {
        "api_key": api_key,
        "base_url": settings.groq_base_url or "https://api.groq.com/openai/v1",
        "model": settings.groq_model or DEFAULT_MODEL,
    }


async def _call_llm(messages: List[Dict[str, str]], temperature: float = 0.3) -> str:
    config = _get_api_config()
    if not config:
        raise RuntimeError("LLM not configured. Set GROQ_API_KEY environment variable.")

    url = f"{config['base_url']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": config["model"],
        "messages": messages,
        "temperature": temperature,
        "max_tokens": ANSWER_MAX_TOKENS,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code != 200:
            detail = resp.text[:500]
            raise RuntimeError(f"LLM API error {resp.status_code}: {detail}")
        data = resp.json()
        return data["choices"][0]["message"]["content"]


# ── Context retrieval ─────────────────────────────────────────────

def _search_nodes_by_keywords(
    nodes: List[Dict[str, Any]], keywords: List[str]
) -> List[Dict[str, Any]]:
    scored = []
    for n in nodes:
        name = (n.get("name") or "").lower()
        fp = (n.get("file_path") or n.get("path") or "").lower()
        label = (n.get("label") or "").lower()
        combined = f"{name} {fp} {label}"

        hits = sum(1 for kw in keywords if kw in combined)
        if hits > 0:
            scored.append((hits, n))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [n for _, n in scored[:30]]


def _search_rels_for_nodes(
    rels: List[Dict[str, Any]], node_ids: set
) -> List[Dict[str, Any]]:
    return [
        r for r in rels
        if r.get("from_id") in node_ids or r.get("to_id") in node_ids
    ]


def _format_node_for_context(n: Dict[str, Any]) -> str:
    label = n.get("label") or n.get("labels", ["?"])[0] if isinstance(n.get("labels"), list) else n.get("label", "?")
    name = n.get("name", "?")
    fp = n.get("file_path") or n.get("path") or ""
    lines = []
    if n.get("start_line") and n.get("end_line"):
        lines = [f"  lines {n['start_line']}-{n['end_line']}"]
    extras = []
    if n.get("is_async"):
        extras.append("async")
    if n.get("is_exported"):
        extras.append("exported")
    if n.get("extends"):
        extras.append(f"extends {n['extends']}")
    if n.get("method"):
        extras.append(f"method={n['method']}")

    parts = [f"[{label}] {name}"]
    if fp:
        parts[0] += f"  ({fp})"
    if lines:
        parts.append(lines[0])
    if extras:
        parts.append(f"  {', '.join(extras)}")
    return "\n".join(parts)


def _format_rel_for_context(r: Dict[str, Any]) -> str:
    return f"  {r.get('from_name', '?')} --[{r.get('type', '?')}]--> {r.get('to_name', '?')}"


def build_context(
    question: str,
    nodes: List[Dict[str, Any]],
    rels: List[Dict[str, Any]],
    repo_owner: str = "",
    repo_name: str = "",
) -> str:
    keywords = re.findall(r'\w+', question.lower())
    relevant_nodes = _search_nodes_by_keywords(nodes, keywords)

    if not relevant_nodes:
        relevant_nodes = nodes[:30]

    node_ids = {n.get("node_id") for n in relevant_nodes}
    relevant_rels = _search_rels_for_nodes(rels, node_ids)

    parts = []
    parts.append(f"Repository: {repo_owner}/{repo_name}" if repo_owner else "Repository: unknown")
    parts.append(f"Total nodes: {len(nodes)}, Total relationships: {len(rels)}")
    parts.append("")

    parts.append("RELEVANT CODE ENTITIES:")
    for n in relevant_nodes:
        parts.append(_format_node_for_context(n))
    parts.append("")

    if relevant_rels:
        parts.append("RELEVANT RELATIONSHIPS:")
        for r in relevant_rels[:50]:
            parts.append(_format_rel_for_context(r))
        parts.append("")

    context = "\n".join(parts)
    if len(context) > MAX_CONTEXT_CHARS:
        context = context[:MAX_CONTEXT_CHARS] + "\n\n[Context truncated to fit token limit]"
    return context


# ── Prompt templates ──────────────────────────────────────────────

SYSTEM_PROMPT = """You are DevPilot AI, an expert codebase assistant. You answer questions about a software repository using ONLY the evidence provided in the context below.

RULES:
1. ONLY reference code entities and relationships that appear in the provided context.
2. If the context does not contain enough information to answer, say so clearly. Do NOT guess or hallucinate.
3. Always cite source files and line numbers when available (use the format `file_path:line`).
4. Be concise and technical. Use code references when explaining.
5. When explaining a function or class, describe what it does, its inputs/outputs, and its relationships.
6. When asked "what calls X", trace the relationship graph from the context.
7. Format your answer with clear sections and bullet points where appropriate.

AVAILABLE CONTEXT:
{context}
"""

HISTORY_ROLE_MAP = {"user": "user", "assistant": "assistant"}


# ── Conversation history ──────────────────────────────────────────

_conversations: Dict[str, List[Dict[str, str]]] = {}


def _make_conv_id(owner: str, repo: str, user_token: str) -> str:
    raw = f"{owner}:{repo}:{user_token}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def get_history(owner: str, repo: str, user_token: str) -> List[Dict[str, str]]:
    cid = _make_conv_id(owner, repo, user_token)
    return _conversations.get(cid, [])


def append_history(owner: str, repo: str, user_token: str, role: str, content: str) -> None:
    cid = _make_conv_id(owner, repo, user_token)
    if cid not in _conversations:
        _conversations[cid] = []
    hist = _conversations[cid]
    hist.append({"role": role, "content": content})
    if len(hist) > MAX_HISTORY_TURNS * 2:
        _conversations[cid] = hist[-(MAX_HISTORY_TURNS * 2):]


def clear_history(owner: str, repo: str, user_token: str) -> None:
    cid = _make_conv_id(owner, repo, user_token)
    _conversations.pop(cid, None)


# ── Answer generation ─────────────────────────────────────────────

async def answer_question(
    question: str,
    nodes: List[Dict[str, Any]],
    rels: List[Dict[str, Any]],
    owner: str,
    repo: str,
    user_token: str,
) -> Dict[str, Any]:
    context = build_context(question, nodes, rels, owner, repo)
    history = get_history(owner, repo, user_token)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(context=context)},
    ]
    for h in history[-MAX_HISTORY_TURNS * 2:]:
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": question})

    append_history(owner, repo, user_token, "user", question)

    try:
        answer = await _call_llm(messages)
    except RuntimeError:
        answer = (
            "I cannot answer this question because the AI provider is not configured. "
            "Set the GROQ_API_KEY environment variable to enable AI responses."
        )
        append_history(owner, repo, user_token, "assistant", answer)
        return {
            "answer": answer,
            "sources": [],
            "error": "LLM not configured",
        }

    append_history(owner, repo, user_token, "assistant", answer)

    sources = _extract_sources(answer, nodes)

    return {
        "answer": answer,
        "sources": sources,
        "error": None,
    }


def _extract_sources(answer: str, nodes: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    sources = []
    seen = set()

    file_pattern = re.compile(r'`?([a-zA-Z0-9_/.-]+\.\w+):?(\d+)?`?')
    for match in file_pattern.finditer(answer):
        fp = match.group(1)
        line = match.group(2)
        key = f"{fp}:{line or ''}"
        if key not in seen and ("/" in fp or "." in fp):
            seen.add(key)
            seen.add(fp)
            sources.append({"file": fp, "line": line or ""})

    for n in nodes:
        fp = n.get("file_path") or n.get("path") or ""
        name = n.get("name", "")
        if fp and fp in answer:
            dedup_key = fp
            if dedup_key not in seen:
                seen.add(dedup_key)
                sources.append({"file": fp, "line": str(n.get("start_line", "")), "entity": name})

    return sources[:20]
