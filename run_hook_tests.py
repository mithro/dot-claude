#!/usr/bin/env python3
"""Run every hook plugin's tests.

Two test styles live under marketplace/hook-*/hooks/:

  - pytest-style modules (contain `def test_...`), run via
    `uv run --with pytest python -m pytest`;
  - self-contained scripts (top-level checks, exit 1 on failure), run via
    `python3 <script>` exactly as the hooks themselves are invoked.

Usage:  uv run run_hook_tests.py [substring-filter]
Exits non-zero if any test file fails.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PYTEST_STYLE = re.compile(r"^def test_", re.MULTILINE)


def is_pytest_style(path: Path) -> bool:
    return bool(PYTEST_STYLE.search(path.read_text()))


def run_one(path: Path) -> bool:
    if is_pytest_style(path):
        cmd = ["uv", "run", "--no-project", "--with", "pytest",
               "python", "-m", "pytest", "-q", str(path)]
    else:
        cmd = ["python3", str(path)]
    print(f"\n=== {path.relative_to(ROOT)}  ({'pytest' if cmd[0] == 'uv' else 'script'})",
          flush=True)
    proc = subprocess.run(cmd, cwd=ROOT)
    return proc.returncode == 0


def main(argv: list[str]) -> int:
    needle = argv[1] if len(argv) > 1 else ""
    files = sorted(ROOT.glob("marketplace/hook-*/hooks/test_*.py"))
    files = [f for f in files if needle in str(f)]
    if not files:
        print("no test files matched", file=sys.stderr)
        return 2

    results = {f: run_one(f) for f in files}
    failed = [f for f, ok in results.items() if not ok]

    print("\n=== summary")
    for f, ok in results.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {f.relative_to(ROOT)}")
    print(f"\n{len(results) - len(failed)} passed, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
