from __future__ import annotations

import hashlib
import os
import stat
import subprocess
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.resolution.lane as lane_adapter
import ethos.adapters.mutation.resolution.observation as observation_adapter
from ethos.adapters.mutation.resolution.observation import OwnerlessGitObservationError
from ethos.adapters.mutation.resolution.observation import git_object_bytes
from ethos.adapters.mutation.resolution.observation import read_root_bound_regular_file
from tests.support.contract_helpers import git
from tests.support.contract_helpers import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path


_accepted_chronicle = lane_adapter._accepted_chronicle  # noqa: SLF001, RUF100 - dedicated private-gate coverage


def _commit_bytes(repo: Path, relative: str, raw: bytes, *, executable: bool = False) -> None:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    if executable:
        path.chmod(0o755)
    git(repo, "add", relative)
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        f"add {relative}",
    )


def test_root_bound_snapshot_preserves_exact_bytes_and_identity(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    path = root / "evidence/chronicle/example.md"
    path.parent.mkdir(parents=True)
    raw = b"line one\r\nline two\xff\n"
    path.write_bytes(raw)

    snapshot = read_root_bound_regular_file(
        root, "evidence/chronicle/example.md", maximum_bytes=len(raw)
    )

    assert snapshot.raw == raw
    assert snapshot.identity.size == len(raw)
    assert stat.S_ISREG(snapshot.identity.mode)


@pytest.mark.parametrize("shape", ["root", "component"])
def test_root_bound_snapshot_rejects_symlinked_paths(tmp_path: Path, shape: str) -> None:
    real_root = tmp_path / "real"
    target = real_root / "evidence/chronicle/example.md"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"decision\n")
    root = real_root
    if shape == "root":
        root = tmp_path / "linked"
        root.symlink_to(real_root, target_is_directory=True)
    else:
        moved = real_root / "actual-chronicle"
        target.parent.rename(moved)
        target.parent.symlink_to(moved, target_is_directory=True)

    with pytest.raises(OwnerlessGitObservationError):
        read_root_bound_regular_file(root, "evidence/chronicle/example.md", maximum_bytes=1024)


def test_root_bound_snapshot_rejects_directory_swap_during_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "repo"
    directory = root / "evidence/chronicle"
    directory.mkdir(parents=True)
    raw = b"x" * 128
    (directory / "example.md").write_bytes(raw)
    moved = root / "evidence/original-chronicle"
    real_read = os.read
    swapped = False

    def swapping_read(descriptor: int, maximum: int) -> bytes:
        nonlocal swapped
        chunk = real_read(descriptor, maximum)
        if not swapped:
            swapped = True
            directory.rename(moved)
            directory.mkdir()
            (directory / "example.md").write_bytes(raw)
        return chunk

    monkeypatch.setattr(observation_adapter.os, "read", swapping_read)

    with pytest.raises(OwnerlessGitObservationError):
        read_root_bound_regular_file(root, "evidence/chronicle/example.md", maximum_bytes=len(raw))


