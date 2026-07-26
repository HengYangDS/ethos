# ruff: noqa: E501 - source-budget closeout preserves the exact AST in a compact representation.
# fmt: off
"""Atomic accepted-root closeout with an optional fast-forward release mirror."""

from __future__ import annotations

import ctypes
import errno
import hashlib
import json
import os
import re
import stat
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

import ethos.adapters.mutation.remediation.core as remediation
from ethos.adapters.admission.closeout_intent.core import CloseoutTransition
from ethos.adapters.admission.closeout_intent.core import clear_closeout_intent
from ethos.adapters.admission.closeout_intent.core import sweep_stale_closeout_intents
from ethos.adapters.admission.closeout_intent.core import write_closeout_intent
from ethos.adapters.mutation.lane_lifecycle.core import is_ancestor
from ethos.adapters.mutation.lane_lifecycle.core import run_git
from ethos.adapters.mutation.proof import carry_executed_proof_record
from ethos.adapters.mutation.proof import discard_executed_proof
from ethos.adapters.mutation.proof import executed_proof_record
from ethos.repository.policy.gates import gate_policy_digest
from ethos_core.contracts.branch.roles import RELEASE_MIRROR_ACCEPTED_FF
from ethos_core.contracts.branch.roles import BranchRolePolicy

if TYPE_CHECKING:
    import subprocess
    from collections.abc import Callable


@dataclass(frozen=True, slots=True)
class CloseoutDependencies:
    """Injected closeout collaborators; production uses the canonical adapters."""

    run_git: Callable[..., subprocess.CompletedProcess[str]] = run_git
    is_ancestor: Callable[..., bool] = is_ancestor
    carry_proof: Callable[..., object] = carry_executed_proof_record
    discard_proof: Callable[..., object] = discard_executed_proof


_DEFAULT_DEPENDENCIES = CloseoutDependencies()
_HEAD = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")


@dataclass(frozen=True, slots=True)
class CloseoutRequest:
    """Immutable promotion inputs shared by validation and execution."""

    root: Path
    policy: BranchRolePolicy
    current_head: str
    candidate_head: str
    candidate_path: Path
    worktrees: list[dict[str, object]]


@dataclass(frozen=True, slots=True)
class CloseoutWorktreeRecoveryRequest:
    """Exact inputs for one interrupted accepted-worktree sync recovery."""

    root: Path
    policy: BranchRolePolicy
    current_head: str
    candidate_head: str
    candidate_path: Path
    failure_receipt: Path | None
    expected_failure_receipt_sha256: str
    expected_index_lock_sha256: str
    lock_quarantine: Path | None


def promote_candidate_to_accepted(request: CloseoutRequest, *, dependencies: CloseoutDependencies = _DEFAULT_DEPENDENCIES) -> dict[str, object]:
    """Promote candidate; when enabled, atomically fast-forward release too."""
    preflight = _promotion_preflight(request, dependencies)
    if isinstance(preflight, dict):
        return preflight
    return _execute_promotion(request, preflight, dependencies)


def _promotion_preflight(request: CloseoutRequest, dependencies: CloseoutDependencies) -> tuple[CloseoutTransition, CloseoutTransition | None, str] | dict[str, object]:
    if not dependencies.is_ancestor(request.root, request.current_head, request.candidate_head):
        return _blocked(request.policy, request.current_head, ["candidate_diverged_from_accepted"], candidate_head=request.candidate_head)
    mirror = request.policy.release_mirror == RELEASE_MIRROR_ACCEPTED_FF
    release_old = dependencies.run_git(request.root, "rev-parse", request.policy.release_branch, check=False).stdout.strip() if mirror else ""
    if mirror and (not release_old or not dependencies.is_ancestor(request.root, release_old, request.current_head)):
        gap = "release_mirror_release_branch_missing" if not release_old else "release_mirror_ahead_of_accepted" if dependencies.is_ancestor(request.root, request.current_head, release_old) else "release_mirror_diverged"
        return _blocked(request.policy, request.current_head, [gap], candidate_head=request.candidate_head)
    accepted = _transition(request.root, request.policy.accepted_branch, request.candidate_head, dependencies.run_git)
    release = _transition(request.root, request.policy.release_branch, request.candidate_head, dependencies.run_git) if mirror else None
    return accepted, release, release_old


