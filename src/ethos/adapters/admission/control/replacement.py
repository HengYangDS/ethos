"""Independent verification admission for governance-control replacement."""

from __future__ import annotations

import hashlib
import json
import subprocess
from typing import TYPE_CHECKING
from typing import cast

import ethos.adapters.repo.git as git
from ethos.adapters.admission.evidence.external import default_provider_config_path
from ethos.adapters.admission.evidence.external import independent_verification_policy
from ethos.adapters.admission.evidence.external import independent_verification_report
from ethos.adapters.admission.evidence.external import load_independent_verification_provider
from ethos.adapters.admission.evidence.external import path_is_within
from ethos.adapters.admission.evidence.external import verify_independent_receipt_signature
from ethos.adapters.mutation.proof import proof_attestation
from ethos.adapters.mutation.proof import proof_gaps
from ethos.contracts.rules import stable_digest
from ethos.contracts.verdict import report_verdict

if TYPE_CHECKING:
    from pathlib import Path

_CONTROL_PREFIXES = (
    ".ethos/",
    ".config/checks/",
    "system/",
    "tools/ci/",
    "src/ethos/contracts/",
    "src/ethos/measure.py",
    "src/ethos/adapters/admission/",
    "src/ethos/adapters/gates/",
    "src/ethos/adapters/mutation/",
    "src/ethos/adapters/repo/git.py",
    "src/ethos/domain/campaign/",
    "src/ethos/domain/land/",
    "src/ethos/domain/report",
    "src/ethos/domain/source_budget/",
    "src/ethos/repository/adoption/",
    "src/ethos/repository/context.py",
    "src/ethos/repository/evidence/",
    "src/ethos/repository/policy/",
    "src/ethos/repository/profile.py",
    "src/ethos/surface/cli/hook/",
    "src/ethos/surface/cli/root/",
)


def control_replacement_report(
    *,
    candidate_root: Path,
    accepted_head: str,
    candidate_head: str,
    independent_verification_receipt: Path | None = None,
) -> dict[str, object]:
    """Require one protected signed receipt when the candidate changes control."""
    changed = _changed_paths(candidate_root, accepted_head, candidate_head)
    changed_paths = changed or ()
    control_paths = tuple(sorted(path for path in changed_paths if _is_control_path(path)))
    required = changed is None or bool(control_paths)
    report: dict[str, object] = {
        "kind": "control_replacement_admission",
        "required": required,
        "accepted_head": accepted_head,
        "candidate_head": candidate_head,
        "changed_paths": list(changed_paths),
        "control_paths": list(control_paths),
        "subject": {},
        "verification_request": {},
        "independent_verification": {},
        "self_approval": False,
        "mints_authority": False,
        "verdict": "pass" if not required else "unknown",
        "required_gaps": [],
    }
    if changed is None:
        report["required_gaps"] = ["control_replacement_diff_unavailable"]
        return report
    if not control_paths:
        return report
    subject, request, gaps = _verification_subject(
        candidate_root, accepted_head, candidate_head, control_paths
    )
    report.update(subject=subject, verification_request=request, required_gaps=gaps)
    if gaps:
        return report
    verification = _verification_report(
        root=candidate_root,
        request=request,
        receipt_path=independent_verification_receipt,
    )
    report["independent_verification"] = verification
    report["required_gaps"] = list(cast("list[str]", verification["required_gaps"]))
    report["verdict"] = report_verdict(verification)
    return report


def _changed_paths(root: Path, accepted_head: str, candidate_head: str) -> tuple[str, ...] | None:
    completed = subprocess.run(
        ["git", "diff", "--no-renames", "--name-only", f"{accepted_head}..{candidate_head}"],
        cwd=root,
        check=False,
        text=True,
        capture_output=True,
    )
    return (
        tuple(path for path in completed.stdout.splitlines() if path)
        if completed.returncode == 0
        else None
    )


def _is_control_path(path: str) -> bool:
    return any(path == prefix or path.startswith(prefix) for prefix in _CONTROL_PREFIXES)


def _verification_subject(
    root: Path,
    accepted_head: str,
    candidate_head: str,
    control_paths: tuple[str, ...],
) -> tuple[dict[str, object], dict[str, object], list[str]]:
    accepted_tree = git.git_stdout(root, "rev-parse", f"{accepted_head}^{{tree}}")
    candidate_tree = git.git_stdout(root, "rev-parse", f"{candidate_head}^{{tree}}")
    accepted_digest = _control_digest(root, accepted_head, control_paths)
    candidate_digest = _control_digest(root, candidate_head, control_paths)
    proof = proof_attestation(root, candidate_head)
    if not accepted_tree or not candidate_tree or not accepted_digest or not candidate_digest:
        return {}, {}, ["control_replacement_control_snapshot_unavailable"]
    if proof is None:
        return {}, {}, proof_gaps(root, candidate_head)
    subject = {
        "schema_version": 1,
        "kind": "control-replacement",
        "accepted": {
            "head": accepted_head,
            "tree": accepted_tree,
            "control_digest": accepted_digest,
        },
        "candidate": {
            "head": candidate_head,
            "tree": candidate_tree,
            "control_digest": candidate_digest,
            "proof": {
                "attestation": proof.id,
                "statement": proof.statement_digest,
                "plan": proof.plan_digest,
            },
        },
        "control_paths": list(control_paths),
    }
    request = {
        "remote": git.git_stdout(root, "remote", "get-url", "origin") or "local",
        "commit": candidate_head,
        "tree": candidate_tree,
        "action": "control-replacement",
        "proof_floor_id": "ethos:control-replacement:v1",
        "proof_floor_digest": stable_digest(subject),
        "policy_digest": proof.policy_digest,
        "implementation_digest": "",
    }
    return subject, request, []


def _verification_report(
    *, root: Path, request: dict[str, object], receipt_path: Path | None
) -> dict[str, object]:
    policy = independent_verification_policy(root, "control_replacement")
    if receipt_path is None:
        return independent_verification_report(
            root=root,
            policy=policy,
            request=request,
            receipt_path=None,
        )
    provider, gaps = load_independent_verification_provider(default_provider_config_path())
    if provider is None:
        return _blocked_verification(root, gaps)
    if not path_is_within(receipt_path, provider.receipt_store):
        return _blocked_verification(root, ["independent_verification_receipt_outside_store"])
    return independent_verification_report(
        root=root,
        policy=policy,
        request={**request, "implementation_digest": provider.implementation_digest},
        receipt_path=receipt_path,
        signature_verifier=lambda receipt: verify_independent_receipt_signature(receipt, provider),
    )


def _blocked_verification(root: Path, gaps: list[str]) -> dict[str, object]:
    return {
        "root": root.resolve().as_posix(),
        "mode": "required",
        "receipt": {},
        "evidence_class": "local_readiness",
        "mints_authority": False,
        "verdict": "block",
        "state": "blocked",
        "required_gaps": gaps,
    }


def _control_digest(root: Path, head: str, paths: tuple[str, ...]) -> str | None:
    """Return the content-addressed control snapshot for one immutable Git tree."""
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
        content = (
            subprocess.run(
                ["git", "show", f"{head}:{path}"],
                cwd=root,
                check=False,
                capture_output=True,
            )
            if probe.stdout
            else None
        )
        if content is not None and content.returncode != 0:
            return None
        records.append(
            {
                "path": path,
                "present": bool(probe.stdout),
                "tree_entry_sha256": hashlib.sha256(probe.stdout).hexdigest(),
                "sha256": hashlib.sha256(content.stdout).hexdigest() if content else "",
            }
        )
    return hashlib.sha256(
        json.dumps(records, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
