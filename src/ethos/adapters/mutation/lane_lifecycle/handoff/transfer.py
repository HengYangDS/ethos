"""Cross-host Work Lane handoff command orchestration."""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import cast

import ethos.adapters.mutation.lane_lifecycle.handoff.package as handoff_package
from ethos.adapters.mutation.decision import mutation_envelope
from ethos.adapters.mutation.lane_lifecycle.handoff.destination_import import apply_handoff_import
from ethos.adapters.openspec.profile import load_profile_lease_bound_commitment
from ethos.adapters.repo.dirty.change_provenance import changed_paths
from ethos.adapters.repo.git import repository_root
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.status.workspace import workspace_status
from ethos.adapters.store.state.lease.lifecycle.effects import revoke_lease
from ethos.adapters.store.state.lease.projection import integer_value
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.branch.roles import ROLE_ACCEPTED_ROOT
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from ethos.contracts.coordination import CrossHostHandoff
from ethos.contracts.coordination import CrossHostHandoffExportRequest
from ethos.contracts.coordination import CrossHostHandoffImportRequest
from ethos.contracts.coordination import CrossHostHandoffSourceRevocationRequest
from ethos.contracts.coordination import HolderRef
from ethos.contracts.coordination import LeaseOperationRequest
from ethos.contracts.coordination import MutationAdmissionRequest
from ethos.contracts.lifecycle.declaration import load_lifecycle_declaration
from ethos.contracts.lifecycle.reducer import TransitionFacts
from ethos.contracts.lifecycle.reducer import TransitionRequest
from ethos.contracts.lifecycle.reducer import reduce_transition

if TYPE_CHECKING:
    from collections.abc import Callable


def export_cross_host_handoff(request: CrossHostHandoffExportRequest) -> dict[str, object]:
    """Create a portable Git/context package without copying local lease state."""
    repo = repository_root(Path(request.root))
    status = workspace_status(repo)
    head = _git_value(repo, "rev-parse", "HEAD")
    tree = _git_value(repo, "rev-parse", "HEAD^{tree}")
    lease = leases_by_branch(repo).get(request.branch, {})
    base_commitment_digest = str(lease.get("base_commitment_digest") or "")
    try:
        selected_base_digest = load_profile_lease_bound_commitment(
            repo,
            expected_head=head,
            base_commitment_digest=base_commitment_digest,
        ).digest()
    except ValueError:
        selected_base_digest = ""
    context_file = Path(request.context_file) if request.context_file else None
    context, context_gap = _handoff_context(
        context_text=request.context_text,
        context_file=context_file,
    )
    dirty_paths = changed_paths(repo)
    dirty_content_sha256 = handoff_package.dirty_content_sha256(repo)
    expected_state: dict[str, object] = {
        "root": repo.resolve().as_posix(),
        "branch": request.branch,
        "head": request.expect_head,
        "tree": tree,
        "holder_ref": request.holder_ref,
        "target_holder_ref": request.target_holder_ref,
        "lease_id": request.lease_id,
        "epoch": request.epoch,
        "expires_at": request.expected_expires_at,
        "payload_sha256": request.expected_payload_sha256,
        "base_commitment_digest": base_commitment_digest,
    }
    checks = (
        (status.get("role") == ROLE_WORK_LANE, "work_lane_required"),
        (status.get("branch") == request.branch, "lane_branch_mismatch"),
        (lease.get("lease_state") == "valid", _lease_state_gap(request.branch, lease)),
        (head == request.expect_head, "expect_head_mismatch"),
        (str(lease.get("holder_ref") or "") == request.holder_ref, "lease_holder_mismatch"),
        (str(lease.get("lease_id") or "") == request.lease_id, "lease_id_stale"),
        (integer_value(lease.get("epoch")) == request.epoch, "lease_epoch_stale"),
        (str(lease.get("expected_head") or "") == head, "lease_head_stale"),
        (
            str(lease.get("expires_at") or "") == request.expected_expires_at
            and str(lease.get("payload_sha256") or "") == request.expected_payload_sha256,
            "lease_generation_stale",
        ),
        (bool(base_commitment_digest), "lease_base_commitment_digest_missing"),
        (
            base_commitment_digest == selected_base_digest,
            "lease_base_commitment_digest_mismatch",
        ),
        (
            os.environ.get("ETHOS_ACTOR", "").strip() == request.holder_ref,
            "lease_actor_mismatch",
        ),
        (not dirty_paths, "handoff_export_requires_clean_lane"),
    )
    gaps = list(
        dict.fromkeys(
            [context_gap] * bool(context_gap)
            + _holder_ref_gaps(request.holder_ref, request.target_holder_ref)
            + [gap for ok, gap in checks if not ok]
        )
    )
    evaluation = reduce_transition(
        load_lifecycle_declaration(repo).policy("guarded"),
        TransitionRequest(apply=request.apply),
        TransitionFacts(initial_gaps=tuple(gaps)),
    )
    report = _handoff_report(branch=request.branch, evaluation=evaluation)
    if request.apply and evaluation.ok:
        output_root = Path(request.output_root) if request.output_root else None
        _apply_report(
            report,
            "handoff_export_failed",
            lambda: handoff_package.write_handoff_package(
                repo=repo,
                handoff=CrossHostHandoff(
                    source_lane_ref=request.branch,
                    source_head=head,
                    source_tree=tree,
                    source_holder_ref=HolderRef.parse(request.holder_ref),
                    target_holder_ref=HolderRef.parse(request.target_holder_ref),
                    source_lease_id=request.lease_id,
                    source_lease_epoch=request.epoch,
                    source_lease_expires_at=request.expected_expires_at,
                    source_lease_payload_sha256=request.expected_payload_sha256,
                    base_commitment_digest=base_commitment_digest,
                    dirty_content_sha256=dirty_content_sha256,
                    context_digest=hashlib.sha256(context.encode("utf-8")).hexdigest(),
                ),
                context=context,
                output_root=output_root,
            ),
        )
    return _finish_report(
        report,
        ("lane-handoff-export", "lane.handoff.export", request.branch),
        expected_state,
        apply=request.apply,
    )


