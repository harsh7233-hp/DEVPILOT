from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


MAX_CHUNK_LINES = 80
OVERLAP_LINES = 5


class CodeChunk:
    __slots__ = ("file_path", "entity_name", "entity_kind", "snippet", "start_line", "end_line")

    def __init__(
        self,
        file_path: str,
        entity_name: str,
        entity_kind: str,
        snippet: str,
        start_line: int,
        end_line: int,
    ) -> None:
        self.file_path = file_path
        self.entity_name = entity_name
        self.entity_kind = entity_kind
        self.snippet = snippet
        self.start_line = start_line
        self.end_line = end_line

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "entity_name": self.entity_name,
            "entity_kind": self.entity_kind,
            "snippet": self.snippet,
            "start_line": self.start_line,
            "end_line": self.end_line,
        }


def _extract_lines(source: str, start: int, end: int) -> str:
    lines = source.split("\n")
    s = max(0, start - 1)
    e = min(len(lines), end)
    return "\n".join(lines[s:e])


def chunk_parsed_file(parsed: Dict[str, Any], source: str) -> List[CodeChunk]:
    fp = parsed.get("file_path", "")
    lines = source.split("\n")
    chunks: List[CodeChunk] = []

    for fn in parsed.get("functions", []):
        name = fn.get("name", "")
        s = fn.get("start_line", 0)
        e = fn.get("end_line", 0)
        if s and e:
            snippet = _extract_lines(source, s, e)
            chunks.append(CodeChunk(fp, name, "function", snippet, s, e))

    for cls in parsed.get("classes", []):
        name = cls.get("name", "")
        s = cls.get("start_line", 0)
        e = cls.get("end_line", 0)
        if s and e:
            snippet = _extract_lines(source, s, e)
            chunks.append(CodeChunk(fp, name, "class", snippet, s, e))

    for m in parsed.get("methods", []):
        name = m.get("name", "")
        cls_name = m.get("class_name", "")
        s = m.get("start_line", 0)
        e = m.get("end_line", 0)
        if s and e:
            snippet = _extract_lines(source, s, e)
            display = f"{cls_name}.{name}" if cls_name else name
            chunks.append(CodeChunk(fp, display, "method", snippet, s, e))

    chunk_starts = set()
    for c in chunks:
        for ln in range(c.start_line - 1, c.end_line):
            chunk_starts.add(ln)

    if parsed.get("imports"):
        imp_lines = []
        first_line = None
        for imp in parsed["imports"]:
            s = imp.get("start_line", 0)
            if s:
                if first_line is None or s < first_line:
                    first_line = s
                line_idx = s - 1
                if 0 <= line_idx < len(lines):
                    imp_lines.append(lines[line_idx])
        if imp_lines and first_line:
            snippet = "\n".join(imp_lines)
            chunks.append(CodeChunk(fp, "imports", "imports", snippet, first_line, first_line + len(imp_lines) - 1))

    if not chunks and lines:
        for block_start in range(0, len(lines), MAX_CHUNK_LINES - OVERLAP_LINES):
            block_end = min(len(lines), block_start + MAX_CHUNK_LINES)
            snippet = "\n".join(lines[block_start:block_end])
            if snippet.strip():
                chunks.append(CodeChunk(fp, fp.split("/")[-1] if fp else "block", "file", snippet, block_start + 1, block_end))

    return chunks


def chunk_all_files(parsed_files: List[Dict[str, Any]], sources: Dict[str, str]) -> List[CodeChunk]:
    all_chunks: List[CodeChunk] = []
    for pf in parsed_files:
        fp = pf.get("file_path", "")
        source = sources.get(fp, "")
        if source:
            all_chunks.extend(chunk_parsed_file(pf, source))
    return all_chunks
