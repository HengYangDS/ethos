"""Dependency declaration evidence for the sole Python distribution."""

from __future__ import annotations

import json
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

from ethos.adapters.repo.git import current_tracked_head

if TYPE_CHECKING:
    import nox

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "build/evidence/quality/dependency/deptry-ethos.json"
SUMMARY = ROOT / "build/evidence/quality/dependency/summary.json"


def run(session: nox.Session) -> None:
    """Run deptry and write one bounded verdict over its JSON result."""
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.unlink(missing_ok=True)
    SUMMARY.unlink(missing_ok=True)
    result = cast(
        "str",
        session.run(
            "deptry",
            "src/ethos",
            "--config",
            "pyproject.toml",
            "--known-first-party",
            "ethos",
            "--package-module-name-map",
            "cel-expr-python=cel_expr_python,pyyaml=yaml",
            "--json-output",
            str(OUTPUT),
            "--no-ansi",
            success_codes=[0, 1],
            silent=True,
        ),
    )
    try:
        parsed = json.loads(OUTPUT.read_text(encoding="utf-8"))
        findings = parsed if isinstance(parsed, list) else None
    except (OSError, TypeError, json.JSONDecodeError):
        verdict, state, gaps = (
            "unknown",
            "unobservable",
            ["dependency_hygiene_output_unparseable"],
        )
    else:
        if findings is None:
            verdict, state, gaps = (
                "unknown",
                "unobservable",
                ["dependency_hygiene_output_unparseable"],
            )
        else:
            verdict, state, gaps = (
                ("block", "findings_reported", ["dependency_hygiene_findings_reported"])
                if findings
                else ("pass", "passed", [])
            )
    payload = {
        "schema_version": 1,
        "kind": "ethos_dependency_hygiene",
        "verdict": verdict,
        "state": state,
        "head": current_tracked_head(ROOT),
        "config": ".config/checks/deptry/policy.toml",
        "generated_at": datetime.now(UTC).isoformat(),
        "tool": "deptry",
        "evidence_class": "local_owner_gate",
        "required_gaps": gaps,
        "not_claimed": ["vulnerability scan", "hosted CI passed"],
        "outputs": [OUTPUT.relative_to(ROOT).as_posix()],
    }
    SUMMARY.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    session.log(json.dumps(payload, indent=2, sort_keys=True))
    if verdict != "pass":
        session.error(f"dependency hygiene did not pass; deptry output: {result}")
