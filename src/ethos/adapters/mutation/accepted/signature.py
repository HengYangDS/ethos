"""Recover one accepted signature through existing native and Git effect owners."""

from __future__ import annotations

import os
import shlex
import subprocess
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import cast

from filelock import FileLock
from filelock import Timeout

from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.attestation_set import record_attestation_once
from ethos.adapters.repo.attestation_set import record_attestations
from ethos.adapters.repo.commit.creation import create_signed_replacement
from ethos.adapters.repo.commit.signature import ATTEMPT
from ethos.adapters.repo.commit.signature import RESULT
from ethos.adapters.repo.commit.signature import observe_signature_effects
from ethos.adapters.repo.commit.signature import signature_coordinates
from ethos.adapters.repo.commit.signature import signature_plan
from ethos.adapters.repo.commit.signature import signature_record_coordinates
from ethos.adapters.repo.commit.signature import validate_signature_coordinates
from ethos.adapters.repo.commit.signature import validate_signature_result
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git_effects import execute_git_effect
from ethos.adapters.repo.git_ref_worktrees import sync_ref_worktrees
from ethos.adapters.store.state.schema import local_state_root
from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import canonical_json_digest


def _require(condition: object, gap: str) -> None:
    if not condition:
        raise ValueError(gap)


def _record(predicate: str, coordinates: dict[str, object], **result: object) -> Attestation:
    now = datetime.now(UTC)
    return Attestation.issue(
        {
            "schema_version": 2,
            "predicate": predicate,
            "verifier": str(coordinates["actor"]),
            "subject": f"signature-repair:{canonical_json_digest(coordinates)}",
            "issued_at": now,
            "valid_from": now,
            "valid_until": None,
            "verdict": "pass",
            "payload": {"kind": predicate, "body": {"coordinates": coordinates, **result}},
            "relations": (),
            "advisories": (),
            "evidence_refs": (f"git:{coordinates['old']}",),
            "commitment_digest": None,
            "facts_digest": canonical_json_digest(coordinates),
            "plan_digest": result.get("plan_digest"),
            "policy_digest": coordinates["policy_sha256"],
            "effect_digest": None,
            "mints_authority": False,
        }
    )


def _records(root: Path, old: str, actor: str) -> tuple[Attestation | None, Attestation | None]:
    _, values = read_attestation_set(root)
    selected = []
    for item in values:
        if item.predicate not in {ATTEMPT, RESULT}:
            continue
        coordinates = signature_record_coordinates(item)
        if coordinates["old"] != old:
            continue
        _require(coordinates["actor"] == actor, "signature_repair_actor_mismatch")
        _require(coordinates["root"] == root.as_posix(), "signature_repair_root_mismatch")
        selected.append(item)
    attempts = [item for item in selected if item.predicate == ATTEMPT]
    results = [item for item in selected if item.predicate == RESULT]
    _require(len(attempts) <= 1 and len(results) <= 1, "signature_repair_evidence_ambiguous")
    attempt, result = next(iter(attempts), None), next(iter(results), None)
    if attempt:
        _require(attempt.plan_digest is None, "signature_repair_evidence_invalid")
    if result:
        _require(
            attempt is not None
            and attempt.payload.body["coordinates"] == result.payload.body["coordinates"],
            "signature_repair_attempt_mismatch",
        )
        validate_signature_result(root, result, actor)
    return attempt, result


def _apply(
    root: Path,
    coordinates: dict[str, object],
    attempt: Attestation | None,
    result: Attestation | None,
    replacement: str,
) -> dict[str, object]:
    old, actor = str(coordinates["old"]), str(coordinates["actor"])
    try:
        if result is None:
            _require(
                attempt is None or bool(replacement), "signature_repair_signing_outcome_unknown"
            )
            if attempt is None:
                _require(not replacement, "signature_repair_replacement_without_attempt")
                attempt = record_attestation_once(root, _record(ATTEMPT, coordinates))
                validate_signature_coordinates(root, coordinates, actor)
                replacement = create_signed_replacement(root, old)
            validate_signature_coordinates(root, coordinates, actor, replacement)
            plan = signature_plan(root, coordinates, replacement)
            result = _record(
                RESULT,
                coordinates,
                replacement=replacement,
                plan=plan.model_dump(mode="json"),
                plan_digest=plan.digest,
            )
            record_attestations(root, (result,))
        else:
            replacement = str(result.payload.body["replacement"])
            plan = validate_signature_result(root, result, actor)
        validate_signature_coordinates(root, coordinates, actor, replacement)
        effect_result = execute_git_effect(root, plan, issuer=actor)
        synced = []
        for item in cast("list[dict[str, str]]", coordinates["worktrees"]):
            observed = sync_ref_worktrees(
                root, (Path(item["path"]),), item["branch"], replacement, old
            )
            _require(
                observed["worktree_sync"] == "synced",
                f"signature_repair_worktree_sync_failed:{item['path']}",
            )
            synced.extend(cast("list[object]", observed["worktrees"]))
        validate_signature_coordinates(root, coordinates, actor, replacement)
        return {
            "verdict": "pass",
            "state": "signature_repaired",
            "head": replacement,
            "previous_head": old,
            "required_gaps": [],
            "worktrees": synced,
            "attestation": effect_result.model_dump(mode="json"),
            "next_action": (
                f"ethos prove --root {shlex.quote(str(root))} --execute "
                f"--expect-head {replacement} --json"
            ),
        }

    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError) as error:
        return _failure(
            root,
            old,
            error,
            replacement=replacement,
            attempted=True,
            coordinates=coordinates,
        )


