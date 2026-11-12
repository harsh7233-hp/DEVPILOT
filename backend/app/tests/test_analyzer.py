from __future__ import annotations

import os
import pytest

from app.analyzer.base import analyze_file, detect_language, get_supported_extensions
from app.analyzer.parser import JSParser, TSParser

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _read_fixture(name: str) -> str:
    path = os.path.join(FIXTURES_DIR, name)
    with open(path, encoding="utf-8") as f:
        return f.read()


# ── Language detection ─────────────────────────────────────────────


class TestLanguageDetection:
    def test_detect_typescript(self):
        assert detect_language("src/index.ts") == "typescript"

    def test_detect_tsx(self):
        assert detect_language("src/App.tsx") == "typescript"

    def test_detect_javascript(self):
        assert detect_language("lib/util.js") == "javascript"

    def test_detect_jsx(self):
        assert detect_language("src/Button.jsx") == "javascript"

    def test_detect_mjs(self):
        assert detect_language("lib/index.mjs") == "javascript"

    def test_detect_cjs(self):
        assert detect_language("lib/index.cjs") == "javascript"

    def test_detect_python(self):
        assert detect_language("src/main.py") == "python"

    def test_detect_python_stub(self):
        assert detect_language("src/types.pyi") == "python"

    def test_detect_java(self):
        assert detect_language("src/Main.java") == "java"

    def test_unsupported_returns_none_md(self):
        assert detect_language("README.md") is None

    def test_unsupported_returns_none_ruby(self):
        assert detect_language("src/main.rb") is None


# ── Supported extensions ───────────────────────────────────────────


class TestSupportedExtensions:
    def test_has_common_extensions(self):
        exts = get_supported_extensions()
        assert ".ts" in exts
        assert ".tsx" in exts
        assert ".js" in exts
        assert ".jsx" in exts
        assert ".mjs" in exts
        assert ".cjs" in exts
        assert ".py" in exts
        assert ".java" in exts


# ── JS Parser ──────────────────────────────────────────────────────


class TestJSParser:
    def setup_method(self):
        self.parser = JSParser()

    def test_parse_sample_js(self):
        code = _read_fixture("sample.js")
        result = self.parser.parse(code, "sample.js")
        assert result.language == "javascript"
        assert result.file_path == "sample.js"

    def test_extract_functions(self):
        code = _read_fixture("sample.js")
        result = self.parser.parse(code, "sample.js")
        names = [f.name for f in result.functions]
        assert "formatPrice" in names
        assert "loadOrder" in names
        assert result.functions[0].is_async is False

    def test_extract_async_function(self):
        code = _read_fixture("sample.js")
        result = self.parser.parse(code, "sample.js")
        async_funcs = [f for f in result.functions if f.is_async]
        assert len(async_funcs) >= 1
        assert async_funcs[0].name == "loadOrder"

    def test_extract_class(self):
        code = _read_fixture("sample.js")
        result = self.parser.parse(code, "sample.js")
        assert len(result.classes) >= 1
        assert result.classes[0].name == "OrderProcessor"

    def test_extract_imports(self):
        code = _read_fixture("sample.js")
        result = self.parser.parse(code, "sample.js")
        sources = [i.source for i in result.imports]
        assert "react" in sources
        assert "date-fns" in sources
        assert "./math" in sources

    def test_extract_default_import(self):
        code = _read_fixture("sample.js")
        result = self.parser.parse(code, "sample.js")
        react_import = [i for i in result.imports if i.source == "react"][0]
        assert react_import.import_kind == "default"

    def test_extract_named_import(self):
        code = _read_fixture("sample.js")
        result = self.parser.parse(code, "sample.js")
        date_import = [i for i in result.imports if i.source == "date-fns"][0]
        assert date_import.import_kind == "named"
        assert "format" in date_import.names

    def test_extract_exports(self):
        code = _read_fixture("sample.js")
        result = self.parser.parse(code, "sample.js")
        export_kinds = [e.export_kind for e in result.exports]
        assert "named" in export_kinds
        assert "default" in export_kinds or any(
            e.name == "loadOrder" for e in result.exports
        )

    def test_extract_calls(self):
        code = _read_fixture("sample.js")
        result = self.parser.parse(code, "sample.js")
        call_names = [c.name for c in result.calls]
        assert "toFixed" in call_names
        assert "fetch" in call_names
        assert "loadOrder" in call_names

    def test_parse_sample_mjs(self):
        code = _read_fixture("sample_mjs.mjs")
        result = self.parser.parse(code, "sample_mjs.mjs")
        assert result.language == "javascript"
        assert len(result.imports) >= 1
        sources = [i.source for i in result.imports]
        assert "express" in sources

    def test_broken_code_no_crash(self):
        code = _read_fixture("broken.js")
        result = self.parser.parse(code, "broken.js")
        assert result.language == "javascript"
        assert isinstance(result.functions, list)
        assert isinstance(result.classes, list)
        assert isinstance(result.imports, list)