def import_cross_host_handoff(request: CrossHostHandoffImportRequest) -> dict[str, object]:
    """Import a verified package and create destination-local coordination."""
    destination = repository_root(Path(request.root))
    package = Path(request.package)
    status = workspace_status(destination)
    manifest, gaps = handoff_package.verified_handoff_manifest(package=package, root=destination)
    expected_state: dict[str, object] = {
        "root": destination.resolve().as_posix(),
        "package": package.resolve().as_posix(),
        "package_id": str(manifest.get("package_id") or ""),
        "source_lane_ref": str(manifest.get("source_lane_ref") or ""),
        "source_head": str(manifest.get("source_head") or ""),
        "target_holder_ref": request.target_holder_ref,
        "base_commitment_digest": str(manifest.get("base_commitment_digest") or ""),
    }
    try:
        normalized_target = HolderRef.parse(request.target_holder_ref).serialize()
    except ValueError:
        gaps.append("target_holder_ref_invalid")
        normalized_target = request.target_holder_ref
    if manifest and normalized_target != str(manifest.get("target_holder_ref") or ""):
        gaps.append("handoff_target_holder_mismatch")
    if os.environ.get("ETHOS_ACTOR", "").strip() != normalized_target:
        gaps.append("handoff_target_actor_mismatch")
    branch = str(manifest.get("source_lane_ref") or "")
    checks = (
        (status.get("role") == ROLE_ACCEPTED_ROOT, "handoff_import_requires_accepted_root"),
        (not bool(status.get("dirty")), "handoff_import_requires_clean_destination"),
    )
    evaluation = reduce_transition(
        load_lifecycle_declaration(destination).policy("guarded"),
        TransitionRequest(apply=request.apply),
        TransitionFacts(initial_gaps=tuple(gaps), checks=checks),
    )
    report = _handoff_report(branch=branch, evaluation=evaluation)
    if request.apply and evaluation.ok:
        _apply_report(
            report,
            "handoff_import_failed",
            lambda: apply_handoff_import(
                destination=destination,
                package=package,
                manifest=manifest,
                target_holder_ref=normalized_target,
            ),
        )
    return _finish_report(
        report,
        ("lane-handoff-import", "lane.handoff.import", branch or package.resolve().as_posix()),
        expected_state,
        apply=request.apply,
    )


