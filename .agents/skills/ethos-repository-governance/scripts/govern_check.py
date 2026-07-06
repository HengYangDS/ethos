#!/usr/bin/env python3
"""Deterministic governance-health summary for an ETHOS repository.

Runs the read-only governance triad — status -> audit (shape) -> report — in order,
parses each JSON verdict, and prints a compact scorecard: role, the number of
required gaps per surface, and the first few blockers. It does NOT mutate and does
not run deep OpenSpec validation. It is a lens over the public command plane; the
live command JSON remains authoritative.

Usage:
    govern_check.py [ROOT]
    govern_check.py [--root PATH]

Exit status: 0 when status+audit+report are all ok, 1 when any reports a gap, 2 on a
harness error.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

STEPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("status", ("status", "--json")),
    ("audit", ("audit", "--mode", "shape", "--json")),
    ("report", ("report", "--json")),
)


def _run(args: tuple[str, ...], root: str) -> dict[str, object]:
    completed = subprocess.run(
        ["ethos", *args, "--root", root],
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError:
        stderr = completed.stderr.strip()[:200]
        return {"ok": False, "state": "unparseable", "required_gaps": [stderr]}


def main() -> int:
    parser = argparse.ArgumentParser(description="ETHOS governance-health summary")
    parser.add_argument("root_arg", nargs="?", help="Repository root (positional convenience).")
    parser.add_argument("--root", dest="root_option", help="Repository root.")
    options = parser.parse_args()
    root = options.root_option or options.root_arg or "."

    all_ok = True
    for name, args in STEPS:
        payload = _run(args, root)
        ok = bool(payload.get("ok"))
        gaps = list(payload.get("required_gaps", []))
        marker = "ok" if ok else "GAP"
        print(f"[{marker}] {name}: {payload.get('state', '?')} ({len(gaps)} gaps)")
        if not ok:
            all_ok = False
            for gap in gaps[:5]:
                print(f"      - {gap}")
    print("GOVERNANCE CLEAN" if all_ok else "GOVERNANCE GAPS — see above")
    return 0 if all_ok else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except FileNotFoundError:
        print("error: `ethos` command not found on PATH", file=sys.stderr)
        raise SystemExit(2) from None