# ── TS Parser ──────────────────────────────────────────────────────


class TestTSParser:
    def setup_method(self):
        self.parser = TSParser(tsx=False)

    def test_parse_sample_ts(self):
        code = _read_fixture("sample.ts")
        result = self.parser.parse(code, "sample.ts")
        assert result.language == "typescript"
        assert result.file_path == "sample.ts"

    def test_extract_functions(self):
        code = _read_fixture("sample.ts")
        result = self.parser.parse(code, "sample.ts")
        names = [f.name for f in result.functions]
        assert "UserCard" in names

    def test_extract_imports(self):
        code = _read_fixture("sample.ts")
        result = self.parser.parse(code, "sample.ts")
        sources = [i.source for i in result.imports]
        assert "react" in sources
        assert "../api/user" in sources

    def test_extract_named_imports_with_types(self):
        code = _read_fixture("sample.ts")
        result = self.parser.parse(code, "sample.ts")
        react_import = [i for i in result.imports if i.source == "react"][0]
        assert react_import.import_kind == "named"

    def test_extract_exports(self):
        code = _read_fixture("sample.ts")
        result = self.parser.parse(code, "sample.ts")
        export_names = [e.name for e in result.exports]
        assert "UserCard" in export_names

    def test_parse_class_with_extends(self):
        code = _read_fixture("sample_class.ts")
        result = self.parser.parse(code, "sample_class.ts")
        assert len(result.classes) >= 2
        card_class = [c for c in result.classes if c.name == "Card"][0]
        assert card_class.extends == "BaseComponent"

    def test_extract_methods(self):
        code = _read_fixture("sample_class.ts")
        result = self.parser.parse(code, "sample_class.ts")
        method_names = [m.name for m in result.methods]
        assert "render" in method_names

    def test_extract_constructor(self):
        code = _read_fixture("sample_class.ts")
        result = self.parser.parse(code, "sample_class.ts")
        constructor_methods = [m for m in result.methods if m.name == "constructor"]
        assert len(constructor_methods) >= 1

    def test_methods_scoped_to_class(self):
        code = _read_fixture("sample_class.ts")
        result = self.parser.parse(code, "sample_class.ts")
        card_methods = [m for m in result.methods if m.class_name == "Card"]
        assert len(card_methods) >= 2
        base_methods = [m for m in result.methods if m.class_name == "BaseComponent"]
        assert len(base_methods) == 0

    def test_parse_hooks_file(self):
        code = _read_fixture("sample_hooks.ts")
        result = self.parser.parse(code, "sample_hooks.ts")
        assert result.language == "typescript"
        names = [f.name for f in result.functions]
        assert "fetchData" in names
        assert "handleSubmit" in names


# ── Python Parser ──────────────────────────────────────────────────


PYTHON_SAMPLE = """
import os
from typing import List

class Base:
    def method(self, x: int) -> str:
        return helper(x)

class Child(Base, Mixin):
    async def run(self):
        return self.method(1)

def top(a, b=2, *args, **kwargs):
    return Child().run()
"""


class TestPythonParser:
    def test_parse_python(self):
        result = analyze_file(PYTHON_SAMPLE, "app.py")
        assert result is not None
        assert result.language == "python"
        assert result.file_path == "app.py"

    def test_extract_classes_and_bases(self):
        result = analyze_file(PYTHON_SAMPLE, "app.py")
        classes = {c.name: c for c in result.classes}
        assert classes["Base"].extends is None
        assert classes["Child"].extends == "Base"
        assert "Mixin" in classes["Child"].implements

    def test_extract_functions_and_methods(self):
        result = analyze_file(PYTHON_SAMPLE, "app.py")
        function_names = [f.name for f in result.functions]
        method_names = [m.name for m in result.methods]
        assert "top" in function_names
        assert "method" in method_names
        assert "run" in method_names
        assert [m for m in result.methods if m.name == "run"][0].is_async is True

    def test_extract_imports_and_calls(self):
        result = analyze_file(PYTHON_SAMPLE, "app.py")
        sources = [i.source for i in result.imports]
        assert "os" in sources
        assert "typing" in sources
        call_names = [c.name for c in result.calls]
        assert "helper" in call_names
        assert "run" in call_names


