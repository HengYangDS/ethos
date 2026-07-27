#!/usr/bin/env python3
"""Read-only ETHOS governance summary for one checkout."""

from __future__ import annotations

import json
import subprocess
import sys

from cyclopts import App

STEPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("status", ("status", "--json")),
    ("plan", ("plan", "--changed", "--json")),
    ("prove", ("prove", "--json")),
)


def _run(args: tuple[str, ...], root: str) -> dict[str, object]:
    completed = subprocess.run(
        ["uv", "run", "--group", "dev", "ethos", *args, "--root", root],
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError:
        return {
            "ok": False,
            "state": "unparseable",
            "required_gaps": [completed.stderr.strip()[:200]],
        }


app = App(name="ethos-govern-check")


@app.default
def main(*, root: str = ".") -> int:
    all_ok = True
    for name, args in STEPS:
        payload = _run(args, root)
        gaps = [str(gap) for gap in payload.get("required_gaps", [])]
        ok = bool(payload.get("ok"))
        print(f"[{'ok' if ok else 'GAP'}] {name}: {payload.get('state', '?')} ({len(gaps)} gaps)")
        if not ok:
            all_ok = False
            for gap in gaps[:5]:
                print(f"      - {gap}")
    print("GOVERNANCE CLEAN" if all_ok else "GOVERNANCE GAPS — see above")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(app(sys.argv[1:]))
