from __future__ import annotations

from typing import Any, List, Optional

import tree_sitter_python as tsp
from tree_sitter import Language, Parser

from app.analyzer.base import BaseParser
from app.analyzer.models import (
    CallEntity,
    ClassEntity,
    FileAnalysis,
    FunctionEntity,
    ImportEntity,
    MethodEntity,
)

PY_LANG = Language(tsp.language())


def _text(node: Any, source_bytes: bytes) -> str:
    return source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _name_of(node: Any, source_bytes: bytes) -> str:
    name_node = node.child_by_field_name("name")
    if name_node is not None:
        return _text(name_node, source_bytes)
    for child in node.named_children:
        if child.type == "identifier":
            return _text(child, source_bytes)
    return "<anonymous>"


def _params(node: Any, source_bytes: bytes) -> List[str]:
    params_node = node.child_by_field_name("parameters")
    if params_node is None:
        return []

    names: List[str] = []
    for child in params_node.named_children:
        if child.type == "identifier":
            names.append(_text(child, source_bytes))
        elif child.type in ("typed_parameter", "default_parameter", "typed_default_parameter"):
            name_node = child.child_by_field_name("name")
            if name_node is not None:
                names.append(_text(name_node, source_bytes))
            else:
                ident = next(
                    (c for c in child.named_children if c.type == "identifier"), None
                )
                if ident is not None:
                    names.append(_text(ident, source_bytes))
        elif child.type in ("list_splat_pattern", "dictionary_splat_pattern"):
            ident = next(
                (c for c in child.named_children if c.type == "identifier"), None
            )
            if ident is not None:
                names.append(_text(ident, source_bytes))
    return names


def _is_async(node: Any) -> bool:
    return any(child.type == "async" for child in node.children)


def _enclosing_class(node: Any, source_bytes: bytes) -> str:
    parent = node.parent
    while parent is not None:
        if parent.type == "function_definition":
            return ""
        if parent.type == "class_definition":
            return _name_of(parent, source_bytes)
        parent = parent.parent
    return ""


def _class_bases(node: Any, source_bytes: bytes) -> List[str]:
    bases: List[str] = []
    for child in node.named_children:
        if child.type == "argument_list":
            for base in child.named_children:
                if base.type in ("identifier", "attribute", "subscript"):
                    bases.append(_text(base, source_bytes))
            break
    return bases


def _walk(node: Any, source_bytes: bytes, analysis: FileAnalysis) -> None:
    if node.type == "decorated_definition":
        for child in node.named_children:
            if child.type in ("function_definition", "class_definition"):
                _walk(child, source_bytes, analysis)
        return

    if node.type == "class_definition":
        bases = _class_bases(node, source_bytes)
        analysis.classes.append(
            ClassEntity(
                name=_name_of(node, source_bytes),
                file_path=analysis.file_path,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                extends=bases[0] if bases else None,
                implements=bases[1:],
                is_exported=True,
            )
        )
    elif node.type == "function_definition":
        class_name = _enclosing_class(node, source_bytes)
        if class_name:
            analysis.methods.append(
                MethodEntity(
                    name=_name_of(node, source_bytes),
                    file_path=analysis.file_path,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    class_name=class_name,
                    params=_params(node, source_bytes),
                    is_async=_is_async(node),
                )
            )
        else:
            analysis.functions.append(
                FunctionEntity(
                    name=_name_of(node, source_bytes),
                    file_path=analysis.file_path,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    params=_params(node, source_bytes),
                    is_async=_is_async(node),
                    is_exported=True,
                )
            )
    elif node.type == "import_statement":
        for child in node.named_children:
            if child.type == "dotted_name":
                source = _text(child, source_bytes)
                analysis.imports.append(
                    ImportEntity(
                        file_path=analysis.file_path,
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                        source=source,
                        names=[source],
                    )
                )
    elif node.type == "import_from_statement":
        source = ""
        names: List[str] = []
        for child in node.named_children:
            if child.type in ("dotted_name", "relative_import"):
                if not source:
                    source = _text(child, source_bytes)
                else:
                    names.append(_text(child, source_bytes))
            elif child.type == "wildcard_import":
                names.append("*")
        if source:
            analysis.imports.append(
                ImportEntity(
                    file_path=analysis.file_path,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    source=source,
                    names=names,
                    import_kind="namespace" if "*" in names else "named",
                )
            )
    elif node.type == "call":
        func_node = node.child_by_field_name("function")
        if func_node is not None:
            if func_node.type == "attribute":
                attr = func_node.child_by_field_name("attribute")
                name = (
                    _text(attr, source_bytes)
                    if attr is not None
                    else _text(func_node, source_bytes)
                )
            else:
                name = _text(func_node, source_bytes)
            analysis.calls.append(
                CallEntity(
                    name=name,
                    file_path=analysis.file_path,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                )
            )

    for child in node.named_children:
        _walk(child, source_bytes, analysis)


class PythonParser(BaseParser):
    def __init__(self) -> None:
        self._parser = Parser(PY_LANG)

    def language_name(self) -> str:
        return "python"

    def parse(self, code: str, file_path: str) -> FileAnalysis:
        source_bytes = code.encode("utf-8")
        tree = self._parser.parse(source_bytes)
        analysis = FileAnalysis(file_path=file_path, language="python")
        _walk(tree.root_node, source_bytes, analysis)
        return analysis
