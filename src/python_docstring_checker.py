#!/usr/bin/env python3
"""Check public functions carry a docstring.

Run: python3 src/python_docstring_checker.py src/
     python3 src/python_docstring_checker.py --json module.py

An undocumented public function is a guessing game
for the next reader, and the gap is found months
later when someone has to use it. This tool reads
each Python file, checks every public function —
module-level functions and methods — carries a
docstring, and reports each one without, with the
file and the line, exiting 1, so it can fail a CI
run. A file where every public function is
documented exits 0.

Presence only, never style: a docstring of any
length and any wording counts. A docstring that is
empty, or only whitespace, does not count — it
documents nothing.

Private functions (a name starting with `_`) and
dunder functions (`__init__`, `__str__` and the
rest) are never flagged. Nested functions — a
function defined inside another function — are not
checked either: only module-level functions and
methods are public surface. Module and class
docstrings are not checked; this tool checks
functions only.

It never edits a file, never touches the network,
and reads only the files and folders you point it
at. It uses the standard library `ast` module, so
it reads the code as Python sees it — a string
that only looks like a function is never flagged.
"""

import argparse
import ast
import fnmatch
import json
import os
import sys
from pathlib import Path

__version__ = "1.0.0"

PYTHON_SUFFIXES = (".py",)


def _is_public(name):
    """True when a function name is public surface.

    A name starting with an underscore is private, and
    a name wrapped in double underscores is a dunder —
    neither is flagged.
    """
    return not name.startswith("_")


def _has_docstring(node):
    """True when a function has a real docstring.

    ast.get_docstring returns the docstring, or None
    when there is none. An empty or whitespace-only
    string does not count: it documents nothing.
    """
    text = ast.get_docstring(node, clean=False)
    return bool(text and text.strip())


def _check_class(node, findings):
    """Check one class's methods, and any class nested in it."""
    for child in node.body:
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if _is_public(child.name) and not _has_docstring(child):
                findings.append({
                    "line": child.lineno,
                    "reason": 'method "%s.%s" has no docstring'
                              % (node.name, child.name),
                })
        elif isinstance(child, ast.ClassDef):
            _check_class(child, findings)


def check_functions(tree):
    """Check one parsed module.

    Returns a list of {"line": int, "reason": str} for
    every public function without a docstring, in the
    order they appear in the file. Module-level
    functions and methods are checked; nested functions
    are not.
    """
    findings = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if _is_public(node.name) and not _has_docstring(node):
                findings.append({
                    "line": node.lineno,
                    "reason": 'function "%s" has no docstring'
                              % node.name,
                })
        elif isinstance(node, ast.ClassDef):
            _check_class(node, findings)
    return findings


def check_text(text):
    """Check one Python source text.

    Returns (findings, error): findings is a list of
    {"line": int, "reason": str} in file order, and
    error is None or a string saying why the file
    could not be checked at all.
    """
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        return [], "not valid Python: %s" % exc
    return check_functions(tree), None


