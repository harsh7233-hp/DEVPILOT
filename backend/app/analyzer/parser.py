from __future__ import annotations

from typing import Any, Dict, List, Optional

import tree_sitter_javascript as tsjs
import tree_sitter_typescript as tsts
from tree_sitter import Language, Parser

from app.analyzer.base import BaseParser, register_parser
from app.analyzer.models import (
    CallEntity,
    ClassEntity,
    ExportEntity,
    FileAnalysis,
    FunctionEntity,
    ImportEntity,
    MethodEntity,
)

JS_LANG = Language(tsjs.language())
TS_LANG = Language(tsts.language_typescript())
TSX_LANG = Language(tsts.language_tsx())


def _get_node_text(node: Any, source_bytes: bytes) -> str:
    return source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _get_params(func_node: Any, source_bytes: bytes) -> List[str]:
    params_node = func_node.child_by_field_name("parameters")
    if params_node is None:
        return []
    names = []
    for child in params_node.named_children:
        if child.type in ("identifier", "required_parameter"):
            names.append(_get_node_text(child, source_bytes))
        elif child.type == "formal_parameter":
            for p in child.named_children:
                names.append(_get_node_text(p, source_bytes))
    return names


def _walk_imports(node: Any, source_bytes: bytes, file_path: str) -> List[ImportEntity]:
    results: List[ImportEntity] = []
    if node.type == "import_statement":
        results.append(_parse_import(node, source_bytes, file_path))
    for child in node.named_children:
        results.extend(_walk_imports(child, source_bytes, file_path))
    return results


def _parse_import(node: Any, source_bytes: bytes, file_path: str) -> ImportEntity:
    names: List[str] = []
    source = ""
    kind = "named"
    for child in node.named_children:
        if child.type == "import_clause":
            for sub in child.named_children:
                if sub.type == "identifier":
                    names.append(_get_node_text(sub, source_bytes))
                    kind = "default"
                elif sub.type == "named_imports":
                    for spec in sub.named_children:
                        if spec.type == "import_specifier":
                            names.append(_get_node_text(spec, source_bytes))
        elif child.type == "string":
            source = _get_node_text(child, source_bytes).strip("'\"")
    if kind != "default" and len(names) > 0:
        kind = "named"
    if len(names) == 0 and node.text and b"* as" in node.text:
        kind = "namespace"
        names = ["*"]
    return ImportEntity(
        file_path=file_path,
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        source=source,
        names=names,
        import_kind=kind,
    )


def _walk_exports(node: Any, source_bytes: bytes, file_path: str) -> List[ExportEntity]:
    results: List[ExportEntity] = []
    if node.type in (
        "export_statement",
        "export_default_declaration",
        "export_declaration",
    ):
        results.append(_parse_export(node, source_bytes, file_path))
    for child in node.named_children:
        results.extend(_walk_exports(child, source_bytes, file_path))
    return results


def _parse_export(node: Any, source_bytes: bytes, file_path: str) -> ExportEntity:
    name = ""
    kind = "named"
    if node.type == "export_default_declaration":
        kind = "default"
        for child in node.named_children:
            if child.type == "identifier":
                name = _get_node_text(child, source_bytes)
                break
            elif child.type in ("function_declaration", "class_declaration", "abstract_class_declaration"):
                n = child.child_by_field_name("name")
                if n:
                    name = _get_node_text(n, source_bytes)
                break
        if not name:
            name = "default"
    else:
        for child in node.named_children:
            if child.type in ("function_declaration", "class_declaration", "abstract_class_declaration"):
                n = child.child_by_field_name("name")
                if n:
                    name = _get_node_text(n, source_bytes)
                break
            elif child.type == "identifier":
                name = _get_node_text(child, source_bytes)
                break
            elif child.type == "export_clause":
                specifiers = []
                for spec in child.named_children:
                    if spec.type == "export_specifier":
                        orig = spec.child_by_field_name("name")
                        if orig:
                            specifiers.append(_get_node_text(orig, source_bytes))
                if specifiers:
                    name = ", ".join(specifiers)
                break
            elif child.type == "type_identifier":
                name = _get_node_text(child, source_bytes)
                break
    if not name:
        text = _get_node_text(node, source_bytes)
        kind = "namespace" if "* as" in text else "unnamed"
        name = kind
    return ExportEntity(
        name=name,
        file_path=file_path,
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        export_kind=kind,
    )