def _execute_promotion(request: CloseoutRequest, preflight: tuple[CloseoutTransition, CloseoutTransition | None, str], dependencies: CloseoutDependencies) -> dict[str, object]:
    accepted, release, release_old = preflight
    sweep_stale_closeout_intents(request.root)
    proof = dependencies.carry_proof(source_root=request.candidate_path, target_root=request.root, head=request.candidate_head)
    if failure := proof_carry_failure(request, proof):
        return failure
    digest = _proof_digest(request.candidate_path, request.candidate_head)
    policy_digest = gate_policy_digest(request.root, tree_ref=request.candidate_head)
    bootstrap = _hook_bootstrap_required(request, release, dependencies)
    first_leg = (accepted,) if bootstrap else tuple(item for item in (accepted, release) if item is not None)
    sync_attempts = _advance_and_sync_accepted(request, dependencies, first_leg, digest, policy_digest)
    if isinstance(sync_attempts, dict):
        return sync_attempts
    if bootstrap and release:
        release_intents = _write_intents(request.root, (release,), digest, policy_digest)
        try:
            mirror_update = _ref_transaction(request.root, (release,), dependencies.run_git)
        finally:
            _clear_intents(request.root, release_intents)
        if mirror_update.returncode:
            return _blocked(request.policy, request.candidate_head, ["release_mirror_bootstrap_incomplete"], candidate_head=request.candidate_head, accepted_advanced=True, release_mirror={"mode": RELEASE_MIRROR_ACCEPTED_FF, "branch": request.policy.release_branch, "previous_head": release_old, "head": release_old, "worktree_sync": "not_attempted", "bootstrap": "incomplete", "stderr": mirror_update.stderr.strip()})
    mirror_result = sync_release_mirror(release, request.worktrees, request.candidate_head, release_old, dependencies.run_git)
    if mirror_result["worktree_sync"] in {"failed", "dirty"}:
        return _blocked(request.policy, request.candidate_head, ["release_mirror_worktree_sync_failed" if mirror_result["worktree_sync"] == "failed" else "release_mirror_worktree_dirty_after_sync"], candidate_head=request.candidate_head, release_mirror=mirror_result)
    if bootstrap:
        mirror_result["bootstrap"] = "completed"
    return {"ok": True, "state": "accepted_validated", "branch": request.policy.accepted_branch, "source_branch": request.policy.candidate_branch, "head": request.candidate_head, "previous_head": request.current_head, "proof_carry": proof, "sync_attempts": sync_attempts, "release_mirror": mirror_result, "required_gaps": []}


def _advance_and_sync_accepted(request, dependencies, transitions, evidence_digest, policy_digest):
    intents = _write_intents(request.root, transitions, evidence_digest, policy_digest)
    try:
        update = _ref_transaction(request.root, transitions, dependencies.run_git, ref_checks=((f"refs/heads/{request.policy.candidate_branch}", request.candidate_head),))
    finally:
        _clear_intents(request.root, intents)
    if update.returncode:
        dependencies.discard_proof(request.root, request.candidate_head)
        return _ref_transaction_failure(request, transitions[0], update, dependencies.run_git)
    synced, attempts = sync_worktree_to_head(request.root, request.candidate_head, dependencies.run_git)
    if synced.returncode:
        return _blocked(request.policy, request.current_head, ["accepted_worktree_sync_failed"], candidate_head=request.candidate_head, stderr=synced.stderr.strip(), sync_attempts=attempts)
    checked = dependencies.run_git(request.root, "status", "--short", check=False)
    if checked.returncode or checked.stdout.strip():
        return _blocked(request.policy, request.current_head, ["accepted_worktree_dirty_after_sync"], candidate_head=request.candidate_head, stderr=checked.stderr.strip(), status=checked.stdout.strip())
    return attempts


