#!/usr/bin/env python3
"""Candidate-external bootstrap verifier for governance-control replacement.

This script intentionally uses only the Python standard library and Git. Run a
reviewed copy from outside the candidate worktree. It consumes an exact bootstrap
decision and candidate-proof record, recomputes both control trees, and emits a
digest-bound receipt for one accepted-to-candidate transition.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Annotated
from typing import Any

from cyclopts import App
from cyclopts import Parameter
from pydantic import BaseModel
from pydantic import ConfigDict

CONTROL_PREFIXES = (
    ".githooks/",
    ".config/checks/",
    "system/authority.toml",
    "system/commands.toml",
    "system/evidence_boundaries.toml",
    "system/gates.toml",
    "system/invalid_states.toml",
    "system/policies/",
    "system/quality-",
    "system/routing.toml",
    "system/schemas/",
    "system/surfaces.toml",
    "system/tools.toml",
    "system/workflows.toml",
    "tools/ci/scripts/",
    "packages/ethos-core/src/ethos_core/contracts/admission.py",
    "packages/ethos-core/src/ethos_core/contracts/evidence/external.py",
    "packages/ethos/src/ethos/adapters/admission/",
    "packages/ethos/src/ethos/adapters/mutation/",
    "packages/ethos/src/ethos/repository/policy/gates.py",
    "packages/ethos/src/ethos/repository/policy/schema.py",
    "packages/ethos/src/ethos/surface/cli/hook/",
)


class VerificationRequest(BaseModel):
    """Strict boundary request for one control-replacement verification."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    accepted_root: Path
    candidate_root: Path
    accepted_head: str
    candidate_head: str
    candidate_proof: Path
    bootstrap_chronicle: Path
    write_receipt: Path