def revoke_cross_host_source(
    request: CrossHostHandoffSourceRevocationRequest,
) -> dict[str, object]:
    """Revoke the exact source lease only after destination acknowledgement."""
    repo = repository_root(Path(request.root))
    package = Path(request.package)
    acknowledgement = Path(request.acknowledgement)
    status = workspace_status(repo)
    manifest, gaps = handoff_package.verified_handoff_manifest(package=package, root=repo)
    ack, acknowledgement_gaps = handoff_package.verified_handoff_acknowledgement(
        acknowledgement=acknowledgement,
        root=repo,
    )
    gaps.extend(acknowledgement_gaps)
    branch = str(manifest.get("source_lane_ref") or "")
    head = _git_value(repo, "rev-parse", "HEAD")
    source_binding = manifest.get("source_lease_binding")
    binding = source_binding if isinstance(source_binding, dict) else {}
    lease = leases_by_branch(repo).get(branch, {})
    expected_state: dict[str, object] = {
        "root": repo.resolve().as_posix(),
        "package_id": str(manifest.get("package_id") or ""),
        "branch": branch,
        "head": request.expect_head,
        "holder_ref": request.holder_ref,
        "lease_id": request.lease_id,
        "epoch": request.epoch,
        "expires_at": request.expected_expires_at,
        "payload_sha256": request.expected_payload_sha256,
        "acknowledgement_id": str(ack.get("acknowledgement_id") or ""),
        "base_commitment_digest": str(manifest.get("base_commitment_digest") or ""),
    }
    comparisons = (
        (
            str(binding.get("holder_ref") or ""),
            request.holder_ref,
            "handoff_source_holder_mismatch",
        ),
        (str(binding.get("lease_id") or ""), request.lease_id, "handoff_source_lease_mismatch"),
        (integer_value(binding.get("epoch")), request.epoch, "handoff_source_epoch_mismatch"),
        (
            str(binding.get("expected_head") or ""),
            request.expect_head,
            "handoff_source_head_mismatch",
        ),
        (
            str(ack.get("package_id") or ""),
            str(manifest.get("package_id") or ""),
            "handoff_acknowledgement_package_mismatch",
        ),
        (
            str(ack.get("destination_head") or ""),
            request.expect_head,
            "handoff_acknowledgement_head_mismatch",
        ),
        (
            str(ack.get("destination_tree") or ""),
            str(manifest.get("source_tree") or ""),
            "handoff_acknowledgement_tree_mismatch",
        ),
        (
            str(ack.get("destination_lane_ref") or ""),
            branch,
            "handoff_acknowledgement_lane_mismatch",
        ),
        (
            str(ack.get("destination_holder_ref") or ""),
            str(manifest.get("target_holder_ref") or ""),
            "handoff_acknowledgement_holder_mismatch",
        ),
        (
            str(ack.get("destination_lease_expected_head") or ""),
            request.expect_head,
            "handoff_acknowledgement_destination_head_mismatch",
        ),
        (
            str(ack.get("base_commitment_digest") or ""),
            str(manifest.get("base_commitment_digest") or ""),
            "handoff_acknowledgement_base_commitment_digest_mismatch",
        ),
        (
            str(lease.get("base_commitment_digest") or ""),
            str(manifest.get("base_commitment_digest") or ""),
            "handoff_source_base_commitment_digest_mismatch",
        ),
        (
            request.expected_expires_at,
            str(binding.get("expires_at") or ""),
            "handoff_source_lease_mismatch",
        ),
        (
            request.expected_payload_sha256,
            str(binding.get("payload_sha256") or ""),
            "handoff_source_lease_mismatch",
        ),
        (
            str(lease.get("expires_at") or ""),
            request.expected_expires_at,
            "lease_generation_stale",
        ),
        (
            str(lease.get("payload_sha256") or ""),
            request.expected_payload_sha256,
            "lease_generation_stale",
        ),
        (os.environ.get("ETHOS_ACTOR", "").strip(), request.holder_ref, "lease_actor_mismatch"),
    )
    checks = (
        (
            status.get("role") == ROLE_WORK_LANE and status.get("branch") == branch,
            "handoff_source_lane_mismatch",
        ),
        (lease.get("lease_state") == "valid", _lease_state_gap(branch, lease)),
        (head == request.expect_head, "expect_head_mismatch"),
        *((actual == expected, gap) for actual, expected, gap in comparisons),
        (
            ack.get("source_lease_transferred") is False,
            "handoff_acknowledgement_lease_boundary_invalid",
        ),
    )
    evaluation = reduce_transition(
        load_lifecycle_declaration(repo).policy("guarded"),
        TransitionRequest(apply=request.apply),
        TransitionFacts(initial_gaps=tuple(gaps), checks=checks),
    )
    report = _handoff_report(branch=branch, evaluation=evaluation)
    if request.apply and evaluation.ok:
        try:
            revoked = revoke_lease(
                state_database(repo),
                request=LeaseOperationRequest(
                    operation="handoff_source_revoke",
                    branch=branch,
                    holder_ref=request.holder_ref,
                    lease_id=request.lease_id,
                    expected_epoch=request.epoch,
                    expect_head=request.expect_head,
                    expected_expires_at=request.expected_expires_at,
                    expected_payload_sha256=request.expected_payload_sha256,
                    apply=True,
                ),
            )
        except ValueError as exc:
            report.update(ok=False, state="blocked", required_gaps=[str(exc)])
        else:
            report.update(
                state="source_revoked",
                receipt={
                    "operation": "cross-host-source-revoke",
                    "package_id": str(manifest["package_id"]),
                    "acknowledgement_id": str(ack["acknowledgement_id"]),
                    **revoked,
                },
            )
    return _finish_report(
        report,
        ("lane-handoff-revoke-source", "lane.handoff.revoke_source", branch),
        expected_state,
        apply=request.apply,
    )


