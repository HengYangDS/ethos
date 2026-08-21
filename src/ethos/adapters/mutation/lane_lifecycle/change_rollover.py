"""Start the next OpenSpec Change inside one exact owned Work Lane."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING
from typing import NamedTuple
from typing import cast

import tomli_w

import ethos.adapters.openspec.cli as openspec_cli
from ethos.adapters.mutation.lane_lifecycle.change_overlay import ChangeOverlay
from ethos.adapters.mutation.lane_lifecycle.change_overlay import advance_committed_lease
from ethos.adapters.mutation.lane_lifecycle.change_overlay import change_overlay_report
from ethos.adapters.mutation.lane_lifecycle.change_overlay import lifecycle_report
from ethos.adapters.mutation.lane_lifecycle.change_overlay import work_lane_transition_gaps
from ethos.adapters.mutation.local_state import local_state_mutation_guard
from ethos.adapters.openspec.generation.attestation import committed_start_attestation
from ethos.adapters.openspec.generation.attestation import prepare_start_effect
from ethos.adapters.openspec.generation.attestation import recognized_start_effect
from ethos.adapters.openspec.generation.attestation import recoverable_start_effect
from ethos.adapters.openspec.generation.attestation import start_effect_authority
from ethos.adapters.openspec.lifecycle.intent import committed_successor_mismatch
from ethos.adapters.openspec.lifecycle.intent import selected_input_gaps
from ethos.adapters.openspec.lifecycle.intent import successor_commitment
from ethos.adapters.repo.commit_message import lifecycle_commit_subject
from ethos.adapters.repo.commitment import exact_commitment_fields
from ethos.adapters.repo.commitment import load_commitment
from ethos.adapters.repo.commitment import load_lease_bound_commitment
from ethos.adapters.repo.commitment import load_repository_commitment
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git_effects import commit_git_worktree
from ethos.adapters.repo.git_effects import compensate_created_paths
from ethos.adapters.repo.git_effects import remove_untracked_tree
from ethos.adapters.repo.git_effects import stage_git_paths
from ethos.adapters.repo.status.bindings import lease_generation
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.store.state.lease.lifecycle.transitions import commitment_rebind_successor
from ethos.adapters.store.state.lease.lifecycle.transitions import rebind_lease_commitment
from ethos.adapters.store.state.lease.projection import integer_value
from ethos.adapters.store.state.lease.projection import project_lease
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.coordination import LaneLease
from ethos.contracts.coordination import LeaseOperationRequest
from ethos.repository.openspec.identifiers import logical_change_identifier_issue

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

_ARCHIVE_PREFIX = "openspec/changes/archive/"


class _StartRequest(NamedTuple):
    branch: str
    head: str
    change: str
    intent: str
    scope: tuple[str, ...]
    expect_head: str
    selected_attestations: tuple[str, ...]
    expected_overlay_digest: str
    apply: bool
    lease: dict[str, object]


class _FinishRequest(NamedTuple):
    branch: str
    change: str
    previous_head: str
    start_head: str
    head: str
    old_generation: dict[str, object]
    command: tuple[str, ...]
    state: str


def start_change(
    *,
    root: Path,
    change: str,
    intent: str,
    scope: tuple[str, ...],
    expect_head: str,
    selected_attestations: tuple[str, ...] = (),
    expected_overlay_digest: str = "",
    apply: bool = False,
) -> dict[str, object]:
    """Atomically start a new Change generation in the current owned lane."""
    repo = root.resolve()
    branch = git_stdout(repo, "branch", "--show-current")
    head = current_tracked_head(repo)
    lease = leases_by_branch(repo).get(branch, {})
    request = _StartRequest(
        branch,
        head,
        change,
        intent,
        scope,
        expect_head,
        selected_attestations,
        expected_overlay_digest,
        apply,
        lease,
    )
    if committed_successor_mismatch(
        repo,
        change=change,
        previous_head=expect_head,
        intent=intent,
        scope=scope,
        selected_attestations=selected_attestations,
    ):
        return lifecycle_report(
            branch,
            head,
            "blocked",
            ["openspec_change_request_mismatch"],
            change=change,
        )
    recognized = _recognized(repo, branch, change, expect_head, lease)
    recovery = None
    if recognized is None and head != expect_head:
        try:
            recovery = recoverable_start_effect(
                repo,
                change=change,
                previous_head=expect_head,
                lease=lease,
                command=openspec_cli.new_change_command(change),
            )
        except (OSError, TypeError, ValueError) as error:
            recognized = lifecycle_report(
                branch,
                head,
                "repair_required",
                [str(error)],
                change=change,
            )
    if recognized is not None:
        return recognized
    if recovery is not None:
        recovered = _recover(repo, request, recovery)
        if recovered is not None:
            return recovered
    gaps, overlay, selected_set_root = _preflight(repo, request)
    guard = local_state_mutation_guard(repo) if apply and not gaps else {"required_gaps": []}
    if guard["required_gaps"]:
        gaps = cast("list[str]", guard["required_gaps"])
    if gaps or not apply:
        return lifecycle_report(
            branch,
            head,
            "blocked" if gaps else "ready_to_start",
            gaps,
            change=change,
            overlay=overlay,
            **({"next_action": guard["next_action"]} if guard["required_gaps"] else {}),
        )
    try:
        return _apply(repo, request, overlay, selected_set_root)
    except (OSError, TypeError, ValueError) as error:
        return lifecycle_report(
            branch,
            current_tracked_head(repo),
            "repair_required",
            [str(error)],
            change=change,
        )


def _recover(
    root: Path,
    request: _StartRequest,
    recovery: tuple[dict[str, object], tuple[str, ...], str],
) -> dict[str, object] | None:
    branch, head, change, _, _, previous_head, _, _, apply, _lease = request
    guard = local_state_mutation_guard(root) if apply else {"required_gaps": []}
    if guard["required_gaps"]:
        return None
    if not apply:
        return lifecycle_report(
            branch,
            head,
            "ready_to_recover",
            [],
            change=change,
            previous_head=previous_head,
        )
    try:
        return _finish(
            root,
            _FinishRequest(
                branch,
                change,
                previous_head,
                recovery[2],
                head,
                recovery[0],
                recovery[1],
                "recovered",
            ),
        )
    except (OSError, TypeError, ValueError) as error:
        return lifecycle_report(
            branch,
            head,
            "repair_required",
            [str(error)],
            change=change,
        )


def _preflight(
    root: Path,
    request: _StartRequest,
) -> tuple[list[str], ChangeOverlay, str]:
    (
        branch,
        head,
        change,
        intent,
        scope,
        expect_head,
        selected_attestations,
        expected_digest,
        apply,
        lease,
    ) = request
    actor = os.environ.get("ETHOS_ACTOR", "").strip()
    carrier = str(lease.get("base_commitment_path") or "")
    gaps = work_lane_transition_gaps(
        root,
        branch=branch,
        head=head,
        expect_head=expect_head,
        lease=lease,
        actor=actor,
        role_gap="work_lane_required",
    )
    checks = (
        (carrier.startswith(_ARCHIVE_PREFIX), "openspec_archived_commitment_required"),
        (
            not logical_change_identifier_issue(change),
            f"openspec_change_identifier_invalid:{change}",
        ),
        (bool(intent.strip()), "openspec_change_intent_missing"),
        (bool(scope), "openspec_change_scope_missing"),
        (
            not (root / "openspec" / "changes" / change).exists(),
            f"openspec_change_exists:{change}",
        ),
    )
    gaps.extend(gap for valid, gap in checks if not valid)
    overlay: ChangeOverlay = {"paths": (), "digest": "", "required_gaps": []}
    selected_set_root = ""
    if not gaps:
        try:
            predecessor = load_lease_bound_commitment(root, lease=lease)
        except ValueError as error:
            gaps.append(str(error))
    if not gaps:
        try:
            successor_commitment(
                root=root,
                change=change,
                intent=intent,
                scope=scope,
                predecessor=predecessor,
                selected_attestations=selected_attestations,
            )
        except ValueError:
            gaps.append("openspec_change_commitment_invalid")
    if not gaps:
        selected_set_root, selection_gaps = selected_input_gaps(
            root,
            change,
            selected_attestations,
        )
        gaps.extend(selection_gaps)
    if not gaps:
        overlay = change_overlay_report(
            root,
            scope=scope,
            expected_digest=expected_digest,
            apply=apply,
        )
        gaps.extend(str(gap) for gap in overlay["required_gaps"])
    if not gaps:
        gaps.extend(openspec_cli.active_change_gaps(root))
    return gaps, overlay, selected_set_root


def _apply(
    root: Path,
    request: _StartRequest,
    overlay: ChangeOverlay,
    selected_set_root: str,
) -> dict[str, object]:
    (
        branch,
        _head,
        change,
        intent,
        scope,
        previous_head,
        selected_attestations,
        _digest,
        _apply,
        old_lease,
    ) = request
    command = openspec_cli.new_change_command(change)
    _selected_root, selection_gaps = selected_input_gaps(
        root, change, selected_attestations, expected_root=selected_set_root
    )
    if selection_gaps:
        raise ValueError(selection_gaps[0])
    result = openspec_cli.run_json(root, command[:-4], command[-4:])
    change_root = f"openspec/changes/{change}"
    created_paths = (f"{change_root}/.openspec.yaml", f"{change_root}/commitment.toml")
    _selected_root, selection_gaps = selected_input_gaps(
        root, change, selected_attestations, expected_root=selected_set_root
    )
    if selection_gaps:
        remove_untracked_tree(root, change_root)
        raise ValueError(selection_gaps[0])
    if not openspec_cli.new_change_result_valid(root, change, result):
        remove_untracked_tree(root, change_root)
        msg = "openspec_change_create_failed"
        raise ValueError(msg)
    commitment_path = f"{change_root}/commitment.toml"
    commitment_text = tomli_w.dumps(
        successor_commitment(
            root,
            change=change,
            intent=intent,
            scope=scope,
            predecessor=load_lease_bound_commitment(root, lease=old_lease),
            selected_attestations=selected_attestations,
        ).model_dump(mode="python")
    ).replace("\n    ", "\n  ")
    (root / commitment_path).write_text(commitment_text, encoding="utf-8")
    overlay_paths = tuple(str(path) for path in overlay.get("paths", ()))
    stage_git_paths(root, (*overlay_paths, *created_paths))
    target_tree = git_stdout(root, "write-tree")
    commitment = load_commitment(
        root,
        carrier=commitment_path,
        change_id=change,
        tree_ref=target_tree,
    )
    repository = load_repository_commitment(root, tree_ref=target_tree)
    prepare_start_effect(
        root,
        change=change,
        previous_head=previous_head,
        target_tree=target_tree,
        current_lease=old_lease,
        commitment=commitment,
        repository_id=repository.id,
        command=command,
        create=True,
    )
    committed = commit_git_worktree(
        root,
        previous=previous_head,
        message=lifecycle_commit_subject(root, "start", change),
    )
    if committed["verdict"] != "pass":
        compensate_created_paths(
            root,
            head=previous_head,
            paths=created_paths,
            untracked_root=change_root,
        )
        msg = str(committed.get("error") or "openspec_change_commit_failed")
        raise ValueError(msg)
    head = current_tracked_head(root)
    advance_committed_lease(
        root,
        branch=branch,
        previous_head=previous_head,
        head=head,
        failure_gap="openspec_change_lease_head_transition_failed",
    )
    return _finish(
        root,
        _FinishRequest(
            branch,
            change,
            previous_head,
            head,
            head,
            lease_generation(old_lease),
            command,
            "started",
        ),
    )


def _finish(
    root: Path,
    request: _FinishRequest,
) -> dict[str, object]:
    branch, change, previous_head, start_head, head, old_generation, command, state = request
    carrier = f"openspec/changes/{change}/commitment.toml"
    current_lease = leases_by_branch(root).get(branch, {})
    target = exact_commitment_fields(root, head=head, carrier=carrier, change_id=change)
    start_target = exact_commitment_fields(root, head=start_head, carrier=carrier, change_id=change)
    current = LaneLease.from_payload(dict(cast("Mapping[str, object]", current_lease["payload"])))
    successor_record = project_lease(commitment_rebind_successor(current, binding=target))
    start_successor_record = project_lease(
        commitment_rebind_successor(current, binding=start_target)
    )
    commitment = load_commitment(root, carrier=carrier, change_id=change, tree_ref=head)
    repository = load_repository_commitment(root, tree_ref=head)
    prepared_old = prepare_start_effect(
        root,
        change=change,
        previous_head=previous_head,
        target_tree=str(start_target["expected_tree"]),
        current_lease=current_lease,
        commitment=commitment,
        repository_id=repository.id,
        command=command,
        create=False,
    )
    if old_generation != prepared_old:
        message = "openspec_change_start_attestation_collision"
        raise ValueError(message)
    attestation = committed_start_attestation(
        root,
        change=change,
        command=command,
        previous_head=previous_head,
        head=start_head,
        old_generation=old_generation,
        new_generation=lease_generation(start_successor_record),
        commitment=commitment,
        repository_id=repository.id,
    )
    updated = rebind_lease_commitment(
        state_database(root),
        request=_lease_request(
            branch, current_lease, str(current_lease.get("expected_head") or "")
        ),
        binding=target,
    )
    if lease_generation(updated) != lease_generation(successor_record):
        message = "openspec_change_lease_successor_mismatch"
        raise ValueError(message)
    if not start_effect_authority(
        root,
        attestation,
        head,
        repository.id,
        commitment,
        updated,
    ):
        message = "openspec_change_start_attestation_invalid"
        raise ValueError(message)
    return lifecycle_report(
        branch,
        head,
        state,
        [],
        change=change,
        previous_head=previous_head,
        lease=updated,
        tool_version=openspec_cli.OFFICIAL_VERSION,
        command=list(command),
        attestation=attestation.model_dump(mode="json"),
    )


def _lease_request(
    branch: str,
    lease: Mapping[str, object],
    head: str,
) -> LeaseOperationRequest:
    return LeaseOperationRequest(
        operation="commitment_rebind",
        branch=branch,
        holder_ref=str(lease.get("holder_ref") or ""),
        lease_id=str(lease.get("lease_id") or ""),
        expected_epoch=integer_value(lease.get("epoch")),
        expect_head=head,
        expected_expires_at=str(lease.get("expires_at") or ""),
        expected_payload_sha256=str(lease.get("payload_sha256") or ""),
        apply=True,
    )


def _recognized(
    root: Path,
    branch: str,
    change: str,
    previous_head: str,
    lease: dict[str, object],
) -> dict[str, object] | None:
    head = current_tracked_head(root)
    attestation = recognized_start_effect(
        root,
        change=change,
        previous_head=previous_head,
        lease=lease,
    )
    if attestation is None:
        return None
    return lifecycle_report(
        branch,
        head,
        "recognized",
        [],
        change=change,
        previous_head=previous_head,
        lease=lease,
        tool_version=openspec_cli.OFFICIAL_VERSION,
        attestation=attestation.model_dump(mode="json"),
    )