def main(request: Annotated[VerificationRequest, Parameter(name="*")]) -> int:
    accepted_root = request.accepted_root.resolve()
    candidate_root = request.candidate_root.resolve()
    proof_path = request.candidate_proof.resolve()
    decision_path = request.bootstrap_chronicle.resolve()
    output_path = request.write_receipt.resolve()
    verifier_path = Path(__file__).resolve()

    _require(
        _git(accepted_root, "rev-parse", "HEAD") == request.accepted_head,
        "accepted_head_mismatch",
    )
    _require(
        _git(candidate_root, "rev-parse", "HEAD") == request.candidate_head,
        "candidate_head_mismatch",
    )
    _run(
        candidate_root,
        "git",
        "merge-base",
        "--is-ancestor",
        request.accepted_head,
        request.candidate_head,
    )

    changed_paths = _git(
        candidate_root,
        "diff",
        "--name-only",
        f"{request.accepted_head}..{request.candidate_head}",
    ).splitlines()
    control_paths = sorted(path for path in changed_paths if _is_control_path(path))
    _require(bool(control_paths), "control_replacement_not_detected")

    proof = _json(proof_path)
    proof_head = _native_executed_proof_head(proof)
    _require(bool(proof_head), "candidate_proof_not_proven")
    _require(proof_head == request.candidate_head, "candidate_proof_head_mismatch")
    proof_digest = _sha256(proof_path)
    verifier_digest = _sha256(verifier_path)

    decision = _json(decision_path)
    _validate_bootstrap_decision(
        decision,
        accepted_head=request.accepted_head,
        candidate_head=request.candidate_head,
        verifier_digest=verifier_digest,
        proof_digest=proof_digest,
    )

    receipt = {
        "schema_version": 1,
        "kind": "control-replacement-verifier",
        "provenance": "protected_external_bootstrap",
        "accepted_head": request.accepted_head,
        "candidate_head": request.candidate_head,
        "control_paths": control_paths,
        "accepted_control_digest": _control_digest(
            candidate_root, request.accepted_head, control_paths
        ),
        "candidate_control_digest": _control_digest(
            candidate_root, request.candidate_head, control_paths
        ),
        "verifier_path": verifier_path.as_posix(),
        "verifier_sha256": verifier_digest,
        "candidate_proof_path": proof_path.as_posix(),
        "candidate_proof_digest": proof_digest,
        "bootstrap_decision_path": decision_path.as_posix(),
        "bootstrap_decision_digest": _sha256(decision_path),
        "issued_at": datetime.now(UTC).isoformat(),
        "verdict": "allow",
        "mints_authority": False,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    sys.stdout.write(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return 0


app = App(name="ethos-control-verifier", default_command=main)


def _validate_bootstrap_decision(
    decision: dict[str, Any],
    *,
    accepted_head: str,
    candidate_head: str,
    verifier_digest: str,
    proof_digest: str,
) -> None:
    checks = (
        (decision.get("schema_version") == 1, "bootstrap_decision_schema_invalid"),
        (
            decision.get("kind") == "control-replacement-bootstrap-decision",
            "bootstrap_decision_kind_invalid",
        ),
        (decision.get("event_type") == "decision", "bootstrap_chronicle_event_invalid"),
        (
            decision.get("decision") == "bootstrap/control-replacement",
            "bootstrap_decision_value_invalid",
        ),
        (decision.get("accepted_head") == accepted_head, "bootstrap_accepted_head_mismatch"),
        (decision.get("candidate_head") == candidate_head, "bootstrap_candidate_head_mismatch"),
        (decision.get("verifier_sha256") == verifier_digest, "bootstrap_verifier_digest_mismatch"),
        (
            decision.get("candidate_proof_digest") == proof_digest,
            "bootstrap_candidate_proof_digest_mismatch",
        ),
        (bool(decision.get("evidence_ids")), "bootstrap_evidence_required"),
        (decision.get("mints_authority") is False, "bootstrap_authority_invalid"),
        (
            decision.get("reusable_authorization") is False,
            "bootstrap_reusable_authorization_invalid",
        ),
    )
    for ok, gap in checks:
        _require(ok, gap)


def _control_digest(root: Path, head: str, paths: list[str]) -> str:
    records = []
    for path in paths:
        completed = subprocess.run(
            ["git", "show", f"{head}:{path}"], cwd=root, check=False, capture_output=True
        )
        records.append(
            {
                "path": path,
                "present": completed.returncode == 0,
                "sha256": hashlib.sha256(completed.stdout).hexdigest()
                if completed.returncode == 0
                else "",
            }
        )
    body = json.dumps(records, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(body).hexdigest()


def _is_control_path(path: str) -> bool:
    return any(path == prefix or path.startswith(prefix) for prefix in CONTROL_PREFIXES)


def _json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(payload, dict), f"invalid_json_mapping:{path.name}")
    return payload


def _native_executed_proof_head(proof: dict[str, Any]) -> str:
    """Return the candidate HEAD only for a native executed ETHOS proof result."""
    if (
        proof.get("command") != "prove"
        or proof.get("ok") is not True
        or proof.get("state") != "proven"
    ):
        return ""
    data = proof.get("data")
    if not isinstance(data, dict) or data.get("executed") is not True:
        return ""
    evidence = data.get("evidence")
    provenance = data.get("provenance")
    if not isinstance(evidence, dict) or not isinstance(provenance, dict):
        return ""
    predicate = provenance.get("predicate")
    if not isinstance(predicate, dict):
        return ""
    evidence_head = evidence.get("head")
    predicate_head = predicate.get("head")
    if not isinstance(evidence_head, str) or evidence_head != predicate_head:
        return ""
    return evidence_head


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(root: Path, *args: str) -> str:
    return _run(root, "git", *args).stdout.strip()


def _run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=root, check=True, capture_output=True, text=True)


def _require(condition: bool, message: str) -> None:  # noqa: FBT001
    if not condition:
        raise SystemExit(message)


if __name__ == "__main__":
    app(sys.argv[1:])
