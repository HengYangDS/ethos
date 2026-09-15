"""Validate and materialize bounded Git history attribution/signature repairs."""

from __future__ import annotations

import hashlib
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import TypedDict

from ethos.adapters.repo.commit.creation import configured_signer_fingerprint
from ethos.adapters.repo.commit.creation import create_signed_payload
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_object import read_objects
from ethos.adapters.repo.git_object import unsigned_commit_payload
from ethos.adapters.repo.trust_anchor.verification import verify_commit_trust
from ethos.adapters.repo.trust_anchor.verification import verify_git_object_trust


class PreparedHistoryRepair(TypedDict):
    """Verified replacement tip and exact original-to-replacement object relation."""

    replacement: str
    mapping: dict[str, str]


def _require(condition: object, gap: str) -> None:
    if not condition:
        raise ValueError(gap)


def _headers(payload: bytes) -> tuple[list[bytes], bytes]:
    header, separator, message = payload.partition(b"\n\n")
    _require(separator, "history_repair_payload_unavailable")
    blocks: list[bytes] = []
    for line in header.split(b"\n"):
        if line.startswith(b" "):
            _require(blocks, "history_repair_header_invalid")
            blocks[-1] += b"\n" + line
        else:
            blocks.append(line)
    for key in (b"tree", b"author", b"committer"):
        _require(
            sum(block.startswith(key + b" ") for block in blocks) == 1,
            "history_repair_header_invalid",
        )
    return blocks, message


def _parents(payload: bytes) -> tuple[str, ...]:
    return tuple(
        block.split(b" ", 1)[1].decode("ascii")
        for block in _headers(payload)[0]
        if block.startswith(b"parent ")
    )


def _identity(block: bytes) -> tuple[dict[str, str], bytes]:
    identity, separator, timestamp = block.split(b" ", 1)[1].rpartition(b"> ")
    name, opening, email = identity.rpartition(b" <")
    _require(separator and opening, "history_repair_identity_invalid")
    return {"name": name.decode("utf-8"), "email": email.decode("utf-8")}, timestamp


def _correction(value: object) -> Mapping[str, object]:
    _require(isinstance(value, Mapping) and value, "history_repair_correction_invalid")
    assert isinstance(value, Mapping)
    _require(
        not set(value) - {"author", "committer", "resign"}, "history_repair_correction_invalid"
    )
    if "resign" in value:
        _require(value["resign"] is True, "history_repair_correction_invalid")
    for role in ("author", "committer"):
        if role not in value:
            continue
        pair = value[role]
        _require(
            isinstance(pair, Mapping) and set(pair) == {"expected", "replacement"},
            "history_repair_correction_invalid",
        )
        assert isinstance(pair, Mapping)
        for item in pair.values():
            _require(
                isinstance(item, Mapping)
                and set(item) == {"name", "email"}
                and all(
                    isinstance(text, str)
                    and text.strip() == text
                    and text
                    and not any(char in text for char in "\r\n\x00<>")
                    for text in item.values()
                ),
                "history_repair_correction_invalid",
            )
    return value


def replacement_payload(
    payload: bytes, *, parents: tuple[str, ...], correction: Mapping[str, object] | None
) -> bytes:
    """Allow only explicit attribution fields and position-preserving parent replacement."""
    blocks, message = _headers(payload)
    _require(len(parents) == len(_parents(payload)), "history_repair_parent_count_changed")
    parent_values = iter(parents)
    selected = _correction(correction) if correction is not None else {}
    output = []
    for original in blocks:
        block = original
        key = block.split(b" ", 1)[0].decode("ascii")
        if key == "parent":
            block = b"parent " + next(parent_values).encode("ascii")
        elif key in {"author", "committer"} and key in selected:
            actual, timestamp = _identity(block)
            pair = selected[key]
            assert isinstance(pair, Mapping)
            _require(actual == pair["expected"], "history_repair_expected_identity_mismatch")
            new = pair["replacement"]
            assert isinstance(new, Mapping)
            block = f"{key} {new['name']} <{new['email']}> ".encode() + timestamp
        output.append(block)
    return b"\n".join(output) + b"\n\n" + message


def history_repair_scope(
    root: Path, old: str, *, corrections: Mapping[str, object]
) -> tuple[str, ...]:
    """Derive an exact affected DAG from existing objects without creating any object."""
    _require(corrections, "history_repair_selection_required")
    ordered = tuple(run_git(root, "rev-list", "--reverse", "--topo-order", old).stdout.splitlines())
    _require(set(corrections) <= set(ordered), "history_repair_selection_not_reachable")
    payloads = read_objects(root, ordered, kind="commit")
    affected: set[str] = set()
    for oid, raw in zip(ordered, payloads, strict=True):
        payload = unsigned_commit_payload(raw)
        parents = _parents(payload)
        inherited = any(parent in affected for parent in parents)
        if oid in corrections:
            selected = _correction(corrections[oid])
            replacement = replacement_payload(payload, parents=parents, correction=selected)
            if replacement == payload and not inherited:
                _require(selected.get("resign") is True, "history_repair_no_effect")
                trust = verify_git_object_trust(root, oid, "commit")
                _require(
                    trust["verdict"] != "pass"
                    or trust.get("fingerprint") != configured_signer_fingerprint(root),
                    "history_repair_no_effect",
                )
        if oid in corrections or inherited:
            affected.add(oid)
    return tuple(oid for oid in ordered if oid in affected)


