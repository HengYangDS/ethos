"""Start the next OpenSpec Change inside one exact owned Work Lane."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any
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
from ethos.adapters.openspec.generation.attestation import start_effect_authority
from ethos.adapters.openspec.lifecycle.report import official_change_rows
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.attestation_set import record_attestations
from ethos.adapters.repo.commit_message import lifecycle_commit_subject
from ethos.adapters.repo.commitment import exact_commitment_fields
from ethos.adapters.repo.commitment import load_commitment
from ethos.adapters.repo.commitment import load_lease_bound_commitment
from ethos.adapters.repo.commitment import load_repository_commitment
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_effect_attestation import NativeEffect
from ethos.adapters.repo.git_effect_attestation import issue_native_effect
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
from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import Commitment
from ethos.repository.openspec.identifiers import logical_change_identifier_issue

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
    head: str
    old_lease: dict[str, object]
    command: tuple[str, ...]
    state: str


class _RecoveryRequest(NamedTuple):
    branch: str
    change: str
    previous_head: str
    head: str
    lease: dict[str, object]
    command: tuple[str, ...]
    apply: bool


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
    if _committed_request_mismatch(
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
    if recognized is not None:
        return recognized
    recovery = _recoverable(repo, change, expect_head, lease)
    if recovery is not None:
        guard = local_state_mutation_guard(repo) if apply else {"required_gaps": []}
        if guard["required_gaps"]:
            recovery = None
        else:
            return _recover(
                repo,
                _RecoveryRequest(branch, change, expect_head, head, lease, recovery, apply),
            )
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
    request: _RecoveryRequest,
) -> dict[str, object]:
    branch, change, previous_head, head, lease, command, apply = request
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
                head,
                lease,
                command,
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
    overlay = _empty_overlay()
    selected_set_root = ""
    if not gaps:
        try:
            _commitment(
                root=root,
                change=change,
                intent=intent,
                scope=scope,
                predecessor=load_lease_bound_commitment(root, lease=lease),
                selected_attestations=selected_attestations,
            )
        except ValueError:
            gaps.append("openspec_change_commitment_invalid")
    if not gaps:
        selected_set_root, selection_gaps = _selection_observation(
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
        try:
            load_lease_bound_commitment(root, lease=lease)
        except ValueError as error:
            gaps.append(str(error))
    if not gaps:
        gaps.extend(_openspec_start_gaps(root))
    return gaps, overlay, selected_set_root


def _openspec_start_gaps(root: Path) -> list[str]:
    command = openspec_cli.openspec_base_command()
    if command is None:
        return ["openspec_official_cli_missing"]
    listed = openspec_cli.run_json(root, command, ("list", "--json"))
    rows = official_change_rows(listed.get("json", {}))
    if listed.get("exit_code") != 0 or listed.get("parse_error") or rows is None:
        return ["openspec_list_unreadable"]
    return ["openspec_active_change_present"] if rows else []


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
    command = openspec_cli.openspec_base_command()
    if command is None:
        msg = "openspec_official_cli_missing"
        raise ValueError(msg)
    _require_selection_boundary(
        root,
        change=change,
        identities=selected_attestations,
        expected_root=selected_set_root,
    )
    result = openspec_cli.run_json(root, command, ("new", "change", change, "--json"))
    change_root = f"openspec/changes/{change}"
    created_paths = (f"{change_root}/.openspec.yaml", f"{change_root}/commitment.toml")
    try:
        _require_selection_boundary(
            root,
            change=change,
            identities=selected_attestations,
            expected_root=selected_set_root,
        )
    except ValueError:
        remove_untracked_tree(root, change_root)
        raise
    if not _official_new_result(root, change, result):
        remove_untracked_tree(root, change_root)
        msg = "openspec_change_create_failed"
        raise ValueError(msg)
    commitment_path = f"{change_root}/commitment.toml"
    (root / commitment_path).write_text(
        _commitment_text(
            root=root,
            change=change,
            intent=intent,
            scope=scope,
            predecessor=load_lease_bound_commitment(root, lease=old_lease),
            selected_attestations=selected_attestations,
        ),
        encoding="utf-8",
    )
    overlay_paths = tuple(str(path) for path in overlay.get("paths", ()))
    stage_git_paths(root, (*overlay_paths, *created_paths))
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
        msg = "openspec_change_commit_failed"
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
            old_lease,
            tuple(str(item) for item in result["command"]),
            "started",
        ),
    )


def _finish(
    root: Path,
    request: _FinishRequest,
) -> dict[str, object]:
    branch, change, previous_head, head, old_lease, command, state = request
    carrier = f"openspec/changes/{change}/commitment.toml"
    current_lease = leases_by_branch(root).get(branch, {})
    target = exact_commitment_fields(root, head=head, carrier=carrier, change_id=change)
    current = LaneLease.from_payload(dict(current_lease["payload"]))
    successor = commitment_rebind_successor(current, binding=target)
    successor_record = project_lease(successor)
    commitment = load_commitment(root, carrier=carrier, change_id=change, tree_ref=head)
    repository = load_repository_commitment(root, tree_ref=head)
    _selected_root, attestations = read_attestation_set(root)
    prepared = tuple(
        item
        for item in attestations
        if item.predicate == "effect:openspec-change-start"
        and item.payload.body.get("freshness", {}).get("subject")
        == {"change": change, "previous_head": previous_head, "head": head}
    )
    if len(prepared) > 1:
        message = "openspec_change_start_attestation_collision"
        raise ValueError(message)
    attestation = prepared[0] if prepared else _attestation(
        root,
        change=change,
        command=command,
        previous_head=previous_head,
        head=head,
        old_lease=old_lease,
        new_lease=successor_record,
        issued_at=datetime.fromtimestamp(
            int(git_stdout(root, "show", "-s", "--format=%ct", head)), UTC
        ),
        commitment=commitment,
        repository_id=repository.id,
    )
    if not prepared:
        record_attestations(root, (attestation,))
    updated = rebind_lease_commitment(
        state_database(root),
        request=_lease_request(branch, current_lease, head),
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


def _empty_overlay() -> ChangeOverlay:
    return {"paths": (), "digest": "", "required_gaps": []}


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


def _commitment_text(
    *,
    root: Path,
    change: str,
    intent: str,
    scope: tuple[str, ...],
    predecessor: Commitment,
    selected_attestations: tuple[str, ...],
) -> str:
    text = tomli_w.dumps(
        _commitment(
            root=root,
            change=change,
            intent=intent,
            scope=scope,
            predecessor=predecessor,
            selected_attestations=selected_attestations,
        ).model_dump(mode="python")
    )
    return text.replace("\n    ", "\n  ")


def _commitment(
    *,
    root: Path,
    change: str,
    intent: str,
    scope: tuple[str, ...],
    predecessor: Commitment,
    selected_attestations: tuple[str, ...],
) -> Commitment:
    repository_id = load_repository_commitment(root).id
    bounded_scope = tuple(
        sorted(
            {f"openspec/changes/{change}/**", *scope},
            key=lambda value: json.dumps(
                value,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode(),
        )
    )
    return Commitment(
        schema_version=2,
        id=f"change:{change}",
        intent=intent.strip(),
        subjects=(repository_id,),
        scope=bounded_scope,
        invariants=(),
        acceptance=(),
        risks=(),
        authority_refs=(),
        predecessors=(predecessor.digest(),),
        selected_attestations=selected_attestations,
        dependencies=(),
        hypotheses=(),
        falsifiers=(),
        experiment_protocols=(),
    )


def _selection_observation(
    root: Path,
    change: str,
    identities: tuple[str, ...],
    *,
    expected_root: str | None = None,
) -> tuple[str, list[str]]:
    if not identities:
        return "", []
    try:
        selected_root, selected = read_attestation_set(root)
    except (OSError, TypeError, ValueError) as error:
        return "", [str(error)]
    if expected_root is not None and selected_root != expected_root:
        return selected_root, ["selected_attestation_set_changed"]
    members = {item.id: item for item in selected}
    gaps: list[str] = []
    owner = f"change:{change}"
    now = datetime.now(UTC)
    for identity in identities:
        attestation = members.get(identity)
        if attestation is None:
            gaps.append(f"selected_attestation_missing:{identity}")
            continue
        body = attestation.payload.body
        relations = {
            (relation.kind, relation.target_kind, relation.target_id)
            for relation in attestation.relations
        }
        disposed = {
            target_id
            for kind, target_kind, target_id in relations
            if kind == "relation:disposes" and target_kind == "semantic:attestation"
        }
        valid = (
            _selection_is_current(attestation, now)
            and attestation.predicate == "selection:input"
            and attestation.payload.kind == "selection:disposition"
            and body.get("disposition") == "semantic-owner"
            and body.get("owner") == owner
            and ("relation:selected-for", "semantic:commitment", owner) in relations
            and len(disposed) == 1
            and attestation.subject in disposed
            and disposed <= members.keys()
        )
        if not valid:
            gaps.append(f"selected_attestation_disposition_invalid:{identity}")
    return selected_root, gaps


def _require_selection_boundary(
    root: Path,
    *,
    change: str,
    identities: tuple[str, ...],
    expected_root: str,
) -> None:
    _selected_root, gaps = _selection_observation(
        root,
        change,
        identities,
        expected_root=expected_root,
    )
    if gaps:
        raise ValueError(gaps[0])


def _selection_is_current(attestation: Attestation, now: datetime) -> bool:
    return (
        attestation.verdict == "pass"
        and not attestation.payload.body.get("required_gaps")
        and (attestation.valid_from or attestation.issued_at) <= now
        and (attestation.valid_until is None or now <= attestation.valid_until)
    )


def _committed_request_mismatch(
    root: Path,
    *,
    change: str,
    previous_head: str,
    intent: str,
    scope: tuple[str, ...],
    selected_attestations: tuple[str, ...],
) -> bool:
    head = current_tracked_head(root)
    if (
        head == previous_head
        or run_git(root, "rev-parse", f"{head}^").stdout.strip() != previous_head
    ):
        return False
    try:
        current = load_commitment(
            root,
            carrier=f"openspec/changes/{change}/commitment.toml",
            change_id=change,
            tree_ref=head,
        )
    except ValueError:
        return False
    expected_scope = tuple(
        sorted(
            {f"openspec/changes/{change}/**", *scope},
            key=lambda value: json.dumps(
                value,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode(),
        )
    )
    expected_selection = tuple(sorted(set(selected_attestations)))
    return (
        current.intent != intent.strip()
        or current.scope != expected_scope
        or current.selected_attestations != expected_selection
    )


def _official_new_result(root: Path, change: str, result: Mapping[str, Any]) -> bool:
    payload = result.get("json")
    created = payload.get("change") if isinstance(payload, Mapping) else None
    if not isinstance(created, Mapping):
        return False
    expected = (root / "openspec" / "changes" / change).resolve()
    try:
        actual = Path(str(created.get("path") or "")).resolve()
    except OSError:
        return False
    return (
        result.get("exit_code") == 0
        and not result.get("parse_error")
        and created.get("id") == change
        and actual == expected
        and (expected / ".openspec.yaml").is_file()
    )


def _attestation(
    root: Path,
    *,
    change: str,
    command: tuple[str, ...],
    previous_head: str,
    head: str,
    old_lease: Mapping[str, object],
    new_lease: Mapping[str, object],
    issued_at: datetime,
    commitment: Commitment,
    repository_id: str,
) -> Attestation:
    return issue_native_effect(
        root,
        effect=NativeEffect(
            predicate="effect:openspec-change-start",
            operation="openspec.change.start",
            command=command,
            subject={"change": change, "previous_head": previous_head, "head": head},
            before={"head": previous_head, "lease": lease_generation(dict(old_lease))},
            after={"head": head, "lease": lease_generation(dict(new_lease))},
        ),
        state="prepared",
        commitment_digest=commitment.digest(),
        repository_id=repository_id,
        issued_at=issued_at,
    )


def _recognized(
    root: Path,
    branch: str,
    change: str,
    previous_head: str,
    lease: dict[str, object],
) -> dict[str, object] | None:
    carrier = f"openspec/changes/{change}/commitment.toml"
    head = current_tracked_head(root)
    if (
        lease.get("lease_state") != "valid"
        or lease.get("holder_ref") != os.environ.get("ETHOS_ACTOR", "").strip()
        or lease.get("expected_head") != head
        or lease.get("base_commitment_path") != carrier
        or run_git(root, "rev-parse", f"{head}^").stdout.strip() != previous_head
    ):
        return None
    commitment = load_commitment(root, carrier=carrier, change_id=change, tree_ref=head)
    repository = load_repository_commitment(root, tree_ref=head)
    _selected_root, attestations = read_attestation_set(root)
    validated = tuple(
        attestation
        for attestation in attestations
        if start_effect_authority(
            root,
            attestation,
            head,
            repository.id,
            commitment,
            lease,
        )
    )
    if len(validated) != 1:
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
        attestation=validated[0].model_dump(mode="json"),
    )

def _recoverable(
    root: Path,
    change: str,
    previous_head: str,
    lease: dict[str, object],
) -> tuple[str, ...] | None:
    head = current_tracked_head(root)
    carrier = f"openspec/changes/{change}/commitment.toml"
    actor = os.environ.get("ETHOS_ACTOR", "").strip()
    if (
        head == previous_head
        or lease.get("lease_state") != "valid"
        or lease.get("holder_ref") != actor
        or lease.get("expected_head") != head
        or not str(lease.get("base_commitment_path") or "").startswith(_ARCHIVE_PREFIX)
        or run_git(root, "rev-parse", f"{head}^").stdout.strip() != previous_head
        or git_stdout(root, "status", "--short")
    ):
        return None
    try:
        exact_commitment_fields(root, head=head, carrier=carrier, change_id=change)
    except ValueError:
        return None
    command = openspec_cli.openspec_base_command()
    return (*command, "new", "change", change, "--json") if command else None