# ── Java Parser ────────────────────────────────────────────────────


JAVA_SAMPLE = """
package com.example;
import java.util.List;

public class Foo extends Bar implements Baz, Qux {
    public Foo(int x) { this.x = x; }
    public int add(int a, int b) { return helper(a, b); }
    public static void main(String[] args) { new Foo(1).add(2, 3); }
}

interface Baz { void doIt(); }
enum Color { RED, GREEN }
"""


class TestJavaParser:
    def test_parse_java(self):
        result = analyze_file(JAVA_SAMPLE, "Foo.java")
        assert result is not None
        assert result.language == "java"

    def test_extract_classes_extends_implements(self):
        result = analyze_file(JAVA_SAMPLE, "Foo.java")
        classes = {c.name: c for c in result.classes}
        assert classes["Foo"].extends == "Bar"
        assert classes["Foo"].implements == ["Baz", "Qux"]
        assert "Baz" in classes
        assert "Color" in classes

    def test_extract_methods(self):
        result = analyze_file(JAVA_SAMPLE, "Foo.java")
        methods = {(m.class_name, m.name) for m in result.methods}
        assert ("Foo", "Foo") in methods
        assert ("Foo", "add") in methods
        assert ("Foo", "main") in methods
        assert ("Baz", "doIt") in methods

    def test_extract_imports_and_calls(self):
        result = analyze_file(JAVA_SAMPLE, "Foo.java")
        sources = [i.source for i in result.imports]
        assert "java.util.List" in sources
        call_names = [c.name for c in result.calls]
        assert "helper" in call_names
        assert "add" in call_names


# ── Analyze file via base interface ────────────────────────────────


class TestAnalyzeFileInterface:
    def test_analyze_ts_file(self):
        code = _read_fixture("sample.ts")
        result = analyze_file(code, "sample.ts")
        assert result is not None
        assert result.language == "typescript"
        assert len(result.functions) >= 1

    def test_analyze_js_file(self):
        code = _read_fixture("sample.js")
        result = analyze_file(code, "sample.js")
        assert result is not None
        assert result.language == "javascript"

    def test_unsupported_file_returns_none(self):
        result = analyze_file("puts 'hello'", "main.rb")
        assert result is None

    def test_broken_code_returns_result(self):
        code = _read_fixture("broken.js")
        result = analyze_file(code, "broken.js")
        assert result is not None
        assert isinstance(result.functions, list)


# ── Model serialization ────────────────────────────────────────────


class TestModelSerialization:
    def test_file_analysis_to_dict(self):
        code = _read_fixture("sample.ts")
        result = analyze_file(code, "sample.ts")
        d = result.to_dict()
        assert "file_path" in d
        assert "language" in d
        assert "functions" in d
        assert "classes" in d
        assert "methods" in d
        assert "imports" in d
        assert "exports" in d
        assert "calls" in d
        assert "summary" in d

    def test_function_entity_to_dict(self):
        code = _read_fixture("sample.ts")
        result = analyze_file(code, "sample.ts")
        func = result.functions[0]
        d = func.to_dict()
        assert d["kind"] == "function"
        assert "name" in d
        assert "is_async" in d

    def test_class_entity_to_dict(self):
        code = _read_fixture("sample.js")
        result = analyze_file(code, "sample.js")
        cls = result.classes[0]
        d = cls.to_dict()
        assert d["kind"] == "class"
        assert d["name"] == "OrderProcessor"

    def test_import_entity_to_dict(self):
        code = _read_fixture("sample.js")
        result = analyze_file(code, "sample.js")
        imp = result.imports[0]
        d = imp.to_dict()
        assert d["kind"] == "import"
        assert "source" in d
        assert "names" in d


# ── Edge cases ─────────────────────────────────────────────────────


class TestEdgeCases:
    def test_empty_file(self):
        result = analyze_file("", "empty.ts")
        assert result is not None
        assert len(result.functions) == 0
        assert len(result.classes) == 0
        assert len(result.imports) == 0

    def test_comments_only(self):
        code = "// just a comment\n/* block comment */"
        result = analyze_file(code, "comments.js")
        assert result is not None
        assert len(result.functions) == 0

    def test_complex_typescript(self):
        code = _read_fixture("sample_class.ts")
        result = analyze_file(code, "sample_class.ts")
        assert result is not None
        assert len(result.classes) >= 2
        assert len(result.imports) >= 1
        assert len(result.exports) >= 1

    def test_file_path_preserved(self):
        code = _read_fixture("sample.js")
        result = analyze_file(code, "lib/services/order.js")
        assert result.file_path == "lib/services/order.js"
