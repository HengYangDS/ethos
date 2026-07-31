#!/usr/bin/env python3
"""Deterministic readiness driver for the ETHOS change lifecycle.

Runs the read-only prefix of the loop — status -> plan -> prove (readiness) — in
order, parses each command's JSON verdict, and prints a compact readiness summary
with the first blocking gap and its next action. It does NOT mutate: it never runs
`land`, `publish`, or `prove --execute`. It is a lens over the public command plane,
not a second source of truth (the ETHOS command JSON remains authoritative).

Usage:
    python readiness.py [--root PATH]

Exit status mirrors readiness: 0 when status+plan+prove all return `verdict=pass`, 1 when any
read-only gate reports a gap (so a caller can gate on it), 2 on a harness error.
"""

from __future__ import annotations

import json
import subprocess
import sys

from cyclopts import App

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
        return {
            "verdict": "unknown",
            "state": "unparseable",
            "required_gaps": [stderr or "command_output_unparseable"],
        }


app = App(name="ethos-readiness")


@app.default
def main(*, root: str = ".") -> int:
    all_pass = True
    for name, args in READONLY_STEPS:
        payload = _run(args, root)
        verdict = str(payload.get("verdict") or "unknown")
        state = payload.get("state", "?")
        gaps = list(payload.get("required_gaps", []))
        passed = verdict == "pass"
        print(f"[{'PASS' if passed else verdict.upper()}] {name}: {state}")
        if not passed:
            all_pass = False
            for gap in gaps[:5]:
                print(f"      - {gap}")
            next_actions = payload.get("next_actions") or ()
            for action in next_actions[:1]:
                print(f"      next: {action}")
    print("READY" if all_pass else "NOT READY — resolve the gaps above before land/publish")
    return 0 if all_pass else 1


if __name__ == "__main__":
    try:
        app(sys.argv[1:])
    except FileNotFoundError:
        print("error: `ethos` command not found on PATH", file=sys.stderr)
        raise SystemExit(2) from None
