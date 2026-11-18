#!/bin/sh
# Run the checker over each example file and show the result.
# The flagged example fails on purpose, so each run is allowed to fail.
cd "$(dirname "$0")/.."
echo "== examples/clean.py =="
python3 src/python_docstring_checker.py examples/clean.py || true
echo
echo "== examples/flagged.py =="
python3 src/python_docstring_checker.py examples/flagged.py || true
echo
echo "== examples/edge.py =="
python3 src/python_docstring_checker.py examples/edge.py || true
echo
echo "== examples/ : the whole folder =="
python3 src/python_docstring_checker.py examples/ || true