def _walk_classes(
    node: Any, source_bytes: bytes, file_path: str, is_exported: bool = False
) -> List[ClassEntity]:
    results: List[ClassEntity] = []
    if node.type in ("class_declaration", "abstract_class_declaration"):
        results.append(_parse_class(node, source_bytes, file_path, is_exported))
    if node.type == "export_statement":
        exp = _parse_export(node, source_bytes, file_path)
        if exp.export_kind in ("named", "default"):
            for child in node.named_children:
                if child.type in ("class_declaration", "abstract_class_declaration"):
                    results.append(
                        _parse_class(child, source_bytes, file_path, is_exported=True)
                    )
    for child in node.named_children:
        results.extend(_walk_classes(child, source_bytes, file_path, is_exported))
    return results


def _parse_class(
    node: Any, source_bytes: bytes, file_path: str, is_exported: bool
) -> ClassEntity:
    name_node = node.child_by_field_name("name")
    name = _get_node_text(name_node, source_bytes) if name_node else "<anonymous>"
    extends = None
    implements: List[str] = []
    for child in node.named_children:
        if child.type == "class_heritage":
            for sub in child.named_children:
                if sub.type == "extends_clause":
                    for ssub in sub.named_children:
                        if ssub.type in ("identifier", "type_identifier"):
                            extends = _get_node_text(ssub, source_bytes)
                            break
                elif sub.type == "implements_clause":
                    for ssub in sub.named_children:
                        if ssub.type in ("type_identifier", "generic_type"):
                            if ssub.type == "generic_type":
                                ident = ssub.child_by_field_name("name")
                                if ident:
                                    implements.append(_get_node_text(ident, source_bytes))
                            else:
                                implements.append(_get_node_text(ssub, source_bytes))
    return ClassEntity(
        name=name,
        file_path=file_path,
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        extends=extends,
        implements=implements,
        is_exported=is_exported,
    )


def _walk_methods(
    node: Any, source_bytes: bytes, file_path: str, class_name: str = ""
) -> List[MethodEntity]:
    results: List[MethodEntity] = []
    if node.type in ("class_declaration", "abstract_class_declaration"):
        name_node = node.child_by_field_name("name")
        current_class = _get_node_text(name_node, source_bytes) if name_node else ""
        if class_name and current_class == class_name:
            body = node.child_by_field_name("body")
            if body:
                for child in body.named_children:
                    if child.type == "method_definition":
                        results.append(_parse_method(child, source_bytes, file_path, class_name))
                    elif child.type == "field_definition":
                        name_node = child.child_by_field_name("property")
                        if name_node and _get_node_text(name_node, source_bytes) in ("constructor",):
                            results.append(
                                MethodEntity(
                                    name="constructor",
                                    file_path=file_path,
                                    start_line=child.start_point[0] + 1,
                                    end_line=child.end_point[0] + 1,
                                    class_name=class_name,
                                    params=_get_params(child, source_bytes),
                                )
                            )
        return results
    for child in node.named_children:
        results.extend(_walk_methods(child, source_bytes, file_path, class_name))
    return results


def _parse_method(
    node: Any, source_bytes: bytes, file_path: str, class_name: str
) -> MethodEntity:
    name_node = node.child_by_field_name("name")
    name = _get_node_text(name_node, source_bytes) if name_node else "<anonymous>"
    is_async = any(c.type == "async" for c in node.children)
    return MethodEntity(
        name=name,
        file_path=file_path,
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        class_name=class_name,
        params=_get_params(node, source_bytes),
        is_async=is_async,
    )