def _ref_transaction_failure(request, accepted, update, run_git):
    """Classify atomic closeout failure from both observed source and target refs."""
    accepted_now = run_git(request.root, "rev-parse", "--verify", accepted.ref_name, check=False).stdout.strip()
    candidate_ref = f"refs/heads/{request.policy.candidate_branch}"
    candidate_now = run_git(request.root, "rev-parse", "--verify", candidate_ref, check=False).stdout.strip()
    observed = {"stderr": update.stderr.strip(), "observed_accepted_head": accepted_now, "observed_candidate_head": candidate_now}
    if accepted_now != accepted.old_value:
        gaps = ["accepted_advanced_concurrently"]
        return _blocked(request.policy, request.current_head, gaps, remediation=remediation.remediation_for_gaps(gaps), **observed)
    if candidate_now != request.candidate_head:
        return _blocked(request.policy, request.current_head, ["candidate_head_changed_after_control_replacement_check"], verified_candidate_head=request.candidate_head, **observed)
    return _blocked(request.policy, request.current_head, ["accepted_atomic_update_rejected"], **observed)


def _hook_bootstrap_required(request, release, dependencies):
    if release is None:
        return False
    accepted_blob = dependencies.run_git(request.root, "rev-parse", f"{request.current_head}:.githooks/reference-transaction", check=False)
    candidate_blob = dependencies.run_git(request.root, "rev-parse", f"{request.candidate_head}:.githooks/reference-transaction", check=False)
    return accepted_blob.returncode == 0 and candidate_blob.returncode == 0 and accepted_blob.stdout.strip() != candidate_blob.stdout.strip()


def _write_intents(root, transitions, evidence_digest, policy_digest):
    return [write_closeout_intent(root=root, transition=item, evidence_digest=evidence_digest, gate_policy_digest=policy_digest) for item in transitions if item]


def _clear_intents(root, intents):
    for intent in intents:
        clear_closeout_intent(root, str(intent["nonce"]))


def _ref_transaction(root, transitions, run_git, *, ref_checks=()):
    program = "\n".join(["start", *(f"update {ref} {head} {head}" for ref, head in ref_checks), *(f"update {item.ref_name} {item.new_value} {item.old_value}" for item in transitions), "prepare", "commit", ""])
    return run_git(root, "update-ref", "--stdin", check=False, stdin=program)


def _transition(root, branch, head, run_git):
    return CloseoutTransition(f"refs/heads/{branch}", run_git(root, "rev-parse", "--verify", branch).stdout.strip(), head, head)


def sync_worktree_to_head(root, head, run_git):
    """Synchronize one checkout to an already selected head with one lock retry."""
    result = run_git(root, "reset", "--hard", head, check=False)
    if not result.returncode or not any(token in result.stderr.lower() for token in ("index.lock", "could not lock index")):
        return result, 1
    return run_git(root, "reset", "--hard", head, check=False), 2


def sync_release_mirror(transition, worktrees, head, previous, run_git):
    if transition is None:
        return {"mode": "independent", "worktree_sync": "not_enabled"}
    branch = transition.ref_name.removeprefix("refs/heads/")
    root = next((Path(str(item["path"])) for item in worktrees if item.get("branch") == branch and item.get("worktree_binding") in {"current", "linked"}), None)
    result = {"mode": RELEASE_MIRROR_ACCEPTED_FF, "branch": branch, "previous_head": previous, "head": head, "worktree_sync": "not_linked" if root is None else "synced"}
    if root is None:
        return result
    reset, attempts = sync_worktree_to_head(root, head, run_git)
    if reset.returncode:
        return {**result, "worktree_sync": "failed", "sync_attempts": attempts, "stderr": reset.stderr.strip()}
    status = run_git(root, "status", "--short", check=False)
    return {**result, "worktree_sync": "dirty" if status.returncode or status.stdout.strip() else "synced"}


