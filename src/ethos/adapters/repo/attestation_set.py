"""Deterministic Git-native set of canonical Attestation values."""

from __future__ import annotations

import tempfile
from pathlib import Path
from pathlib import PurePosixPath
from threading import Condition
from typing import TYPE_CHECKING
from typing import Protocol
from typing import cast

from cachetools import LRUCache
from cachetools import cached

from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_object import read_objects
from ethos.contracts.semantic import Attestation

if TYPE_CHECKING:
    from collections.abc import Mapping

ATTESTATION_SET_REF = "refs/ethos/attestations-set"
_MEMBER_ROOT = "evidence/attestations"
_AUTHOR = "ETHOS Attestation Set <attestations@example.invalid> 0 +0000"
_COMMIT_MESSAGE = "ETHOS Attestation Set\n"
_MAX_CAS_ATTEMPTS = 16
# Retained serialized input; the 2026-10-13 selected set already holds 280 MiB.
_MEMBER_REUSE_BYTES = 512 * 1024 * 1024


class _MemberValidator(Protocol):
    """The cached validator's native byte-keyed lookup and synchronization contract."""

    cache: Mapping[bytes, tuple[bytes, Attestation]]
    cache_lock: Condition

    def __call__(self, raw: bytes) -> tuple[bytes, Attestation]: ...


def member_validator(capacity: int) -> _MemberValidator:
    """Bound pure canonical member validation reuse by retained serialized bytes."""

    @cached(
        cache=LRUCache(maxsize=capacity, getsizeof=lambda value: len(value[0])),
        key=lambda raw: raw,
        condition=Condition(),
    )
    def validate(raw: bytes) -> tuple[bytes, Attestation]:
        """Reuse pure canonical validation, never membership or current authority."""
        return raw, Attestation.model_validate_json(raw)

    return cast("_MemberValidator", validate)


_validated_member = member_validator(_MEMBER_REUSE_BYTES)


def _attestation_member_path(identity: str) -> str:
    return f"{_MEMBER_ROOT}/{identity[:2]}/{identity}.json"


def _selected_root(repo: Path) -> str:
    observed = run_git(
        repo,
        "for-each-ref",
        "--format=%(refname)%00%(objectname)%00%(symref)",
        ATTESTATION_SET_REF,
        check=False,
        observation=True,
    )
    if observed.returncode:
        repository = run_git(repo, "rev-parse", "--git-dir", check=False, observation=True)
        message = (
            "attestation_set_repository_invalid"
            if repository.returncode
            else "attestation_set_ref_invalid"
        )
        raise ValueError(message)
    message = "attestation_set_ref_invalid"
    if observed.stderr:
        raise ValueError(message)
    try:
        selected = [
            (identity, symbolic)
            for row in observed.stdout.splitlines()
            for name, identity, symbolic in (row.split("\0"),)
            if name == ATTESTATION_SET_REF
        ]
    except ValueError as error:
        raise ValueError(message) from error
    if len(selected) == 1:
        identity, symbolic = selected[0]
        if symbolic:
            message = "attestation_set_ref_symbolic"
            raise ValueError(message)
        if len(identity) not in {40, 64} or set(identity) - set("0123456789abcdef"):
            raise ValueError(message)
        return identity
    if selected:
        raise ValueError(message)
    existence = run_git(
        repo, "show-ref", "--exists", ATTESTATION_SET_REF, check=False, observation=True
    )
    if existence.returncode == 2:
        return ""
    symbolic = run_git(
        repo, "symbolic-ref", "--quiet", ATTESTATION_SET_REF, check=False, observation=True
    )
    if existence.returncode == 0 and symbolic.returncode == 0:
        message = "attestation_set_ref_symbolic"
    raise ValueError(message)


