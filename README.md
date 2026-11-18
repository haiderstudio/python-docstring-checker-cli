# python-docstring-checker-cli

Check public functions carry a docstring — fail CI when one does not.

[![CI](https://github.com/haiderstudio/python-docstring-checker-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/haiderstudio/python-docstring-checker-cli/actions/workflows/ci.yml) [![Licence: MIT](https://img.shields.io/badge/Licence-MIT-yellow.svg)](LICENSE)

## What it does

`python_docstring_checker` reads each Python file,
checks every public function — module-level
functions and methods — carries a docstring, and
reports each one without, with the file and the
line. It exits 1 when any public function is
undocumented, so it can fail a CI run. A file where
every public function is documented exits 0.

- Presence only, never style: a docstring of any
  length and any wording counts. An empty docstring,
  or one that is only whitespace, does not count —
  it documents nothing.
- Private functions (a name starting with `_`) and
  dunder functions (`__init__`, `__str__` and the
  rest) are never flagged.
- Nested functions — a function defined inside
  another function — are not checked: only
  module-level functions and methods are public
  surface.
- It reads the code with the standard library `ast`
  module, so it reads the code as Python sees it —
  a string that only looks like a function is never
  flagged, and a docstring hidden behind a decorator
  is still found.
- A file given directly on the command line is
  always checked, whatever its name. A folder is
  walked for files ending in `.py` only,
  recursively by default (`--no-recursive` stops
  at the top level). `.git` folders are never
  walked, and directory links are never followed.
- `--json` prints the result as JSON, and
  `--stdin` checks one Python document read from
  standard input.

## Who it is for

Every Python project. An undocumented public
function is a guessing game for the next reader,
and the gap is found months later when someone has
to use it. This is the gate that keeps the public
surface documented at the pull request, when the
fix is one string per function.

## What it does NOT do

- It does not check docstring style, wording, or
  format — that is the job of pydocstyle, the
  1,113-star docstring style checker, which owns
  the broad docstring-linting job, including its
  missing-docstring codes (D100–D107). This tool
  is the presence-only narrow slice: one check
  only (a public function has a docstring or it
  does not), zero-install standard library CLI,
  per-line reporting, CI exit code.
- It does not check module or class docstrings —
  functions only.
- It does not check type hints — that is a
  different check on the same files.
- It does not check that a docstring is true, or
  that it describes the arguments — presence only.
- It never edits a file. It only reports what it
  finds.

## How this differs

- A fresh search of GitHub on Nov 17, 2026 found 0
  results for `"python-docstring-checker-cli"` and 9
  results for `python docstring checker`. The giant
  is PyCQA/pydocstyle, 1,113 stars, a docstring
  style checker that owns the broad docstring-linting
  job — this tool is the presence-only narrow slice
  of that job, as noted above. The other small
  rivals are different jobs: DenverCoder1/
  docstring-utils, 6 stars, a style-format parser;
  mabdullahsoyturk/docstring-checker, 2 stars,
  enforces usage examples inside docstrings, not
  presence; Casper321/reST-docstring-checker, 2
  stars, a PEP 287 format checker; Mr-Pepe/lintel,
  0 stars, a docstring style checker.
- No rival is a tested standard library CLI gate
  for docstring presence alone.

## Install

```sh
git clone https://github.com/haiderstudio/python-docstring-checker-cli.git
cd python-docstring-checker-cli
```

There is nothing else to install: Python 3.10 or newer,
standard library only, no dependencies.

## Usage

Check one Python file:

```sh
python3 src/python_docstring_checker.py module.py
```

A file with three undocumented public functions
fails, with the file and line for each one:

```sh
$ python3 src/python_docstring_checker.py examples/flagged.py
FAIL examples/flagged.py: line 9 function "add" has no docstring
FAIL examples/flagged.py: line 19 method "Counter.bump" has no docstring
FAIL examples/flagged.py: line 27 function "blank" has no docstring
Checked 1 file(s), 3 public function(s) without a docstring in 1 file(s).
```

A file where every public function is documented
passes:

```sh
$ python3 src/python_docstring_checker.py examples/clean.py
OK — 1 file(s) checked, every public function has a docstring.
```

Check a whole folder (`.py` files only):

```sh
$ python3 src/python_docstring_checker.py examples/
FAIL examples/flagged.py: line 9 function "add" has no docstring
FAIL examples/flagged.py: line 19 method "Counter.bump" has no docstring
FAIL examples/flagged.py: line 27 function "blank" has no docstring
Checked 3 file(s), 3 public function(s) without a docstring in 1 file(s).
```

Check one document from standard input:

```sh
$ printf 'def f():\n    pass\n' | python3 src/python_docstring_checker.py --stdin
FAIL <stdin>: line 1 function "f" has no docstring
Checked 1 file(s), 1 public function(s) without a docstring in 1 file(s).
```

Machine-readable output:

```sh
$ python3 src/python_docstring_checker.py --json examples/flagged.py
{
  "files": [
    {
      "path": "examples/flagged.py",
      "findings": [
        {
          "line": 9,
          "reason": "function \"add\" has no docstring"
        },
        {
          "line": 19,
          "reason": "method \"Counter.bump\" has no docstring"
        },
        {
          "line": 27,
          "reason": "function \"blank\" has no docstring"
        }
      ],
      "error": null
    }
  ],
  "checked": 1,
  "findings": 3
}
```

Exit codes: 0 when every public function has a
docstring, 1 when any public function is
undocumented or a file cannot be read or parsed, 2
for a usage error (a missing path, a missing file,
a bad flag, or no Python files found).

## Examples

An empty docstring does not count — `examples/flagged.py`
has a `blank()` function whose docstring is an
empty string, and it is reported on line 27 like a
function with no docstring at all.

Private names, dunder methods, and nested functions
are never flagged — `examples/edge.py` has a
`_helper` function, a `_reset` method, an
`__init__`, and a nested `inner()` function, all
without docstrings, and it passes:

```sh
$ python3 src/python_docstring_checker.py examples/edge.py
OK — 1 file(s) checked, every public function has a docstring.
```

Run every bundled example at once with `sh
examples/run-example.sh` — the output is saved in
[examples/sample-output.md](examples/sample-output.md).

## How it is tested

```sh
python3 tests/test_python_docstring_checker.py
```

The tests run the real CLI on throwaway Python
files and folders, check the bundled examples
against their saved output, and check every command
quoted in this README by running it.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Licence

MIT — see [LICENSE](LICENSE).

## Original work

This tool is original work, written for this
repository. It builds on the Python standard
library only (`ast` for parsing). The idea was
researched against GitHub on Nov 17, 2026 — no
existing tool does this exact job, as noted above
under "How this differs". pydocstyle is named
there honestly as the owner of the broad
docstring-linting job.