def check_file(path):
    """Check one file. Returns (findings, error)."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return [], "not valid UTF-8"
    except OSError as exc:
        return [], str(exc)
    return check_text(text)


def _is_python_file(path):
    return Path(path).name.lower().endswith(PYTHON_SUFFIXES)


def collect_files(paths, recursive=True, exclude=None):
    """Expand CLI paths into a sorted list of Python files.

    A file given directly is always checked, whatever its
    name. A folder is walked for files ending in .py
    only, recursively by default (--no-recursive stops
    at the top level). .git folders are never walked,
    and directory links are never followed.
    """
    exclude = exclude or []
    found = []
    for raw in paths:
        path = Path(raw)
        if path.is_file():
            found.append(str(path))
        elif path.is_dir():
            for dirpath, dirs, files in os.walk(path, followlinks=False):
                dirs[:] = [
                    d for d in dirs
                    if d != ".git"
                    and not any(fnmatch.fnmatch(d, pat) for pat in exclude)
                ]
                for name in files:
                    candidate = Path(dirpath) / name
                    if not _is_python_file(candidate):
                        continue
                    if any(
                        fnmatch.fnmatch(str(candidate), pat)
                        or fnmatch.fnmatch(name, pat)
                        for pat in exclude
                    ):
                        continue
                    found.append(str(candidate))
                if not recursive:
                    break
        else:
            raise FileNotFoundError("no such file or folder: %s" % raw)
    seen = set()
    unique = []
    for item in found:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return sorted(unique)


def format_finding(path, finding):
    """One human-readable line for one missing docstring."""
    return ("FAIL %s: line %d %s"
            % (path, finding["line"], finding["reason"]))


def run(paths, recursive=True, exclude=None, as_json=False):
    """Check paths, print the report, return the exit code."""
    try:
        files = collect_files(paths, recursive=recursive, exclude=exclude)
    except FileNotFoundError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    if not files:
        print("error: no Python files found", file=sys.stderr)
        return 2
    results = []
    findings = 0
    files_with_findings = 0
    for path in files:
        bad, error = check_file(path)
        count = len(bad) + (1 if error else 0)
        if count:
            findings += count
            files_with_findings += 1
        results.append({"path": path, "findings": bad, "error": error})
    if as_json:
        print(json.dumps(
            {"files": results, "checked": len(files),
             "findings": findings},
            indent=2))
    else:
        for result in results:
            if result["error"]:
                print("FAIL %s: %s" % (result["path"], result["error"]))
            for finding in result["findings"]:
                print(format_finding(result["path"], finding))
        if findings:
            print("Checked %d file(s), %d public function(s) "
                  "without a docstring in %d file(s)."
                  % (len(files), findings, files_with_findings))
        else:
            print("OK — %d file(s) checked, every public function "
                  "has a docstring." % len(files))
    return 1 if findings else 0


def run_stdin(as_json=False):
    """Check one Python document read from standard input."""
    text = sys.stdin.read()
    bad, error = check_text(text)
    findings = len(bad) + (1 if error else 0)
    if as_json:
        print(json.dumps(
            {"files": [{"path": "<stdin>", "findings": bad,
                        "error": error}],
             "checked": 1, "findings": findings},
            indent=2))
    else:
        if error:
            print("FAIL <stdin>: %s" % error)
        for finding in bad:
            print(format_finding("<stdin>", finding))
        if findings:
            print("Checked 1 file(s), %d public function(s) "
                  "without a docstring in 1 file(s)." % findings)
        else:
            print("OK — 1 file(s) checked, every public function "
                  "has a docstring.")
    return 1 if findings else 0


def main(argv=None):
    """Parse arguments and run the checker."""
    parser = argparse.ArgumentParser(
        prog="python_docstring_checker",
        description="Check public functions carry a docstring, "
                    "fail CI when one does not.")
    parser.add_argument("paths", nargs="*",
                        help="Python files or folders to walk")
    parser.add_argument("--no-recursive", action="store_true",
                        help="do not walk into subfolders")
    parser.add_argument("--exclude", action="append", default=[],
                        help="skip files or folders matching this pattern "
                             "(repeatable)")
    parser.add_argument("--json", action="store_true",
                        help="print the result as JSON")
    parser.add_argument("--stdin", action="store_true",
                        help="check one Python document from standard input")
    parser.add_argument("--version", action="version",
                        version="%(prog)s " + __version__)
    args = parser.parse_args(argv)
    if args.stdin:
        if args.paths:
            parser.error("--stdin takes no file or folder arguments")
        return run_stdin(as_json=args.json)
    if not args.paths:
        parser.error("give at least one Python file or folder")
    return run(args.paths,
               recursive=not args.no_recursive,
               exclude=args.exclude, as_json=args.json)


if __name__ == "__main__":
    sys.exit(main())