def _tree_entries(repo: Path, root: str) -> tuple[tuple[str, str, str, str], ...]:
    listed_result = run_git(
        repo,
        "ls-tree",
        "-r",
        "-t",
        "-z",
        root,
        text=False,
        check=False,
        observation=True,
    )
    if listed_result.returncode != 0:
        message = "attestation_set_root_invalid"
        raise ValueError(message)
    listed = listed_result.stdout
    entries: list[tuple[str, str, str, str]] = []
    paths: set[bytes] = set()
    try:
        for record in (item for item in listed.split(b"\0") if item):
            metadata, raw_path = record.split(b"\t", maxsplit=1)
            _require_entry(valid=raw_path not in paths)
            paths.add(raw_path)
            mode, kind, object_id = metadata.decode().split(" ", maxsplit=2)
            entries.append((mode, kind, object_id, raw_path.decode()))
    except (UnicodeError, ValueError) as error:
        message = "attestation_set_root_invalid"
        raise ValueError(message) from error
    return tuple(entries)


def _validated_members(repo: Path, root: str) -> tuple[dict[str, bytes], tuple[Attestation, ...]]:
    if not root:
        return {}, ()
    tree_paths: set[str] = set()
    files: list[tuple[str, str]] = []
    for mode, kind, object_id, path in _tree_entries(repo, root):
        if kind == "tree":
            _require_entry(valid=mode == "040000")
            tree_paths.add(path)
        else:
            _require_entry(valid=mode == "100644" and kind == "blob")
            files.append((object_id, path))
    raw_root, *raw_members = read_objects(
        repo,
        (root, *(object_id for object_id, _path in files)),
        kind=("commit", *("blob" for _ in files)),
        gap="attestation_set_root_invalid",
    )
    tree_bytes = raw_root[5 : 5 + len(root)]
    _require_entry(
        valid=len(tree_bytes) == len(root) and not set(tree_bytes) - set(b"0123456789abcdef")
    )
    tree = tree_bytes.decode("ascii")
    _require_entry(valid=raw_root == _root_payload(tree))
    # Read retained current bytes before admitting misses can evict them.
    with _validated_member.cache_lock:
        retained = {
            raw: _validated_member.cache[raw]
            for raw in raw_members
            if raw in _validated_member.cache
        }
    members: dict[str, bytes] = {}
    attestations: list[Attestation] = []
    for (_object_id, path), raw in zip(files, raw_members, strict=True):
        try:
            _, attestation = retained[raw] if raw in retained else _validated_member(raw)
        except ValueError as error:
            message = f"attestation_set_member_invalid:{path}"
            raise ValueError(message) from error
        _require_entry(valid=path == _attestation_member_path(attestation.id))
        members[attestation.id] = raw
        attestations.append(attestation)
    _require_entry(valid=tree_paths == _member_tree_paths(members))
    return members, tuple(attestations)


def _require_entry(*, valid: bool) -> None:
    if not valid:
        message = "attestation_set_root_invalid"
        raise ValueError(message)


def _member_tree_paths(members: dict[str, bytes]) -> set[str]:
    return {
        parent.as_posix()
        for identity in members
        for parent in PurePosixPath(_attestation_member_path(identity)).parents
        if parent.as_posix() != "."
    }


def _canonical_inputs(attestations: tuple[Attestation, ...]) -> dict[str, bytes]:
    members: dict[str, bytes] = {}
    for attestation in attestations:
        raw = attestation.canonical_json().encode()
        if previous := members.get(attestation.id):
            if previous != raw:
                message = f"attestation_set_identity_collision:{attestation.id}"
                raise ValueError(message)
        else:
            members[attestation.id] = raw
    return members