def _holder_ref_gaps(holder_ref: str, target_holder_ref: str) -> list[str]:
    gaps: list[str] = []
    for ref, gap in (
        (holder_ref, "holder_ref_invalid"),
        (target_holder_ref, "target_holder_ref_invalid"),
    ):
        try:
            HolderRef.parse(ref)
        except ValueError:
            gaps.append(gap)
    return gaps


def _lease_state_gap(branch: str, lease: dict[str, object]) -> str:
    state = str(lease.get("lease_state") or "missing")
    return {
        "unknown": f"work_lane_lease_unknown:{branch}",
        "expired": f"work_lane_lease_expired:{branch}",
    }.get(state, f"work_lane_missing_lease:{branch}")


def _handoff_context(*, context_text: str, context_file: Path | None) -> tuple[str, str]:
    if context_text and context_file is not None:
        return "", "handoff_context_ambiguous"
    if context_file is not None:
        try:
            value = context_file.resolve().read_text(encoding="utf-8")
        except OSError:
            return "", "handoff_context_file_unreadable"
        return value, "" if value.strip() else "handoff_context_required"
    return context_text, "" if context_text.strip() else "handoff_context_required"


def _handoff_report(*, branch: str, evaluation: Any) -> dict[str, object]:
    return {
        "ok": evaluation.ok,
        "state": evaluation.state,
        "branch": branch,
        **dict.fromkeys(("package_id", "package_path"), ""),
        **{key: {} for key in ("manifest", "lease", "acknowledgement", "receipt")},
        "required_gaps": list(evaluation.gaps),
    }


def _apply_report(
    report: dict[str, object], gap: str, effect: Callable[[], dict[str, object]]
) -> None:
    try:
        report.update(effect())
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        report.update(ok=False, state="blocked", required_gaps=[f"{gap}:{exc}"])


def _finish_report(
    report: dict[str, object],
    envelope: tuple[str, str, str],
    expected_state: dict[str, object],
    *,
    apply: bool,
) -> dict[str, object]:
    command, action, resource = envelope
    gaps = tuple(str(gap) for gap in cast("list[object]", report["required_gaps"]))
    report["mutation"] = mutation_envelope(
        TransitionRequest(command=command, apply=apply, authorized=False, expect_head=None),
        MutationAdmissionRequest(
            action=action,
            resource=resource,
            expected_state=expected_state,
            verdict=cast("Any", "pass" if report["ok"] else "block"),
            required_gaps=gaps,
            why=(str(report["state"]),) if report["ok"] else (),
            state=str(report["state"]),
            identity_basis="holder_ref_equality",
            evidence_boundary="content_addressed_git_and_context",
            enforcement_boundary="local_package_and_git_ref_transition",
            verifier_provenance="current_worktree_runner",
        ),
    )
    return report


def _git_value(root: Path, *args: str) -> str:
    return run_git(root, *args).stdout.strip()
