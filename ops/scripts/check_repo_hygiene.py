from __future__ import annotations

import re
import subprocess
import sys

FORBIDDEN_TRACKED_PATH = re.compile(
    r"(^|/)(?:"
    r"__pycache__|\.mypy_cache|\.pytest_cache|\.ruff_cache|\.hypothesis|\.pyre|"
    r"htmlcov|build|dist|\.venv|venv|\.eggs|[^/]+\.egg-info"
    r")(?:/|$)|"
    r"^env/|"
    r"\.py[co]$|"
    r"(^|/)\.coverage(?:\..*)?$|"
    r"(^|/)coverage\.xml$"
)


def main() -> int:
    tracked_files = subprocess.run(
        ["git", "ls-files"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.splitlines()
    forbidden = [path for path in tracked_files if FORBIDDEN_TRACKED_PATH.search(path)]
    if not forbidden:
        return 0

    print("Forbidden generated/cache artifacts are tracked:", file=sys.stderr)
    for path in forbidden:
        print(f"  {path}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
