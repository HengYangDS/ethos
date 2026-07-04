#!/usr/bin/env python3
"""Deterministic readiness driver for the ETHOS change lifecycle.

Runs the read-only prefix of the loop — status -> plan -> prove (readiness) — in
order, parses each command's JSON verdict, and prints a compact readiness summary
with the first blocking gap and its next action. It does NOT mutate: it never runs
`land`, `publish`, or `prove --execute`. It is a lens over the public command plane,
not a second source of truth (the ETHOS command JSON remains authoritative).

Usage:
    python readiness.py [--root PATH]

Exit status mirrors readiness: 0 when status+plan+prove are all ok, 1 when any
read-only gate reports a gap (so a caller can gate on it), 2 on a harness error.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

READONLY_STEPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("status", ("status", "--json")),
    ("plan", ("plan", "--changed", "--json")),
    ("prove", ("prove", "--json")),
)


def _run(args: tuple[str, ...], root: str) -> dict[str, object]:
    completed = subprocess.run(
        ["ethos", *args, "--root", root] if "--root" not in args else ["ethos", *args],
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
    parser = argparse.ArgumentParser(description="ETHOS change-lifecycle readiness driver")
    parser.add_argument("--root", default=".")
    options = parser.parse_args()

    all_ok = True
    for name, args in READONLY_STEPS:
        payload = _run(args, options.root)
        ok = bool(payload.get("ok"))
        state = payload.get("state", "?")
        gaps = list(payload.get("required_gaps", []))
        marker = "ok" if ok else "GAP"
        print(f"[{marker}] {name}: {state}")
        if not ok:
            all_ok = False
            for gap in gaps[:5]:
                print(f"      - {gap}")
            next_actions = payload.get("next_actions") or ()
            for action in next_actions[:1]:
                print(f"      next: {action}")
    print("READY" if all_ok else "NOT READY — resolve the gaps above before land/publish")
    return 0 if all_ok else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except FileNotFoundError:
        print("error: `ethos` command not found on PATH", file=sys.stderr)
        raise SystemExit(2) from None
