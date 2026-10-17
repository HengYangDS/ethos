"""Deterministic Git-native set of canonical Attestation values."""

from __future__ import annotations

import hashlib
import subprocess
import tempfile
from contextlib import nullcontext
from pathlib import Path
from pathlib import PurePosixPath
from threading import Lock
from typing import TYPE_CHECKING
from typing import Final

from cachetools import LRUCache

from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.repo.attestation_lifetime import ended
from ethos.adapters.repo.attestation_lifetime import lifetime
from ethos.adapters.repo.attestation_lifetime_facts import UNOBSERVABLE_FACTS
from ethos.adapters.repo.attestation_lifetime_facts import observe_lifetime_facts
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_object import read_objects
from ethos.adapters.store.custody import binds_custody
from ethos.adapters.store.custody import custody_digests
from ethos.adapters.store.custody import custody_lock
from ethos.adapters.store.custody import release_custody
from ethos.adapters.store.custody import require_custody
from ethos.adapters.store.custody import store_custody
from ethos.adapters.store.custody import stored_custody
from ethos.contracts.semantic import Attestation

if TYPE_CHECKING:
    from collections.abc import Iterable
    from contextlib import AbstractContextManager

ATTESTATION_SET_REF = "refs/ethos/attestations-set"
_MEMBER_ROOT = "evidence/attestations"
_AUTHOR = "ETHOS Attestation Set <attestations@example.invalid> 0 +0000"
_COMMIT_MESSAGE = "ETHOS Attestation Set\n"
_MAX_CAS_ATTEMPTS = 16
# A member is a claim; file bytes belong to custody evidence bound by digest.
MEMBER_BYTES_LIMIT: Final = 1024 * 1024
# Retained validated members by serialized size; the 2026-10-15 selected set holds 560 MiB.
_MEMBER_REUSE_BYTES = 1024 * 1024 * 1024


class MemberReuse:
    """Reuse pure member validation by immutable Git blob id, never membership or authority."""

    def __init__(self, capacity: int) -> None:
        self._members: LRUCache[str, tuple[int, Attestation]] = LRUCache(
            maxsize=capacity, getsizeof=lambda value: value[0]
        )
        self._lock = Lock()

    def known(self, object_ids: Iterable[str]) -> dict[str, Attestation]:
        """Return members already validated from exactly these blob ids."""
        with self._lock:
            return {
                object_id: self._members[object_id][1]
                for object_id in object_ids
                if object_id in self._members
            }

    def remember(self, object_id: str, size: int, attestation: Attestation) -> None:
        """Retain one validated member while its serialized size fits the bound."""
        if size <= self._members.maxsize:
            with self._lock:
                self._members[object_id] = (size, attestation)


_member_reuse = MemberReuse(_MEMBER_REUSE_BYTES)


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


def _validated_members(repo: Path, root: str) -> tuple[dict[str, str], tuple[Attestation, ...]]:
    """Map member identities to blob ids, reading only members not yet validated."""
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
    known = _member_reuse.known(object_id for object_id, _path in files)
    unread = tuple(dict.fromkeys(object_id for object_id, _path in files if object_id not in known))
    raw_root, *raw_members = read_objects(
        repo,
        (root, *unread),
        kind=("commit", *("blob" for _ in unread)),
        gap="attestation_set_root_invalid",
    )
    tree_bytes = raw_root[5 : 5 + len(root)]
    _require_entry(
        valid=len(tree_bytes) == len(root) and not set(tree_bytes) - set(b"0123456789abcdef")
    )
    tree = tree_bytes.decode("ascii")
    _require_entry(valid=raw_root == _root_payload(tree))
    raw_by_id = dict(zip(unread, raw_members, strict=True))
    members: dict[str, str] = {}
    attestations: list[Attestation] = []
    for object_id, path in files:
        attestation = known.get(object_id)
        if attestation is None:
            raw = raw_by_id[object_id]
            try:
                attestation = Attestation.model_validate_json(raw)
            except ValueError as error:
                message = f"attestation_set_member_invalid:{path}"
                raise ValueError(message) from error
            known[object_id] = attestation
            _member_reuse.remember(object_id, len(raw), attestation)
        _require_entry(valid=path == _attestation_member_path(attestation.id))
        members[attestation.id] = object_id
        attestations.append(attestation)
    _require_entry(valid=tree_paths == _member_tree_paths(members))
    return members, tuple(attestations)


def _blob_id(raw: bytes, *, like: str) -> str:
    """Return the Git blob id of exact bytes in the object format of an observed id."""
    digest = hashlib.new({40: "sha1", 64: "sha256"}[len(like)], usedforsecurity=False)
    digest.update(b"blob %d\0" % len(raw))
    digest.update(raw)
    return digest.hexdigest()


