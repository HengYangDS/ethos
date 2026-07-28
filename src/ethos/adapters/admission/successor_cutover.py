"""Single-use semantic-kernel successor cutover.

This module exists only to cross one self-hosting boundary.  It validates an
immutable incumbent-to-successor commit, lets Git perform one exact ref CAS,
and rebinds the corresponding raw Lease row by full-row CAS.  The successor
commit must delete this module after the cutover; normal lifecycle operations
must never acquire a digest-rebinding capability.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import sqlite3
import stat
import subprocess
import sys
import tarfile
import tempfile
import tomllib
from pathlib import Path
from typing import Any
from typing import cast

from ethos.adapters.store.state.schema import state_database

_ENVELOPE_ENV = "ETHOS_SUCCESSOR_ENVELOPE"
_ENVELOPE_SHA_ENV = "ETHOS_SUCCESSOR_ENVELOPE_SHA256"
_ACTOR_ENV = "ETHOS_ACTOR"
_HOOK_PHASE_ENV = "ETHOS_SUCCESSOR_HOOK_PHASE"
_HOOK_REF_ENV = "ETHOS_SUCCESSOR_HOOK_REF"
_HOOK_OLD_ENV = "ETHOS_SUCCESSOR_HOOK_OLD"
_HOOK_NEW_ENV = "ETHOS_SUCCESSOR_HOOK_NEW"
_OPERATION = "semantic-kernel-successor-cutover-v1"
_ZERO_EXIT = 0
_LEASE_FIELDS = ("id", "subject", "owner", "expires_at", "payload_json", "payload_sha256")
_LEASE_PAYLOAD_FIELDS = {
    "lane_incarnation_id",
    "lease_id",
    "lane_ref",
    "holder_ref",
    "epoch",
    "issued_at",
    "renewed_at",
    "expires_at",
    "expected_head",
    "path_scope",
    "handoff",
}
_BASELINE_FIELDS = {
    "schema_version": 1,
    "id": "",
    "intent": "",
    "subjects": [],
    "scope": [],
    "invariants": [],
    "acceptance": [],
    "risks": [],
    "authority_refs": [],
    "permissions": [],
    "hypotheses": [],
    "dependencies": [],
    "campaign": "",
    "collaboration": "single",
    "compatibility": "none",
    "publication": "local",
}


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_digest(value: object) -> str:
    return _sha256_bytes(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def _run(root: Path, *args: str, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        input=input_text,
    )


def _git(root: Path, *args: str) -> str:
    completed = _run(root, "git", *args)
    if completed.returncode:
        message = completed.stderr.strip() or completed.stdout.strip() or "git_command_failed"
        raise ValueError(message)
    return completed.stdout.strip()


def _regular_private_file(path: Path) -> None:
    if path.is_symlink() or not path.is_file():
        raise ValueError("successor_envelope_not_regular_file")
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & (stat.S_IWGRP | stat.S_IWOTH):
        raise ValueError("successor_envelope_is_group_or_world_writable")


def load_envelope(path: Path, expected_sha256: str) -> dict[str, Any]:
    """Load one externally bound, non-writable successor envelope."""
    absolute = path.expanduser().resolve(strict=True)
    _regular_private_file(absolute)
    raw = absolute.read_bytes()
    if _sha256_bytes(raw) != expected_sha256:
        raise ValueError("successor_envelope_digest_mismatch")
    payload = json.loads(raw)
    if not isinstance(payload, dict) or payload.get("operation") != _OPERATION:
        raise ValueError("successor_envelope_operation_invalid")
    return cast("dict[str, Any]", payload)


def _envelope_from_environment() -> tuple[Path, dict[str, Any]]:
    path_text = os.environ.get(_ENVELOPE_ENV, "").strip()
    digest = os.environ.get(_ENVELOPE_SHA_ENV, "").strip()
    if not path_text or len(digest) != 64:
        raise ValueError("successor_envelope_binding_missing")
    path = Path(path_text)
    return path, load_envelope(path, digest)


def _exact_keys(value: object, expected: set[str], name: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        message = f"successor_envelope_{name}_shape_invalid"
        raise ValueError(message)
    return cast("dict[str, Any]", value)


def _lease_rows(root: Path, subject: str) -> tuple[sqlite3.Connection, sqlite3.Row | None]:
    connection = sqlite3.connect(state_database(root))
    connection.row_factory = sqlite3.Row
    row = connection.execute(
        "select id, subject, owner, expires_at, payload_json from leases where subject = ?",
        (subject,),
    ).fetchone()
    return connection, row


def _raw_lease(row: sqlite3.Row | None) -> dict[str, str]:
    if row is None:
        return {}
    payload_json = str(row["payload_json"])
    return {
        "id": str(row["id"]),
        "subject": str(row["subject"]),
        "owner": str(row["owner"]),
        "expires_at": str(row["expires_at"]),
        "payload_json": payload_json,
        "payload_sha256": _sha256_bytes(payload_json.encode()),
    }


def _assert_raw_lease(actual: dict[str, str], expected: dict[str, Any], label: str) -> None:
    if not actual or set(actual) != set(_LEASE_FIELDS):
        message = f"successor_{label}_lease_drift"
        raise ValueError(message)
    comparable = {key: str(expected[key]) for key in _LEASE_FIELDS}
    if actual != comparable:
        message = f"successor_{label}_lease_drift"
        raise ValueError(message)


def _read_raw_lease(root: Path, subject: str) -> dict[str, str]:
    connection, row = _lease_rows(root, subject)
    try:
        return _raw_lease(row)
    finally:
        connection.close()


def _lease_payload(row: dict[str, Any], field: str) -> dict[str, Any]:
    payload_json = str(row["payload_json"])
    if _sha256_bytes(payload_json.encode()) != str(row["payload_sha256"]):
        message = f"successor_{field}_digest_mismatch"
        raise ValueError(message)
    payload = json.loads(payload_json)
    expected = _LEASE_PAYLOAD_FIELDS | {
        "base_change_contract_digest" if field == "lease_before" else "base_commitment_digest"
    }
    return _exact_keys(payload, expected, field)


def _validate_lease_coordinates(
    envelope: dict[str, Any], baseline: dict[str, Any], successor: dict[str, Any]
) -> None:
    before = _exact_keys(envelope["lease_before"], set(_LEASE_FIELDS), "lease_before")
    after = _exact_keys(envelope["lease_after"], set(_LEASE_FIELDS), "lease_after")
    branch = str(envelope["branch"])
    actor = str(envelope["actor"])
    prepare_head = str(envelope["prepare_head"])
    successor_head = str(envelope["successor_head"])
    if (before["id"], before["subject"]) != (after["id"], after["subject"]):
        raise ValueError("successor_lease_identity_mismatch")
    if before["subject"] != branch or before["owner"] != actor or after["owner"] != actor:
        raise ValueError("successor_lease_coordinate_mismatch")
    before_payload = _lease_payload(before, "lease_before")
    after_payload = _lease_payload(after, "lease_after")
    shared = (
        "lane_incarnation_id",
        "lease_id",
        "lane_ref",
        "holder_ref",
        "issued_at",
        "path_scope",
    )
    if any(before_payload[key] != after_payload[key] for key in shared):
        raise ValueError("successor_lease_payload_identity_mismatch")
    if (
        before_payload["lease_id"] != before["id"]
        or before_payload["lane_ref"] != branch
        or before_payload["holder_ref"] != actor
        or before_payload["expires_at"] != before["expires_at"]
        or after_payload["expires_at"] != after["expires_at"]
        or before_payload["expected_head"] != prepare_head
        or after_payload["expected_head"] != successor_head
        or before_payload["base_change_contract_digest"] != baseline["digest"]
        or after_payload["base_commitment_digest"] != successor["digest"]
        or before_payload["handoff"] is not None
        or after_payload["handoff"] is not None
    ):
        raise ValueError("successor_lease_payload_coordinate_mismatch")
    before_epoch = before_payload["epoch"]
    after_epoch = after_payload["epoch"]
    if (
        isinstance(before_epoch, bool)
        or not isinstance(before_epoch, int)
        or isinstance(after_epoch, bool)
        or not isinstance(after_epoch, int)
        or after_epoch != before_epoch + 1
    ):
        raise ValueError("successor_lease_epoch_mismatch")


def _baseline_digest(root: Path, tree_ref: str, carrier: str) -> str:
    repository = tomllib.loads(_git(root, "show", f"{tree_ref}:.ethos/contract.toml"))
    repository_id = repository.get("id")
    if not isinstance(repository_id, str) or not repository_id:
        raise ValueError("successor_baseline_repository_identity_invalid")
    payload = tomllib.loads(_git(root, "show", f"{tree_ref}:{carrier}"))
    if unknown := set(payload) - set(_BASELINE_FIELDS):
        message = f"successor_baseline_field_invalid:{sorted(unknown)[0]}"
        raise ValueError(message)
    normalized = dict(_BASELINE_FIELDS) | payload
    subjects = normalized.get("subjects")
    if not isinstance(subjects, list):
        raise TypeError("successor_baseline_subjects_invalid")
    normalized["subjects"] = [
        repository_id if subject == "repository:self" else subject for subject in subjects
    ]
    return _canonical_digest(normalized)


def _validate_git_coordinates(root: Path, envelope: dict[str, Any]) -> tuple[str, str]:
    actual_root = root.resolve()
    if str(envelope["root"]) != actual_root.as_posix():
        raise ValueError("successor_root_mismatch")
    actor = os.environ.get(_ACTOR_ENV, "").strip()
    if actor != str(envelope["actor"]):
        raise ValueError("successor_actor_mismatch")
    branch = str(envelope["branch"])
    if str(envelope["ref_name"]) != f"refs/heads/{branch}":
        raise ValueError("successor_ref_branch_mismatch")
    if _git(actual_root, "branch", "--show-current") != branch:
        raise ValueError("successor_branch_mismatch")
    prepare_head = str(envelope["prepare_head"])
    successor_head = str(envelope["successor_head"])
    if _git(actual_root, "rev-parse", f"{successor_head}^") != prepare_head:
        raise ValueError("successor_parent_mismatch")
    if _git(actual_root, "rev-parse", f"{prepare_head}^{{tree}}") != str(envelope["prepare_tree"]):
        raise ValueError("successor_prepare_tree_mismatch")
    if _git(actual_root, "rev-parse", f"{successor_head}^{{tree}}") != str(
        envelope["successor_tree"]
    ):
        raise ValueError("successor_tree_mismatch")
    return prepare_head, successor_head


def _diff_identity(root: Path, old_head: str, new_head: str) -> tuple[str, tuple[str, ...]]:
    completed = subprocess.run(
        ["git", "diff-tree", "--no-commit-id", "--raw", "-r", "-z", old_head, new_head],
        cwd=root,
        check=False,
        capture_output=True,
    )
    if completed.returncode:
        raise ValueError("successor_diff_unavailable")
    names = _git(root, "diff", "--name-only", "-z", old_head, new_head).split("\0")
    return _sha256_bytes(completed.stdout), tuple(sorted(name for name in names if name))


def _validate_static_transition(root: Path, envelope: dict[str, Any]) -> None:
    """Validate immutable Git, actor, carrier, and patch coordinates."""
    expected_top = {
        "operation",
        "root",
        "branch",
        "ref_name",
        "actor",
        "prepare_head",
        "successor_head",
        "prepare_tree",
        "successor_tree",
        "baseline",
        "successor",
        "patch",
        "lease_before",
        "lease_after",
    }
    if set(envelope) != expected_top:
        raise ValueError("successor_envelope_shape_invalid")
    actual_root = root.resolve()
    prepare_head, successor_head = _validate_git_coordinates(actual_root, envelope)

    baseline = _exact_keys(envelope["baseline"], {"carrier", "digest"}, "baseline")
    successor = _exact_keys(envelope["successor"], {"carrier", "digest", "tests"}, "successor")
    _validate_lease_coordinates(envelope, baseline, successor)

    patch = _exact_keys(envelope["patch"], {"raw_sha256", "paths"}, "patch")
    raw_digest, paths = _diff_identity(actual_root, prepare_head, successor_head)
    if raw_digest != str(patch["raw_sha256"]) or list(paths) != patch["paths"]:
        raise ValueError("successor_patch_mismatch")

    if _baseline_digest(actual_root, prepare_head, str(baseline["carrier"])) != str(
        baseline["digest"]
    ):
        raise ValueError("successor_baseline_digest_mismatch")


def validate_transition(root: Path, envelope: dict[str, Any]) -> None:
    """Validate immutable transition coordinates and the incumbent Lease."""
    _validate_static_transition(root, envelope)
    actual_root = root.resolve()

    lease_before = _exact_keys(
        envelope["lease_before"],
        {"id", "subject", "owner", "expires_at", "payload_json", "payload_sha256"},
        "lease_before",
    )
    connection, row = _lease_rows(actual_root, str(lease_before["subject"]))
    try:
        _assert_raw_lease(_raw_lease(row), lease_before, "incumbent")
    finally:
        connection.close()


def evaluate_successor(
    root: Path, envelope: dict[str, Any], *, require_incumbent_lease: bool = True
) -> dict[str, object]:
    """Execute the successor evaluator from the immutable proposed Git tree."""
    if require_incumbent_lease:
        validate_transition(root, envelope)
    else:
        _validate_static_transition(root, envelope)
    successor = _exact_keys(envelope["successor"], {"carrier", "digest", "tests"}, "successor")
    head = str(envelope["successor_head"])
    with tempfile.TemporaryDirectory(prefix="ethos-successor-evaluator-") as directory:
        target = Path(directory)
        archive = subprocess.run(
            ["git", "archive", "--format=tar", head],
            cwd=root,
            check=False,
            capture_output=True,
        )
        if archive.returncode != _ZERO_EXIT:
            raise ValueError("successor_archive_failed")
        with tarfile.open(fileobj=io.BytesIO(archive.stdout), mode="r:") as stream:
            stream.extractall(target, filter="data")
        python = Path(sys.executable)
        carrier = str(successor["carrier"])
        digest = str(successor["digest"])
        script = (
            "from pathlib import Path; "
            "from ethos.contracts.semantic import load_commitment_file; "
            f"c=load_commitment_file(Path({carrier!r}), "
            "repository_id='repository:ethos'); "
            f"assert c.digest()=={digest!r}"
        )
        environment = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith("ETHOS_SUCCESSOR_")
        }
        environment["PYTHONPATH"] = str(target / "src")
        semantic = subprocess.run(
            [str(python), "-c", script],
            cwd=target,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )
        if semantic.returncode:
            message = f"successor_semantic_evaluation_failed:{semantic.stderr.strip()}"
            raise ValueError(message)
        tests = successor["tests"]
        if (
            not isinstance(tests, list)
            or not tests
            or any(not isinstance(item, str) for item in tests)
        ):
            raise ValueError("successor_test_set_invalid")
        proof = subprocess.run(
            [str(python), "-m", "pytest", "-q", *tests],
            cwd=target,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )
        if proof.returncode:
            message = f"successor_tests_failed:{proof.stdout[-2000:]}{proof.stderr[-2000:]}"
            raise ValueError(message)
    return {
        "state": "successor_evaluated",
        "successor_head": head,
        "commitment_digest": str(successor["digest"]),
        "tests": tests,
    }


def replace_lease(root: Path, envelope: dict[str, Any]) -> None:
    """Replace the incumbent raw Lease with the successor wire by exact full-row CAS."""
    before = cast("dict[str, Any]", envelope["lease_before"])
    after = _exact_keys(
        envelope["lease_after"],
        {"id", "subject", "owner", "expires_at", "payload_json", "payload_sha256"},
        "lease_after",
    )
    if (before["id"], before["subject"]) != (after["id"], after["subject"]):
        raise ValueError("successor_lease_identity_mismatch")
    if _sha256_bytes(str(after["payload_json"]).encode()) != str(after["payload_sha256"]):
        raise ValueError("successor_lease_after_digest_mismatch")
    connection, row = _lease_rows(root, str(before["subject"]))
    try:
        connection.execute("begin immediate")
        _assert_raw_lease(_raw_lease(row), before, "incumbent")
        cursor = connection.execute(
            "update leases set owner = ?, expires_at = ?, payload_json = ? "
            "where id = ? and subject = ? and owner = ? and expires_at = ? and payload_json = ?",
            (
                str(after["owner"]),
                str(after["expires_at"]),
                str(after["payload_json"]),
                str(before["id"]),
                str(before["subject"]),
                str(before["owner"]),
                str(before["expires_at"]),
                str(before["payload_json"]),
            ),
        )
        _require_replaced_row(cursor.rowcount)
        reread = connection.execute(
            "select id, subject, owner, expires_at, payload_json from leases where subject = ?",
            (str(after["subject"]),),
        ).fetchone()
        _assert_raw_lease(_raw_lease(reread), after, "successor")
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _require_replaced_row(rowcount: int) -> None:
    if rowcount != 1:
        raise ValueError("successor_lease_full_row_cas_failed")


def _require_successor_ref(root: Path, envelope: dict[str, Any]) -> None:
    if _git(root, "rev-parse", str(envelope["ref_name"])) != str(envelope["successor_head"]):
        raise ValueError("successor_ref_state_invalid")


def _materialize_successor(root: Path, envelope: dict[str, Any]) -> None:
    prepare_head = str(envelope["prepare_head"])
    prepare_tree = str(envelope["prepare_tree"])
    successor_head = str(envelope["successor_head"])
    successor_tree = str(envelope["successor_tree"])
    ref_name = str(envelope["ref_name"])
    if _git(root, "rev-parse", ref_name) != successor_head:
        raise ValueError("successor_ref_state_invalid")
    current_tree = _git(root, "write-tree")
    clean = _run(root, "git", "diff-files", "--quiet", "--").returncode == _ZERO_EXIT
    untracked = _git(root, "ls-files", "--others", "--exclude-standard")
    if clean and not untracked and current_tree == successor_tree:
        return
    if not clean or untracked or current_tree != prepare_tree:
        raise ValueError("successor_worktree_not_exact_prepare")
    materialized = _run(
        root,
        "git",
        "-c",
        "core.hooksPath=/dev/null",
        "read-tree",
        "-u",
        "-m",
        prepare_head,
        successor_head,
    )
    if materialized.returncode:
        raise ValueError("successor_worktree_materialization_failed")
    if (
        _git(root, "rev-parse", ref_name) != successor_head
        or _git(root, "write-tree") != successor_tree
        or _run(root, "git", "diff-files", "--quiet", "--").returncode
        or _git(root, "ls-files", "--others", "--exclude-standard")
    ):
        raise ValueError("successor_worktree_materialization_mismatch")


def _materialize_successor_with_lease_lock(root: Path, envelope: dict[str, Any]) -> None:
    after = cast("dict[str, Any]", envelope["lease_after"])
    connection, _ = _lease_rows(root, str(after["subject"]))
    try:
        connection.execute("begin immediate")
        row = connection.execute(
            "select id, subject, owner, expires_at, payload_json from leases where subject = ?",
            (str(after["subject"]),),
        ).fetchone()
        _assert_raw_lease(_raw_lease(row), after, "successor")
        _materialize_successor(root, envelope)
        reread = connection.execute(
            "select id, subject, owner, expires_at, payload_json from leases where subject = ?",
            (str(after["subject"]),),
        ).fetchone()
        _assert_raw_lease(_raw_lease(reread), after, "successor")
        _require_successor_ref(root, envelope)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _transition_state(root: Path, envelope: dict[str, Any]) -> str:
    ref_name = str(envelope["ref_name"])
    before = cast("dict[str, Any]", envelope["lease_before"])
    after = cast("dict[str, Any]", envelope["lease_after"])
    first_ref = _git(root, "rev-parse", ref_name)
    lease = _read_raw_lease(root, str(before["subject"]))
    if _git(root, "rev-parse", ref_name) != first_ref:
        raise ValueError("successor_ref_observation_raced")
    if first_ref == str(envelope["prepare_head"]):
        _assert_raw_lease(lease, before, "incumbent")
        return "prepare_before"
    if first_ref == str(envelope["successor_head"]):
        try:
            _assert_raw_lease(lease, after, "successor")
        except ValueError:
            _assert_raw_lease(lease, before, "incumbent")
            return "successor_before"
        return "successor_after"
    raise ValueError("successor_ref_state_invalid")


def hook_entry() -> None:
    """Validate the one envelope-bound reference transaction and rebind its Lease."""
    root = Path(os.environ["ETHOS_SUCCESSOR_ROOT"])
    _, envelope = _envelope_from_environment()
    phase = os.environ.get(_HOOK_PHASE_ENV, "")
    ref_name = os.environ.get(_HOOK_REF_ENV, "")
    old_value = os.environ.get(_HOOK_OLD_ENV, "")
    new_value = os.environ.get(_HOOK_NEW_ENV, "")
    expected = (
        str(envelope["ref_name"]),
        str(envelope["prepare_head"]),
        str(envelope["successor_head"]),
    )
    if (ref_name, old_value, new_value) != expected:
        raise ValueError("successor_ref_transition_mismatch")
    validate_transition(root, envelope)
    if phase == "committed":
        replace_lease(root, envelope)
        state = "successor_lease_rebound"
    elif phase == "prepared":
        state = "successor_ref_admitted"
    else:
        raise ValueError("successor_hook_phase_invalid")
    sys.stdout.write(json.dumps({"ok": True, "state": state}, sort_keys=True) + "\n")


def apply_from_environment() -> None:
    """Evaluate and advance the one successor transition without backward mutation."""
    root = Path(os.environ["ETHOS_SUCCESSOR_ROOT"]).resolve()
    _, envelope = _envelope_from_environment()
    prepare_head = str(envelope["prepare_head"])
    successor_head = str(envelope["successor_head"])
    _validate_static_transition(root, envelope)
    initial = _transition_state(root, envelope)
    evaluation = evaluate_successor(
        root,
        envelope,
        require_incumbent_lease=initial == "prepare_before",
    )
    state = _transition_state(root, envelope)
    if state == "prepare_before":
        moved = subprocess.run(
            ["git", "update-ref", str(envelope["ref_name"]), successor_head, prepare_head],
            cwd=root,
            env={**os.environ, "ETHOS_SUCCESSOR_ROOT": root.as_posix()},
            check=False,
            capture_output=True,
            text=True,
        )
        if moved.returncode:
            message = f"successor_ref_cas_failed:{moved.stderr.strip()}"
            raise ValueError(message)
        state = _transition_state(root, envelope)
    if state == "successor_before":
        replace_lease(root, envelope)
        state = _transition_state(root, envelope)
    if state != "successor_after":
        raise ValueError("successor_state_invalid")
    _materialize_successor_with_lease_lock(root, envelope)
    sys.stdout.write(
        json.dumps(
            {
                **evaluation,
                "state": (
                    "successor_cutover_complete"
                    if initial == "prepare_before"
                    else "successor_cutover_recovered"
                ),
            },
            sort_keys=True,
        )
        + "\n"
    )
