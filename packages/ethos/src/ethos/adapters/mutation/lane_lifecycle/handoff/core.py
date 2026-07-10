"""Cross-host Work Lane handoff command orchestration."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import cast

import ethos.adapters.mutation.lane_lifecycle.handoff.package as handoff_package
from ethos.adapters.mutation.core import MutationRequest
from ethos.adapters.mutation.core import mutation_envelope
from ethos.adapters.mutation.lane_lifecycle.core import repo_root
from ethos.adapters.mutation.lane_lifecycle.core import run_git
from ethos.adapters.repo.dirty.core import changed_paths
from ethos.adapters.repo.status.core import workspace_status
from ethos.adapters.store.state.lease.lifecycle.effects import revoke_lease
from ethos.adapters.store.state.lease.projection import active_leases
from ethos.adapters.store.state.lease.projection import integer_value
from ethos_core.contracts.branch.roles import ROLE_ACCEPTED_ROOT
from ethos_core.contracts.branch.roles import ROLE_WORK_LANE
from ethos_core.contracts.coordination import HolderRef

if TYPE_CHECKING:
    from collections.abc import Sequence


def export_cross_host_handoff(
    *,
    root: Path,
    branch: str,
    holder_ref: str,
    target_holder_ref: str,
    lease_id: str,
    epoch: int,
    expect_head: str,
    context_text: str,
    context_file: Path | None,
    output_root: Path | None,
    dirty_disposition: str | None,
    apply: bool,
) -> dict[str, object]:
    """Create a portable Git/context package without copying local lease state."""
    repo = repo_root(root)
    status = workspace_status(repo)
    head = _git_value(repo, "rev-parse", "HEAD")
    tree = _git_value(repo, "rev-parse", "HEAD^{tree}")
    lease = _current_lease(status=status, repo=repo, branch=branch)
    context, context_gap = _handoff_context(context_text=context_text, context_file=context_file)
    dirty_paths = changed_paths(repo)
    disposition = dirty_disposition or ("clean" if not dirty_paths else "")
    expected_state: dict[str, object] = {
        "root": repo.resolve().as_posix(),
        "branch": branch,
        "head": expect_head,
        "tree": tree,
        "holder_ref": holder_ref,
        "target_holder_ref": target_holder_ref,
        "lease_id": lease_id,
        "epoch": epoch,
        "dirty_disposition": disposition,
    }
    gaps = _export_gaps(
        status=status,
        branch=branch,
        head=head,
        expect_head=expect_head,
        holder_ref=holder_ref,
        target_holder_ref=target_holder_ref,
        lease_id=lease_id,
        epoch=epoch,
        lease=lease,
        dirty_paths=dirty_paths,
        dirty_disposition=disposition,
        context_gap=context_gap,
    )
    report = _handoff_report(branch=branch, apply=apply, gaps=gaps)
    if apply and not gaps:
        try:
            report.update(
                handoff_package.write_handoff_package(
                    repo=repo,
                    branch=branch,
                    head=head,
                    tree=tree,
                    holder_ref=holder_ref,
                    target_holder_ref=target_holder_ref,
                    lease_id=lease_id,
                    epoch=epoch,
                    context=context,
                    output_root=output_root,
                    dirty_disposition=disposition,
                    dirty_paths=dirty_paths,
                )
            )
        except (OSError, subprocess.SubprocessError, ValueError) as exc:
            report.update(ok=False, state="blocked", required_gaps=[f"handoff_export_failed:{exc}"])
    report["mutation"] = _handoff_envelope(
        command="lane-handoff-export",
        action="lane.handoff.export",
        resource=branch,
        expected_state=expected_state,
        report=report,
        apply=apply,
    )
    return report


def import_cross_host_handoff(
    *,
    root: Path,
    package: Path,
    target_holder_ref: str,
    apply: bool,
) -> dict[str, object]:
    """Import a verified package and create destination-local coordination."""
    destination = repo_root(root)
    status = workspace_status(destination)
    manifest, gaps = handoff_package.verified_handoff_manifest(package=package, root=destination)
    expected_state: dict[str, object] = {
        "root": destination.resolve().as_posix(),
        "package": package.resolve().as_posix(),
        "package_id": str(manifest.get("package_id") or ""),
        "source_lane_ref": str(manifest.get("source_lane_ref") or ""),
        "source_head": str(manifest.get("source_head") or ""),
        "target_holder_ref": target_holder_ref,
    }
    try:
        normalized_target = HolderRef.parse(target_holder_ref).serialize()
    except ValueError:
        gaps.append("target_holder_ref_invalid")
        normalized_target = target_holder_ref
    if manifest and normalized_target != str(manifest.get("target_holder_ref") or ""):
        gaps.append("handoff_target_holder_mismatch")
    if status.get("role") != ROLE_ACCEPTED_ROOT:
        gaps.append("handoff_import_requires_accepted_root")
    if status.get("dirty"):
        gaps.append("handoff_import_requires_clean_destination")
    branch = str(manifest.get("source_lane_ref") or "")
    if branch and _branch_exists(destination, branch):
        gaps.append("handoff_destination_branch_exists")
    gaps = list(dict.fromkeys(gaps))
    report = _handoff_report(branch=branch, apply=apply, gaps=gaps)
    if apply and not gaps:
        try:
            report.update(
                handoff_package.apply_handoff_import(
                    destination=destination,
                    package=package,
                    manifest=manifest,
                    target_holder_ref=normalized_target,
                )
            )
        except (OSError, subprocess.SubprocessError, ValueError) as exc:
            report.update(ok=False, state="blocked", required_gaps=[f"handoff_import_failed:{exc}"])
    report["mutation"] = _handoff_envelope(
        command="lane-handoff-import",
        action="lane.handoff.import",
        resource=branch or package.resolve().as_posix(),
        expected_state=expected_state,
        report=report,
        apply=apply,
    )
    return report


def revoke_cross_host_source(
    *,
    root: Path,
    package: Path,
    acknowledgement: Path,
    holder_ref: str,
    lease_id: str,
    epoch: int,
    expect_head: str,
    apply: bool,
) -> dict[str, object]:
    """Revoke the exact source lease only after destination acknowledgement."""
    repo = repo_root(root)
    status = workspace_status(repo)
    manifest, gaps = handoff_package.verified_handoff_manifest(package=package, root=repo)
    ack = _json_mapping(acknowledgement, gap="handoff_acknowledgement_invalid", gaps=gaps)
    branch = str(manifest.get("source_lane_ref") or "")
    head = _git_value(repo, "rev-parse", "HEAD")
    source_binding = manifest.get("source_lease_binding")
    binding = source_binding if isinstance(source_binding, dict) else {}
    expected_state: dict[str, object] = {
        "root": repo.resolve().as_posix(),
        "package_id": str(manifest.get("package_id") or ""),
        "branch": branch,
        "head": expect_head,
        "holder_ref": holder_ref,
        "lease_id": lease_id,
        "epoch": epoch,
        "acknowledgement_id": str(ack.get("acknowledgement_id") or ""),
    }
    if status.get("role") != ROLE_WORK_LANE or status.get("branch") != branch:
        gaps.append("handoff_source_lane_mismatch")
    if head != expect_head:
        gaps.append("expect_head_mismatch")
    comparisons = (
        (str(binding.get("holder_ref") or ""), holder_ref, "handoff_source_holder_mismatch"),
        (str(binding.get("lease_id") or ""), lease_id, "handoff_source_lease_mismatch"),
        (integer_value(binding.get("epoch")), epoch, "handoff_source_epoch_mismatch"),
        (str(binding.get("expected_head") or ""), expect_head, "handoff_source_head_mismatch"),
        (
            str(ack.get("package_id") or ""),
            str(manifest.get("package_id") or ""),
            "handoff_acknowledgement_package_mismatch",
        ),
        (
            str(ack.get("destination_head") or ""),
            expect_head,
            "handoff_acknowledgement_head_mismatch",
        ),
    )
    gaps.extend(gap for actual, expected, gap in comparisons if actual != expected)
    if ack.get("source_lease_transferred") is not False:
        gaps.append("handoff_acknowledgement_lease_boundary_invalid")
    gaps = list(dict.fromkeys(gaps))
    report = _handoff_report(branch=branch, apply=apply, gaps=gaps)
    if apply and not gaps:
        try:
            revoked = revoke_lease(
                _state_root(status=status, repo=repo) / ".ethos" / "state" / "state.sqlite",
                subject=branch,
                holder_ref=holder_ref,
                expected_lease_id=lease_id,
                expected_epoch=epoch,
                expected_head=expect_head,
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
    report["mutation"] = _handoff_envelope(
        command="lane-handoff-revoke-source",
        action="lane.handoff.revoke_source",
        resource=branch,
        expected_state=expected_state,
        report=report,
        apply=apply,
    )
    return report


def _export_gaps(
    *,
    status: dict[str, object],
    branch: str,
    head: str,
    expect_head: str,
    holder_ref: str,
    target_holder_ref: str,
    lease_id: str,
    epoch: int,
    lease: dict[str, object],
    dirty_paths: Sequence[str],
    dirty_disposition: str,
    context_gap: str,
) -> list[str]:
    gaps: list[str] = [context_gap] if context_gap else []
    gaps.extend(_holder_ref_gaps(holder_ref, target_holder_ref))
    gaps.extend(
        _export_binding_gaps(
            status=status,
            branch=branch,
            head=head,
            expect_head=expect_head,
            holder_ref=holder_ref,
            lease_id=lease_id,
            epoch=epoch,
            lease=lease,
        )
    )
    gaps.extend(_dirty_disposition_gaps(dirty_paths, dirty_disposition))
    return list(dict.fromkeys(gaps))


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


def _export_binding_gaps(
    *,
    status: dict[str, object],
    branch: str,
    head: str,
    expect_head: str,
    holder_ref: str,
    lease_id: str,
    epoch: int,
    lease: dict[str, object],
) -> list[str]:
    gaps: list[str] = []
    if status.get("role") != ROLE_WORK_LANE:
        gaps.append("work_lane_required")
    if status.get("branch") != branch:
        gaps.append("lane_branch_mismatch")
    if not expect_head:
        gaps.append("expect_head_required")
    elif expect_head != head:
        gaps.append("expect_head_mismatch")
    if str(lease.get("holder_ref") or "") != holder_ref:
        gaps.append("lease_holder_mismatch")
    if str(lease.get("lease_id") or "") != lease_id:
        gaps.append("lease_id_stale")
    if integer_value(lease.get("epoch")) != epoch:
        gaps.append("lease_epoch_stale")
    if str(lease.get("expected_head") or "") != head:
        gaps.append("lease_head_stale")
    return gaps


def _dirty_disposition_gaps(dirty_paths: Sequence[str], dirty_disposition: str) -> list[str]:
    if dirty_paths and not dirty_disposition:
        return ["dirty_disposition_required"]
    if dirty_disposition not in {"clean", "committed", "preserved"}:
        return ["dirty_disposition_invalid"]
    if dirty_paths and dirty_disposition in {"clean", "committed"}:
        return ["dirty_disposition_mismatch"]
    if not dirty_paths and dirty_disposition not in {"clean", "committed"}:
        return ["dirty_disposition_mismatch"]
    return []


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


def _current_lease(*, status: dict[str, object], repo: Path, branch: str) -> dict[str, object]:
    state_root = repo
    worktrees = status.get("worktrees")
    if isinstance(worktrees, list):
        for worktree in worktrees:
            if not isinstance(worktree, dict):
                continue
            worktree_payload = cast("dict[str, object]", worktree)
            if worktree_payload.get("role") == ROLE_ACCEPTED_ROOT and worktree_payload.get("path"):
                state_root = Path(str(worktree_payload["path"]))
                break
    matches = [
        lease
        for lease in active_leases(state_root / ".ethos" / "state" / "state.sqlite")
        if lease.get("subject") == branch
    ]
    return cast("dict[str, object]", matches[0]) if len(matches) == 1 else {}


def _state_root(*, status: dict[str, object], repo: Path) -> Path:
    worktrees = status.get("worktrees")
    if isinstance(worktrees, list):
        for worktree in worktrees:
            if not isinstance(worktree, dict):
                continue
            worktree_payload = cast("dict[str, object]", worktree)
            if worktree_payload.get("role") == ROLE_ACCEPTED_ROOT and worktree_payload.get("path"):
                return Path(str(worktree_payload["path"]))
    return repo


def _json_mapping(path: Path, *, gap: str, gaps: list[str]) -> dict[str, Any]:
    try:
        payload = json.loads(path.resolve().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        gaps.append(gap)
        return {}
    if not isinstance(payload, dict):
        gaps.append(gap)
        return {}
    return cast("dict[str, Any]", payload)


def _handoff_report(*, branch: str, apply: bool, gaps: list[str]) -> dict[str, object]:
    return {
        "ok": not gaps,
        "state": "planned" if not apply and not gaps else "blocked" if gaps else "applying",
        "branch": branch,
        "package_id": "",
        "package_path": "",
        "manifest": {},
        "lease": {},
        "acknowledgement": {},
        "receipt": {},
        "required_gaps": gaps,
    }


def _handoff_envelope(
    *,
    command: str,
    action: str,
    resource: str,
    expected_state: dict[str, object],
    report: dict[str, object],
    apply: bool,
) -> dict[str, object]:
    gaps = tuple(str(gap) for gap in cast("list[object]", report["required_gaps"]))
    return mutation_envelope(
        MutationRequest(command=command, apply=apply, authorized=False, expect_head=None),
        action=action,
        resource=resource,
        expected_state=expected_state,
        verdict=cast("Any", "allow" if report["ok"] else "block"),
        required_gaps=gaps,
        why=(str(report["state"]),) if report["ok"] else (),
        state=str(report["state"]),
        identity_basis="holder_ref_equality",
        evidence_boundary="content_addressed_git_and_context",
        enforcement_boundary="local_package_and_git_ref_transition",
        verifier_provenance="current_worktree_runner",
    )


def _branch_exists(root: Path, branch: str) -> bool:
    return (
        run_git(
            root, "show-ref", "--verify", "--quiet", f"refs/heads/{branch}", check=False
        ).returncode
        == 0
    )


def _git_value(root: Path, *args: str) -> str:
    return run_git(root, *args).stdout.strip()