def prepare_history_repair(
    root: Path, old: str, *, corrections: Mapping[str, object], recover: bool = False
) -> PreparedHistoryRepair:
    """Create a verified replacement DAG without moving local or remote refs."""
    affected = history_repair_scope(root, old, corrections=corrections)
    mapping: dict[str, str] = {}
    payloads = read_objects(root, affected, kind="commit")
    existing = _existing_signed_payloads(root) if recover else {}
    for oid, raw in zip(affected, payloads, strict=True):
        payload = unsigned_commit_payload(raw)
        replacement = replacement_payload(
            payload,
            parents=tuple(mapping.get(parent, parent) for parent in _parents(payload)),
            correction=_correction(corrections[oid]) if oid in corrections else None,
        )
        matches = [
            revision
            for revision in existing.get(replacement, ())
            if verify_commit_trust(root, revision)["verdict"] == "pass"
        ]
        _require(len(matches) <= 1, "history_repair_recovery_ambiguous")
        mapping[oid] = matches[0] if matches else create_signed_payload(root, replacement)
    replacement = mapping[old]
    observed = validate_history_repair(root, old, replacement, corrections=corrections)
    _require(observed == mapping, "history_repair_mapping_mismatch")
    return {"replacement": replacement, "mapping": mapping}


def _existing_signed_payloads(root: Path) -> dict[bytes, list[str]]:
    """Recover immutable signed objects, including those created before a lost ACK."""
    inventory = run_git(
        root,
        "cat-file",
        "--batch-all-objects",
        "--unordered",
        "--batch-check=%(objectname) %(objecttype)",
        timeout=120,
    )
    commits = tuple(
        line.split()[0] for line in inventory.stdout.splitlines() if line.endswith(" commit")
    )
    existing: dict[bytes, list[str]] = {}
    for oid, raw in zip(commits, read_objects(root, commits, kind="commit"), strict=True):
        payload = unsigned_commit_payload(raw)
        if payload and payload != raw:
            existing.setdefault(payload, []).append(oid)
    return existing


def validate_history_repair(
    root: Path, old: str, new: str, *, corrections: Mapping[str, object]
) -> dict[str, str]:
    """Reconstruct and verify the replacement relation from actual DAGs, not a claimed map."""
    affected = set(history_repair_scope(root, old, corrections=corrections))
    ordered = tuple(run_git(root, "rev-list", new, old).stdout.splitlines())
    payloads = {
        oid: unsigned_commit_payload(raw)
        for oid, raw in zip(ordered, read_objects(root, ordered, kind="commit"), strict=True)
    }
    mapping: dict[str, str] = {}
    inverse: dict[str, str] = {}
    pending = [(old, new)]
    while pending:
        previous, current = pending.pop()
        if previous not in affected:
            _require(previous == current, "history_repair_unselected_object_changed")
            continue
        _require(previous != current, "history_repair_selected_object_unchanged")
        if previous in mapping:
            _require(mapping[previous] == current, "history_repair_mapping_ambiguous")
            continue
        _require(
            current not in inverse or inverse[current] == previous,
            "history_repair_mapping_not_bijective",
        )
        payload, actual = payloads[previous], payloads[current]
        parents, replacements = _parents(payload), _parents(actual)
        _require(len(parents) == len(replacements), "history_repair_parent_count_changed")
        expected = replacement_payload(
            payload,
            parents=replacements,
            correction=_correction(corrections[previous]) if previous in corrections else None,
        )
        _require(actual == expected, "history_repair_payload_changed")
        mapping[previous], inverse[current] = current, previous
        pending.extend(zip(parents, replacements, strict=True))
    _require(set(mapping) == affected, "history_repair_mapping_incomplete")
    trust = verify_commit_trust(root, tuple(mapping.values()))
    _require(trust["verdict"] == "pass", "history_repair_signature_untrusted")
    return mapping


def history_repair_coordinates(
    root: Path, old: str, *, corrections: Mapping[str, object], reason: str, backup: Path
) -> dict[str, object]:
    """Bind explicit repair intent to a native verified original-object bundle."""
    _require(reason.strip(), "history_repair_reason_required")
    _require(
        backup.is_absolute() and backup.is_file() and not backup.is_symlink(),
        "history_repair_backup_required",
    )
    _require(backup.resolve() == backup, "history_repair_backup_path_invalid")
    data = backup.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    header, separator, _pack = data.partition(b"\n\n")
    _require(
        separator and not any(line.startswith(b"-") for line in header.splitlines()),
        "history_repair_backup_not_self_contained",
    )
    verified = run_git(root, "bundle", "verify", str(backup), check=False)
    _require(verified.returncode == 0, "history_repair_backup_invalid")
    heads = run_git(root, "bundle", "list-heads", str(backup)).stdout.splitlines()
    _require(
        any(line.split(" ", 1)[0] == old for line in heads), "history_repair_backup_missing_head"
    )
    _verify_backup_recovery(root, old, backup)
    _require(
        hashlib.sha256(backup.read_bytes()).hexdigest() == digest, "history_repair_backup_changed"
    )
    affected = history_repair_scope(root, old, corrections=corrections)
    return {
        "corrections": dict(corrections),
        "reason": reason,
        "backup": {"path": str(backup), "sha256": digest},
        "affected_count": len(affected),
    }


def _verify_backup_recovery(root: Path, old: str, backup: Path) -> None:
    """Restore and validate the complete object closure without repository alternates."""
    object_format = run_git(root, "rev-parse", "--show-object-format").stdout.strip()
    with tempfile.TemporaryDirectory(
        prefix="ethos-history-restore-", dir=git_common_dir(root)
    ) as temporary:
        recovery = Path(temporary)
        for command in (
            ("init", "--bare", "--template=", f"--object-format={object_format}"),
            ("bundle", "unbundle", str(backup)),
            ("fsck", "--full", "--no-dangling", old),
        ):
            restored = run_git(recovery, *command, check=False, timeout=120)
            _require(restored.returncode == 0, "history_repair_backup_not_recoverable")