def _require_entry(*, valid: bool) -> None:
    if not valid:
        message = "attestation_set_root_invalid"
        raise ValueError(message)


def _member_tree_paths(identities: Iterable[str]) -> set[str]:
    return {
        parent.as_posix()
        for identity in identities
        for parent in PurePosixPath(_attestation_member_path(identity)).parents
        if parent.as_posix() != "."
    }


def _canonical_inputs(attestations: tuple[Attestation, ...]) -> dict[str, bytes]:
    members: dict[str, bytes] = {}
    for attestation in attestations:
        custody_digests(attestation)
        raw = attestation.canonical_json().encode()
        if previous := members.get(attestation.id):
            if previous != raw:
                message = f"attestation_set_identity_collision:{attestation.id}"
                raise ValueError(message)
        else:
            members[attestation.id] = raw
    return members


def _require_bounded(incoming: dict[str, bytes], identities: Iterable[str]) -> None:
    """Refuse oversized members among those being added; replaying a member stays a no-op."""
    for identity in identities:
        if len(incoming[identity]) > MEMBER_BYTES_LIMIT:
            message = f"attestation_member_too_large:{identity}"
            raise ValueError(message)


def _require_known_bytes(incoming: dict[str, bytes], current: dict[str, str]) -> None:
    for identity, raw in incoming.items():
        if identity in current and current[identity] != _blob_id(raw, like=current[identity]):
            message = f"attestation_set_identity_collision:{identity}"
            raise ValueError(message)


def _write_tree(
    repo: Path,
    members: dict[str, bytes],
    *,
    observed: str = "",
    removed: tuple[str, ...] = (),
) -> str:
    """Change an observed tree through one native batch and an isolated index."""
    common = Path(git_common_dir(repo))
    with tempfile.TemporaryDirectory(prefix="attestation-set-", dir=common) as directory:
        staging = Path(directory)
        environment = {"GIT_INDEX_FILE": (staging / "index").as_posix()}
        if observed:
            run_git(repo, "read-tree", observed, env=environment)
        if removed:
            run_git(
                repo,
                "update-index",
                "-z",
                "--force-remove",
                "--stdin",
                stdin="".join(f"{_attestation_member_path(identity)}\0" for identity in removed),
                env=environment,
            )
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


def _ended_members(
    repo: Path, members: tuple[Attestation, ...], recorded: Iterable[str]
) -> tuple[frozenset[str], str]:
    """Return the members an update removes, or none and the gap when facts are unobservable."""
    try:
        facts = observe_lifetime_facts(repo, members)
    except (OSError, subprocess.SubprocessError, ProcessExecutionError) as error:
        return frozenset(), str(error)
    except ValueError as error:
        if str(error) not in UNOBSERVABLE_FACTS:
            raise
        return frozenset(), str(error)
    return ended(members, facts) - frozenset(recorded), ""


def _custody_guard(
    repo: Path, members: Iterable[Attestation], custody: tuple[bytes, ...]
) -> AbstractContextManager[object]:
    """Hold custody across a swap that stores, binds or may delete custody bytes."""
    if custody or any(binds_custody(member) for member in members) or stored_custody(repo):
        return custody_lock(repo)
    return nullcontext()


def _require_bound_custody(repo: Path, attestations: tuple[Attestation, ...]) -> None:
    """Under the custody lock, every digest a recorded member binds still has its bytes."""
    require_custody(
        repo, sorted({digest for item in attestations for digest in custody_digests(item)})
    )


def _release_unbound_custody(
    repo: Path,
    members: tuple[Attestation, ...],
    removed: frozenset[str],
    recorded: tuple[Attestation, ...] = (),
) -> tuple[tuple[str, ...], str]:
    """Under the lock, delete stored bytes the new set no longer binds; report, never raise.

    The swap has already happened, so a failure here must not read as a failed update. Bytes a
    failed earlier cleanup left behind are unbound too, so the next locked swap removes them.
    """
    try:
        bound = {
            digest
            for member in (*members, *recorded)
            if member.id not in removed
            for digest in custody_digests(member)
        }
        return release_custody(repo, sorted(stored_custody(repo) - bound)), ""
    except (OSError, ValueError) as error:
        return (), str(error)


def read_attestation_set(repo: Path) -> tuple[str, tuple[Attestation, ...]]:
    """Read and validate the selected immutable Attestation set."""
    root = _selected_root(repo)
    members, attestations = _validated_members(repo, root)
    by_identity = {attestation.id: attestation for attestation in attestations}
    return root, tuple(by_identity[key] for key in sorted(members))


