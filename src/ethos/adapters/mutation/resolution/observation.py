"""Exact Git, Chronicle, and worktree-registration observation."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
from dataclasses import asdict
from dataclasses import dataclass
from pathlib import Path
from pathlib import PurePosixPath
from typing import Literal
from typing import NoReturn

import ethos.adapters.mutation.resolution.records.io.posix as posix
from ethos.adapters.mutation.resolution.capture import digest_untracked_inventory
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.contracts.resolution.lane import LaneObservation

_POINTER_LIMIT = 16 * 1024
_REGISTRATION_FLAGS = {b"detached", b"bare", b"locked", b"prunable"}
_WORKTREE_FIELDS = _REGISTRATION_FLAGS | {b"worktree", b"HEAD", b"branch"}
_REGISTRATION_PREFIX = "git-worktree-registration:v1:"
_DIFF_FLAGS = ("--no-ext-diff", "--no-textconv", "--binary")


class OwnerlessGitObservationError(ValueError):
    """Classified fail-closed native Git observation error."""

    def __init__(self, kind: str, detail: str) -> None:
        super().__init__(f"{kind}:{detail}")
        self.kind = kind
        self.detail = detail


@dataclass(frozen=True, slots=True)
class DescriptorIdentity:
    """Exact descriptor identity including content-version metadata."""

    device: int
    inode: int
    mode: int
    size: int
    mtime_ns: int
    ctime_ns: int


@dataclass(frozen=True, slots=True)
class ExactFileSnapshot:
    """Exact file bytes and the descriptor identity that supplied them."""

    raw: bytes
    identity: DescriptorIdentity


@dataclass(frozen=True, slots=True)
class GitWorktreeRegistrationToken:
    """Descriptor-bound linked-worktree registration facts."""

    worktree_identity: DescriptorIdentity
    gitfile_identity: DescriptorIdentity
    gitfile_sha256: str
    administration_identity: DescriptorIdentity
    backlink_identity: DescriptorIdentity
    backlink_sha256: str
    registered_path: str
    administration_path: str


@dataclass(frozen=True, slots=True)
class OwnerlessGitFacts:
    """Exact accepted and target Git facts for ownerless admission."""

    accepted_head: str
    observation: LaneObservation
    registration_token: GitWorktreeRegistrationToken


type _WorktreeRecord = dict[bytes, bytes]
type _TargetSnapshot = tuple[LaneObservation, GitWorktreeRegistrationToken, tuple[object, ...]]


def observe_lane(root: Path, branch: str) -> tuple[LaneObservation, list[str]]:
    """Observe one lane with exact registration, Git, dirt, and lease facts."""
    try:
        canonical_root, root_descriptor, root_identity = _pin_root(root)
        try:
            records = _strict_worktrees(canonical_root)
            if not _matching_records(records, branch):
                head = _zero_oid(canonical_root)
                _require_directory_live(canonical_root, root_descriptor, root_identity, "root")
                return _empty_observation(canonical_root, branch, head), [
                    "lane_resolution_target_missing"
                ]
            lease = leases_by_branch(canonical_root).get(branch, {})
            holder = str(lease.get("holder_ref") or "")
            observation, _token = _observe_target(
                canonical_root,
                branch,
                coordination=(holder, not bool(lease)),
                require_clean=False,
            )
            _require_directory_live(canonical_root, root_descriptor, root_identity, "root")
            return observation, []
        finally:
            os.close(root_descriptor)
    except (OwnerlessGitObservationError, OSError, TypeError, ValueError):
        return _empty_observation(root.absolute(), branch, "0" * 40), [
            "lane_resolution_target_unverifiable"
        ]


def observe_ownerless_git(root: Path, *, branch: str, accepted_branch: str) -> OwnerlessGitFacts:
    """Observe exact accepted and target Git facts for ownerless admission."""
    canonical_root, root_descriptor, root_identity = _pin_root(root)
    try:
        accepted = _accepted_snapshot(canonical_root, accepted_branch)
        observation, token = _observe_target(
            canonical_root, branch, coordination=("", True), require_clean=True
        )
        try:
            terminal_accepted = _accepted_snapshot(canonical_root, accepted_branch)
        except OwnerlessGitObservationError as error:
            _raise("registration", "accepted_drift", error)
        if accepted != terminal_accepted:
            _fail("registration", "accepted_drift")
        _require_directory_live(canonical_root, root_descriptor, root_identity, "root")
        return OwnerlessGitFacts(accepted[1], observation, token)
    finally:
        os.close(root_descriptor)


def read_root_bound_regular_file(
    root: Path, relative_path: str, *, maximum_bytes: int
) -> ExactFileSnapshot:
    """Read one regular file through a descriptor-bound repository root."""
    parts = _relative_parts(relative_path)
    if type(maximum_bytes) is not int or maximum_bytes < 0:
        _fail("unverifiable", "root_bound_file")
    canonical_root, root_descriptor, root_identity = _pin_root(root)
    opened: list[tuple[int, str, int, DescriptorIdentity]] = []
    parent = root_descriptor
    try:
        for name in parts[:-1]:
            child = posix.open_directory_child(parent, name, create=False)
            identity = _identity(os.fstat(child))
            opened.append((parent, name, child, identity))
            parent = child
        snapshot = _bound_snapshot(parent, parts[-1], maximum_bytes)
        for parent_fd, name, descriptor, identity in opened:
            _require_child_live(parent_fd, name, descriptor, identity)
        _require_directory_live(canonical_root, root_descriptor, root_identity, "root_bound_file")
    except FileNotFoundError:
        _fail("unverifiable", "file_missing")
    except OwnerlessGitObservationError:
        raise
    except (OSError, TypeError, ValueError) as error:
        _raise("unverifiable", "root_bound_file", error)
    finally:
        for _parent, _name, descriptor, _identity_value in reversed(opened):
            os.close(descriptor)
        os.close(root_descriptor)
    return snapshot


def git_object_bytes(root: Path, object_spec: str) -> bytes:
    """Return exact bytes from one accepted-tree regular blob record."""
    treeish, separator, relative = object_spec.partition(":")
    if not separator or not treeish or not relative:
        _fail("unverifiable", "git_object_spec")
    parts = _relative_parts(relative)
    path = PurePosixPath(*parts).as_posix()
    listing = _git_bytes(root, "ls-tree", "-z", treeish, "--", path, detail="git_object_tree")
    if not listing.endswith(b"\0") or listing == b"\0":
        _fail("unverifiable", "git_object_tree")
    records = listing[:-1].split(b"\0")
    if len(records) != 1:
        _fail("unverifiable", "git_object_tree")
    metadata, tab, name = records[0].partition(b"\t")
    try:
        mode, object_type, raw_oid = metadata.split(b" ")
    except ValueError as error:
        _raise("unverifiable", "git_object_tree", error)
    if (
        not tab
        or mode not in {b"100644", b"100755"}
        or object_type != b"blob"
        or name != os.fsencode(path)
    ):
        _fail("unverifiable", "git_object_mode")
    oid = _oid(raw_oid, "git_object_tree")
    return _git_bytes(root, "cat-file", "blob", oid, detail="git_object")


def git_ancestry(
    root: Path, ancestor: str, descendant: str
) -> Literal["ancestor", "diverged", "unverifiable"]:
    """Classify one Git ancestry relation without collapsing uncertainty."""
    try:
        completed = _git_run(root, "merge-base", "--is-ancestor", ancestor, descendant)
    except (OSError, subprocess.SubprocessError, TypeError):
        return "unverifiable"
    if (
        not isinstance(completed.stdout, bytes)
        or not isinstance(completed.stderr, bytes)
        or completed.stdout
        or completed.stderr
    ):
        return "unverifiable"
    if completed.returncode == 0:
        return "ancestor"
    if completed.returncode == 1:
        return "diverged"
    return "unverifiable"


def untracked_files(path: Path) -> list[bytes] | None:
    """Return exact sorted non-ignored untracked paths or ``None`` on failure."""
    try:
        output = _git_bytes(
            path, "ls-files", "--others", "--exclude-standard", "-z", detail="untracked"
        )
    except OwnerlessGitObservationError:
        return None
    if output and not output.endswith(b"\0"):
        return None
    return sorted(item for item in output.split(b"\0") if item)


def _accepted_snapshot(root: Path, branch: str) -> tuple[_WorktreeRecord, str, bytes]:
    accepted = _unique_registration(_strict_worktrees(root), branch, "accepted")
    if _absolute_path(accepted.get(b"worktree"), "accepted") != root:
        _fail("registration", "accepted")
    head = _branch_head(root, branch, "accepted_ref")
    return accepted, head, _live_registration(root, accepted, branch, head, detail="accepted")


def _observe_target(
    root: Path,
    branch: str,
    *,
    coordination: tuple[str, bool],
    require_clean: bool,
) -> tuple[LaneObservation, GitWorktreeRegistrationToken]:
    first = _target_snapshot(root, branch, coordination=coordination, require_clean=require_clean)
    second = _target_snapshot(root, branch, coordination=coordination, require_clean=require_clean)
    if first != second:
        _fail("registration", "target_drift")
    return first[0], first[1]


def _target_snapshot(
    root: Path,
    branch: str,
    *,
    coordination: tuple[str, bool],
    require_clean: bool,
) -> _TargetSnapshot:
    holder_ref, orphan = coordination
    target = _unique_registration(_strict_worktrees(root), branch, "target")
    path = _absolute_path(target.get(b"worktree"), "target")
    common = _common_git_dir(root)
    if _common_git_dir(path) != common:
        _fail("registration", "target")
    token = _registration_token(path, common)
    head = _branch_head(root, branch, "target_ref")
    symbolic = _live_registration(path, target, branch, head, detail="target")
    status = _git_bytes(
        path, "status", "--porcelain=v2", "-z", "--untracked-files=all", detail="status"
    )
    worktree = _git_bytes(path, "diff", *_DIFF_FLAGS, "HEAD", "--", detail="worktree")
    index = _git_bytes(path, "diff", "--cached", *_DIFF_FLAGS, "HEAD", "--", detail="index")
    untracked = _git_bytes(
        path, "ls-files", "--others", "--exclude-standard", "-z", detail="untracked"
    )
    flags = _git_bytes(path, "ls-files", "-v", "-z", detail="index_flags")
    dirt = _dirt_detail(status, worktree, index, untracked, flags)
    if require_clean and dirt:
        _fail("dirty", dirt)
    observation = LaneObservation(
        lane_ref=branch,
        head=head,
        lane_incarnation_id=_serialize_registration(token),
        holder_ref=holder_ref,
        path=token.registered_path,
        dirty=bool(dirt),
        foreign=not bool(holder_ref),
        orphan=orphan,
        ambiguous=False,
        tracked_digest=_framed_digest(status, worktree, index, flags),
        untracked_digest=digest_untracked_inventory(source=path, inventory=untracked),
    )
    try:
        terminal_head = _branch_head(root, branch, "target_ref")
        terminal_symbolic = _live_registration(path, target, branch, terminal_head, detail="target")
        if {_common_git_dir(root), _common_git_dir(path)} != {common}:
            _fail("registration", "target_drift")
        terminal_token = _registration_token(path, common)
    except OwnerlessGitObservationError as error:
        _raise("registration", "target_drift", error)
    if (head, symbolic, token) != (terminal_head, terminal_symbolic, terminal_token):
        _fail("registration", "target_drift")
    return observation, token, (target, common, status, worktree, index, untracked, flags, symbolic)


def _registration_token(path: Path, common_git_dir: Path) -> GitWorktreeRegistrationToken:
    descriptor = administration_descriptor = -1
    try:
        descriptor = posix.open_directory_path(path, create=False)
        worktree_identity = _identity(os.fstat(descriptor))
        gitfile = _bound_snapshot(descriptor, ".git", _POINTER_LIMIT)
        administration_path = _pointer_path(gitfile.raw, prefix=b"gitdir: ")
        if administration_path.parent != common_git_dir / "worktrees":
            _fail("registration", "target")
        administration_descriptor = posix.open_directory_path(administration_path, create=False)
        administration_identity = _identity(os.fstat(administration_descriptor))
        backlink = _bound_snapshot(administration_descriptor, "gitdir", _POINTER_LIMIT)
        if _pointer_path(backlink.raw, prefix=b"") != path / ".git":
            _fail("registration", "target")
        _require_directory_live(path, descriptor, worktree_identity, "target")
        _require_directory_live(
            administration_path,
            administration_descriptor,
            administration_identity,
            "target",
        )
        return GitWorktreeRegistrationToken(
            worktree_identity=worktree_identity,
            gitfile_identity=gitfile.identity,
            gitfile_sha256=hashlib.sha256(gitfile.raw).hexdigest(),
            administration_identity=administration_identity,
            backlink_identity=backlink.identity,
            backlink_sha256=hashlib.sha256(backlink.raw).hexdigest(),
            registered_path=path.as_posix(),
            administration_path=administration_path.as_posix(),
        )
    except OwnerlessGitObservationError:
        raise
    except (OSError, TypeError, ValueError) as error:
        _raise("registration", "target", error)
    finally:
        for held in (administration_descriptor, descriptor):
            if held >= 0:
                os.close(held)


def _strict_worktrees(root: Path) -> tuple[_WorktreeRecord, ...]:
    output = _git_bytes(root, "worktree", "list", "--porcelain", "-z", detail="worktree_list")
    if not output.endswith(b"\0\0") or output == b"\0\0":
        _fail("unverifiable", "worktree_list")
    records: list[_WorktreeRecord] = []
    for raw_record in output[:-2].split(b"\0\0"):
        record: _WorktreeRecord = {}
        fields = raw_record.split(b"\0")
        if not fields or any(not field for field in fields):
            _fail("unverifiable", "worktree_list")
        for field in fields:
            key, separator, value = field.partition(b" ")
            if key not in _WORKTREE_FIELDS or key in record:
                _fail("unverifiable", "worktree_list")
            if key in {b"worktree", b"HEAD", b"branch"} and not separator:
                _fail("unverifiable", "worktree_list")
            record[key] = value
        if b"worktree" not in record or b"HEAD" not in record:
            _fail("unverifiable", "worktree_list")
        _oid(record[b"HEAD"], "worktree_list")
        records.append(record)
    registrations = {(record[b"worktree"], record.get(b"branch")) for record in records}
    if len({path for path, _branch in registrations}) != len(registrations):
        _fail("unverifiable", "worktree_list")
    return tuple(records)


def _unique_registration(
    records: tuple[_WorktreeRecord, ...], branch: str, detail: str
) -> _WorktreeRecord:
    matches = _matching_records(records, branch)
    if len(matches) != 1:
        _fail("registration", detail)
    record = matches[0]
    if _REGISTRATION_FLAGS.intersection(record):
        _fail("registration", detail)
    return record


def _matching_records(
    records: tuple[_WorktreeRecord, ...], branch: str
) -> tuple[_WorktreeRecord, ...]:
    expected = os.fsencode(f"refs/heads/{branch}")
    return tuple(record for record in records if record.get(b"branch") == expected)


def _live_registration(
    path: Path,
    record: _WorktreeRecord,
    branch: str,
    head: str,
    *,
    detail: str,
) -> bytes:
    if _oid(record[b"HEAD"], "worktree_list") != head:
        _fail("registration", f"{detail}_head")
    symbolic = _git_line(path, "symbolic-ref", "-q", "HEAD", detail=f"{detail}_branch")
    if os.fsdecode(symbolic) != f"refs/heads/{branch}":
        _fail("registration", f"{detail}_branch")
    live_head = _git_oid(path, "rev-parse", "--verify", "HEAD^{commit}", detail=f"{detail}_live")
    if live_head != head:
        _fail("registration", f"{detail}_head")
    return symbolic


def _absolute_path(raw: object, detail: str) -> Path:
    raw = raw if isinstance(raw, bytes) else _fail("registration", detail)
    path = Path(os.fsdecode(raw))
    if not path.is_absolute() or ".." in path.parts or os.fsencode(path) != raw:
        _fail("registration", detail)
    return path


def _common_git_dir(root: Path) -> Path:
    raw = _git_line(
        root, "rev-parse", "--path-format=absolute", "--git-common-dir", detail="common_git_dir"
    )
    return _absolute_path(raw, "target")


def _pin_root(root: Path) -> tuple[Path, int, DescriptorIdentity]:
    canonical = root.absolute()
    descriptor = -1
    try:
        descriptor = posix.open_directory_path(canonical, create=False)
        identity = _identity(os.fstat(descriptor))
        _require_directory_live(canonical, descriptor, identity, "root")
    except (OSError, TypeError, ValueError) as error:
        if descriptor >= 0:
            os.close(descriptor)
        _raise("unverifiable", "root", error)
    return canonical, descriptor, identity


def _require_directory_live(
    path: Path, descriptor: int, expected: DescriptorIdentity, detail: str
) -> None:
    directory = (expected.device, expected.inode, expected.mode)
    held = _identity(os.fstat(descriptor))
    if held != expected or not posix.directory_descriptor_is_live(path, descriptor, directory):
        _fail("unverifiable", detail)


def _require_child_live(
    parent: int, name: str, descriptor: int, expected: DescriptorIdentity
) -> None:
    directory = (expected.device, expected.inode, expected.mode)
    held = _identity(os.fstat(descriptor))
    if held != expected or posix.entry_directory_identity(parent, name) != directory:
        _fail("unverifiable", "root_bound_file")


def _bound_snapshot(parent: int, name: str, maximum_bytes: int) -> ExactFileSnapshot:
    expected = posix.entry_file_identity(parent, name)
    if expected is None or not stat.S_ISREG(expected[2]):
        raise FileNotFoundError(name)
    raw = posix.read_bound_file(parent, name, expected, max_bytes=maximum_bytes)
    if raw is None:
        raise ValueError(name)
    return ExactFileSnapshot(raw, DescriptorIdentity(*expected))


def _relative_parts(relative: str) -> tuple[str, ...]:
    if type(relative) is not str:
        _fail("unverifiable", "path")
    path = PurePosixPath(relative)
    invalid = not relative or not path.parts or path.is_absolute() or path.as_posix() != relative
    if invalid or {".", ".."}.intersection(path.parts):
        _fail("unverifiable", "path")
    return path.parts


def _pointer_path(raw: bytes, *, prefix: bytes) -> Path:
    if not raw.startswith(prefix) or not raw.endswith(b"\n") or raw.count(b"\n") != 1:
        _fail("registration", "target")
    return _absolute_path(raw[len(prefix) : -1], "target")


def _dirt_detail(
    status: bytes, worktree: bytes, index: bytes, untracked: bytes, flags: bytes
) -> str:
    if flags and not flags.endswith(b"\0"):
        _fail("unverifiable", "index_flags")
    for entry in (item for item in flags.split(b"\0") if item):
        if len(entry) < len(b"H x") or entry[1:2] != b" ":
            _fail("unverifiable", "index_flags")
        marker = entry[:1]
        if marker.islower():
            return "assume_unchanged"
        if marker == b"S":
            return "skip_worktree"
        if marker != b"H":
            _fail("unverifiable", "index_flags")
    if untracked:
        return "untracked"
    if index:
        return "index"
    if worktree:
        return "worktree"
    return "status" if status else ""


def _serialize_registration(token: GitWorktreeRegistrationToken) -> str:
    return _REGISTRATION_PREFIX + json.dumps(
        asdict(token), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )


def _framed_digest(*values: bytes) -> str:
    framed = b"".join(len(value).to_bytes(8, "big") + value for value in values)
    return hashlib.sha256(framed).hexdigest()


def _empty_observation(root: Path, branch: str, head: str) -> LaneObservation:
    empty = hashlib.sha256(b"").hexdigest()
    return LaneObservation(
        lane_ref=branch or "unknown",
        head=head,
        lane_incarnation_id="missing",
        path=root.as_posix(),
        dirty=True,
        foreign=True,
        orphan=True,
        ambiguous=True,
        tracked_digest=empty,
        untracked_digest=empty,
    )


def _identity(metadata: os.stat_result) -> DescriptorIdentity:
    return DescriptorIdentity(*posix.file_identity(metadata))


def _zero_oid(root: Path) -> str:
    object_format = _git_line(root, "rev-parse", "--show-object-format", detail="object_format")
    if object_format not in {b"sha1", b"sha256"}:
        _fail("unverifiable", "object_format")
    return "0" * (64 if object_format == b"sha256" else 40)


def _branch_head(root: Path, branch: str, detail: str) -> str:
    return _git_oid(root, "rev-parse", "--verify", f"refs/heads/{branch}^{{commit}}", detail=detail)


def _git_oid(root: Path, *args: str, detail: str) -> str:
    return _oid(_git_line(root, *args, detail=detail), detail)


def _oid(raw: bytes, detail: str) -> str:
    allowed = set(b"0123456789abcdef")
    if len(raw) not in {40, 64} or set(raw).difference(allowed):
        _fail("unverifiable", detail)
    return raw.decode("ascii")


def _git_line(root: Path, *args: str, detail: str) -> bytes:
    output = _git_bytes(root, *args, detail=detail)
    if not output.endswith(b"\n") or output.count(b"\n") != 1:
        _fail("unverifiable", detail)
    return output[:-1]


def _git_bytes(root: Path, *args: str, detail: str) -> bytes:
    try:
        completed = _git_run(root, *args)
    except (OSError, subprocess.SubprocessError, TypeError) as error:
        _raise("unverifiable", detail, error)
    if (
        completed.returncode
        or completed.stderr
        or not isinstance(completed.stdout, bytes)
        or not isinstance(completed.stderr, bytes)
    ):
        _fail("unverifiable", detail)
    return completed.stdout


def _git_run(root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    environment = {"PATH": os.environ.get("PATH", os.defpath), "GIT_NO_REPLACE_OBJECTS": "1"}
    environment |= {"LC_ALL": "C", "GIT_OPTIONAL_LOCKS": "0", "GIT_CONFIG_NOSYSTEM": "1"}
    environment |= {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_ATTR_NOSYSTEM": "1"}
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        capture_output=True,
        env=environment,
        shell=False,
    )


def _raise(kind: str, detail: str, cause: BaseException) -> NoReturn:
    raise OwnerlessGitObservationError(kind, detail) from cause


def _fail(kind: str, detail: str) -> NoReturn:
    raise OwnerlessGitObservationError(kind, detail)
