from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Optional

from app.analyzer.models import FileAnalysis

SUPPORTED_EXTENSIONS = {
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".py": "python",
    ".pyi": "python",
    ".java": "java",
}


def detect_language(file_path: str) -> Optional[str]:
    ext = os.path.splitext(file_path)[1].lower()
    return SUPPORTED_EXTENSIONS.get(ext)


def get_supported_extensions():
    return set(SUPPORTED_EXTENSIONS.keys())


class BaseParser(ABC):
    @abstractmethod
    def language_name(self) -> str:
        pass

    @abstractmethod
    def parse(self, code: str, file_path: str) -> FileAnalysis:
        pass


_parser_registry = {}


def register_parser(lang: str, parser: BaseParser) -> None:
    _parser_registry[lang] = parser


def get_parser(lang: str) -> Optional[BaseParser]:
    return _parser_registry.get(lang)


def analyze_file(code: str, file_path: str) -> Optional[FileAnalysis]:
    lang = detect_language(file_path)
    if lang is None:
        return None
    parser = get_parser(lang)
    if parser is None:
        return None
    return parser.parse(code, file_path)
