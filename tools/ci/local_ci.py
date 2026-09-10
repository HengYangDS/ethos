"""Local CI transport over the repository's sole quality graph."""

from __future__ import annotations

import json
import shlex
from dataclasses import asdict
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.gates.runner import LocalGateRunner
from ethos.adapters.gates.runner import run_gate_waves
from ethos.adapters.repo.dirty.change_provenance import dirty_content_sha256
from ethos.adapters.repo.dirty.change_provenance import dirty_provenance
from ethos.adapters.repo.gate_policy import resolve_gate_policy
from ethos.adapters.repo.git import current_tracked_head
from ethos.repository.policy.gates import gate_execution_identity

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
    head = current_tracked_head(ROOT)
    overlay = dirty_content_sha256(ROOT)
    policy = resolve_gate_policy(ROOT, full=True)
    preflight = list(policy.gaps)
    if not head:
        preflight.append("local_ci_head_missing")
    if dirty_provenance(ROOT)["state"] != "clean":
        preflight.append("local_ci_requires_clean_head")
    if not policy.nodes:
        preflight.append("local_ci_selection_empty")
    if preflight:
        _write_receipt(
            {
                "verdict": "block",
                "state": "blocked",
                "head": head,
                "command": COMMAND,
                "required_gaps": preflight,
                "policy_digest": policy.digest,
            }
        )
        session.error("local_ci_preflight: " + ", ".join(preflight))
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    results = run_gate_waves(
        LocalGateRunner(), policy.nodes, policy.registry, root=ROOT, capacity=4, parallel=True
    )
    gaps = [
        f"gate_execution_not_proven:{result.action_id}"
        for result in results
        if result.verdict != "pass" or result.exit_code != 0
    ]
    if not results or sorted((result.action_id, result.command) for result in results) != sorted(
        (node.id, node.command) for node in policy.nodes
    ):
        gaps.append("local_ci_results_incomplete")
    if (
        current_tracked_head(ROOT) != head
        or dirty_provenance(ROOT)["state"] != "clean"
        or dirty_content_sha256(ROOT) != overlay
        or resolve_gate_policy(ROOT, full=True).digest != policy.digest
    ):
        gaps.append("local_ci_source_or_policy_changed")
    for result in results:
        (LOG_ROOT / f"{result.action_id}.log").write_text(
            result.stdout + result.stderr, encoding="utf-8"
        )
    payload: dict[str, object] = {
        "schema_version": 1,
        "kind": "ethos_local_ci_fallback_evidence",
        "verdict": "block" if gaps else "pass",
        "state": "blocked" if gaps else "passed",
        "head": head,
        "policy_digest": policy.digest,
        "source_overlay_sha256": overlay,
        "command": COMMAND,
        "owner_commands": [
            shlex.join(gate_execution_identity(policy.registry[node.id])) for node in policy.nodes
        ],
        "checks": [asdict(result) for result in results],
        "required_gaps": gaps,
        "generated_at": datetime.now(UTC).isoformat(),
        "head_stability": "changed"
        if "local_ci_source_or_policy_changed" in gaps
        else "verified_before_evidence_write",
        "hosted_ci_status_claimed": False,
        "remote_publication_claimed": False,
    }
    _write_receipt(payload)
    session.log(f"local CI: {payload['verdict']}; {len(results)} checks; {EVIDENCE}")
    if gaps:
        session.error("local_ci_incomplete: " + ", ".join(gaps))


def _write_receipt(payload: dict[str, object]) -> None:
    """Replace one diagnostic receipt; interruption can never preserve old success."""
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    temporary = EVIDENCE.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(EVIDENCE)