def _blocked(policy, current, gaps, **extra):
    return dict(ok=False, state="blocked", branch=policy.accepted_branch, source_branch=policy.candidate_branch, head=current, candidate_head=extra.pop("candidate_head", ""), previous_head=current, required_gaps=gaps, **extra)


def _proof_digest(root, head):
    record = executed_proof_record(root, head)
    return str(record.get("evidence", {}).get("digest", "")) if isinstance(record, dict) else ""


def proof_required_gaps(proof: object) -> list[str]:
    if not isinstance(proof, dict):
        return ["proof_invalid"]
    raw = proof.get("required_gaps")
    if not isinstance(raw, list) or not raw or not all(isinstance(gap, str) for gap in raw):
        return ["proof_invalid"]
    return [gap for gap in raw if isinstance(gap, str)]


def proof_carry_failure(request: CloseoutRequest, proof: object) -> dict[str, object] | None:
    if not isinstance(proof, dict):
        return _blocked(request.policy, request.current_head, ["proof_invalid"], proof_carry=proof)
    if proof.get("ok") is not True:
        return _blocked(request.policy, request.current_head, proof_required_gaps(proof), proof_carry=proof)
    return None


def inspect_accepted_worktree_sync_recovery(
    request: CloseoutWorktreeRecoveryRequest,
    *,
    dependencies: CloseoutDependencies = _DEFAULT_DEPENDENCIES,
) -> dict[str, object]:
    """Read the exact residue shape; this inspection never relocates the lock."""
    receipt, receipt_gaps = _recovery_receipt(request)
    previous = str(receipt.get("previous_head") or "")
    candidate = str(receipt.get("candidate_head") or "")
    heads = _recovery_heads(request, dependencies)
    gaps = [*receipt_gaps]
    if not previous:
        gaps.append("recovery_previous_head_missing")
    if not candidate:
        gaps.append("recovery_candidate_head_missing")
    if candidate and candidate != request.current_head:
        gaps.append("recovery_receipt_candidate_head_mismatch")
    if heads["head"] != request.current_head or heads["accepted"] != request.current_head:
        gaps.append("recovery_promoted_refs_mismatch")
    observed_candidate = heads["candidate"]
    if not observed_candidate or not dependencies.is_ancestor(request.root, request.current_head, observed_candidate):
        gaps.append("recovery_candidate_not_descendant")
    if previous and _HEAD.fullmatch(previous) and _HEAD.fullmatch(request.current_head):
        if not dependencies.is_ancestor(request.root, previous, request.current_head):
            gaps.append("recovery_previous_head_not_ancestor")
    elif previous:
        gaps.append("recovery_previous_head_invalid")
    residue_gaps = _recovery_residue_gaps(request.root, previous, dependencies.run_git)
    gaps.extend(residue_gaps)
    lock_path, lock_path_gap = _index_lock_path(request.root, dependencies.run_git)
    if lock_path_gap:
        gaps.append(lock_path_gap)
    lock, lock_gaps = _lock_fact(lock_path, request.expected_index_lock_sha256)
    gaps.extend(lock_gaps)
    quarantine, quarantine_gaps = _quarantine_fact(
        request.lock_quarantine,
        root=request.root,
        candidate_path=request.candidate_path,
        lock=lock,
    )
    gaps.extend(quarantine_gaps)
    ordered = list(dict.fromkeys(gaps))
    return {
        "ok": not ordered,
        "state": "ready" if not ordered else "blocked",
        "previous_head": previous,
        "candidate_head": candidate,
        "heads": heads,
        "receipt": receipt,
        "index_lock": lock,
        "lock_quarantine": quarantine,
        "residue_exact": not residue_gaps,
        "required_gaps": ordered,
    }


