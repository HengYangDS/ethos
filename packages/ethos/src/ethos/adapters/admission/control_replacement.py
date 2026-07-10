"""Incumbent/bootstrap provenance admission for governance-control replacement."""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING
from typing import Any
from typing import cast

if TYPE_CHECKING:
    from pathlib import Path


_CONTROL_PREFIXES = (
    ".githooks/",
    ".config/checks/",
    "system/authority.toml",
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
    "packages/ethos-core/src/ethos_core/contracts/external_evidence.py",
    "packages/ethos/src/ethos/adapters/admission/",
    "packages/ethos/src/ethos/adapters/mutation/",
    "packages/ethos/src/ethos/repository/policy/gates.py",
    "packages/ethos/src/ethos/repository/policy/schema.py",
    "packages/ethos/src/ethos/surface/cli/hook/",
)


def control_replacement_report(
    *,
    accepted_root: Path,
    candidate_root: Path,
    accepted_head: str,
    candidate_head: str,
    external_receipt: Path | None = None,
) -> dict[str, object]:
    """Evaluate candidate control changes without letting candidate approve itself."""
    changed = _changed_paths(candidate_root, accepted_head, candidate_head)
    control_paths = tuple(path for path in changed if _is_control_path(path))
    required = bool(control_paths)
    report: dict[str, object] = {
        "kind": "control_replacement_admission",
        "required": required,
        "accepted_head": accepted_head,
        "candidate_head": candidate_head,
        "changed_paths": list(changed),
        "control_paths": list(control_paths),
        "candidate_conformance": {
            "root": candidate_root.resolve().as_posix(),
            "head": candidate_head,
            "verifier_provenance": "candidate_runner",
            "self_approving": False,
        },
        "incumbent_or_bootstrap": {},
        "verifier_provenance": "not_required" if not required else "unknown",
        "self_approval": False,
        "mints_authority": False,
        "verdict": "allow" if not required else "defer",
        "required_gaps": [],
    }
    if not required:
        return report
    receipt, receipt_gaps = _external_receipt(
        path=external_receipt,
        accepted_head=accepted_head,
        candidate_head=candidate_head,
        candidate_root=candidate_root,
    )
    report["incumbent_or_bootstrap"] = receipt
    if receipt_gaps:
        report["required_gaps"] = receipt_gaps
        return report
    report["verifier_provenance"] = str(receipt["provenance"])
    report["verdict"] = "allow"
    return report


def _changed_paths(root: Path, accepted_head: str, candidate_head: str) -> tuple[str, ...]:
    completed = subprocess.run(
        ["git", "diff", "--name-only", f"{accepted_head}..{candidate_head}"],
        cwd=root,
        check=False,
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0:
        return ()
    return tuple(path for path in completed.stdout.splitlines() if path)


def _is_control_path(path: str) -> bool:
    return any(path == prefix or path.startswith(prefix) for prefix in _CONTROL_PREFIXES)


def _external_receipt(
    *,
    path: Path | None,
    accepted_head: str,
    candidate_head: str,
    candidate_root: Path,
) -> tuple[dict[str, Any], list[str]]:
    if path is None:
        return {}, ["incumbent_or_bootstrap_verifier_required"]
    resolved = path.resolve()
    if resolved == candidate_root.resolve() or candidate_root.resolve() in resolved.parents:
        return {}, ["bootstrap_verifier_inside_candidate_tree"]
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}, ["control_replacement_receipt_invalid"]
    if not isinstance(payload, dict):
        return {}, ["control_replacement_receipt_invalid"]
    receipt = cast("dict[str, Any]", payload)
    return receipt, _receipt_gaps(
        receipt, accepted_head=accepted_head, candidate_head=candidate_head
    )


def _receipt_gaps(receipt: dict[str, Any], *, accepted_head: str, candidate_head: str) -> list[str]:
    checks = (
        (
            receipt.get("kind") == "control-replacement-verifier",
            "control_replacement_receipt_kind_invalid",
        ),
        (
            receipt.get("provenance") in {"incumbent_runner", "protected_external_bootstrap"},
            "control_replacement_provenance_invalid",
        ),
        (
            receipt.get("accepted_head") == accepted_head,
            "control_replacement_accepted_head_mismatch",
        ),
        (
            receipt.get("candidate_head") == candidate_head,
            "control_replacement_candidate_head_mismatch",
        ),
        (receipt.get("verdict") == "allow", "control_replacement_verdict_not_allow"),
        (receipt.get("mints_authority") is False, "control_replacement_receipt_authority_invalid"),
    )
    return [gap for ok, gap in checks if not ok]
