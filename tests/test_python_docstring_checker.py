"""Tests for python_docstring_checker.

Run from the repo root:

    python3 tests/test_python_docstring_checker.py
"""

import ast
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "src" / "python_docstring_checker.py"

sys.path.insert(0, str(REPO / "src"))
import python_docstring_checker as tool  # noqa: E402


def write(tmp, name, text, encoding="utf-8"):
    path = Path(tmp) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding=encoding)
    return str(path)


def run_cli(args, input=None, cwd=None):
    result = subprocess.run(
        [sys.executable, str(SRC)] + args,
        cwd=cwd or str(REPO), capture_output=True, text=True,
        input=input)
    return result.returncode, result.stdout, result.stderr


class TestCheckText(unittest.TestCase):
    def test_documented_function_passes(self):
        bad, error = tool.check_text(
            'def greet(name):\n    """Say hello."""\n    return name\n')
        self.assertEqual((bad, error), ([], None))

    def test_undocumented_function_reports_line(self):
        bad, error = tool.check_text(
            'def greet(name):\n    return name\n')
        self.assertIsNone(error)
        self.assertEqual(len(bad), 1)
        self.assertEqual(bad[0]["line"], 1)
        self.assertIn('function "greet" has no docstring',
                      bad[0]["reason"])

    def test_undocumented_method_reports_class_and_line(self):
        bad, error = tool.check_text(
            'class Counter:\n    """A counter."""\n\n'
            '    def bump(self):\n        self.value += 1\n')
        self.assertIsNone(error)
        self.assertEqual(len(bad), 1)
        self.assertEqual(bad[0]["line"], 4)
        self.assertIn('method "Counter.bump" has no docstring',
                      bad[0]["reason"])

    def test_private_function_not_flagged(self):
        bad, error = tool.check_text(
            'def _helper():\n    return 1\n')
        self.assertEqual((bad, error), ([], None))

    def test_private_method_not_flagged(self):
        bad, error = tool.check_text(
            'class Widget:\n    def _reset(self):\n        pass\n')
        self.assertEqual((bad, error), ([], None))

    def test_dunder_methods_not_flagged(self):
        bad, error = tool.check_text(
            'class Widget:\n    def __init__(self):\n        pass\n\n'
            '    def __str__(self):\n        return "w"\n')
        self.assertEqual((bad, error), ([], None))

    def test_nested_function_not_flagged(self):
        bad, error = tool.check_text(
            'def outer():\n    """Outer."""\n'
            '    def inner():\n        return 1\n'
            '    return inner()\n')
        self.assertEqual((bad, error), ([], None))

    def test_async_function_checked(self):
        bad, error = tool.check_text(
            'async def fetch(url):\n    return url\n')
        self.assertEqual(len(bad), 1)
        self.assertIn('function "fetch" has no docstring',
                      bad[0]["reason"])

    def test_async_method_checked(self):
        bad, error = tool.check_text(
            'class Client:\n    async def get(self):\n        pass\n')
        self.assertEqual(len(bad), 1)
        self.assertIn('method "Client.get" has no docstring',
                      bad[0]["reason"])

    def test_empty_docstring_does_not_count(self):
        bad, error = tool.check_text(
            'def blank():\n    """"""\n    return None\n')
        self.assertEqual(len(bad), 1)
        self.assertIn('function "blank" has no docstring',
                      bad[0]["reason"])

    def test_whitespace_docstring_does_not_count(self):
        bad, error = tool.check_text(
            'def blank():\n    """   """\n    return None\n')
        self.assertEqual(len(bad), 1)

    def test_any_wording_counts(self):
        bad, error = tool.check_text(
            'def f():\n    """x"""\n    return 1\n')
        self.assertEqual((bad, error), ([], None))

    def test_module_docstring_not_required(self):
        bad, error = tool.check_text(
            'def greet():\n    """Hi."""\n    return 1\n')
        self.assertEqual((bad, error), ([], None))

    def test_class_docstring_not_checked(self):
        bad, error = tool.check_text(
            'class Widget:\n    def show(self):\n        """Show."""\n'
            '        return 1\n')
        self.assertEqual((bad, error), ([], None))

    def test_nested_class_method_checked(self):
        bad, error = tool.check_text(
            'class Outer:\n    class Inner:\n'
            '        def show(self):\n            pass\n')
        self.assertEqual(len(bad), 1)
        self.assertIn('method "Inner.show" has no docstring',
                      bad[0]["reason"])

    def test_findings_in_file_order(self):
        bad, error = tool.check_text(
            'def a():\n    pass\n\n\ndef b():\n    pass\n')
        self.assertEqual([f["line"] for f in bad], [1, 5])

    def test_syntax_error_is_error(self):
        bad, error = tool.check_text('def broken(:\n')
        self.assertEqual(bad, [])
        self.assertIn("not valid Python", error)

    def test_empty_file_passes(self):
        self.assertEqual(tool.check_text(""), ([], None))

    def test_decorated_function_checked(self):
        bad, error = tool.check_text(
            '@property\ndef size(self):\n    return 1\n')
        self.assertEqual(len(bad), 1)
        self.assertIn('function "size" has no docstring',
                      bad[0]["reason"])