def recover_accepted_worktree_sync(
    request: CloseoutWorktreeRecoveryRequest,
    *,
    dependencies: CloseoutDependencies = _DEFAULT_DEPENDENCIES,
) -> dict[str, object]:
    """Quarantine one proven stale lock and synchronize only the accepted checkout."""
    inspected = inspect_accepted_worktree_sync_recovery(request, dependencies=dependencies)
    if not inspected["ok"]:
        return _recovery_blocked(request, inspected)
    lock_raw, quarantine_raw = inspected["index_lock"], inspected["lock_quarantine"]
    observation_invalid = not isinstance(lock_raw, dict) or not isinstance(quarantine_raw, dict)
    fingerprint = lock_raw.get("fingerprint") if isinstance(lock_raw, dict) else None
    if observation_invalid or not isinstance(fingerprint, dict):
        gap = "recovery_observation_invalid" if observation_invalid else "recovery_index_lock_fingerprint_invalid"
        return _recovery_blocked(request, {**inspected, "required_gaps": [gap]})
    lock = cast("dict[str, object]", lock_raw)
    quarantine = cast("dict[str, object]", quarantine_raw)
    lock_path = Path(str(lock["path"]))
    quarantine_path = Path(str(quarantine["path"]))
    lock_digest = str(lock.get("sha256") or "")
    quarantine_gap = _quarantine_lock(lock_path, quarantine_path, fingerprint, lock_digest)
    pre_sync_gaps = [] if quarantine_gap else _recovery_head_drift_gaps(request, dependencies)
    if quarantine_gap or pre_sync_gaps:
        failure = {**inspected, "required_gaps": [quarantine_gap] if quarantine_gap else pre_sync_gaps}
        if not quarantine_gap:
            failure["lock_quarantined"] = quarantine_path.as_posix()
        return _recovery_blocked(request, failure)
    synced, attempts = sync_worktree_to_head(request.root, request.current_head, dependencies.run_git)
    if synced.returncode:
        return _recovery_blocked(
            request,
            {
                **inspected,
                "required_gaps": ["recovery_worktree_sync_failed"],
                "sync_attempts": attempts,
                "stderr": synced.stderr.strip(),
                "lock_quarantined": quarantine_path.as_posix(),
            },
        )
    post_gaps = _post_recovery_gaps(
        request,
        lock=lock,
        quarantine=quarantine_path,
        run=dependencies.run_git,
    )
    if post_gaps:
        return _recovery_blocked(
            request,
            {
                **inspected,
                "required_gaps": post_gaps,
                "sync_attempts": attempts,
                "lock_quarantined": quarantine_path.as_posix(),
            },
        )
    return {
        "ok": True,
        "state": "accepted_worktree_recovered",
        "branch": request.policy.accepted_branch,
        "source_branch": request.policy.candidate_branch,
        "head": request.current_head,
        "candidate_head": request.candidate_head,
        "previous_head": inspected["previous_head"],
        "receipt": inspected["receipt"],
        "index_lock": {**lock, "quarantined_to": quarantine_path.as_posix()},
        "sync_attempts": attempts,
        "required_gaps": [],
    }


def _recovery_blocked(request, observation):
    return {
        "ok": False,
        "state": "blocked",
        "branch": request.policy.accepted_branch,
        "source_branch": request.policy.candidate_branch,
        "head": request.current_head,
        "candidate_head": request.candidate_head,
        "previous_head": str(observation.get("previous_head") or ""),
        "receipt": observation.get("receipt", {}),
        "index_lock": observation.get("index_lock", {}),
        "lock_quarantine": observation.get("lock_quarantine", {}),
        "sync_attempts": observation.get("sync_attempts", 0),
        "stderr": observation.get("stderr", ""),
        "required_gaps": list(observation.get("required_gaps", [])),
    }


