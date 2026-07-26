from __future__ import annotations

import os
import stat
import subprocess
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.resolution.observation as observation_adapter
from ethos.adapters.mutation.resolution.observation import DescriptorIdentity
from ethos.adapters.mutation.resolution.observation import ExactFileSnapshot
from ethos.adapters.mutation.resolution.observation import GitWorktreeRegistrationToken
from ethos.adapters.mutation.resolution.observation import OwnerlessGitObservationError
from ethos.adapters.mutation.resolution.observation import git_ancestry
from ethos.adapters.mutation.resolution.observation import git_object_bytes
from ethos.adapters.mutation.resolution.observation import read_root_bound_regular_file

if TYPE_CHECKING:
    from pathlib import Path


def _assert_git_ancestry_failures(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for factory in (
        lambda: (_ for _ in ()).throw(OSError("git unavailable")),
        lambda: subprocess.CompletedProcess(["git"], 0, "not-bytes", b""),
        lambda: subprocess.CompletedProcess(["git"], 2, b"", b""),
    ):
        with monkeypatch.context() as scoped:
            scoped.setattr(
                observation_adapter,
                "_git_run",
                lambda *_args, factory=factory: factory(),
            )
            assert git_ancestry(tmp_path, "ancestor", "descendant") == "unverifiable"


def _assert_untracked_file_observations(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with monkeypatch.context() as scoped:
        scoped.setattr(
            observation_adapter,
            "_git_bytes",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                OwnerlessGitObservationError("unverifiable", "untracked")
            ),
        )
        assert observation_adapter.untracked_files(tmp_path) is None
    with monkeypatch.context() as scoped:
        scoped.setattr(observation_adapter, "_git_bytes", lambda *_args, **_kwargs: b"unterminated")
        assert observation_adapter.untracked_files(tmp_path) is None
    with monkeypatch.context() as scoped:
        scoped.setattr(observation_adapter, "_git_bytes", lambda *_args, **_kwargs: b"b\0a\0\0")
        assert observation_adapter.untracked_files(tmp_path) == [b"a", b"b"]


def _assert_registration_token_reraises_target_error(
    *,
    path: Path,
    common: Path,
    identity: DescriptorIdentity,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with monkeypatch.context() as scoped:
        scoped.setattr(
            observation_adapter.posix,
            "open_directory_path",
            lambda *_args, **_kwargs: 1,
        )
        scoped.setattr(observation_adapter.os, "fstat", lambda _descriptor: object())
        scoped.setattr(observation_adapter, "_identity", lambda _metadata: identity)
        scoped.setattr(
            observation_adapter,
            "_bound_snapshot",
            lambda *_args: (_ for _ in ()).throw(
                OwnerlessGitObservationError("registration", "target")
            ),
        )
        scoped.setattr(observation_adapter.os, "close", lambda _descriptor: None)
        with pytest.raises(OwnerlessGitObservationError) as reraise:
            observation_adapter._registration_token(path, common)  # noqa: SLF001, RUF100
    assert (reraise.value.kind, reraise.value.detail) == ("registration", "target")


def test_observation_low_level_git_and_path_fail_closed_matrix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(OwnerlessGitObservationError) as invalid_spec:
        git_object_bytes(tmp_path, "HEAD")
    assert (invalid_spec.value.kind, invalid_spec.value.detail) == (
        "unverifiable",
        "git_object_spec",
    )

    with monkeypatch.context() as scoped:
        scoped.setattr(observation_adapter, "_git_bytes", lambda *_args, **_kwargs: b"broken")
        with pytest.raises(OwnerlessGitObservationError) as invalid_tree:
            git_object_bytes(tmp_path, "HEAD:file")
    assert (invalid_tree.value.kind, invalid_tree.value.detail) == (
        "unverifiable",
        "git_object_tree",
    )

    with monkeypatch.context() as scoped:
        scoped.setattr(
            observation_adapter,
            "_git_bytes",
            lambda *_args, **_kwargs: b"broken\tfile\0",
        )
        with pytest.raises(OwnerlessGitObservationError) as malformed_tree:
            git_object_bytes(tmp_path, "HEAD:file")
    assert (malformed_tree.value.kind, malformed_tree.value.detail) == (
        "unverifiable",
        "git_object_tree",
    )

    oid = b"a" * 40

    def exact_object_bytes(_root: Path, *args: str, detail: str) -> bytes:
        if args[0] == "ls-tree":
            return b"100644 blob " + oid + b"\tfile\0"
        assert args == ("cat-file", "blob", oid.decode())
        assert detail == "git_object"
        return b"exact bytes"

    with monkeypatch.context() as scoped:
        scoped.setattr(observation_adapter, "_git_bytes", exact_object_bytes)
        assert git_object_bytes(tmp_path, "HEAD:file") == b"exact bytes"

    _assert_git_ancestry_failures(tmp_path, monkeypatch)

    _assert_untracked_file_observations(tmp_path, monkeypatch)

    with pytest.raises(OwnerlessGitObservationError) as bad_limit:
        read_root_bound_regular_file(tmp_path, "file", maximum_bytes=-1)
    assert (bad_limit.value.kind, bad_limit.value.detail) == ("unverifiable", "root_bound_file")
    with pytest.raises(OwnerlessGitObservationError) as bad_relative:
        observation_adapter._relative_parts(1)  # type: ignore[arg-type]  # noqa: SLF001, RUF100
    assert (bad_relative.value.kind, bad_relative.value.detail) == ("unverifiable", "path")
    with pytest.raises(OwnerlessGitObservationError):
        observation_adapter._pointer_path(b"bad", prefix=b"gitdir: ")  # noqa: SLF001, RUF100
    with pytest.raises(OwnerlessGitObservationError):
        observation_adapter._absolute_path(b"relative", "target")  # noqa: SLF001, RUF100
    with pytest.raises(OwnerlessGitObservationError):
        observation_adapter._dirt_detail(  # noqa: SLF001, RUF100
            b"",
            b"",
            b"",
            b"",
            b"unterminated",
        )
    with pytest.raises(OwnerlessGitObservationError):
        observation_adapter._dirt_detail(b"", b"", b"", b"", b"Hx\0")  # noqa: SLF001, RUF100

    with monkeypatch.context() as scoped:
        scoped.setattr(observation_adapter, "_git_bytes", lambda *_args, **_kwargs: b"no newline")
        with pytest.raises(OwnerlessGitObservationError):
            observation_adapter._git_line(tmp_path, "status", detail="status")  # noqa: SLF001, RUF100
    with monkeypatch.context() as scoped:
        scoped.setattr(
            observation_adapter,
            "_git_run",
            lambda *_args: (_ for _ in ()).throw(OSError("git unavailable")),
        )
        with pytest.raises(OwnerlessGitObservationError):
            observation_adapter._git_bytes(tmp_path, "status", detail="status")  # noqa: SLF001, RUF100


def test_observation_registration_parser_fail_closed_matrix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    oid = b"a" * 40
    malformed = (
        b"worktree /lane\0\0\0",
        b"worktree\0HEAD " + oid + b"\0\0",
        b"worktree /lane\0\0",
    )
    for output in malformed:
        with monkeypatch.context() as scoped:
            scoped.setattr(
                observation_adapter,
                "_git_bytes",
                lambda *_args, output=output, **_kwargs: output,
            )
            with pytest.raises(OwnerlessGitObservationError) as invalid:
                observation_adapter._strict_worktrees(tmp_path)  # noqa: SLF001, RUF100
        assert (invalid.value.kind, invalid.value.detail) == ("unverifiable", "worktree_list")

    record = {
        b"worktree": os.fsencode(tmp_path),
        b"HEAD": oid,
        b"branch": b"refs/heads/work/edge",
        b"locked": b"reason",
    }
    with pytest.raises(OwnerlessGitObservationError) as flagged:
        observation_adapter._unique_registration((record,), "work/edge", "target")  # noqa: SLF001, RUF100
    assert (flagged.value.kind, flagged.value.detail) == ("registration", "target")

    live_record = {b"HEAD": oid}
    with monkeypatch.context() as scoped:
        scoped.setattr(
            observation_adapter,
            "_git_line",
            lambda *_args, **_kwargs: b"refs/heads/other",
        )
        with pytest.raises(OwnerlessGitObservationError) as live_mismatch:
            observation_adapter._live_registration(  # noqa: SLF001, RUF100
                tmp_path,
                live_record,
                "work/edge",
                oid.decode(),
                detail="target",
            )
    assert (live_mismatch.value.kind, live_mismatch.value.detail) == (
        "registration",
        "target_branch",
    )

    other = tmp_path / "other"
    with monkeypatch.context() as scoped:
        scoped.setattr(observation_adapter, "_strict_worktrees", lambda _root: ())
        scoped.setattr(
            observation_adapter,
            "_unique_registration",
            lambda *_args: {b"worktree": os.fsencode(other)},
        )
        with pytest.raises(OwnerlessGitObservationError) as accepted:
            observation_adapter._accepted_snapshot(tmp_path, "dev")  # noqa: SLF001, RUF100
    assert (accepted.value.kind, accepted.value.detail) == ("registration", "accepted")


def test_observation_target_and_registration_token_fail_closed_matrix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    oid = "a" * 40
    path = tmp_path / "lane"
    common = tmp_path / "common"
    identity = DescriptorIdentity(1, 2, stat.S_IFDIR, 0, 0, 0)
    regular = DescriptorIdentity(1, 3, stat.S_IFREG, 0, 0, 0)
    token = GitWorktreeRegistrationToken(
        worktree_identity=identity,
        gitfile_identity=regular,
        gitfile_sha256="b" * 64,
        administration_identity=identity,
        backlink_identity=regular,
        backlink_sha256="c" * 64,
        registered_path=path.as_posix(),
        administration_path=(common / "worktrees" / "lane").as_posix(),
    )
    record = {
        b"worktree": os.fsencode(path),
        b"HEAD": oid.encode(),
        b"branch": b"refs/heads/work/edge",
    }
    common_dirs = iter((common, common, tmp_path / "changed", common))
    with monkeypatch.context() as scoped:
        scoped.setattr(observation_adapter, "_strict_worktrees", lambda _root: ())
        scoped.setattr(observation_adapter, "_unique_registration", lambda *_args: record)
        scoped.setattr(observation_adapter, "_common_git_dir", lambda _root: next(common_dirs))
        scoped.setattr(observation_adapter, "_registration_token", lambda *_args: token)
        scoped.setattr(observation_adapter, "_branch_head", lambda *_args, **_kwargs: oid)
        scoped.setattr(
            observation_adapter,
            "_live_registration",
            lambda *_args, **_kwargs: b"refs/heads/work/edge",
        )
        scoped.setattr(observation_adapter, "_git_bytes", lambda *_args, **_kwargs: b"")
        scoped.setattr(
            observation_adapter, "digest_untracked_inventory", lambda **_kwargs: "d" * 64
        )
        with pytest.raises(OwnerlessGitObservationError) as drift:
            observation_adapter._target_snapshot(  # noqa: SLF001, RUF100
                tmp_path,
                "work/edge",
                coordination=("", True),
                require_clean=False,
            )
    assert (drift.value.kind, drift.value.detail) == ("registration", "target_drift")

    bad_administration = tmp_path / "bad" / "entry"
    with monkeypatch.context() as scoped:
        descriptors = iter((1, 2))
        scoped.setattr(
            observation_adapter.posix,
            "open_directory_path",
            lambda *_args, **_kwargs: next(descriptors),
        )
        scoped.setattr(observation_adapter.os, "fstat", lambda _descriptor: object())
        scoped.setattr(observation_adapter, "_identity", lambda _metadata: identity)
        scoped.setattr(
            observation_adapter,
            "_bound_snapshot",
            lambda *_args: ExactFileSnapshot(
                b"gitdir: " + os.fsencode(bad_administration) + b"\n",
                regular,
            ),
        )
        scoped.setattr(observation_adapter.os, "close", lambda _descriptor: None)
        with pytest.raises(OwnerlessGitObservationError) as bad_parent:
            observation_adapter._registration_token(path, common)  # noqa: SLF001, RUF100
    assert (bad_parent.value.kind, bad_parent.value.detail) == ("registration", "target")

    administration = common / "worktrees" / "lane"
    mismatched_backlink = tmp_path / "other" / ".git"
    with monkeypatch.context() as scoped:
        descriptors = iter((1, 2))
        snapshots = iter(
            (
                ExactFileSnapshot(b"gitdir: " + os.fsencode(administration) + b"\n", regular),
                ExactFileSnapshot(os.fsencode(mismatched_backlink) + b"\n", regular),
            )
        )
        scoped.setattr(
            observation_adapter.posix,
            "open_directory_path",
            lambda *_args, **_kwargs: next(descriptors),
        )
        scoped.setattr(observation_adapter.os, "fstat", lambda _descriptor: object())
        scoped.setattr(observation_adapter, "_identity", lambda _metadata: identity)
        scoped.setattr(observation_adapter, "_bound_snapshot", lambda *_args: next(snapshots))
        scoped.setattr(observation_adapter.os, "close", lambda _descriptor: None)
        with pytest.raises(OwnerlessGitObservationError) as bad_backlink:
            observation_adapter._registration_token(path, common)  # noqa: SLF001, RUF100
    assert (bad_backlink.value.kind, bad_backlink.value.detail) == ("registration", "target")

    _assert_registration_token_reraises_target_error(
        path=path,
        common=common,
        identity=identity,
        monkeypatch=monkeypatch,
    )


def test_observation_root_and_bound_snapshot_fail_closed_edges(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    identity = DescriptorIdentity(1, 2, stat.S_IFDIR, 0, 0, 0)
    closed: list[int] = []
    with monkeypatch.context() as scoped:
        scoped.setattr(
            observation_adapter.posix,
            "open_directory_path",
            lambda *_args, **_kwargs: 7,
        )
        scoped.setattr(observation_adapter.os, "fstat", lambda _descriptor: object())
        scoped.setattr(observation_adapter, "_identity", lambda _metadata: identity)
        scoped.setattr(
            observation_adapter,
            "_require_directory_live",
            lambda *_args: (_ for _ in ()).throw(ValueError("root changed")),
        )
        scoped.setattr(observation_adapter.os, "close", closed.append)
        with pytest.raises(OwnerlessGitObservationError) as root_error:
            observation_adapter._pin_root(tmp_path)  # noqa: SLF001, RUF100
    assert (root_error.value.kind, root_error.value.detail) == ("unverifiable", "root")
    assert closed == [7]

    regular = (1, 2, stat.S_IFREG, 3, 4, 5)
    with monkeypatch.context() as scoped:
        scoped.setattr(observation_adapter.posix, "entry_file_identity", lambda *_args: None)
        with pytest.raises(FileNotFoundError):
            observation_adapter._bound_snapshot(1, "file", 1024)  # noqa: SLF001, RUF100
    with monkeypatch.context() as scoped:
        scoped.setattr(observation_adapter.posix, "entry_file_identity", lambda *_args: regular)
        scoped.setattr(observation_adapter.posix, "read_bound_file", lambda *_args, **_kwargs: None)
        with pytest.raises(ValueError, match=r"^file$"):
            observation_adapter._bound_snapshot(1, "file", 1024)  # noqa: SLF001, RUF100
