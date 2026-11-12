from __future__ import annotations

from typing import Any, List, Optional

import tree_sitter_java as tsj
from tree_sitter import Language, Parser

from app.analyzer.base import BaseParser
from app.analyzer.models import (
    CallEntity,
    ClassEntity,
    FileAnalysis,
    ImportEntity,
    MethodEntity,
)

JAVA_LANG = Language(tsj.language())

CLASS_NODE_TYPES = (
    "class_declaration",
    "interface_declaration",
    "enum_declaration",
    "record_declaration",
)
METHOD_NODE_TYPES = ("method_declaration", "constructor_declaration")


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


def _type_name(node: Any, source_bytes: bytes) -> str:
    if node.type == "generic_type":
        name_node = node.child_by_field_name("name")
        if name_node is not None:
            return _text(name_node, source_bytes)
    return _text(node, source_bytes)


def _params(node: Any, source_bytes: bytes) -> List[str]:
    params_node = node.child_by_field_name("parameters")
    if params_node is None:
        return []

    names: List[str] = []
    for child in params_node.named_children:
        name_node = child.child_by_field_name("name")
        if name_node is not None:
            names.append(_text(name_node, source_bytes))
            continue
        ident = next(
            (c for c in reversed(child.named_children) if c.type == "identifier"), None
        )
        if ident is not None:
            names.append(_text(ident, source_bytes))
    return names


def _enclosing_class(node: Any, source_bytes: bytes) -> str:
    parent = node.parent
    while parent is not None:
        if parent.type in METHOD_NODE_TYPES:
            return ""
        if parent.type in CLASS_NODE_TYPES:
            return _name_of(parent, source_bytes)
        parent = parent.parent
    return ""


def _superclass(node: Any, source_bytes: bytes) -> Optional[str]:
    superclass = node.child_by_field_name("superclass")
    if superclass is not None:
        for child in superclass.named_children:
            if child.type in ("type_identifier", "generic_type"):
                return _type_name(child, source_bytes)
    return None


def _interfaces(node: Any, source_bytes: bytes) -> List[str]:
    result: List[str] = []
    interfaces = node.child_by_field_name("interfaces")
    if interfaces is None:
        return result
    for child in interfaces.named_children:
        if child.type == "type_list":
            for item in child.named_children:
                if item.type in ("type_identifier", "generic_type"):
                    result.append(_type_name(item, source_bytes))
        elif child.type in ("type_identifier", "generic_type"):
            result.append(_type_name(child, source_bytes))
    return result


def _walk(node: Any, source_bytes: bytes, analysis: FileAnalysis) -> None:
    if node.type in CLASS_NODE_TYPES:
        analysis.classes.append(
            ClassEntity(
                name=_name_of(node, source_bytes),
                file_path=analysis.file_path,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                extends=_superclass(node, source_bytes),
                implements=_interfaces(node, source_bytes),
                is_exported=True,
            )
        )
    elif node.type in METHOD_NODE_TYPES:
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
                    is_async=False,
                )
            )
    elif node.type == "import_declaration":
        ident = next(
            (
                c
                for c in node.named_children
                if c.type in ("scoped_identifier", "identifier")
            ),
            None,
        )
        if ident is not None:
            source = _text(ident, source_bytes)
            analysis.imports.append(
                ImportEntity(
                    file_path=analysis.file_path,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    source=source,
                    names=[source],
                )
            )
    elif node.type == "method_invocation":
        name_node = node.child_by_field_name("name")
        if name_node is not None:
            analysis.calls.append(
                CallEntity(
                    name=_text(name_node, source_bytes),
                    file_path=analysis.file_path,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                )
            )
    elif node.type == "object_creation_expression":
        type_node = node.child_by_field_name("type")
        if type_node is not None:
            analysis.calls.append(
                CallEntity(
                    name=_type_name(type_node, source_bytes),
                    file_path=analysis.file_path,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                )
            )

    for child in node.named_children:
        _walk(child, source_bytes, analysis)


class JavaParser(BaseParser):
    def __init__(self) -> None:
        self._parser = Parser(JAVA_LANG)

    def language_name(self) -> str:
        return "java"

    def parse(self, code: str, file_path: str) -> FileAnalysis:
        source_bytes = code.encode("utf-8")
        tree = self._parser.parse(source_bytes)
        analysis = FileAnalysis(file_path=file_path, language="java")
        _walk(tree.root_node, source_bytes, analysis)
        return analysis
