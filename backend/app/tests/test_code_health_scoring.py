"""Code metrics tests: cyclomatic complexity, duplication, docs, scoring."""

from app.services.code_metrics import (
    compute_code_health,
    duplication_ratio,
    extract_functions,
    reliability_pattern_counts,
)


class TestPythonCC:
    def test_simple_function_cc_1(self):
        code = "def f(x):\n    return x\n"
        fns, _ = extract_functions("a.py", "Python", code)
        assert len(fns) == 1
        assert fns[0].cc == 1

    def test_if_branch_increments(self):
        code = "def f(x):\n    if x:\n        return 1\n    return 0\n"
        fns, _ = extract_functions("a.py", "Python", code)
        assert fns[0].cc == 2

    def test_for_and_while(self):
        code = "def g(items):\n    for i in items:\n        while i > 0:\n            i -= 1\n"
        fns, _ = extract_functions("a.py", "Python", code)
        assert fns[0].cc == 3  # 1 + for + while

    def test_comprehension_if(self):
        code = "nums = [x for x in xs if x > 0]\n"
        fns, _ = extract_functions("a.py", "Python", code)
        # comprehension at top level: if adds cc
        assert fns[0].cc >= 2

    def test_boolean_ops(self):
        code = "def f(a,b,c):\n    if a and b or c:\n        pass\n"
        fns, _ = extract_functions("a.py", "Python", code)
        # if=1, and=1, or=1 → cc=4
        assert fns[0].cc == 4


class TestPythonDocstrings:
    def test_docstring_detected(self):
        code = 'def f():\n    """Do something."""\n    pass\n'
        fns, _ = extract_functions("a.py", "Python", code)
        assert fns[0].doc is True

    def test_no_docstring(self):
        code = "def f():\n    pass\n"
        fns, _ = extract_functions("a.py", "Python", code)
        assert fns[0].doc is False


class TestDuplication:
    def test_no_duplication(self):
        files = {
            "a.py": "def foo():\n    return 1\n",
            "b.py": "def bar():\n    return 2\n",
        }
        result = duplication_ratio(files)
        assert result["ratio"] == 0.0

    def test_exact_block_duplicates(self):
        block = "x = 1\ny = 2\nz = 3\na = x + y\nb = y + z\nc = z + a\n"
        files = {"a.py": block, "b.py": "import os\n" * 10 + block}
        result = duplication_ratio(files)
        assert result["ratio"] > 0
        assert result["duplicated_lines"] > 0


class TestScoring:
    def test_score_bounds(self):
        funcs, _ = extract_functions("a.py", "Python", "def f():\n    pass\n")
        files = {"a.py": "def f():\n    pass\n", "b.py": "def g():\n    pass\n"}
        langs = {"a.py": "Python", "b.py": "Python"}
        stats = {"source_files": 1, "test_files": 1}
        dep_info = {"has_manifest": True, "has_lockfile": True, "direct_dependencies": 5}
        health = compute_code_health(funcs, files, langs, stats,
                                     {"critical": 0, "high": 0, "medium": 0}, dep_info)
        assert 0 <= health["overall"] <= 100
        assert health["factors"]
        assert all(f["available"] for f in health["factors"])
        # all formulas present
        for key in ("complexity", "maintainability", "duplication", "tests",
                     "documentation", "dependencies", "reliability"):
            assert health["formulas"][key]

    def test_unavailable_factor_renormalizes(self):
        # no functions → complexity unavailable
        health = compute_code_health([], {"x.py": "import os\n"}, {"x.py": "Python"},
                                     {"source_files": 1, "test_files": 0},
                                     {"critical": 0, "high": 0, "medium": 0},
                                     {"has_manifest": True, "has_lockfile": False, "direct_dependencies": 1})
        assert 0 <= health["overall"] <= 100
        assert not any(f["key"] == "complexity" and f["available"] for f in health["factors"])

    def test_high_complexity_lowers_score(self):
        code = (
            "def f(a,b,c):\n"
            "    if a:\n"
            "        if b:\n"
            "            for i in range(10):\n"
            "                while i > 0:\n"
            "                    if c:\n"
            "                        i -= 1\n"
            "    return a\n"
        )
        fns, _ = extract_functions("a.py", "Python", code)
        assert fns[0].cc >= 6
        files = {"a.py": code}
        health = compute_code_health(fns, files, {"a.py": "Python"},
                                     {"source_files": 1, "test_files": 1},
                                     {"critical": 0, "high": 0, "medium": 0},
                                     {"has_manifest": False, "direct_dependencies": 0})
        c_factor = next(f for f in health["factors"] if f["key"] == "complexity")
        assert c_factor["score"] is not None
        assert c_factor["score"] < 85  # CC > 5 → score drops significantly


class TestReliabilityPatterns:
    def test_counts_empty_catch(self):
        files = {"x.js": "try { doStuff(); } catch (e) {}"}
        counts = reliability_pattern_counts(files, {"x.js": "JavaScript"})
        assert counts["high"] >= 1

    def test_counts_bare_except(self):
        files = {"x.py": "try:\n    pass\nexcept:\n    pass"}
        counts = reliability_pattern_counts(files, {"x.py": "Python"})
        assert counts["high"] >= 1

    def test_no_critical_for_safe_code(self):
        files = {"x.py": "import os"}
        counts = reliability_pattern_counts(files, {"x.py": "Python"})
        assert counts["critical"] == 0