class TestCollectFiles(unittest.TestCase):
    def test_file_given_directly_always_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = write(tmp, "notes.txt",
                           'def f():\n    pass\n')
            self.assertEqual(tool.collect_files([target]), [target])

    def test_folder_walks_py_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, "a.py", 'def f():\n    """x"""\n')
            write(tmp, "b.txt", 'def f():\n    pass\n')
            write(tmp, "sub/c.py", 'def g():\n    pass\n')
            found = tool.collect_files([tmp])
            self.assertEqual(len(found), 2)
            self.assertTrue(all(p.endswith(".py") for p in found))

    def test_no_recursive_stops_at_top(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, "a.py", 'def f():\n    """x"""\n')
            write(tmp, "sub/b.py", 'def g():\n    pass\n')
            found = tool.collect_files([tmp], recursive=False)
            self.assertEqual(len(found), 1)
            self.assertTrue(found[0].endswith("a.py"))

    def test_exclude_skips_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, "keep.py", 'def f():\n    """x"""\n')
            write(tmp, "skip_me.py", 'def g():\n    pass\n')
            found = tool.collect_files([tmp], exclude=["skip_*"])
            self.assertEqual(len(found), 1)
            self.assertTrue(found[0].endswith("keep.py"))

    def test_missing_path_raises(self):
        with self.assertRaises(FileNotFoundError):
            tool.collect_files(["/no/such/folder/anywhere"])


