"""Deterministic Git-native set of canonical Attestation values."""

from __future__ import annotations

import tempfile
from pathlib import Path
from pathlib import PurePosixPath

from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.git import run_git
from ethos.contracts.semantic import Attestation

ATTESTATION_SET_REF = "refs/ethos/attestations-set"
_MEMBER_ROOT = "evidence/attestations"
_AUTHOR = "ETHOS Attestation Set <attestations@example.invalid> 0 +0000"
_COMMIT_MESSAGE = "ETHOS Attestation Set\n"
_MAX_CAS_ATTEMPTS = 16


def _attestation_member_path(identity: str) -> str:
    return f"{_MEMBER_ROOT}/{identity[:2]}/{identity}.json"


def _selected_root(repo: Path) -> str:
    repository = run_git(
        repo,
        "rev-parse",
        "--git-dir",
        check=False,
        observation=True,
    )
    if repository.returncode != 0:
        message = "attestation_set_repository_invalid"
        raise ValueError(message)
    symbolic = run_git(
        repo,
        "symbolic-ref",
        "--quiet",
        ATTESTATION_SET_REF,
        check=False,
        observation=True,
    )
    if symbolic.returncode == 0:
        message = "attestation_set_ref_symbolic"
        raise ValueError(message)
    if symbolic.returncode != 1:
        message = "attestation_set_ref_invalid"
        raise ValueError(message)
    existence = run_git(
        repo,
        "show-ref",
        "--exists",
        ATTESTATION_SET_REF,
        check=False,
        observation=True,
    )
    if existence.returncode == 2:
        return ""
    if existence.returncode != 0:
        message = "attestation_set_ref_invalid"
        raise ValueError(message)
    observed = run_git(
        repo,
        "show-ref",
        "--verify",
        "--hash",
        ATTESTATION_SET_REF,
        check=False,
        observation=True,
    )
    if observed.returncode == 0:
        return observed.stdout.strip()
    message = "attestation_set_ref_invalid"
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


def _batch_blobs(repo: Path, object_ids: tuple[str, ...]) -> tuple[bytes, ...]:
    result = run_git(
        repo,
        "cat-file",
        "--batch",
        stdin=b"".join(f"{object_id}\n".encode() for object_id in object_ids),
        text=False,
        check=False,
        observation=True,
    )
    if result.returncode != 0:
        message = "attestation_set_root_invalid"
        raise ValueError(message)
    payload, offset = result.stdout, 0
    blobs: list[bytes] = []
    try:
        for expected in object_ids:
            header_end = payload.index(b"\n", offset)
            object_id, kind, raw_size = payload[offset:header_end].decode().split(" ")
            size = int(raw_size)
            content_start, content_end = header_end + 1, header_end + 1 + size
            _require_entry(
                valid=(
                    object_id == expected
                    and kind == "blob"
                    and payload[content_end : content_end + 1] == b"\n"
                )
            )
            blobs.append(payload[content_start:content_end])
            offset = content_end + 1
    except (UnicodeError, ValueError) as error:
        message = "attestation_set_root_invalid"
        raise ValueError(message) from error
    _require_entry(valid=offset == len(payload))
    return tuple(blobs)


def _validated_members(repo: Path, root: str) -> tuple[dict[str, bytes], tuple[Attestation, ...]]:
    if not root:
        return {}, ()
    tree_result = run_git(
        repo,
        "rev-parse",
        f"{root}^{{commit}}^{{tree}}",
        check=False,
        observation=True,
    )
    if tree_result.returncode != 0:
        message = "attestation_set_root_invalid"
        raise ValueError(message)
    tree = tree_result.stdout.strip()
    if root != _root_identity(repo, tree, write=False):
        message = "attestation_set_root_invalid"
        raise ValueError(message)
    tree_paths: set[str] = set()
    files: list[tuple[str, str]] = []
    for mode, kind, object_id, path in _tree_entries(repo, root):
        if kind == "tree":
            _require_entry(valid=mode == "040000")
            tree_paths.add(path)
        else:
            _require_entry(valid=mode == "100644" and kind == "blob")
            files.append((object_id, path))
    members: dict[str, bytes] = {}
    attestations: list[Attestation] = []
    for (_object_id, path), raw in zip(
        files,
        _batch_blobs(repo, tuple(object_id for object_id, _path in files)),
        strict=True,
    ):
        try:
            attestation = Attestation.model_validate_json(raw)
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


def _write_tree(repo: Path, members: dict[str, bytes]) -> str:
    common = Path(git_common_dir(repo))
    with tempfile.NamedTemporaryFile(prefix="attestation-set-", dir=common, delete=False) as file:
        index = Path(file.name)
    index.unlink()
    environment = {"GIT_INDEX_FILE": index.as_posix()}
    try:
        for identity in sorted(members):
            blob = (
                run_git(
                    repo,
                    "hash-object",
                    "-w",
                    "--stdin",
                    stdin=members[identity],
                    text=False,
                )
                .stdout.decode()
                .strip()
            )
            run_git(
                repo,
                "update-index",
                "--add",
                "--cacheinfo",
                f"100644,{blob},{_attestation_member_path(identity)}",
                env=environment,
            )
        return run_git(repo, "write-tree", env=environment).stdout.strip()
    finally:
        index.unlink(missing_ok=True)


def _root_identity(repo: Path, tree: str, *, write: bool) -> str:
    payload = (
        f"tree {tree}\nauthor {_AUTHOR}\ncommitter {_AUTHOR}\nencoding UTF-8\n\n{_COMMIT_MESSAGE}"
    ).encode()
    arguments = ["hash-object", "-t", "commit"]
    if write:
        arguments.append("-w")
    arguments.append("--stdin")
    return (
        run_git(
            repo,
            *arguments,
            stdin=payload,
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
        union = current | incoming
        desired = _root_identity(repo, _write_tree(repo, union), write=True)
        if _compare_and_swap_root(repo, desired=desired, observed=observed):
            return {"root": desired, "added": added}
    message = "attestation_set_cas_retry_exhausted"
    raise ValueError(message)


def record_attestation_once(repo: Path, attestation: Attestation) -> Attestation:
    """Select exactly one Attestation for a predicate and subject."""
    for _attempt in range(_MAX_CAS_ATTEMPTS):
        observed = _selected_root(repo)
        current, members = _validated_members(repo, observed)
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
        union = current | incoming
        desired = _root_identity(repo, _write_tree(repo, union), write=True)
        if _compare_and_swap_root(repo, desired=desired, observed=observed):
            return attestation
    message = "attestation_set_cas_retry_exhausted"
    raise ValueError(message)