def _recovery_receipt(request):
    path = request.failure_receipt
    gaps = []
    if path is None:
        return {}, ["recovery_failure_receipt_required"]
    if not path.is_absolute() or not path.is_file() or _inside(path, request.root) or _inside(path, request.candidate_path):
        return {}, ["recovery_failure_receipt_invalid"]
    try:
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        payload = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}, ["recovery_failure_receipt_invalid"]
    if not _sha256(request.expected_failure_receipt_sha256):
        gaps.append("recovery_failure_receipt_digest_invalid")
    elif digest != request.expected_failure_receipt_sha256:
        gaps.append("recovery_failure_receipt_digest_mismatch")
    data = payload.get("data") if isinstance(payload, dict) else None
    update = data.get("accepted_update") if isinstance(data, dict) else None
    if not (isinstance(payload, dict) and payload.get("ok") is False and payload.get("state") == "blocked" and isinstance(update, dict)):
        return {"path": path.as_posix(), "sha256": digest}, [*gaps, "recovery_failure_receipt_shape_invalid"]
    required = update.get("required_gaps")
    if not isinstance(required, list) or "accepted_worktree_sync_failed" not in required:
        gaps.append("recovery_failure_receipt_not_sync_failure")
    previous, candidate = str(update.get("previous_head") or ""), str(update.get("candidate_head") or "")
    if update.get("branch") != request.policy.accepted_branch or update.get("source_branch") != request.policy.candidate_branch:
        gaps.append("recovery_failure_receipt_branch_mismatch")
    if update.get("head") != previous or not _HEAD.fullmatch(previous) or not _HEAD.fullmatch(candidate):
        gaps.append("recovery_failure_receipt_head_invalid")
    return {"path": path.as_posix(), "sha256": digest, "previous_head": previous, "candidate_head": candidate, "sync_attempts": update.get("sync_attempts", 0)}, gaps


def _recovery_heads(request, dependencies):
    return {
        "head": _git_text(request.root, dependencies.run_git, "rev-parse", "--verify", "HEAD"),
        "accepted": _git_text(request.root, dependencies.run_git, "rev-parse", "--verify", request.policy.accepted_branch),
        "candidate": _git_text(request.root, dependencies.run_git, "rev-parse", "--verify", request.policy.candidate_branch),
    }


def _recovery_head_drift_gaps(request, dependencies):
    heads = _recovery_heads(request, dependencies)
    gaps = []
    if heads["head"] != request.current_head or heads["accepted"] != request.current_head:
        gaps.append("recovery_promoted_refs_drifted")
    if not heads["candidate"] or not dependencies.is_ancestor(request.root, request.current_head, heads["candidate"]):
        gaps.append("recovery_candidate_drifted")
    return gaps


def _recovery_residue_gaps(root, previous, run):
    if not previous:
        return ["recovery_previous_head_missing"]
    checks = (
        ("recovery_index_not_previous_head", run(root, "diff-index", "--cached", "--quiet", previous, "--", check=False)),
        ("recovery_worktree_not_index", run(root, "diff-files", "--quiet", check=False)),
        ("recovery_untracked_content_present", run(root, "ls-files", "--others", "--exclude-standard", check=False)),
        ("recovery_conflict_entries_present", run(root, "ls-files", "-u", check=False)),
    )
    return [gap for gap, result in checks if result.returncode or result.stdout.strip()]


def _index_lock_path(root, run):
    raw = _git_text(root, run, "rev-parse", "--git-path", "index.lock")
    if not raw:
        return None, "recovery_index_lock_path_unavailable"
    path = Path(raw)
    return (path if path.is_absolute() else root / path), ""


def _lock_fact(path, expected_digest):
    if path is None or not _sha256(expected_digest):
        return {}, ["recovery_index_lock_digest_invalid"]
    try:
        before = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(before.st_mode):
            return {}, ["recovery_index_lock_type_invalid"]
        raw = path.read_bytes()
        after = path.lstat()
    except OSError:
        return {}, ["recovery_index_lock_missing"]
    fingerprint = _fingerprint(before)
    if fingerprint != _fingerprint(after):
        return {}, ["recovery_index_lock_drift"]
    digest = hashlib.sha256(raw).hexdigest()
    if digest != expected_digest:
        return {"path": path.as_posix(), "sha256": digest, "fingerprint": fingerprint}, ["recovery_index_lock_digest_mismatch"]
    return {"path": path.as_posix(), "sha256": digest, "fingerprint": fingerprint}, []


