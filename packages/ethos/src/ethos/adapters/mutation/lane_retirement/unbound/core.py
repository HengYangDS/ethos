from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
import tempfile
import tomllib
from pathlib import Path
from typing import cast

import ethos.adapters.mutation.lane_retirement.shared.core as lane_retirement_shared
from ethos.adapters.mutation.lane_lifecycle.core import repo_root
from ethos.adapters.mutation.lane_lifecycle.core import run_git
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.status.core import workspace_status
from ethos_core.contracts.branch.roles import ROLE_ACCEPTED_ROOT
from ethos_core.contracts.branch.roles import ROLE_WORK_LANE
from ethos_core.contracts.branch.roles import load_branch_role_policy

_ATTEMPT_KIND = "exceptional_unbound_retirement_attempt"
_RECEIPT_KIND = "exceptional_unbound_retirement_receipt"
_EVENT = "lane_retire/unbound_exceptional"
_MAX_STABLE_ERROR_LENGTH = 240


def retire_unbound_work_lane_ref(  # noqa: PLR0911, PLR0913, RUF100 - exact retirement protocol shape
    *,
    root: Path,
    branch: str,
    expect_head: str | None = None,
    reason: str = "",
    chronicle_ref: str = "",
    apply: bool = False,
    authorized: bool = False,
    break_glass: bool = False,
    confirm_irreversible: bool = False,
) -> dict[str, object]:
    """Retire one accepted-policy-bound unbound Work Lane ref.

    This intentionally narrow route never turns an absent checkout into deletion
    authority. It admits exactly one accepted-ancestor ``work/*`` ref only when
    the live repository observation and a byte-identical accepted Chronicle name
    the same target. The sole Git effect is a compare-and-delete ref update.
    """
    repo = repo_root(root)
    branch = branch.strip()
    expected = (expect_head or "").strip()
    reason = reason.strip()
    chronicle_ref = chronicle_ref.strip()
    before = _observe(repo, branch=branch, chronicle_ref=chronicle_ref)
    gaps = _admission_gaps(
        repo,
        branch=branch,
        expect_head=expected,
        reason=reason,
        apply=apply,
        authorized=authorized,
        break_glass=break_glass,
        confirm_irreversible=confirm_irreversible,
        observation=before,
    )
    report = _report(
        branch=branch,
        expect_head=expected,
        reason=reason,
        chronicle_ref=chronicle_ref,
        apply=apply,
        authorized=authorized,
        break_glass=break_glass,
        confirm_irreversible=confirm_irreversible,
        observation=before,
        gaps=gaps,
    )
    if gaps or not apply:
        return report

    control_root, control_gap = _accepted_control_root(
        cast("dict[str, object]", before["status"]),
        accepted_head=str(before["accepted_head"]),
    )
    if control_root is None:
        return _blocked(report, [control_gap])
    records_root = control_root.parent / f"{control_root.name}-records"
    operation_id = _operation_id(
        branch=branch,
        expect_head=expected,
        accepted_head=str(before["accepted_head"]),
        protected_refs=cast("dict[str, str]", before["protected_refs"]),
        claim_id=str(before["claim_id"]),
        chronicle=cast("dict[str, object]", before["chronicle"]),
        reason=reason,
        observation_sha256=str(before["observation_sha256"]),
    )
    attempt = _attempt_payload(
        operation_id=operation_id,
        branch=branch,
        expect_head=expected,
        reason=reason,
        observation=before,
    )
    try:
        attempt_path = _write_record(
            _attempt_path(records_root, operation_id), attempt, kind=_ATTEMPT_KIND
        )
    except (OSError, TypeError, ValueError) as exc:
        return _blocked(report, [_stable_gap(exc)])

    pre_effect = _observe(repo, branch=branch, chronicle_ref=chronicle_ref)
    pre_effect_gaps = _admission_gaps(
        repo,
        branch=branch,
        expect_head=expected,
        reason=reason,
        apply=True,
        authorized=authorized,
        break_glass=break_glass,
        confirm_irreversible=confirm_irreversible,
        observation=pre_effect,
    )
    if _operation_bindings(before) != _operation_bindings(pre_effect):
        pre_effect_gaps.append("unbound_retire_pre_effect_observation_stale")
    if pre_effect_gaps:
        return _blocked(
            {
                **report,
                "attempt_path": attempt_path,
                "operation_id": operation_id,
                "observation": _public_observation(pre_effect),
            },
            pre_effect_gaps,
        )

    deleted = run_git(
        repo,
        "update-ref",
        "-d",
        f"refs/heads/{branch}",
        expected,
        check=False,
    )
    after = _observe(repo, branch=branch, chronicle_ref=chronicle_ref)
    post_gaps = _post_effect_gaps(before=before, after=after, deleted=deleted)
    if post_gaps:
        return _blocked(
            {
                **report,
                "attempt_path": attempt_path,
                "operation_id": operation_id,
                "effect": _effect_summary(deleted),
                "observation": _public_observation(after),
            },
            post_gaps,
        )
    receipt = _receipt_payload(
        operation_id=operation_id,
        branch=branch,
        expect_head=expected,
        reason=reason,
        before=before,
        after=after,
        effect=_effect_summary(deleted),
    )
    try:
        receipt_path = _write_record(
            _receipt_path(records_root, operation_id), receipt, kind=_RECEIPT_KIND
        )
    except (OSError, TypeError, ValueError) as exc:
        return _blocked(
            {
                **report,
                "attempt_path": attempt_path,
                "operation_id": operation_id,
                "effect": _effect_summary(deleted),
                "observation": _public_observation(after),
            },
            [_stable_gap(exc)],
        )
    return {
        **report,
        "ok": True,
        "state": "retired_unbound_exceptional",
        "operation_id": operation_id,
        "attempt_path": attempt_path,
        "receipt_path": receipt_path,
        "receipt": receipt,
        "effect": _effect_summary(deleted),
        "observation": _public_observation(after),
        "required_gaps": [],
        "mutation": _mutation(
            branch=branch,
            expect_head=expected,
            reason=reason,
            chronicle_ref=chronicle_ref,
            apply=True,
            confirmed=True,
            observation=after,
            break_glass=break_glass,
            confirm_irreversible=confirm_irreversible,
            gaps=[],
        ),
    }