@pytest.mark.parametrize(
    ("raw", "file_mode"),
    [
        pytest.param(b"decision: lane_resolution/retire\r\n", 0o644, id="crlf-100644"),
        pytest.param(b"\xff\x00exact\n", 0o755, id="non-utf8-100755"),
    ],
)
def test_git_object_bytes_preserves_regular_blob_bytes(
    tmp_path: Path, raw: bytes, file_mode: int
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    _commit_bytes(repo, "evidence/chronicle/example.bin", raw, executable=file_mode == 0o755)

    assert git_object_bytes(repo, "HEAD:evidence/chronicle/example.bin") == raw


def test_git_object_bytes_ignores_repository_replace_refs(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    relative = "evidence/chronicle/example.bin"
    raw = b"decision: lane_resolution/retire\noriginal\n"
    replacement = b"decision: lane_resolution/retire\nreplacement\n"
    _commit_bytes(repo, relative, raw)
    original_oid = git(repo, "rev-parse", f"HEAD:{relative}")
    replacement_path = tmp_path / "replacement.bin"
    replacement_path.write_bytes(replacement)
    replacement_oid = git(repo, "hash-object", "-w", replacement_path.as_posix())
    git(repo, "replace", original_oid, replacement_oid)

    assert git_object_bytes(repo, f"HEAD:{relative}") == raw


@pytest.mark.parametrize("mode", ["symlink", "tree", "submodule"])
def test_git_object_bytes_rejects_non_regular_tree_modes(tmp_path: Path, mode: str) -> None:
    repo = init_git_repo(tmp_path / "repo")
    relative = f"invalid-{mode}"
    if mode == "symlink":
        (repo / relative).symlink_to("README.md")
        git(repo, "add", relative)
    elif mode == "tree":
        (repo / relative).mkdir()
        (repo / relative / "nested.txt").write_text("nested\n", encoding="utf-8")
        git(repo, "add", relative)
    else:
        oid = git(repo, "rev-parse", "HEAD")
        git(repo, "update-index", "--add", "--cacheinfo", f"160000,{oid},{relative}")
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        f"add {mode}",
    )

    with pytest.raises(OwnerlessGitObservationError) as raised:
        git_object_bytes(repo, f"HEAD:{relative}")

    assert (raised.value.kind, raised.value.detail) == ("unverifiable", "git_object_mode")


def test_git_object_bytes_rejects_duplicate_tree_records(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    oid = git(repo, "rev-parse", "HEAD:README.md").encode()
    record = b"100644 blob " + oid + b"\tREADME.md\0"
    real_run = subprocess.run

    def duplicate_tree(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        if list(args)[1:3] == ["ls-tree", "-z"]:
            return subprocess.CompletedProcess(args, 0, record + record, b"")
        return real_run(args, **kwargs)  # type: ignore[return-value]

    monkeypatch.setattr(observation_adapter.subprocess, "run", duplicate_tree)

    with pytest.raises(OwnerlessGitObservationError) as raised:
        git_object_bytes(repo, "HEAD:README.md")

    assert (raised.value.kind, raised.value.detail) == ("unverifiable", "git_object_tree")


def test_accepted_chronicle_matches_working_and_tree_bytes_exactly(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    relative = "evidence/chronicle/example.md"
    raw = b"decision: lane_resolution/retire\r\n"
    _commit_bytes(repo, relative, raw)

    observed_relative, digest, gaps = _accepted_chronicle(
        repo, chronicle_ref=relative, disposition="retire"
    )

    assert observed_relative == relative
    assert digest == hashlib.sha256(raw).hexdigest()
    assert gaps == []


def test_accepted_chronicle_rejects_same_bytes_file_replacement_during_tree_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    relative = "evidence/chronicle/example.md"
    raw = b"decision: lane_resolution/retire\n"
    _commit_bytes(repo, relative, raw)
    real_git_object_bytes = lane_adapter.git_object_bytes
    replaced = False

    def replacing_git_object_bytes(root: Path, object_spec: str) -> bytes:
        nonlocal replaced
        if not replaced:
            replaced = True
            replacement = repo / f"{relative}.replacement"
            replacement.write_bytes(raw)
            replacement.replace(repo / relative)
        return real_git_object_bytes(root, object_spec)

    monkeypatch.setattr(lane_adapter, "git_object_bytes", replacing_git_object_bytes)

    assert _accepted_chronicle(repo, chronicle_ref=relative, disposition="retire")[2] == [
        "lane_resolution_chronicle_invalid"
    ]


def test_accepted_chronicle_rejects_working_tree_byte_drift(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    relative = "evidence/chronicle/example.md"
    _commit_bytes(repo, relative, b"decision: lane_resolution/retire\n")
    (repo / relative).write_bytes(b"decision: lane_resolution/retire\r\n")

    assert _accepted_chronicle(repo, chronicle_ref=relative, disposition="retire")[2] == [
        "lane_resolution_chronicle_invalid"
    ]


def test_accepted_chronicle_rejects_non_utf8_blob(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    relative = "evidence/chronicle/example.md"
    _commit_bytes(repo, relative, b"decision: lane_resolution/retire\n\xff")

    assert _accepted_chronicle(repo, chronicle_ref=relative, disposition="retire")[2] == [
        "lane_resolution_chronicle_invalid"
    ]
