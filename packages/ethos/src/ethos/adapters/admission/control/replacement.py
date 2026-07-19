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


def control_replacement_report(
    *,
    accepted_root: Path,
    candidate_root: Path,
    accepted_head: str,
    candidate_head: str,
    external_receipt: Path | None = None,
) -> dict[str, object]:
    """Admit exact externally verified control replacement, otherwise defer."""
    gaps = _checkout_gaps(accepted_root, candidate_root, accepted_head, candidate_head)
    if gaps:
        return _report(candidate_root, accepted_head, candidate_head, (), (), gaps)
    ancestry = _git_text(
        candidate_root, "merge-base", "--is-ancestor", accepted_head, candidate_head
    )
    if ancestry.returncode:
        gap = (
            "control_replacement_candidate_not_descendant"
            if ancestry.returncode == 1
            else "control_replacement_ancestry_unreadable"
        )
        return _report(candidate_root, accepted_head, candidate_head, (), (), [gap])
    changed_result = _git_text(
        candidate_root, "diff", "--name-only", f"{accepted_head}..{candidate_head}"
    )
    if changed_result.returncode:
        return _report(
            candidate_root,
            accepted_head,
            candidate_head,
            (),
            (),
            ["control_replacement_diff_unreadable"],
        )
    changed = tuple(filter(None, changed_result.stdout.splitlines()))
    control = tuple(sorted(path for path in changed if _is_control_path(path)))
    if not control:
        return _report(candidate_root, accepted_head, candidate_head, changed, control, [])
    receipt, receipt_gaps = _external_receipt(
        external_receipt,
        accepted_head=accepted_head,
        candidate_head=candidate_head,
        accepted_root=accepted_root,
        candidate_root=candidate_root,
        control_paths=control,
    )
    return _report(
        candidate_root,
        accepted_head,
        candidate_head,
        changed,
        control,
        receipt_gaps,
        receipt=receipt,
    )


def _report(  # noqa: PLR0913, RUF100 - exact control replacement report dimensions
    candidate_root: Path,
    accepted_head: str,
    candidate_head: str,
    changed: tuple[str, ...],
    control: tuple[str, ...],
    gaps: list[str],
    *,
    receipt: dict[str, Any] | None = None,
) -> dict[str, object]:
    required = bool(control or gaps)
    admitted = not gaps
    return {
        "kind": "control_replacement_admission",
        "required": required,
        "accepted_head": accepted_head,
        "candidate_head": candidate_head,
        "changed_paths": list(changed),
        "control_paths": list(control),
        "candidate_conformance": {
            "root": candidate_root.resolve().as_posix(),
            "head": candidate_head,
            "verifier_provenance": "candidate_runner",
            "self_approving": False,
        },
        "incumbent_or_bootstrap": receipt or {},
        "verifier_provenance": (
            str(receipt["provenance"])
            if admitted and receipt
            else "unknown"
            if required
            else "not_required"
        ),
        "self_approval": False,
        "mints_authority": False,
        "verdict": "allow" if admitted else "defer",
        "required_gaps": gaps,
    }


def _checkout_gaps(
    accepted_root: Path, candidate_root: Path, accepted_head: str, candidate_head: str
) -> list[str]:
    gaps = []
    for root, expected, name in (
        (accepted_root, accepted_head, "accepted"),
        (candidate_root, candidate_head, "candidate"),
    ):
        result = _git_text(root, "rev-parse", "HEAD")
        if result.returncode:
            gaps.append(f"control_replacement_{name}_checkout_head_unreadable")
        elif result.stdout.strip() != expected:
            gaps.append(f"control_replacement_{name}_checkout_head_mismatch")
    return gaps


def _is_control_path(path: str) -> bool:
    return any(path == prefix or path.startswith(prefix) for prefix in _CONTROL_PREFIXES)


def _external_receipt(  # noqa: PLR0913, RUF100 - exact dual-root verification dimensions
    path: Path | None,
    *,
    accepted_head: str,
    candidate_head: str,
    accepted_root: Path,
    candidate_root: Path,
    control_paths: tuple[str, ...],
) -> tuple[dict[str, Any], list[str]]:
    if path is None:
        return {}, ["incumbent_or_bootstrap_verifier_required"]
    resolved, candidate = path.resolve(), candidate_root.resolve()
    if resolved == candidate or candidate in resolved.parents:
        return {}, ["bootstrap_verifier_inside_candidate_tree"]
    receipt = _read_json(resolved)
    if receipt is None:
        return {}, ["control_replacement_receipt_invalid"]
    return receipt, _receipt_gaps(
        receipt,
        accepted_head=accepted_head,
        candidate_head=candidate_head,
        accepted_root=accepted_root,
        candidate_root=candidate_root,
        control_paths=control_paths,
    )


