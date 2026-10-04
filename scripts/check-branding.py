#!/usr/bin/env python3
"""Reject legacy implementation names that should not survive extraction."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = (
    "HomeLab Ops Blueprint",
    "HOMELAB_",
    "homelab_",
)


def main() -> int:
    output = subprocess.check_output(["git", "-C", str(ROOT), "ls-files", "-z"])
    failures: list[str] = []

    for raw in output.split(b"\0"):
        if not raw:
            continue
        path = ROOT / raw.decode()
        relative = path.relative_to(ROOT).as_posix()
        if relative == "scripts/check-branding.py":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for marker in FORBIDDEN:
            if marker in text:
                failures.append(f"{marker!r} remains in {relative}")

    if failures:
        for failure in failures:
            print(f"ERROR: {failure}", file=sys.stderr)
        return 1

    print("Branding validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