def _quarantine_fact(path, *, root, candidate_path, lock):
    if path is None or not path.is_absolute() or _inside(path, root) or _inside(path, candidate_path):
        return {}, ["recovery_lock_quarantine_invalid"]
    try:
        path.lstat()
    except FileNotFoundError:
        pass
    except OSError:
        return {}, ["recovery_lock_quarantine_invalid"]
    else:
        return {}, ["recovery_lock_quarantine_exists"]
    try:
        parent = path.parent.resolve(strict=True)
        lock_path = Path(str(lock.get("path") or ""))
        source = lock_path.lstat()
    except (OSError, ValueError):
        return {}, ["recovery_lock_quarantine_invalid"]
    if not parent.is_dir() or parent.stat().st_dev != source.st_dev:
        return {}, ["recovery_lock_quarantine_cross_device"]
    return {"path": path.as_posix(), "parent": parent.as_posix()}, []


def _quarantine_lock(lock, quarantine, fingerprint, digest):
    current, gaps = _lock_fact(lock, digest)
    if gaps or current.get("fingerprint") != fingerprint:
        return "recovery_index_lock_drift"
    try:
        _atomic_rename_no_replace(lock, quarantine)
    except FileExistsError:
        return "recovery_lock_quarantine_exists"
    except OSError:
        return "recovery_lock_quarantine_move_failed"
    current, gaps = _lock_fact(quarantine, digest)
    if gaps or not _same_lock_identity(current.get("fingerprint"), fingerprint):
        return "recovery_lock_quarantine_drifted"
    if lock.exists():
        return "recovery_index_lock_present_after_quarantine"
    return ""


def _atomic_rename_no_replace(source, target):
    library = ctypes.CDLL(None, use_errno=True)
    if sys.platform == "darwin":
        operation = getattr(library, "renameatx_np", None)
        flags = 4  # RENAME_EXCL
    elif sys.platform.startswith("linux"):
        operation = getattr(library, "renameat2", None)
        flags = 1  # RENAME_NOREPLACE
    else:
        operation = None
        flags = 0
    if operation is None:
        raise OSError(errno.ENOTSUP, "atomic no-replace rename is unavailable")
    operation.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    operation.restype = ctypes.c_int
    if operation(-2, os.fsencode(source), -2, os.fsencode(target), flags) == 0:
        return
    error = ctypes.get_errno()
    if error == errno.EEXIST:
        raise FileExistsError(error, os.strerror(error), target)
    raise OSError(error, os.strerror(error), target)


def _post_recovery_gaps(request, *, lock, quarantine, run):
    lock_path = Path(str(lock["path"]))
    fingerprint = lock["fingerprint"]
    digest = str(lock["sha256"])
    gaps = _recovery_head_drift_gaps(request, CloseoutDependencies(run_git=run))
    status = run(request.root, "status", "--short", check=False)
    if status.returncode or status.stdout.strip():
        gaps.append("recovery_worktree_dirty_after_sync")
    if lock_path.exists():
        gaps.append("recovery_index_lock_present_after_sync")
    try:
        recovered = _lock_fact(quarantine, digest)[0]
    except OSError:
        recovered = {}
    if not _same_lock_identity(recovered.get("fingerprint"), fingerprint):
        gaps.append("recovery_lock_quarantine_drifted")
    return gaps


def _git_text(root, run, *args):
    result = run(root, *args, check=False)
    return result.stdout.strip() if not result.returncode else ""


def _fingerprint(value):
    return {"dev": value.st_dev, "ino": value.st_ino, "mode": value.st_mode, "size": value.st_size, "mtime_ns": value.st_mtime_ns, "ctime_ns": value.st_ctime_ns}


def _same_lock_identity(left, right):
    return isinstance(left, dict) and isinstance(right, dict) and all(left.get(name) == right.get(name) for name in ("dev", "ino", "mode", "size", "mtime_ns"))


def _inside(path, root):
    try:
        path.resolve(strict=False).is_relative_to(root.resolve(strict=False))
    except OSError:
        return True
    else:
        return path.resolve(strict=False).is_relative_to(root.resolve(strict=False))


def _sha256(value):
    return bool(re.fullmatch(r"[0-9a-f]{64}", value))
# fmt: on