def repair_signature(
    *,
    root: Path,
    expect_head: str,
    apply: bool = False,
    authorized: bool = False,
    replacement: str = "",
) -> dict[str, object]:
    """Observe, execute or recover one authorized accepted-tip signature repair."""
    root = root.resolve()
    actor = os.environ.get("ETHOS_ACTOR", "").strip()
    action = (
        f"ethos lane repair-signature --root {shlex.quote(str(root))} "
        f"--expect-head {expect_head} --apply --authorize --json"
    )
    try:
        _require(bool(actor), "signature_repair_actor_required")
        _require(not apply or authorized, "authorization_required")
        attempt, result = _records(root, expect_head, actor)
        _require(
            attempt is not None or not replacement, "signature_repair_replacement_without_attempt"
        )
        _require(
            result is None or not replacement or result.payload.body["replacement"] == replacement,
            "signature_repair_replacement_mismatch",
        )
        saved = result or attempt
        coordinates = (
            signature_record_coordinates(saved)
            if saved
            else signature_coordinates(root, expect_head, actor)
        )
        new = str(result.payload.body["replacement"]) if result else replacement
        validate_signature_coordinates(root, coordinates, actor, new)
        _require(
            not (attempt and not result and not new), "signature_repair_signing_outcome_unknown"
        )
        if not apply:
            return {
                "verdict": "pass",
                "state": "ready_to_repair",
                "head": current_tracked_head(root),
                "coordinates": coordinates,
                "required_gaps": [],
                "next_action": action,
            }
        lock = local_state_root(root) / "signature-repair.lock"
        lock.parent.mkdir(parents=True, exist_ok=True)
        with FileLock(str(lock), timeout=0, mode=0o600):
            attempt, result = _records(root, expect_head, actor)
            _require(
                attempt is not None or not replacement,
                "signature_repair_replacement_without_attempt",
            )
            validate_signature_coordinates(
                root,
                coordinates,
                actor,
                str(result.payload.body["replacement"]) if result else replacement,
            )
            return _apply(root, coordinates, attempt, result, replacement)
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError, Timeout) as error:
        return _failure(root, expect_head, error, replacement=replacement)


def _failure(
    root: Path,
    old: str,
    error: Exception,
    *,
    replacement: str = "",
    attempted: bool = False,
    coordinates: dict[str, object] | None = None,
) -> dict[str, object]:
    gap = str(error) or type(error).__name__
    evidence = error.evidence() if isinstance(error, ProcessExecutionError) else {}
    if isinstance(error, ProcessExecutionError):
        replacement = str(error.observation.get("replacement") or replacement)
    waiting = isinstance(error, Timeout)
    rejected = (
        isinstance(error, ProcessExecutionError)
        and error.observation.get("validation_verdict") == "block"
    )
    unknown = (
        not waiting
        and not rejected
        and (
            attempted
            or gap == "signature_repair_signing_outcome_unknown"
            or isinstance(error, (OSError, subprocess.SubprocessError))
        )
    )
    action = (
        f"ethos lane repair-signature --root {shlex.quote(str(root))} "
        f"--expect-head {shlex.quote(old)} "
        + (f"--replacement {shlex.quote(replacement)} " if replacement else "")
        + "--apply --authorize --json"
    )
    if gap == "signature_repair_signing_outcome_unknown":
        action = f"git -C {shlex.quote(str(root))} fsck --no-reflogs --unreachable"
    return {
        "verdict": "unknown" if unknown else "block",
        "state": "waiting" if waiting else "partial_transition" if unknown else "blocked",
        "head": current_tracked_head(root),
        "previous_head": old,
        "replacement": replacement,
        "error": evidence or {"cause": str(error)},
        "effects": observe_signature_effects(root, coordinates, replacement) if coordinates else {},
        "required_gaps": ["signature_repair_in_progress" if waiting else gap],
        "next_action": action,
        "boundary": "accepted-signature-repair",
        "mints_authority": False,
    }