class TestCli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        tmp = self.tmp.name
        write(tmp, "clean.py",
              'def greet():\n    """Hi."""\n    return 1\n')
        write(tmp, "flagged.py",
              'def add(a, b):\n    return a + b\n')
        write(tmp, "notes.txt", 'def f():\n    pass\n')

    def test_flagged_file_fails(self):
        code, out, _err = run_cli(
            [str(Path(self.tmp.name) / "flagged.py")])
        self.assertEqual(code, 1)
        self.assertIn('FAIL', out)
        self.assertIn('function "add" has no docstring', out)
        self.assertIn("Checked 1 file(s), 1 public function(s) "
                      "without a docstring in 1 file(s).", out)

    def test_clean_file_passes(self):
        code, out, _err = run_cli(
            [str(Path(self.tmp.name) / "clean.py")])
        self.assertEqual(code, 0)
        self.assertIn("OK — 1 file(s) checked, every public function "
                      "has a docstring.", out)

    def test_folder_run_counts_py_only(self):
        code, out, _err = run_cli([self.tmp.name])
        self.assertEqual(code, 1)
        self.assertIn("Checked 2 file(s), 1 public function(s) "
                      "without a docstring in 1 file(s).", out)

    def test_json_output(self):
        code, out, _err = run_cli(["--json", self.tmp.name])
        self.assertEqual(code, 1)
        data = json.loads(out)
        self.assertEqual(data["checked"], 2)
        self.assertEqual(data["findings"], 1)
        flagged = [r for r in data["files"]
                   if r["path"].endswith("flagged.py")][0]
        self.assertEqual(flagged["findings"][0]["line"], 1)

    def test_stdin(self):
        code, out, _err = run_cli(
            ["--stdin"], input='def f():\n    pass\n')
        self.assertEqual(code, 1)
        self.assertIn('FAIL <stdin>: line 1 function "f" '
                      "has no docstring", out)

    def test_stdin_clean(self):
        code, out, _err = run_cli(
            ["--stdin"], input='def f():\n    """x"""\n    pass\n')
        self.assertEqual(code, 0)
        self.assertIn("OK — 1 file(s) checked", out)

    def test_syntax_error_counts_as_problem(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, "bad.py", 'def broken(:\n')
            code, out, _err = run_cli([tmp])
            self.assertEqual(code, 1)
            self.assertIn("not valid Python", out)

    def test_no_python_files_is_usage_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(tmp, "notes.txt", "hello\n")
            code, _out, err = run_cli([tmp])
            self.assertEqual(code, 2)
            self.assertIn("no Python files found", err)

    def test_missing_path_is_usage_error(self):
        code, _out, err = run_cli(["/no/such/folder/anywhere"])
        self.assertEqual(code, 2)
        self.assertIn("no such file or folder", err)

    def test_no_paths_is_usage_error(self):
        result = subprocess.run(
            [sys.executable, str(SRC)],
            cwd=str(REPO), capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("give at least one Python file or folder",
                      result.stderr)

    def test_stdin_with_paths_is_usage_error(self):
        result = subprocess.run(
            [sys.executable, str(SRC), "--stdin", "x.py"],
            cwd=str(REPO), capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("--stdin takes no file or folder arguments",
                      result.stderr)

    def test_version_flag(self):
        code, out, _err = run_cli(["--version"])
        self.assertEqual(code, 0)
        self.assertIn("1.0.0", out)

    def test_runs_from_other_folders(self):
        with tempfile.TemporaryDirectory() as other:
            code, out, _err = run_cli([self.tmp.name], cwd=other)
            self.assertEqual(code, 1)
            self.assertIn("1 public function(s)", out)


class TestExamples(unittest.TestCase):
    def test_run_example_matches_saved_output(self):
        result = subprocess.run(
            ["sh", str(REPO / "examples" / "run-example.sh")],
            cwd=str(REPO), capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        saved = (REPO / "examples" / "sample-output.md").read_text()
        self.assertEqual(result.stdout, saved)

    def test_readme_commands_are_real(self):
        readme = (REPO / "README.md").read_text()
        clean = subprocess.run(
            [sys.executable, str(SRC), "examples/clean.py"],
            cwd=str(REPO), capture_output=True, text=True)
        self.assertEqual(clean.returncode, 0)
        self.assertIn(clean.stdout.strip(), readme)
        flagged = subprocess.run(
            [sys.executable, str(SRC), "examples/flagged.py"],
            cwd=str(REPO), capture_output=True, text=True)
        self.assertEqual(flagged.returncode, 1)
        self.assertIn(flagged.stdout.strip(), readme)
        js = subprocess.run(
            [sys.executable, str(SRC), "--json", "examples/flagged.py"],
            cwd=str(REPO), capture_output=True, text=True)
        self.assertEqual(js.returncode, 1)
        self.assertIn(js.stdout.strip(), readme)
        edge = subprocess.run(
            [sys.executable, str(SRC), "examples/edge.py"],
            cwd=str(REPO), capture_output=True, text=True)
        self.assertEqual(edge.returncode, 0)
        self.assertIn(edge.stdout.strip(), readme)


class TestHygiene(unittest.TestCase):
    def _repo_files(self):
        for root, dirs, files in os.walk(REPO):
            # Skip every .git directory anywhere in the tree:
            # GitHub ships sample hooks under .git/hooks, and
            # the example fixtures may carry .git folders too.
            dirs[:] = [d for d in dirs
                       if d not in (".git", "__pycache__", "tests")]
            for name in files:
                if name.endswith(".pyc"):
                    continue
                yield Path(root) / name

    def test_no_placeholder_text(self):
        banned = ["TODO", "coming soon", "lorem", "FIXME", "XXX"]
        hits = []
        for path in self._repo_files():
            text = path.read_text(errors="ignore")
            for word in banned:
                if word in text:
                    hits.append("%s: %s" % (path.name, word))
        self.assertEqual(hits, [])

    def test_no_absolute_paths(self):
        hits = []
        for path in self._repo_files():
            text = path.read_text(errors="ignore")
            for marker in ("/home/", "/Users/", "C:\\"):
                if marker in text:
                    hits.append("%s: %s" % (path.name, marker))
        self.assertEqual(hits, [])

    def test_no_secrets(self):
        hits = []
        for path in self._repo_files():
            text = path.read_text(errors="ignore").lower()
            for marker in ("api_key", "api-key", "password", "secret=",
                           "token="):
                if marker in text:
                    hits.append("%s: %s" % (path.name, marker))
        self.assertEqual(hits, [])

    def test_stdlib_imports_only(self):
        stdlib = set(sys.stdlib_module_names)
        for target in (REPO / "src/python_docstring_checker.py",
                       REPO / "tests/test_python_docstring_checker.py"):
            tree = ast.parse(target.read_text())
            imported = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported.update(a.name.split(".")[0]
                                    for a in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported.add(node.module.split(".")[0])
            self.assertFalse(
                imported - stdlib - {"python_docstring_checker"},
                (target.name, imported))
            self.assertNotIn("yaml", imported)

    def test_no_network_use_in_src(self):
        src = (REPO / "src/python_docstring_checker.py").read_text()
        for marker in ("urllib", "requests", "socket", "http.client",
                       "urlopen", "urlretrieve"):
            self.assertNotIn(marker, src, marker)

    def test_gitignore_lists_env_first(self):
        lines = (REPO / ".gitignore").read_text().splitlines()
        self.assertEqual(lines[0], ".env")

    def test_ci_runs_this_test_file(self):
        ci = (REPO / ".github/workflows/ci.yml").read_text()
        self.assertIn("tests/test_python_docstring_checker.py", ci)
        self.assertIn("ubuntu-latest", ci)
        self.assertIn("3.12", ci)
        self.assertIn("actions/checkout", ci)
        self.assertIn("setup-python", ci)
        self.assertIn("push", ci)
        self.assertIn("pull_request", ci)

    def test_ci_yaml_is_well_formed(self):
        lines = (REPO / ".github/workflows/ci.yml").read_text()
        self.assertNotIn("\t", lines)
        for line in lines.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            self.assertFalse(
                line.startswith(" " * 1) and not line.startswith("  "),
                line)

    def test_hygiene_scan_skips_git_dirs_anywhere(self):
        nested = REPO / "examples" / "fake-fixture" / ".git" / "hooks"
        nested.mkdir(parents=True, exist_ok=True)
        try:
            (nested / "sample").write_text("# TODO: sample hook\n")
            seen = [p for p in self._repo_files()
                    if p.name == "sample"]
            self.assertEqual(seen, [])
        finally:
            import shutil
            shutil.rmtree(REPO / "examples" / "fake-fixture")


if __name__ == "__main__":
    unittest.main(verbosity=2)