def record_attestations(
    repo: Path,
    attestations: tuple[Attestation, ...],
    *,
    custody: tuple[bytes, ...] = (),
) -> dict[str, object]:
    """Exact-CAS union canonical Attestations into the sole selected set.

    The update removes the members whose lifetime ended, never the members it records, and
    stores the custody bytes its members bind under the lock that deletions hold.
    """
    incoming = _canonical_inputs(attestations)
    for _attempt in range(_MAX_CAS_ATTEMPTS):
        observed = _selected_root(repo)
        current, members = _validated_members(repo, observed)
        _require_known_bytes(incoming, current)
        added = tuple(sorted(incoming.keys() - current.keys()))
        if not added:
            return {"root": observed, "previous_root": observed, "added": (), "removed": ()}
        _require_bounded(incoming, added)
        finished, lifetime_gap = _ended_members(repo, members, incoming)
        new_members = {identity: incoming[identity] for identity in added}
        tree = _write_tree(repo, new_members, observed=observed, removed=tuple(sorted(finished)))
        desired = _root_identity(repo, tree)
        removed = tuple(member for member in members if member.id in finished)
        with _custody_guard(repo, (*removed, *attestations), custody):
            for payload in custody:
                store_custody(repo, payload)
            _require_bound_custody(repo, attestations)
            if not _compare_and_swap_root(repo, desired=desired, observed=observed):
                continue
            _released, custody_gap = _release_unbound_custody(repo, members, finished, attestations)
        gaps = {"lifetime_gap": lifetime_gap, "custody_gap": custody_gap}
        return {
            "root": desired,
            "previous_root": observed,
            "added": added,
            "removed": tuple(sorted(finished)),
            **{key: value for key, value in gaps.items() if value},
        }
    _release_failed_custody(repo, custody)
    message = "attestation_set_cas_retry_exhausted"
    raise ValueError(message)


def _release_failed_custody(repo: Path, custody: tuple[bytes, ...]) -> None:
    """Delete bytes a failed update stored that no selected member binds; keep any bound ones."""
    if not custody:
        return
    stored = {hashlib.sha256(payload).hexdigest() for payload in custody}
    with custody_lock(repo):
        _root, members = read_attestation_set(repo)
        bound = {digest for member in members for digest in custody_digests(member)}
        release_custody(repo, sorted(stored - bound))


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
        _require_bounded(incoming, incoming)
        finished, _lifetime_gap = _ended_members(repo, members, incoming)
        tree = _write_tree(repo, incoming, observed=observed, removed=tuple(sorted(finished)))
        desired = _root_identity(repo, tree)
        removed = tuple(member for member in members if member.id in finished)
        with _custody_guard(repo, (*removed, attestation), ()):
            _require_bound_custody(repo, (attestation,))
            if not _compare_and_swap_root(repo, desired=desired, observed=observed):
                continue
            _release_unbound_custody(repo, members, finished, (attestation,))
        return attestation
    message = "attestation_set_cas_retry_exhausted"
    raise ValueError(message)


def release_attestation(
    repo: Path, identity: str, *, actor: str, review: str = "", apply: bool = True
) -> dict[str, object]:
    """Exact-CAS remove one open-predicate member and the custody bytes it alone bound.

    The member's verifier may release it; another actor needs a non-blank review reason.
    """
    for _attempt in range(_MAX_CAS_ATTEMPTS):
        observed = _selected_root(repo)
        _current, members = _validated_members(repo, observed)
        target = next((member for member in members if member.id == identity), None)
        if target is None:
            message = f"attestation_release_member_absent:{identity}"
            raise ValueError(message)
        if lifetime(target)[0] != "open-predicate":
            message = f"attestation_release_product_lifetime:{identity}"
            raise ValueError(message)
        if actor != target.verifier and not review.strip():
            message = "attestation_release_actor_unadmitted"
            raise ValueError(message)
        if not apply:
            return {"previous_root": observed, "root": observed, "released": identity}
        tree = _write_tree(repo, {}, observed=observed, removed=(identity,))
        desired = _root_identity(repo, tree)
        with _custody_guard(repo, (target,), ()):
            if not _compare_and_swap_root(repo, desired=desired, observed=observed):
                continue
            released, custody_gap = _release_unbound_custody(repo, members, frozenset({identity}))
        return {
            "previous_root": observed,
            "root": desired,
            "released": identity,
            "custody_deleted": released,
            **({"custody_gap": custody_gap} if custody_gap else {}),
        }
    message = "attestation_set_cas_retry_exhausted"
    raise ValueError(message)
