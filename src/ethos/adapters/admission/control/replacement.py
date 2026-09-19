"""Independent verification admission for governance-control replacement."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING
from typing import cast

import ethos.adapters.repo.git as git
from ethos.adapters.admission.evidence.external import configured_verification_report
from ethos.adapters.admission.evidence.external import independent_verification_policy
from ethos.adapters.mutation.proof import proof_for_repository_transition
from ethos.adapters.repo.gate_policy import resolve_gate_policy
from ethos.contracts.semantic import canonical_json_digest
from ethos.contracts.verdict import report_verdict
from ethos.repository.policy.gates import gate_execution_identity

if TYPE_CHECKING:
    from pathlib import Path

_CONTROL_PREFIXES = (
    ".ethos/",
    ".config/checks/",
    "system/",
    "tools/ci/",
    "src/ethos/contracts/",
    "src/ethos/measure.py",
    "src/ethos/adapters/",
    "src/ethos/domain/campaign/",
    "src/ethos/domain/land/",
    "src/ethos/domain/report",
    "src/ethos/domain/source_budget/",
    "src/ethos/domain/status.py",
    "src/ethos/repository/adoption/",
    "src/ethos/repository/audit.py",
    "src/ethos/repository/context.py",
    "src/ethos/repository/evidence/",
    "src/ethos/repository/policy/",
    "src/ethos/repository/profile.py",
    "src/ethos/repository/release/",
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
    """Observe control changes and apply exact committed verification policy."""
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
    prior = resolve_gate_policy(candidate_root, tree_ref=accepted_head, full=True)
    proposed = resolve_gate_policy(candidate_root, tree_ref=candidate_head, full=True)
    changed_obligations = tuple(
        gate.id
        for gate in prior.gates
        if gate.policy == "required"
        and not any(
            (
                gate_execution_identity(gate) == gate_execution_identity(candidate)
                or (bool(gate.providers) and set(gate.providers) <= set(candidate.providers))
            )
            and candidate.policy == "required"
            and (not gate.trust_bearing or candidate.trust_bearing)
            and gate.evidence_class == candidate.evidence_class
            and set(gate.dimensions) <= set(candidate.dimensions)
            and set(gate.depends_on) <= set(candidate.depends_on)
            for candidate in proposed.gates
        )
    )
    floor = (
        {
            "accepted_policy_digest": prior.digest,
            "candidate_policy_digest": proposed.digest,
            "changed_obligations": list(changed_obligations),
        }
        if changed_obligations
        else {}
    )
    subject, request, gaps = _verification_subject(
        candidate_root, accepted_head, candidate_head, control_paths, floor=floor
    )
    report.update(subject=subject, verification_request=request, required_gaps=gaps)
    if gaps:
        return report
    verification = _verification_report(
        root=candidate_root,
        accepted_head=accepted_head,
        candidate_head=candidate_head,
        request=request,
        receipt_path=independent_verification_receipt,
    )
    report["independent_verification"] = verification
    report["required_gaps"] = list(cast("list[str]", verification["required_gaps"]))
    report["verdict"] = report_verdict(verification)
    return report


def _changed_paths(root: Path, accepted_head: str, candidate_head: str) -> tuple[str, ...] | None:
    completed = git.run_git(
        root,
        "diff",
        "--no-renames",
        "--name-only",
        f"{accepted_head}..{candidate_head}",
        check=False,
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
    *,
    floor: dict[str, object],
) -> tuple[dict[str, object], dict[str, object], list[str]]:
    accepted_tree = git.git_stdout(root, "rev-parse", f"{accepted_head}^{{tree}}")
    candidate_tree = git.git_stdout(root, "rev-parse", f"{candidate_head}^{{tree}}")
    accepted_digest = _control_digest(root, accepted_head, control_paths)
    candidate_digest = _control_digest(root, candidate_head, control_paths)
    proof, gaps = proof_for_repository_transition(root, candidate_head)
    if not accepted_tree or not candidate_tree or not accepted_digest or not candidate_digest:
        return {}, {}, ["control_replacement_control_snapshot_unavailable"]
    if proof is None:
        return {}, {}, gaps
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
                "statement": canonical_json_digest(proof.payload.body),
                "plan": proof.plan_digest,
            },
        },
        "control_paths": list(control_paths),
        **({"verification_floor": floor} if floor else {}),
    }
    request = {
        "remote": git.git_stdout(root, "remote", "get-url", "origin") or "local",
        "commit": candidate_head,
        "tree": candidate_tree,
        "action": "control-replacement",
        "proof_floor_id": "ethos:control-replacement:v1",
        "proof_floor_digest": canonical_json_digest(subject),
        "policy_digest": proof.policy_digest,
        "implementation_digest": "",
    }
    return subject, request, []


def _verification_report(
    *,
    root: Path,
    accepted_head: str,
    candidate_head: str,
    request: dict[str, object],
    receipt_path: Path | None,
) -> dict[str, object]:
    prior = independent_verification_policy(root, "control_replacement", tree_ref=accepted_head)
    proposed = independent_verification_policy(root, "control_replacement", tree_ref=candidate_head)
    modes = {"disabled": 0, "optional": 1, "required": 2}
    policy = max((prior, proposed), key=lambda item: modes[item.mode])
    return configured_verification_report(
        root=root,
        policy=policy,
        request=request,
        receipt_path=receipt_path,
    )


def _control_digest(root: Path, head: str, paths: tuple[str, ...]) -> str | None:
    """Return the content-addressed control snapshot for one immutable Git tree."""
    records = []
    for path in paths:
        probe = git.run_git(
            root,
            "ls-tree",
            "-z",
            head,
            "--",
            path,
            check=False,
            text=False,
        )
        if probe.returncode != 0:
            return None
        content = (
            git.run_git(
                root,
                "show",
                f"{head}:{path}",
                check=False,
                text=False,
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
    return canonical_json_digest(records)
