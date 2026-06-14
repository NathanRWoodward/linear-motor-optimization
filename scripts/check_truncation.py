#!/usr/bin/env python3
"""Guard against silently truncated / corrupted text files.

The workspace file mount has occasionally handed back stale or partially-flushed
copies of a file; saving one back drops its tail. Code is protected by the test
suite (truncation throws a SyntaxError), but docs and config are not. This script
catches the two reliable symptoms before they get committed:

  1. NUL bytes in a text file (a sign of a bad encoding / partial write), and
  2. a tracked file that shrank by more than a threshold vs HEAD (the signal that
     actually catches a truncated doc — a lost tail is a big size drop).

Usage:
    python scripts/check_truncation.py            # check staged files (pre-commit)
    python scripts/check_truncation.py --all      # check all tracked text files

Exit code is non-zero if any problem is found, so it works as a pre-commit hook
or a CI step. A legitimately large deletion can be acknowledged with
`--allow-shrink <path>` (repeatable) or by setting the env var
TRUNCATION_ALLOW_SHRINK to a comma-separated list of paths.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# Extensions we treat as text worth checking for shrink/NUL.
TEXT_SUFFIXES: set[str] = {".py", ".md", ".json", ".toml", ".cfg", ".ini", ".txt", ".yaml", ".yml"}

# Flag a tracked file that lost more than this fraction of its bytes vs HEAD.
SHRINK_THRESHOLD: float = 0.40


def _run(cmd: list[str]) -> str:
    return subprocess.run(cmd, capture_output=True, text=True, check=False).stdout


def staged_files() -> list[str]:
    out: str = _run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"])
    return [line for line in out.splitlines() if line.strip()]


def all_tracked_files() -> list[str]:
    out: str = _run(["git", "ls-files"])
    return [line for line in out.splitlines() if line.strip()]


def head_size(path: str) -> int | None:
    res = subprocess.run(["git", "show", f"HEAD:{path}"], capture_output=True, check=False)
    if res.returncode != 0:
        return None  # not in HEAD (new file)
    return len(res.stdout)


def check_file(path: str, allow_shrink: set[str]) -> list[str]:
    """Return a list of problem descriptions for ``path`` (empty if clean)."""
    p = Path(path)
    if p.suffix not in TEXT_SUFFIXES or not p.is_file():
        return []

    problems: list[str] = []
    raw: bytes = p.read_bytes()

    if b"\x00" in raw:
        problems.append("contains NUL byte(s) — likely a corrupt/partial write")
        return problems

    if path not in allow_shrink:
        prior: int | None = head_size(path)
        if prior is not None and prior > 0:
            shrink: float = 1.0 - (len(raw) / prior)
            if shrink > SHRINK_THRESHOLD:
                problems.append(
                    f"shrank {shrink:.0%} vs HEAD ({prior} -> {len(raw)} bytes) — verify it "
                    f"wasn't truncated (intentional? add to --allow-shrink)"
                )

    return problems


def main(argv: list[str]) -> int:
    check_all: bool = "--all" in argv
    allow_shrink: set[str] = set()
    for i, a in enumerate(argv):
        if a == "--allow-shrink" and i + 1 < len(argv):
            allow_shrink.add(argv[i + 1])
    allow_shrink |= {s.strip() for s in os.environ.get("TRUNCATION_ALLOW_SHRINK", "").split(",") if s.strip()}

    files: list[str] = all_tracked_files() if check_all else staged_files()

    failures: dict[str, list[str]] = {}
    for path in files:
        problems = check_file(path, allow_shrink)
        if problems:
            failures[path] = problems

    if failures:
        print("Truncation/corruption check FAILED:\n")
        for path, problems in failures.items():
            for problem in problems:
                print(f"  {path}: {problem}")
        print(
            "\nA common cause is the editor/shell handing back a stale copy — re-read the\n"
            "file and verify its last line and length before committing. If the deletion\n"
            "is intentional, re-run with `--allow-shrink <path>`."
        )
        return 1

    print(f"Truncation check passed ({len(files)} file(s)).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