def _write_tree(repo: Path, members: dict[str, bytes], *, observed: str = "") -> str:
    """Extend an observed tree through one native batch and an isolated index."""
    common = Path(git_common_dir(repo))
    with tempfile.TemporaryDirectory(prefix="attestation-set-", dir=common) as directory:
        staging = Path(directory)
        environment = {"GIT_INDEX_FILE": (staging / "index").as_posix()}
        if observed:
            run_git(repo, "read-tree", observed, env=environment)
        identities = sorted(members)
        paths: list[str] = []
        for identity in identities:
            member = staging / identity
            member.write_bytes(members[identity])
            paths.append(member.relative_to(common).as_posix())
        blobs = run_git(
            common,
            "hash-object",
            "-w",
            "--no-filters",
            "--stdin-paths",
            stdin="".join(f"{path}\n" for path in paths),
        ).stdout.splitlines()
        entries = "".join(
            f"100644 {blob}\t{_attestation_member_path(identity)}\0"
            for identity, blob in zip(identities, blobs, strict=True)
        )
        run_git(repo, "update-index", "-z", "--index-info", stdin=entries, env=environment)
        return run_git(repo, "write-tree", env=environment).stdout.strip()


def _root_payload(tree: str) -> bytes:
    """Own the exact canonical root bytes for both reading and writing."""
    return (
        f"tree {tree}\nauthor {_AUTHOR}\ncommitter {_AUTHOR}\nencoding UTF-8\n\n{_COMMIT_MESSAGE}"
    ).encode()


def _root_identity(repo: Path, tree: str) -> str:
    return (
        run_git(
            repo,
            "hash-object",
            "-t",
            "commit",
            "-w",
            "--stdin",
            stdin=_root_payload(tree),
            text=False,
        )
        .stdout.decode()
        .strip()
    )


def _zero_object_id(repo: Path) -> str:
    object_format = run_git(
        repo, "rev-parse", "--show-object-format", observation=True
    ).stdout.strip()
    return "0" * (64 if object_format == "sha256" else 40)


def _compare_and_swap_root(repo: Path, *, desired: str, observed: str) -> bool:
    return (
        run_git(
            repo,
            "update-ref",
            "--no-deref",
            ATTESTATION_SET_REF,
            desired,
            observed or _zero_object_id(repo),
            check=False,
        ).returncode
        == 0
    )


def read_attestation_set(repo: Path) -> tuple[str, tuple[Attestation, ...]]:
    """Read and validate the selected immutable Attestation set."""
    root = _selected_root(repo)
    members, attestations = _validated_members(repo, root)
    by_identity = {attestation.id: attestation for attestation in attestations}
    return root, tuple(by_identity[key] for key in sorted(members))


def record_attestations(
    repo: Path,
    attestations: tuple[Attestation, ...],
) -> dict[str, object]:
    """Exact-CAS union canonical Attestations into the sole selected set."""
    incoming = _canonical_inputs(attestations)
    for _attempt in range(_MAX_CAS_ATTEMPTS):
        observed = _selected_root(repo)
        current, _attestations = _validated_members(repo, observed)
        for identity, raw in incoming.items():
            if identity in current and current[identity] != raw:
                message = f"attestation_set_identity_collision:{identity}"
                raise ValueError(message)
        added = tuple(sorted(incoming.keys() - current.keys()))
        if not added:
            return {"root": observed, "added": ()}
        new_members = {identity: incoming[identity] for identity in added}
        desired = _root_identity(repo, _write_tree(repo, new_members, observed=observed))
        if _compare_and_swap_root(repo, desired=desired, observed=observed):
            return {"root": desired, "added": added}
    message = "attestation_set_cas_retry_exhausted"
    raise ValueError(message)


def record_attestation_once(repo: Path, attestation: Attestation) -> Attestation:
    """Select exactly one Attestation for a predicate and subject."""
    for _attempt in range(_MAX_CAS_ATTEMPTS):
        observed = _selected_root(repo)
        _current, members = _validated_members(repo, observed)
        matches = tuple(
            item
            for item in members
            if item.predicate == attestation.predicate and item.subject == attestation.subject
        )
        if len(matches) > 1:
            message = "attestation_set_semantic_collision"
            raise ValueError(message)
        if matches:
            return matches[0]
        incoming = _canonical_inputs((attestation,))
        desired = _root_identity(repo, _write_tree(repo, incoming, observed=observed))
        if _compare_and_swap_root(repo, desired=desired, observed=observed):
            return attestation
    message = "attestation_set_cas_retry_exhausted"
    raise ValueError(message)