def _walk_functions(
    node: Any,
    source_bytes: bytes,
    file_path: str,
    is_exported: bool = False,
    class_name: str = "",
) -> List[Any]:
    results: List[Any] = []
    is_export_stmt = node.type == "export_statement"
    if node.type == "function_declaration":
        results.append(
            _parse_function(node, source_bytes, file_path, is_exported)
        )
    elif is_export_stmt:
        for child in node.named_children:
            if child.type == "function_declaration":
                results.append(
                    _parse_function(child, source_bytes, file_path, is_exported=True)
                )
    for child in node.named_children:
        results.extend(
            _walk_functions(child, source_bytes, file_path, is_exported, class_name)
        )
    return results


def _parse_function(
    node: Any, source_bytes: bytes, file_path: str, is_exported: bool
) -> FunctionEntity:
    name_node = node.child_by_field_name("name")
    name = _get_node_text(name_node, source_bytes) if name_node else "<anonymous>"
    is_async = any(c.type == "async" for c in node.children)
    return FunctionEntity(
        name=name,
        file_path=file_path,
        start_line=node.start_point[0] + 1,
        end_line=node.end_point[0] + 1,
        params=_get_params(node, source_bytes),
        is_async=is_async,
        is_exported=is_exported,
    )


def _walk_calls(node: Any, source_bytes: bytes, file_path: str) -> List[CallEntity]:
    results: List[CallEntity] = []
    if node.type == "call_expression":
        func_node = node.child_by_field_name("function")
        if func_node:
            if func_node.type == "member_expression":
                prop = func_node.child_by_field_name("property")
                name = _get_node_text(prop, source_bytes) if prop else _get_node_text(func_node, source_bytes)
            else:
                name = _get_node_text(func_node, source_bytes)
            results.append(
                CallEntity(
                    name=name,
                    file_path=file_path,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                )
            )
    for child in node.named_children:
        results.extend(_walk_calls(child, source_bytes, file_path))
    return results


class JSParser(BaseParser):
    def __init__(self) -> None:
        self._parser = Parser(JS_LANG)

    def language_name(self) -> str:
        return "javascript"

    def parse(self, code: str, file_path: str) -> FileAnalysis:
        source_bytes = code.encode("utf-8")
        tree = self._parser.parse(source_bytes)
        root = tree.root_node

        analysis = FileAnalysis(file_path=file_path, language="javascript")

        for cls in _walk_classes(root, source_bytes, file_path):
            analysis.classes.append(cls)
        for func in _walk_functions(root, source_bytes, file_path):
            analysis.functions.append(func)
        for cls in analysis.classes:
            for m in _walk_methods(root, source_bytes, file_path, cls.name):
                if m not in analysis.methods:
                    analysis.methods.append(m)
        analysis.imports = _walk_imports(root, source_bytes, file_path)
        analysis.exports = _walk_exports(root, source_bytes, file_path)
        analysis.calls = _walk_calls(root, source_bytes, file_path)
        return analysis


class TSParser(BaseParser):
    def __init__(self, tsx: bool = False) -> None:
        lang = TSX_LANG if tsx else TS_LANG
        self._parser = Parser(lang)
        self._tsx = tsx

    def language_name(self) -> str:
        return "typescript"

    def parse(self, code: str, file_path: str) -> FileAnalysis:
        source_bytes = code.encode("utf-8")
        tree = self._parser.parse(source_bytes)
        root = tree.root_node

        analysis = FileAnalysis(file_path=file_path, language="typescript")

        for cls in _walk_classes(root, source_bytes, file_path):
            analysis.classes.append(cls)
        for func in _walk_functions(root, source_bytes, file_path):
            analysis.functions.append(func)
        for cls in analysis.classes:
            for m in _walk_methods(root, source_bytes, file_path, cls.name):
                if m not in analysis.methods:
                    analysis.methods.append(m)
        analysis.imports = _walk_imports(root, source_bytes, file_path)
        analysis.exports = _walk_exports(root, source_bytes, file_path)
        analysis.calls = _walk_calls(root, source_bytes, file_path)
        return analysis


register_parser("javascript", JSParser())
register_parser("typescript", TSParser(tsx=False))
