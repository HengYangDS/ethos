"""Local CI transport over the repository's sole quality graph."""

from __future__ import annotations

import json
import shlex
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.gates.runner import observe_gate_execution
from ethos.adapters.repo.gate_policy import resolve_gate_policy
from ethos.adapters.repo.git import current_tracked_head

if TYPE_CHECKING:
    import nox

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "build/evidence/local-ci/fallback.json"
LOG_ROOT = ROOT / "build/runtime/work/local-ci/logs"
COMMAND = "uv run --frozen --offline python -m nox -s local_ci"


def owner_commands() -> list[str]:
    """Project the declared full closure without a second membership list."""
    policy = resolve_gate_policy(ROOT, full=True)
    return [shlex.join(node.command) for node in policy.nodes]


def run(session: nox.Session) -> None:
    """Execute the full declared closure and retain failed as well as passing evidence."""
    _write_receipt(
        {
            "schema_version": 1,
            "kind": "ethos_local_ci_fallback_evidence",
            "verdict": "block",
            "state": "running",
            "command": COMMAND,
            "required_gaps": ["local_ci_execution_incomplete"],
            "generated_at": datetime.now(UTC).isoformat(),
            "hosted_ci_status_claimed": False,
            "remote_publication_claimed": False,
        }
    )
    observed = observe_gate_execution(ROOT, full=True, expect_head=current_tracked_head(ROOT))
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    for result in observed["checks"]:
        (LOG_ROOT / f"{result['action_id']}.log").write_text(
            result["stdout"] + result["stderr"], encoding="utf-8"
        )
    payload = {
        **observed,
        "schema_version": 1,
        "kind": "ethos_local_ci_fallback_evidence",
        "state": "passed" if observed["verdict"] == "pass" else "blocked",
        "command": COMMAND,
        "generated_at": datetime.now(UTC).isoformat(),
        "hosted_ci_status_claimed": False,
        "remote_publication_claimed": False,
    }
    _write_receipt(payload)
    session.log(f"local CI: {payload['verdict']}; {len(observed['checks'])} checks; {EVIDENCE}")
    if observed["verdict"] != "pass":
        session.error("local_ci_incomplete: " + ", ".join(observed["required_gaps"]))


def _write_receipt(payload: dict[str, object]) -> None:
    """Replace one diagnostic receipt; interruption can never preserve old success."""
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    temporary = EVIDENCE.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(EVIDENCE)
