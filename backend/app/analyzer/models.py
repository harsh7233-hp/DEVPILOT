from __future__ import annotations

from typing import Any, Dict, List, Optional


class Entity:
    def __init__(
        self,
        name: str,
        kind: str,
        file_path: str,
        start_line: int,
        end_line: int,
    ) -> None:
        self.name = name
        self.kind = kind
        self.file_path = file_path
        self.start_line = start_line
        self.end_line = end_line

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "file_path": self.file_path,
            "start_line": self.start_line,
            "end_line": self.end_line,
        }


class FunctionEntity(Entity):
    def __init__(
        self,
        name: str,
        file_path: str,
        start_line: int,
        end_line: int,
        params: Optional[List[str]] = None,
        is_async: bool = False,
        is_exported: bool = False,
    ) -> None:
        super().__init__(name, "function", file_path, start_line, end_line)
        self.params = params or []
        self.is_async = is_async
        self.is_exported = is_exported

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["params"] = self.params
        d["is_async"] = self.is_async
        d["is_exported"] = self.is_exported
        return d


class ClassEntity(Entity):
    def __init__(
        self,
        name: str,
        file_path: str,
        start_line: int,
        end_line: int,
        extends: Optional[str] = None,
        implements: Optional[List[str]] = None,
        is_exported: bool = False,
    ) -> None:
        super().__init__(name, "class", file_path, start_line, end_line)
        self.extends = extends
        self.implements = implements or []
        self.is_exported = is_exported

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["extends"] = self.extends
        d["implements"] = self.implements
        d["is_exported"] = self.is_exported
        return d


class MethodEntity(Entity):
    def __init__(
        self,
        name: str,
        file_path: str,
        start_line: int,
        end_line: int,
        class_name: str = "",
        params: Optional[List[str]] = None,
        is_async: bool = False,
    ) -> None:
        super().__init__(name, "method", file_path, start_line, end_line)
        self.class_name = class_name
        self.params = params or []
        self.is_async = is_async

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["class_name"] = self.class_name
        d["params"] = self.params
        d["is_async"] = self.is_async
        return d


class ImportEntity(Entity):
    def __init__(
        self,
        file_path: str,
        start_line: int,
        end_line: int,
        source: str = "",
        names: Optional[List[str]] = None,
        import_kind: str = "named",
    ) -> None:
        super().__init__(source or "default", "import", file_path, start_line, end_line)
        self.source = source
        self.names = names or []
        self.import_kind = import_kind

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["source"] = self.source
        d["names"] = self.names
        d["import_kind"] = self.import_kind
        return d


class ExportEntity(Entity):
    def __init__(
        self,
        name: str,
        file_path: str,
        start_line: int,
        end_line: int,
        export_kind: str = "named",
    ) -> None:
        super().__init__(name, "export", file_path, start_line, end_line)
        self.export_kind = export_kind

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d["export_kind"] = self.export_kind
        return d


class CallEntity(Entity):
    def __init__(
        self,
        name: str,
        file_path: str,
        start_line: int,
        end_line: int,
    ) -> None:
        super().__init__(name, "call", file_path, start_line, end_line)


class FileAnalysis:
    def __init__(self, file_path: str, language: str = "unknown") -> None:
        self.file_path = file_path
        self.language = language
        self.functions: List[FunctionEntity] = []
        self.classes: List[ClassEntity] = []
        self.methods: List[MethodEntity] = []
        self.imports: List[ImportEntity] = []
        self.exports: List[ExportEntity] = []
        self.calls: List[CallEntity] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "language": self.language,
            "functions": [e.to_dict() for e in self.functions],
            "classes": [e.to_dict() for e in self.classes],
            "methods": [e.to_dict() for e in self.methods],
            "imports": [e.to_dict() for e in self.imports],
            "exports": [e.to_dict() for e in self.exports],
            "calls": [e.to_dict() for e in self.calls],
            "summary": {
                "functions": len(self.functions),
                "classes": len(self.classes),
                "methods": len(self.methods),
                "imports": len(self.imports),
                "exports": len(self.exports),
                "calls": len(self.calls),
            },
        }