def _observe(repo: Path, *, branch: str, chronicle_ref: str) -> dict[str, object]:
    status = workspace_status(repo)
    policy = load_branch_role_policy(repo)
    current = _unbound_work_lane_ref(status, branch)
    binding = _branch_binding(status, branch)
    worktrees = status.get("worktrees")
    typed_worktrees = cast("list[dict[str, str]]", worktrees) if isinstance(worktrees, list) else []
    leases = leases_by_branch(typed_worktrees, current_path=repo)
    active_lease = leases.get(branch, {})
    protected_refs = {
        ref: _ref_head(repo, ref)
        for ref in _protected_refs(
            policy.release_branch, policy.accepted_branch, policy.candidate_branch
        )
    }
    accepted_head = _ref_head(repo, policy.accepted_branch)
    head = _ref_head(repo, branch)
    payload: dict[str, object] = {
        "branch": branch,
        "head": head,
        "accepted_head": accepted_head,
        "protected_refs": protected_refs,
        "status_unbound": current is not None,
        "worktree_binding": str((binding or {}).get("worktree_binding") or ""),
        "relation_to_accepted": str((current or {}).get("relation_to_accepted") or ""),
        "claim_id": str((current or {}).get("claim_id") or ""),
        "claim_binding": str((current or {}).get("claim_binding") or ""),
        "active_lease": _public_lease(active_lease),
        "active_lease_present": bool(active_lease),
        "chronicle": _chronicle_observation(
            repo,
            accepted_branch=policy.accepted_branch,
            chronicle_ref=chronicle_ref,
        ),
        "status": status,
    }
    payload["observation_sha256"] = _sha256(_public_observation(payload))
    return payload


def _protected_refs(release: str, accepted: str, candidate: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys((release, accepted, candidate)))