def _receipt_gaps(  # noqa: PLR0913, RUF100 - exact receipt trust-binding dimensions
    receipt: dict[str, Any],
    *,
    accepted_head: str,
    candidate_head: str,
    accepted_root: Path,
    candidate_root: Path,
    control_paths: tuple[str, ...],
) -> list[str]:
    if not validate_schema_instance(
        "control-replacement-verifier-receipt.schema.json", receipt, root=accepted_root
    )["ok"]:
        return ["control_replacement_receipt_invalid"]
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
        (
            receipt.get("control_paths") == list(control_paths),
            "control_replacement_control_paths_mismatch",
        ),
    )
    gaps = [gap for ok, gap in checks if not ok]
    accepted_digest = _control_digest(candidate_root, accepted_head, control_paths)
    candidate_digest = _control_digest(candidate_root, candidate_head, control_paths)
    if accepted_digest is None or candidate_digest is None:
        gaps.append("control_replacement_control_digest_unreadable")
    else:
        if receipt.get("accepted_control_digest") != accepted_digest:
            gaps.append("control_replacement_accepted_control_digest_mismatch")
        if receipt.get("candidate_control_digest") != candidate_digest:
            gaps.append("control_replacement_candidate_control_digest_mismatch")
    candidate = candidate_root.resolve()
    verifier = _artifact(
        receipt,
        path_key="verifier_path",
        digest_key="verifier_sha256",
        candidate=candidate,
        inside_gap="bootstrap_verifier_inside_candidate_tree",
        missing_gap="control_replacement_verifier_missing",
        digest_gap="control_replacement_verifier_digest_mismatch",
        gaps=gaps,
    )
    decision = _artifact(
        receipt,
        path_key="bootstrap_decision_path",
        digest_key="bootstrap_decision_digest",
        candidate=candidate,
        inside_gap="bootstrap_decision_inside_candidate_tree",
        missing_gap="bootstrap_decision_missing",
        digest_gap="bootstrap_decision_digest_mismatch",
        gaps=gaps,
    )
    proof = _artifact(
        receipt,
        path_key="candidate_proof_path",
        digest_key="candidate_proof_digest",
        candidate=None,
        inside_gap="",
        missing_gap="control_replacement_candidate_proof_missing",
        digest_gap="control_replacement_candidate_proof_digest_mismatch",
        gaps=gaps,
    )
    if proof is not None:
        gaps.extend(_proof_gaps(_read_json(proof), candidate_head))
    if decision is not None:
        gaps.extend(
            _decision_gaps(
                _read_json(decision),
                accepted_head=accepted_head,
                candidate_head=candidate_head,
                verifier_digest=_digest(verifier) if verifier else "",
                proof_digest=_digest(proof) if proof else "",
            )
        )
    return list(dict.fromkeys(gaps))


def _artifact(  # noqa: PLR0913, RUF100 - exact artifact validation dimensions
    receipt: dict[str, Any],
    *,
    path_key: str,
    digest_key: str,
    candidate: Path | None,
    inside_gap: str,
    missing_gap: str,
    digest_gap: str,
    gaps: list[str],
) -> Path | None:
    path = Path(str(receipt.get(path_key) or "")).expanduser().resolve()
    if candidate is not None and (path == candidate or candidate in path.parents):
        gaps.append(inside_gap)
        return None
    if not path.is_file():
        gaps.append(missing_gap)
        return None
    if _digest(path) != receipt.get(digest_key):
        gaps.append(digest_gap)
    return path


def _proof_gaps(proof: dict[str, Any] | None, candidate_head: str) -> list[str]:
    if not proof or (
        proof.get("command") != "prove"
        or proof.get("ok") is not True
        or proof.get("state") != "proven"
    ):
        return ["candidate_proof_not_proven"]
    data = proof.get("data")
    if not isinstance(data, dict) or data.get("executed") is not True:
        return ["candidate_proof_not_proven"]
    evidence, provenance = data.get("evidence"), data.get("provenance")
    predicate = provenance.get("predicate") if isinstance(provenance, dict) else None
    if not isinstance(evidence, dict) or not isinstance(predicate, dict):
        return ["candidate_proof_not_proven"]
    if evidence.get("head") != candidate_head or predicate.get("head") != candidate_head:
        return ["candidate_proof_head_mismatch"]
    return []


def _decision_gaps(
    decision: dict[str, Any] | None,
    *,
    accepted_head: str,
    candidate_head: str,
    verifier_digest: str,
    proof_digest: str,
) -> list[str]:
    if decision is None:
        return ["bootstrap_decision_invalid"]
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
    return [gap for ok, gap in checks if not ok]


def _control_digest(root: Path, head: str, paths: tuple[str, ...]) -> str | None:
    records = []
    for path in paths:
        shown = _git_bytes(root, "show", f"{head}:{path}")
        if shown.returncode == 0:
            records.append(
                {"path": path, "present": True, "sha256": hashlib.sha256(shown.stdout).hexdigest()}
            )
            continue
        listed = _git_bytes(root, "ls-tree", "-z", "--full-tree", head, "--", path)
        if listed.returncode or listed.stdout:
            return None
        records.append({"path": path, "present": False, "sha256": ""})
    encoded = json.dumps(records, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return cast("dict[str, Any]", payload) if isinstance(payload, dict) else None


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_text(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(["git", *args], cwd=root, check=False, capture_output=True, text=True)
    except OSError as exc:
        return subprocess.CompletedProcess(["git", *args], 127, "", str(exc))


def _git_bytes(root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(["git", *args], cwd=root, check=False, capture_output=True)
    except OSError as exc:
        return subprocess.CompletedProcess(["git", *args], 127, b"", str(exc).encode())
