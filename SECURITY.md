# Security Policy

This tool runs locally, collects no data, sends nothing anywhere, and needs no API key or secret. It only reads the Python files you point it at, and it never rewrites a file and never changes anything. It writes nothing except the report on standard output (and usage errors on standard error). It never fetches a URL.

It only parses Python files with the standard library `ast` module to find function definitions and their docstrings. It never runs code found in a Python file, never imports the files it checks, and never adds a docstring for you.

If you find a case where the tool rewrites a file, runs code from a checked file, or reports a pass for a public function with no docstring, please open an issue describing the exact commands and input. Do not include any real secret in the report.