def _chronicle_observation(
    repo: Path,
    *,
    accepted_branch: str,
    chronicle_ref: str,
) -> dict[str, object]:
    path = _chronicle_path(repo, chronicle_ref)
    observation: dict[str, object] = {
        "ref": chronicle_ref,
        "path_valid": path is not None,
        "local_present": False,
        "accepted_present": False,
        "byte_identical_to_accepted": False,
        "sha256": "",
        "accepted_sha256": "",
        "event": "",
        "target_branch": "",
        "target_head": "",
        "target_claim": "",
        "claim_local_present": False,
        "claim_accepted_present": False,
        "claim_byte_identical_to_accepted": False,
        "claim_sha256": "",
        "claim_accepted_sha256": "",
        "claim_id_matches_target": False,
        "claim_active": False,
    }
    if path is None:
        return observation
    try:
        mode = os.lstat(path).st_mode
        if not stat.S_ISREG(mode):
            return observation
        local = path.read_bytes()
    except OSError:
        return observation
    observation["local_present"] = True
    observation["sha256"] = hashlib.sha256(local).hexdigest()
    observation.update(_chronicle_fields(local))
    accepted = _git_show_bytes(repo, f"{accepted_branch}:{chronicle_ref}")
    if accepted is None:
        return observation
    observation["accepted_present"] = True
    observation["accepted_sha256"] = hashlib.sha256(accepted).hexdigest()
    observation["byte_identical_to_accepted"] = accepted == local
    observation.update(
        _claim_observation(
            repo,
            accepted_branch=accepted_branch,
            claim_id=str(observation["target_claim"]),
        )
    )
    return observation


def _chronicle_path(repo: Path, chronicle_ref: str) -> Path | None:
    if not chronicle_ref:
        return None
    candidate = Path(chronicle_ref)
    if (
        candidate.is_absolute()
        or any(part in {"", ".", ".."} for part in candidate.parts)
        or not chronicle_ref.startswith("evidence/chronicle/")
    ):
        return None
    root = repo.resolve()
    path = repo / candidate
    try:
        resolved = path.resolve()
    except OSError:
        return None
    return path if resolved.is_relative_to(root) else None


def _chronicle_fields(payload: bytes) -> dict[str, str]:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        return {}
    fields: dict[str, str] = {}
    for line in text.splitlines():
        key, separator, value = line.partition(":")
        if separator and key in {
            "event",
            "target_branch",
            "target_head",
            "target_claim",
        }:
            fields[key] = value.strip()
    return fields


