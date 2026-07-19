"""Incumbent/bootstrap provenance admission for governance-control replacement."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any
from typing import cast

from ethos.repository.policy.schema import validate_schema_instance

_CONTROL_PREFIXES = (
    ".ethos/workspace.toml",
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
    "packages/ethos/src/ethos/domain/land/",
    "packages/ethos/src/ethos/repository/policy/gates.py",
    "packages/ethos/src/ethos/repository/policy/schema.py",
    "packages/ethos/src/ethos/surface/cli/hook/",
    "packages/ethos/src/ethos/surface/cli/root/lifecycle.py",
)
_RECEIPT_CHECK_GAPS = (
    "control_replacement_receipt_kind_invalid",
    "control_replacement_provenance_invalid",
    "control_replacement_accepted_head_mismatch",
    "control_replacement_candidate_head_mismatch",
    "control_replacement_verdict_not_allow",
    "control_replacement_receipt_authority_invalid",
)
_BOOTSTRAP_BINDING_GAPS = (
    "control_replacement_bootstrap_decision_schema_invalid",
    "control_replacement_bootstrap_decision_kind_invalid",
    "control_replacement_bootstrap_chronicle_event_invalid",
    "control_replacement_bootstrap_decision_value_invalid",
    "control_replacement_bootstrap_accepted_head_mismatch",
    "control_replacement_bootstrap_candidate_head_mismatch",
    "control_replacement_bootstrap_verifier_digest_mismatch",
    "control_replacement_bootstrap_candidate_proof_digest_mismatch",
)
_BOOTSTRAP_FLAG_GAPS = (
    "control_replacement_bootstrap_evidence_required",
    "control_replacement_bootstrap_authority_invalid",
    "control_replacement_bootstrap_reusable_authorization_invalid",
)


def control_replacement_report(
    *,
    candidate_root: Path,
    accepted_head: str,
    candidate_head: str,
    external_receipt: Path | None = None,
) -> dict[str, object]:
    """Evaluate candidate control changes without letting candidate approve itself."""
    changed = _changed_paths(candidate_root, accepted_head, candidate_head)
    changed_paths = changed or ()
    control_paths = tuple(sorted(path for path in changed_paths if _is_control_path(path)))
    diff_unavailable = changed is None
    required = diff_unavailable or bool(control_paths)
    gaps = ["control_replacement_diff_unavailable"] if diff_unavailable else []
    report: dict[str, object] = {
        "kind": "control_replacement_admission",
        "required": required,
        "accepted_head": accepted_head,
        "candidate_head": candidate_head,
        "changed_paths": list(changed_paths),
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
        "required_gaps": gaps,
    }
    if diff_unavailable or not required:
        return report
    receipt, receipt_gaps = _external_receipt(
        path=external_receipt,
        accepted_head=accepted_head,
        candidate_head=candidate_head,
        candidate_root=candidate_root,
        control_paths=control_paths,
    )
    report["incumbent_or_bootstrap"] = receipt
    if receipt_gaps:
        report["required_gaps"] = receipt_gaps
        return report
    report.update(verifier_provenance=str(receipt["provenance"]), verdict="allow")
    return report


def _changed_paths(root: Path, accepted_head: str, candidate_head: str) -> tuple[str, ...] | None:
    completed = subprocess.run(
        ["git", "diff", "--no-renames", "--name-only", f"{accepted_head}..{candidate_head}"],
        cwd=root,
        check=False,
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0:
        return None
    return tuple(path for path in completed.stdout.splitlines() if path)


def _is_control_path(path: str) -> bool:
    return any(path == prefix or path.startswith(prefix) for prefix in _CONTROL_PREFIXES)


def _inside_candidate(path: Path, root: Path) -> bool:
    candidate = root.resolve()
    return path == candidate or candidate in path.parents


def _failed_gaps(checks: tuple[bool, ...], gaps: tuple[str, ...]) -> list[str]:
    return [gap for ok, gap in zip(checks, gaps, strict=True) if not ok]


def _external_receipt(
    *,
    path: Path | None,
    accepted_head: str,
    candidate_head: str,
    candidate_root: Path,
    control_paths: tuple[str, ...] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    if path is None:
        return {}, ["incumbent_or_bootstrap_verifier_required"]
    resolved = path.resolve()
    if _inside_candidate(resolved, candidate_root):
        return {}, ["bootstrap_verifier_inside_candidate_tree"]
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}, ["control_replacement_receipt_invalid"]
    if not isinstance(payload, dict):
        return {}, ["control_replacement_receipt_invalid"]
    receipt = cast("dict[str, Any]", payload)
    return receipt, _receipt_gaps(
        receipt,
        accepted_head=accepted_head,
        candidate_head=candidate_head,
        candidate_root=candidate_root,
        control_paths=control_paths,
    )


def _receipt_gaps(
    receipt: dict[str, Any],
    *,
    accepted_head: str,
    candidate_head: str,
    candidate_root: Path,
    control_paths: tuple[str, ...] | None = None,
) -> list[str]:
    validation = validate_schema_instance(
        "control-replacement-verifier-receipt.schema.json", receipt, root=candidate_root
    )
    if not validation["ok"]:
        return ["control_replacement_receipt_invalid"]
    checks = (
        receipt.get("kind") == "control-replacement-verifier",
        receipt.get("provenance") in {"incumbent_runner", "protected_external_bootstrap"},
        receipt.get("accepted_head") == accepted_head,
        receipt.get("candidate_head") == candidate_head,
        receipt.get("verdict") == "allow",
        receipt.get("mints_authority") is False,
    )
    gaps = _failed_gaps(checks, _RECEIPT_CHECK_GAPS)
    if control_paths is not None:
        if receipt.get("control_paths") != list(control_paths):
            gaps.append("control_replacement_control_paths_mismatch")
        gaps.extend(
            _control_snapshot_gaps(
                receipt,
                root=candidate_root,
                accepted_head=accepted_head,
                candidate_head=candidate_head,
                control_paths=control_paths,
            )
        )
    artifacts, artifact_gaps = _external_artifacts(receipt, candidate_root)
    gaps.extend(artifact_gaps)
    decision_bytes = artifacts.get("bootstrap_decision_path")
    if decision_bytes is not None:
        try:
            decision = json.loads(decision_bytes)
        except (UnicodeDecodeError, json.JSONDecodeError):
            gaps.append("control_replacement_bootstrap_decision_invalid")
        else:
            gaps.extend(
                _bootstrap_decision_gaps(
                    decision,
                    receipt=receipt,
                    accepted_head=accepted_head,
                    candidate_head=candidate_head,
                )
            )
    gaps.extend(_candidate_proof_gaps(receipt, candidate_root, candidate_head))
    return list(dict.fromkeys(gaps))


def _control_snapshot_gaps(
    receipt: dict[str, Any],
    *,
    root: Path,
    accepted_head: str,
    candidate_head: str,
    control_paths: tuple[str, ...],
) -> list[str]:
    digests = (
        ("accepted", _control_digest(root, accepted_head, control_paths)),
        ("candidate", _control_digest(root, candidate_head, control_paths)),
    )
    if any(digest is None for _, digest in digests):
        return ["control_replacement_control_snapshot_unavailable"]
    return [
        f"control_replacement_{side}_control_digest_mismatch"
        for side, digest in digests
        if receipt.get(f"{side}_control_digest") != digest
    ]


def _external_artifacts(
    receipt: dict[str, Any], candidate_root: Path
) -> tuple[dict[str, bytes], list[str]]:
    artifacts: dict[str, bytes] = {}
    gaps: list[str] = []
    for name, digest_key in (
        ("verifier", "verifier_sha256"),
        ("bootstrap_decision", "bootstrap_decision_digest"),
    ):
        path_key = f"{name}_path"
        path = Path(str(receipt.get(path_key) or "")).resolve()
        gap_prefix = "control_replacement_" if name == "verifier" else ""
        if _inside_candidate(path, candidate_root):
            gaps.append(f"bootstrap_{name.removeprefix('bootstrap_')}_inside_candidate_tree")
        elif not path.is_file():
            gaps.append(f"{gap_prefix}{name}_missing")
        else:
            try:
                content = path.read_bytes()
            except OSError:
                gaps.append(f"{gap_prefix}{name}_missing")
            else:
                artifacts[path_key] = content
                if hashlib.sha256(content).hexdigest() != receipt.get(digest_key):
                    gaps.append(f"{gap_prefix}{name}_digest_mismatch")
    return artifacts, gaps


def _candidate_proof_gaps(
    receipt: dict[str, Any], candidate_root: Path, candidate_head: str
) -> list[str]:
    proof_path = Path(str(receipt.get("candidate_proof_path") or "")).resolve()
    if _inside_candidate(proof_path, candidate_root):
        return ["control_replacement_candidate_proof_inside_candidate_tree"]
    if not proof_path.is_file():
        return ["control_replacement_candidate_proof_missing"]
    try:
        proof_bytes = proof_path.read_bytes()
    except OSError:
        return ["control_replacement_candidate_proof_not_proven"]
    gaps = []
    if hashlib.sha256(proof_bytes).hexdigest() != receipt.get("candidate_proof_digest"):
        gaps.append("control_replacement_candidate_proof_digest_mismatch")
    try:
        proof = json.loads(proof_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return [*gaps, "control_replacement_candidate_proof_not_proven"]
    proof_head = _native_executed_proof_head(proof)
    if proof_head != candidate_head:
        gaps.append(
            "control_replacement_candidate_proof_head_mismatch"
            if proof_head
            else "control_replacement_candidate_proof_not_proven"
        )
    return gaps


def _bootstrap_decision_gaps(
    decision: object,
    *,
    receipt: dict[str, Any],
    accepted_head: str,
    candidate_head: str,
) -> list[str]:
    """Return exact binding gaps for one operator-supplied bootstrap decision."""
    if not isinstance(decision, dict):
        return ["control_replacement_bootstrap_decision_invalid"]
    bindings = (
        decision.get("schema_version") == 1,
        decision.get("kind") == "control-replacement-bootstrap-decision",
        decision.get("event_type") == "decision",
        decision.get("decision") == "bootstrap/control-replacement",
        decision.get("accepted_head") == accepted_head,
        decision.get("candidate_head") == candidate_head,
        decision.get("verifier_sha256") == receipt.get("verifier_sha256"),
        decision.get("candidate_proof_digest") == receipt.get("candidate_proof_digest"),
    )
    gaps = _failed_gaps(bindings, _BOOTSTRAP_BINDING_GAPS)
    evidence_ids = decision.get("evidence_ids")
    checks = (
        isinstance(evidence_ids, list) and bool(evidence_ids),
        decision.get("mints_authority") is False,
        decision.get("reusable_authorization") is False,
    )
    return [*gaps, *_failed_gaps(checks, _BOOTSTRAP_FLAG_GAPS)]


def _control_digest(root: Path, head: str, paths: tuple[str, ...]) -> str | None:
    """Return the content-addressed control snapshot for one Git tree."""
    records = []
    for path in paths:
        probe = subprocess.run(
            ["git", "ls-tree", "-z", head, "--", path],
            cwd=root,
            check=False,
            capture_output=True,
        )
        if probe.returncode != 0:
            return None
        present = bool(probe.stdout)
        content = (
            subprocess.run(
                ["git", "show", f"{head}:{path}"],
                cwd=root,
                check=False,
                capture_output=True,
            )
            if present
            else None
        )
        if content is not None and content.returncode != 0:
            return None
        records.append(
            {
                "path": path,
                "present": present,
                "tree_entry_sha256": hashlib.sha256(probe.stdout).hexdigest(),
                "sha256": hashlib.sha256(content.stdout).hexdigest() if content else "",
            }
        )
    body = json.dumps(records, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(body).hexdigest()


def _native_executed_proof_head(proof: object) -> str:
    """Return the candidate HEAD only for a native executed ETHOS proof result."""
    if not isinstance(proof, dict) or (
        proof.get("command") != "prove"
        or proof.get("ok") is not True
        or proof.get("state") != "proven"
    ):
        return ""
    data = proof.get("data")
    if not isinstance(data, dict) or data.get("executed") is not True:
        return ""
    provenance = data.get("provenance")
    evidence = data.get("evidence")
    predicate = provenance.get("predicate") if isinstance(provenance, dict) else None
    if not isinstance(evidence, dict) or not isinstance(predicate, dict):
        return ""
    head = evidence.get("head")
    return head if isinstance(head, str) and head == predicate.get("head") else ""