def _claim_observation(
    repo: Path,
    *,
    accepted_branch: str,
    claim_id: str,
) -> dict[str, object]:
    relative = _claim_ref(claim_id)
    observation: dict[str, object] = {
        "claim_local_present": False,
        "claim_accepted_present": False,
        "claim_byte_identical_to_accepted": False,
        "claim_sha256": "",
        "claim_accepted_sha256": "",
        "claim_id_matches_target": False,
        "claim_active": False,
    }
    if relative is None:
        return observation
    path = repo / relative
    try:
        mode = os.lstat(path).st_mode
        if not stat.S_ISREG(mode):
            return observation
        local = path.read_bytes()
        payload = tomllib.loads(local.decode("utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return observation
    claim = payload.get("claim") if isinstance(payload, dict) else {}
    observation["claim_local_present"] = True
    observation["claim_sha256"] = hashlib.sha256(local).hexdigest()
    observation["claim_id_matches_target"] = (
        isinstance(claim, dict) and str(claim.get("id") or "") == claim_id
    )
    observation["claim_active"] = isinstance(claim, dict) and claim.get("state") == "active"
    accepted = _git_show_bytes(repo, f"{accepted_branch}:{relative}")
    if accepted is None:
        return observation
    observation["claim_accepted_present"] = True
    observation["claim_accepted_sha256"] = hashlib.sha256(accepted).hexdigest()
    observation["claim_byte_identical_to_accepted"] = accepted == local
    return observation


def _claim_ref(claim_id: str) -> str | None:
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")
    if not claim_id or any(character not in allowed for character in claim_id):
        return None
    return f"evidence/claims/{claim_id}.toml"


def _git_show_bytes(repo: Path, ref: str) -> bytes | None:
    completed = subprocess.run(["git", "show", ref], cwd=repo, check=False, capture_output=True)
    return completed.stdout if completed.returncode == 0 else None


def _admission_gaps(  # noqa: PLR0913, RUF100 - exact request envelope preserves bound state dimensions
    repo: Path,
    *,
    branch: str,
    expect_head: str,
    reason: str,
    apply: bool,
    authorized: bool,
    break_glass: bool,
    confirm_irreversible: bool,
    observation: dict[str, object],
) -> list[str]:
    gaps: list[str] = []
    branch_gap = _branch_admission_gap(repo, branch=branch, observation=observation)
    if branch_gap:
        gaps.append(branch_gap)
    if not reason:
        gaps.append("retire_reason_required")
    if not expect_head:
        gaps.append("expect_head_required")
    elif expect_head != observation["head"]:
        gaps.append("expect_head_mismatch")
    if not all(cast("dict[str, str]", observation["protected_refs"]).values()):
        gaps.append("unbound_retire_protected_ref_unavailable")
    gaps.extend(
        _chronicle_gaps(
            cast("dict[str, object]", observation["chronicle"]),
            branch=branch,
            head=str(observation["head"]),
        )
    )
    if apply and not authorized:
        gaps.append("authorization_required")
    if apply and not break_glass:
        gaps.append("unbound_retire_requires_break_glass")
    if apply and not confirm_irreversible:
        gaps.append("irreversible_confirmation_required")
    return sorted(set(gaps))


def _branch_admission_gap(
    repo: Path,
    *,
    branch: str,
    observation: dict[str, object],
) -> str:
    policy = load_branch_role_policy(repo)
    checks = (
        (not branch, "unbound_retire_branch_required"),
        (
            policy.role_for_branch(branch) != ROLE_WORK_LANE,
            "unbound_retire_not_work_lane",
        ),
        (not str(observation["head"]), "unbound_retire_branch_not_found"),
        (not bool(observation["status_unbound"]), "unbound_retire_ref_not_unbound"),
        (
            observation["worktree_binding"] != "unbound",
            "unbound_retire_worktree_binding_drift",
        ),
        (
            observation["relation_to_accepted"] != "ancestor_of_accepted",
            "unbound_retire_not_accepted_ancestor",
        ),
        (bool(observation["active_lease_present"]), "unbound_retire_active_lease"),
    )
    return next((gap for failed, gap in checks if failed), "")


def _chronicle_gaps(
    chronicle: dict[str, object],
    *,
    branch: str,
    head: str,
) -> list[str]:
    return (
        _chronicle_reference_gaps(chronicle)
        or _chronicle_target_gaps(chronicle, branch=branch, head=head)
        or _chronicle_claim_gaps(chronicle)
    )


def _chronicle_reference_gaps(chronicle: dict[str, object]) -> list[str]:
    checks = (
        (not chronicle["ref"], "unbound_retire_chronicle_ref_required"),
        (not chronicle["path_valid"], "unbound_retire_chronicle_ref_invalid"),
        (not chronicle["local_present"], "unbound_retire_chronicle_missing"),
        (not chronicle["accepted_present"], "unbound_retire_chronicle_not_accepted"),
        (
            not chronicle["byte_identical_to_accepted"],
            "unbound_retire_chronicle_content_drift",
        ),
    )
    return [gap for failed, gap in checks if failed][:1]


def _chronicle_target_gaps(chronicle: dict[str, object], *, branch: str, head: str) -> list[str]:
    if chronicle["event"] != _EVENT:
        return ["unbound_retire_chronicle_event_missing"]
    if chronicle["target_branch"] != branch or chronicle["target_head"] != head:
        return ["unbound_retire_chronicle_target_mismatch"]
    return []


def _chronicle_claim_gaps(chronicle: dict[str, object]) -> list[str]:
    checks = (
        (not chronicle["target_claim"], "unbound_retire_chronicle_claim_missing"),
        (
            not chronicle["claim_local_present"] or not chronicle["claim_accepted_present"],
            "unbound_retire_claim_missing",
        ),
        (
            not chronicle["claim_byte_identical_to_accepted"],
            "unbound_retire_claim_content_drift",
        ),
        (
            not chronicle["claim_id_matches_target"] or not chronicle["claim_active"],
            "unbound_retire_claim_target_mismatch",
        ),
    )
    return [gap for failed, gap in checks if failed][:1]


def _accepted_control_root(
    status: dict[str, object],
    *,
    accepted_head: str,
) -> tuple[Path | None, str]:
    worktrees = status.get("worktrees")
    if not isinstance(worktrees, list):
        return None, "unbound_retire_accepted_control_root_unavailable"
    for worktree in worktrees:
        if not isinstance(worktree, dict) or worktree.get("role") != ROLE_ACCEPTED_ROOT:
            continue
        raw_path = str(worktree.get("path") or "")
        if not raw_path:
            continue
        root = Path(raw_path).resolve()
        if not root.is_dir():
            return None, "unbound_retire_accepted_control_root_unavailable"
        observed = _ref_head(root, "HEAD")
        if not observed or observed != accepted_head:
            return None, "unbound_retire_accepted_control_root_stale"
        return root, ""
    return None, "unbound_retire_accepted_control_root_unavailable"


def _post_effect_gaps(
    *,
    before: dict[str, object],
    after: dict[str, object],
    deleted: object,
) -> list[str]:
    gaps: list[str] = []
    if int(getattr(deleted, "returncode", 1)) != 0:
        gaps.append("unbound_retire_ref_delete_failed")
    if before["protected_refs"] != after["protected_refs"]:
        gaps.append("unbound_retire_protected_refs_changed")
    if _chronicle_binding(before) != _chronicle_binding(after):
        gaps.append("unbound_retire_chronicle_changed")
    if after["head"]:
        gaps.append("unbound_retire_ref_remove_not_observed")
    if after["status_unbound"] or after["worktree_binding"] == "unbound":
        gaps.append("unbound_retire_status_postcondition_not_observed")
    if after["active_lease_present"]:
        gaps.append("unbound_retire_active_lease")
    return sorted(set(gaps))


def _report(  # noqa: PLR0913, RUF100 - exact request envelope preserves bound state dimensions
    *,
    branch: str,
    expect_head: str,
    reason: str,
    chronicle_ref: str,
    apply: bool,
    authorized: bool,
    break_glass: bool,
    confirm_irreversible: bool,
    observation: dict[str, object],
    gaps: list[str],
) -> dict[str, object]:
    return {
        "ok": not gaps,
        "state": "ready_to_retire_unbound_exceptional" if not gaps else "blocked",
        "branch": branch,
        "head": str(observation["head"]),
        "accepted_head": str(observation["accepted_head"]),
        "relation_to_accepted": str(observation["relation_to_accepted"]),
        "claim_id": str(observation["claim_id"]),
        "claim_binding": str(observation["claim_binding"]),
        "reason": reason,
        "chronicle_ref": chronicle_ref,
        "observation": _public_observation(observation),
        "mutation": _mutation(
            branch=branch,
            expect_head=expect_head,
            reason=reason,
            chronicle_ref=chronicle_ref,
            apply=apply,
            confirmed=authorized and break_glass and confirm_irreversible,
            observation=observation,
            break_glass=break_glass,
            confirm_irreversible=confirm_irreversible,
            gaps=gaps,
        ),
        "required_gaps": sorted(set(gaps)),
    }


def _mutation(  # noqa: PLR0913, RUF100 - exact request envelope preserves bound state dimensions
    *,
    branch: str,
    expect_head: str,
    reason: str,
    chronicle_ref: str,
    apply: bool,
    confirmed: bool,
    observation: dict[str, object],
    break_glass: bool,
    confirm_irreversible: bool,
    gaps: list[str],
) -> dict[str, object]:
    chronicle = cast("dict[str, object]", observation["chronicle"])
    return lane_retirement_shared.retire_mutation_envelope(
        command="lane-retire-unbound",
        action="lane.retire.unbound.exceptional",
        branch=branch,
        expect_head=expect_head,
        apply=apply,
        confirmed=confirmed,
        required_gaps=gaps,
        extra_state={
            "reason": reason,
            "accepted_head": str(observation["accepted_head"]),
            "claim_id": str(observation["claim_id"]),
            "claim_binding": str(observation["claim_binding"]),
            "chronicle_ref": chronicle_ref,
            "chronicle_sha256": str(chronicle["sha256"]),
            "chronicle_claim_id": str(chronicle["target_claim"]),
            "chronicle_claim_sha256": str(chronicle["claim_sha256"]),
            "break_glass": break_glass,
            "confirm_irreversible": confirm_irreversible,
            "observation_sha256": str(observation["observation_sha256"]),
        },
    )


def _operation_id(  # noqa: PLR0913, RUF100 - identity intentionally binds destructive facts
    *,
    branch: str,
    expect_head: str,
    accepted_head: str,
    protected_refs: dict[str, str],
    claim_id: str,
    chronicle: dict[str, object],
    reason: str,
    observation_sha256: str,
) -> str:
    digest = _sha256(
        {
            "branch": branch,
            "expect_head": expect_head,
            "accepted_head": accepted_head,
            "protected_refs": protected_refs,
            "claim_id": claim_id,
            "chronicle": _chronicle_binding(chronicle),
            "reason": reason,
            "before_observation_sha256": observation_sha256,
        }
    )
    return f"exceptional-unbound-retirement:{digest}"


def _attempt_payload(
    *,
    operation_id: str,
    branch: str,
    expect_head: str,
    reason: str,
    observation: dict[str, object],
) -> dict[str, object]:
    chronicle = cast("dict[str, object]", observation["chronicle"])
    return {
        "schema_version": 1,
        "kind": _ATTEMPT_KIND,
        "operation_id": operation_id,
        "branch": branch,
        "expected_head": expect_head,
        "accepted_head": observation["accepted_head"],
        "protected_refs": observation["protected_refs"],
        "claim_id": observation["claim_id"],
        "chronicle_ref": chronicle["ref"],
        "chronicle_sha256": chronicle["sha256"],
        "chronicle_claim_id": chronicle["target_claim"],
        "chronicle_claim_sha256": chronicle["claim_sha256"],
        "reason": reason,
        "before_observation_sha256": observation["observation_sha256"],
        "effect": "git_update_ref_compare_and_delete",
        "mints_authority": False,
        "recheck_required": True,
    }


def _receipt_payload(  # noqa: PLR0913, RUF100 - exact retirement protocol shape
    *,
    operation_id: str,
    branch: str,
    expect_head: str,
    reason: str,
    before: dict[str, object],
    after: dict[str, object],
    effect: dict[str, object],
) -> dict[str, object]:
    chronicle = cast("dict[str, object]", before["chronicle"])
    return {
        "schema_version": 1,
        "kind": _RECEIPT_KIND,
        "operation_id": operation_id,
        "branch": branch,
        "expected_head": expect_head,
        "accepted_head": before["accepted_head"],
        "protected_refs_before": before["protected_refs"],
        "protected_refs_after": after["protected_refs"],
        "claim_id": before["claim_id"],
        "chronicle_ref": chronicle["ref"],
        "chronicle_sha256": chronicle["sha256"],
        "chronicle_claim_id": chronicle["target_claim"],
        "chronicle_claim_sha256": chronicle["claim_sha256"],
        "reason": reason,
        "before_observation_sha256": before["observation_sha256"],
        "after_observation_sha256": after["observation_sha256"],
        "effect": effect,
        "postconditions": {
            "ref_absent": not bool(after["head"]),
            "unbound_absent": not bool(after["status_unbound"]),
            "active_lease_absent": not bool(after["active_lease_present"]),
            "protected_refs_unchanged": before["protected_refs"] == after["protected_refs"],
            "chronicle_unchanged": _chronicle_binding(before) == _chronicle_binding(after),
        },
        "mints_authority": False,
        "recheck_required": True,
    }


def _attempt_path(records_root: Path, operation_id: str) -> Path:
    return (
        records_root
        / "recovery"
        / "unbound-retirement"
        / "attempts"
        / f"{_suffix(operation_id)}.json"
    )


def _receipt_path(records_root: Path, operation_id: str) -> Path:
    return (
        records_root
        / "recovery"
        / "unbound-retirement"
        / "receipts"
        / f"{_suffix(operation_id)}.json"
    )


def _suffix(operation_id: str) -> str:
    return operation_id.rpartition(":")[2]


def _write_record(path: Path, payload: dict[str, object], *, kind: str) -> str:
    """Publish one deterministic local record without clobbering another writer."""
    _validate_record(payload, kind=kind)
    existing = _read_record(path, kind=kind)
    if existing:
        if existing != payload:
            msg = "unbound_retire_record_collision"
            raise ValueError(msg)
        return path.as_posix()
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError as exc:
            existing = _read_record(path, kind=kind)
            if existing != payload:
                msg = "unbound_retire_record_collision"
                raise ValueError(msg) from exc
    finally:
        temporary.unlink(missing_ok=True)
    descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return path.as_posix()


def _read_record(path: Path, *, kind: str) -> dict[str, object]:
    try:
        mode = os.lstat(path).st_mode
    except FileNotFoundError:
        return {}
    if not stat.S_ISREG(mode):
        msg = "unbound_retire_record_unsafe"
        raise ValueError(msg)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        msg = "unbound_retire_record_invalid"
        raise ValueError(msg) from exc
    if not isinstance(payload, dict):
        msg = "unbound_retire_record_invalid"
        raise TypeError(msg)
    _validate_record(payload, kind=kind)
    return payload


def _validate_record(payload: dict[str, object], *, kind: str) -> None:
    common = {
        "schema_version",
        "kind",
        "operation_id",
        "branch",
        "expected_head",
        "accepted_head",
        "claim_id",
        "chronicle_ref",
        "chronicle_sha256",
        "chronicle_claim_id",
        "chronicle_claim_sha256",
        "reason",
        "before_observation_sha256",
        "effect",
        "mints_authority",
        "recheck_required",
    }
    required = (
        common | {"protected_refs"}
        if kind == _ATTEMPT_KIND
        else common
        | {
            "protected_refs_before",
            "protected_refs_after",
            "after_observation_sha256",
            "postconditions",
        }
    )
    if (
        set(payload) != required
        or payload.get("kind") != kind
        or payload.get("schema_version") != 1
    ):
        msg = "unbound_retire_record_invalid"
        raise ValueError(msg)
    if not str(payload.get("operation_id") or "").startswith("exceptional-unbound-retirement:"):
        msg = "unbound_retire_record_invalid"
        raise ValueError(msg)
    if not str(payload.get("branch") or "").startswith("work/"):
        msg = "unbound_retire_record_invalid"
        raise ValueError(msg)
    if not _sha256_text_fields(
        payload,
        "expected_head",
        "accepted_head",
        "chronicle_sha256",
        "chronicle_claim_sha256",
    ):
        msg = "unbound_retire_record_invalid"
        raise ValueError(msg)
    if payload.get("mints_authority") is not False or payload.get("recheck_required") is not True:
        msg = "unbound_retire_record_invalid"
        raise ValueError(msg)
    protected_key = "protected_refs" if kind == _ATTEMPT_KIND else "protected_refs_before"
    protected = payload.get(protected_key)
    if not isinstance(protected, dict) or not protected or not all(protected.values()):
        msg = "unbound_retire_record_invalid"
        raise ValueError(msg)
    if kind == _RECEIPT_KIND:
        after = payload.get("protected_refs_after")
        postconditions = payload.get("postconditions")
        expected_postconditions = {
            "ref_absent",
            "unbound_absent",
            "active_lease_absent",
            "protected_refs_unchanged",
            "chronicle_unchanged",
        }
        if (
            after != protected
            or not isinstance(postconditions, dict)
            or set(postconditions) != expected_postconditions
            or not all(value is True for value in postconditions.values())
        ):
            msg = "unbound_retire_record_invalid"
            raise ValueError(msg)


def _sha256_text_fields(payload: dict[str, object], *keys: str) -> bool:
    return all(
        isinstance(payload.get(key), str) and len(str(payload[key])) in {40, 64} for key in keys
    )


def _public_observation(observation: dict[str, object]) -> dict[str, object]:
    return {
        key: observation[key]
        for key in (
            "branch",
            "head",
            "accepted_head",
            "protected_refs",
            "status_unbound",
            "worktree_binding",
            "relation_to_accepted",
            "claim_id",
            "claim_binding",
            "active_lease",
            "active_lease_present",
            "chronicle",
            "observation_sha256",
        )
        if key in observation
    }


def _operation_bindings(observation: dict[str, object]) -> dict[str, object]:
    return {
        key: observation[key]
        for key in (
            "head",
            "accepted_head",
            "protected_refs",
            "status_unbound",
            "worktree_binding",
            "relation_to_accepted",
            "claim_id",
            "claim_binding",
            "active_lease_present",
        )
    } | {"chronicle": _chronicle_binding(observation)}


def _chronicle_binding(source: dict[str, object]) -> dict[str, object]:
    chronicle = source.get("chronicle") if "chronicle" in source else source
    if not isinstance(chronicle, dict):
        return {}
    return {
        key: chronicle.get(key)
        for key in (
            "ref",
            "accepted_present",
            "byte_identical_to_accepted",
            "sha256",
            "accepted_sha256",
            "event",
            "target_branch",
            "target_head",
            "target_claim",
            "claim_accepted_present",
            "claim_byte_identical_to_accepted",
            "claim_sha256",
            "claim_accepted_sha256",
            "claim_id_matches_target",
            "claim_active",
        )
    }


def _effect_summary(completed: object) -> dict[str, object]:
    return {
        "command": "git update-ref -d",
        "returncode": int(getattr(completed, "returncode", 1)),
        "stderr_sha256": hashlib.sha256(str(getattr(completed, "stderr", "")).encode()).hexdigest(),
    }


def _public_lease(lease: dict[str, object]) -> dict[str, object]:
    return {
        key: str(lease.get(key) or "")
        for key in ("id", "holder_ref", "lease_id", "expected_head", "claim_id")
    }


def _ref_head(repo: Path, ref: str) -> str:
    completed = run_git(repo, "rev-parse", "--verify", ref, check=False)
    return completed.stdout.strip() if completed.returncode == 0 else ""


def _unbound_work_lane_ref(status: dict[str, object], branch: str) -> dict[str, object] | None:
    coordination = status.get("coordination")
    refs = coordination.get("unbound_work_lane_refs") if isinstance(coordination, dict) else None
    if not isinstance(refs, list):
        return None
    for ref in refs:
        if isinstance(ref, dict) and ref.get("branch") == branch:
            return cast("dict[str, object]", ref)
    return None


def _branch_binding(status: dict[str, object], branch: str) -> dict[str, object] | None:
    bindings = status.get("branch_bindings")
    if not isinstance(bindings, list):
        return None
    for binding in bindings:
        if isinstance(binding, dict) and binding.get("branch") == branch:
            return cast("dict[str, object]", binding)
    return None


def _blocked(report: dict[str, object], gaps: list[str]) -> dict[str, object]:
    all_gaps = sorted({*cast("list[str]", report.get("required_gaps", [])), *gaps})
    return {**report, "ok": False, "state": "blocked", "required_gaps": all_gaps}


def _sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _stable_gap(exc: BaseException) -> str:
    message = str(exc).strip()
    return (
        message
        if message and "\n" not in message and len(message) <= _MAX_STABLE_ERROR_LENGTH
        else "unbound_retire_effect_failed"
    )
