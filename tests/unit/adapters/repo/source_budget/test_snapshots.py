from __future__ import annotations

import subprocess
from dataclasses import replace
from shutil import which
from typing import TYPE_CHECKING
from typing import Any
from typing import cast

import pytest

import ethos.adapters.repo.source_budget.snapshots as snapshots

_TREE_DIGEST = cast("Any", vars(snapshots)["_tree_digest"])
_BYTES_DIGEST = cast("Any", vars(snapshots)["_bytes_digest"])

if TYPE_CHECKING:
    from pathlib import Path


def _git(root: Path, *args: str, input_bytes: bytes | None = None) -> bytes:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        input=input_bytes,
        capture_output=True,
        check=True,
    ).stdout


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "Test")
    _git(root, "config", "user.email", "test@example.invalid")
    return root


def _commit(root: Path) -> str:
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "snapshot")
    return _git(root, "rev-parse", "HEAD").decode().strip()


def _batch_frame(
    oid: str,
    content: bytes,
    *,
    object_type: str = "blob",
    size: str | None = None,
) -> bytes:
    declared_size = str(len(content)) if size is None else size
    return f"{oid} {object_type} {declared_size}\n".encode() + content + b"\n"


def test_tree_snapshot_peels_commit_tree_and_reads_no_worktree_content(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    (root / "a.txt").write_text("same\n", encoding="utf-8")
    (root / "nested").mkdir()
    (root / "nested/b.txt").write_text("same\n", encoding="utf-8")
    commit = _commit(root)
    tree = _git(root, "rev-parse", f"{commit}^{{tree}}").decode().strip()

    load = snapshots.tree_snapshot(root, commit[:12])

    assert load.required_gaps == ()
    assert load.snapshot is not None
    assert load.snapshot.commit_sha == commit
    assert load.snapshot.tree_sha == tree
    assert tuple(entry.relative_path for entry in load.snapshot.entries) == (
        "a.txt",
        "nested/b.txt",
    )
    assert all(
        entry.mode == "100644" and entry.object_type == "blob" for entry in load.snapshot.entries
    )


def test_tree_snapshot_binds_exact_git_argv_environment_timeout_and_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _repo(tmp_path)
    (root / "a.txt").write_text("a\n", encoding="utf-8")
    commit = _commit(root)
    tree = _git(root, "rev-parse", f"{commit}^{{tree}}").decode().strip()
    alias = tmp_path / "repo-alias"
    alias.symlink_to(root, target_is_directory=True)
    real_run = subprocess.run
    calls: list[tuple[list[str], dict[str, Any]]] = []

    monkeypatch.setenv("GIT_DIR", "/attacker/git-dir")
    monkeypatch.setenv("GIT_WORK_TREE", "/attacker/worktree")
    monkeypatch.setenv("GIT_NO_REPLACE_OBJECTS", "0")
    monkeypatch.setenv("LANG", "attacker-locale")
    monkeypatch.setenv("SNAPSHOT_TEST_SENTINEL", "preserved")

    def recorded(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        calls.append((command, kwargs))
        return real_run(command, **kwargs)

    monkeypatch.setattr(snapshots.subprocess, "run", recorded)

    load = snapshots.tree_snapshot(alias, commit)

    assert load.snapshot is not None
    prefix = [
        which("git"),
        "--no-replace-objects",
        "-c",
        f"safe.directory={root.resolve()}",
        "-C",
        str(root.resolve()),
    ]
    assert [command for command, _ in calls] == [
        [*prefix, "rev-parse", "--show-toplevel"],
        [*prefix, "rev-parse", "--verify", "--end-of-options", f"{commit}^{{commit}}"],
        [*prefix, "rev-parse", "--verify", "--end-of-options", f"{commit}^{{tree}}"],
        [*prefix, "ls-tree", "-r", "-z", "--full-tree", tree],
    ]
    for _, kwargs in calls:
        assert kwargs["capture_output"] is True
        assert kwargs["check"] is False
        assert kwargs["timeout"] == 30
        assert "cwd" not in kwargs
        environment = kwargs["env"]
        assert environment["LANG"] == "C"
        assert environment["LC_ALL"] == "C"
        assert environment["SNAPSHOT_TEST_SENTINEL"] == "preserved"
        assert {key for key in environment if key.startswith("GIT_")} == {
            "GIT_NO_REPLACE_OBJECTS",
            "GIT_OPTIONAL_LOCKS",
        }
        assert environment["GIT_NO_REPLACE_OBJECTS"] == "1"
        assert environment["GIT_OPTIONAL_LOCKS"] == "0"


def test_snapshot_blob_reads_remain_bound_to_git_objects_after_worktree_mutation(
    tmp_path: Path,
) -> None:
    root = _repo(tmp_path)
    path = root / "a.txt"
    path.write_text("committed\n", encoding="utf-8")
    tree = snapshots.tree_snapshot(root, _commit(root)).snapshot
    assert tree is not None

    path.write_text("mutable worktree\n", encoding="utf-8")
    load = snapshots.read_snapshot_blobs(root, tree, ("a.txt",))

    assert load.required_gaps == ()
    assert load.snapshot is not None
    assert load.snapshot.contents == (("a.txt", b"committed\n"),)


def test_blob_batch_deduplicates_oids_at_first_inventory_occurrence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _repo(tmp_path)
    (root / "a.txt").write_text("same\n", encoding="utf-8")
    (root / "b.txt").write_text("different\n", encoding="utf-8")
    (root / "c.txt").write_text("same\n", encoding="utf-8")
    tree = snapshots.tree_snapshot(root, _commit(root)).snapshot
    assert tree is not None
    real_run = subprocess.run
    batch_calls: list[tuple[list[str], bytes]] = []

    def recorded(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        if "cat-file" in command and "--batch" in command:
            batch_calls.append((command, kwargs.get("input", b"")))
        return real_run(command, **kwargs)

    monkeypatch.setattr(snapshots.subprocess, "run", recorded)
    load = snapshots.read_snapshot_blobs(root, tree, ("a.txt", "b.txt", "c.txt"))

    assert load.required_gaps == ()
    assert load.snapshot is not None
    assert load.snapshot.contents == (
        ("a.txt", b"same\n"),
        ("b.txt", b"different\n"),
        ("c.txt", b"same\n"),
    )
    assert len(batch_calls) == 1
    entries = {entry.relative_path: entry for entry in tree.entries}
    command, batch_input = batch_calls[0]
    assert command == [
        which("git"),
        "--no-replace-objects",
        "-c",
        f"safe.directory={root.resolve()}",
        "-C",
        str(root.resolve()),
        "cat-file",
        "--batch",
    ]
    assert batch_input == (f"{entries['a.txt'].oid}\n{entries['b.txt'].oid}\n".encode())


@pytest.mark.parametrize(
    ("payload", "gap"),
    [
        (b"100644 blob " + b"a" * 40 + b"\tbad", "git_snapshot_ls_tree_invalid"),
        (
            b"120000 blob " + b"a" * 40 + b"\tlink\0",
            "git_snapshot_object_unsupported:link",
        ),
        (
            b"160000 commit " + b"a" * 40 + b"\tsub\0",
            "git_snapshot_object_unsupported:sub",
        ),
        (b"100644 blob " + b"a" * 40 + b"\t../bad\0", "git_snapshot_path_invalid"),
        (b"100644 blob " + b"a" * 40 + b"\t/absolute\0", "git_snapshot_path_invalid"),
        (b"100644 blob " + b"a" * 40 + b"\tbad\\path\0", "git_snapshot_path_invalid"),
    ],
)
def test_tree_snapshot_rejects_invalid_framing_and_unsupported_entries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    payload: bytes,
    gap: str,
) -> None:
    root = _repo(tmp_path)
    (root / "a.txt").write_text("a\n", encoding="utf-8")
    commit = _commit(root)
    real_run = subprocess.run

    def altered(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        if "ls-tree" in command and "-r" in command:
            return subprocess.CompletedProcess(command, 0, stdout=payload, stderr=b"")
        return real_run(command, **kwargs)

    monkeypatch.setattr(snapshots.subprocess, "run", altered)
    load = snapshots.tree_snapshot(root, commit)

    assert load.snapshot is None
    assert gap in load.required_gaps


@pytest.mark.parametrize(
    ("payload", "gap"),
    [
        (
            (b"100644 blob " + b"a" * 40 + b"\ta.txt\0") * 2,
            "git_snapshot_ls_tree_invalid",
        ),
        (
            b"100644 blob " + b"b" * 40 + b"\tb.txt\0" + b"100644 blob " + b"a" * 40 + b"\ta.txt\0",
            "git_snapshot_ls_tree_invalid",
        ),
        (
            b"100644 blob " + b"a" * 40 + b"\tbad-\xff.txt\0",
            "git_snapshot_path_invalid",
        ),
    ],
)
def test_tree_snapshot_rejects_duplicate_disordered_and_non_utf8_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    payload: bytes,
    gap: str,
) -> None:
    root = _repo(tmp_path)
    (root / "a.txt").write_text("a\n", encoding="utf-8")
    commit = _commit(root)
    real_run = subprocess.run

    def altered(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        if "ls-tree" in command and "-r" in command:
            return subprocess.CompletedProcess(command, 0, stdout=payload, stderr=b"")
        return real_run(command, **kwargs)

    monkeypatch.setattr(snapshots.subprocess, "run", altered)
    load = snapshots.tree_snapshot(root, commit)

    assert load.snapshot is None
    assert load.required_gaps == (gap,)


def test_tree_snapshot_rejects_ls_tree_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _repo(tmp_path)
    (root / "a.txt").write_text("a\n", encoding="utf-8")
    commit = _commit(root)
    real_run = subprocess.run

    def failed(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        if "ls-tree" in command and "-r" in command:
            return subprocess.CompletedProcess(command, 1, stdout=b"", stderr=b"failed")
        return real_run(command, **kwargs)

    monkeypatch.setattr(snapshots.subprocess, "run", failed)

    load = snapshots.tree_snapshot(root, commit)

    assert load.snapshot is None
    assert load.required_gaps == ("git_snapshot_ls_tree_failed",)


def test_snapshot_rejects_successful_git_commands_with_stderr(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _repo(tmp_path)
    (root / "a.txt").write_text("a\n", encoding="utf-8")
    commit = _commit(root)
    real_run = subprocess.run

    def noisy_tree(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        completed = real_run(command, **kwargs)
        if "ls-tree" in command:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=completed.stdout,
                stderr=b"warning\n",
            )
        return completed

    monkeypatch.setattr(snapshots.subprocess, "run", noisy_tree)
    tree_load = snapshots.tree_snapshot(root, commit)
    assert tree_load.snapshot is None
    assert tree_load.required_gaps == ("git_snapshot_ls_tree_failed",)

    monkeypatch.undo()
    tree = snapshots.tree_snapshot(root, commit).snapshot
    assert tree is not None

    def noisy_batch(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        completed = real_run(command, **kwargs)
        if "cat-file" in command:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=completed.stdout,
                stderr=b"warning\n",
            )
        return completed

    monkeypatch.setattr(snapshots.subprocess, "run", noisy_batch)
    blob_load = snapshots.read_snapshot_blobs(root, tree, ("a.txt",))
    assert blob_load.snapshot is None
    assert blob_load.required_gaps == ("git_snapshot_blob_batch_failed",)


def test_tree_snapshot_rejects_subdirectory_as_repository_root(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    nested = root / "nested"
    nested.mkdir()
    (nested / "a.txt").write_text("a\n", encoding="utf-8")
    commit = _commit(root)

    load = snapshots.tree_snapshot(nested, commit)

    assert load.snapshot is None
    assert load.required_gaps == ("git_snapshot_root_invalid",)


def test_blob_batch_rejects_missing_wrong_type_size_truncation_and_trailing_data(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _repo(tmp_path)
    (root / "a.txt").write_text("a\n", encoding="utf-8")
    tree = snapshots.tree_snapshot(root, _commit(root)).snapshot
    assert tree is not None
    oid = tree.entries[0].oid
    real_run = subprocess.run
    cases = (
        (f"{oid} missing\n".encode(), f"git_snapshot_blob_missing:{oid}"),
        (_batch_frame(oid, b"a\n", object_type="tree"), "git_snapshot_blob_batch_invalid"),
        (_batch_frame(oid, b"a\n", size="02"), "git_snapshot_blob_batch_invalid"),
        (f"{oid} blob 2\na\n".encode(), "git_snapshot_blob_batch_invalid"),
        (_batch_frame(oid, b"a\n") + b"trailing", "git_snapshot_blob_batch_invalid"),
    )

    for output, expected_gap in cases:
        with monkeypatch.context() as patch:

            def altered(
                command: list[str],
                *,
                _output: bytes = output,
                **kwargs: Any,
            ) -> subprocess.CompletedProcess[bytes]:
                if "cat-file" in command and "--batch" in command:
                    return subprocess.CompletedProcess(command, 0, stdout=_output, stderr=b"")
                return real_run(command, **kwargs)

            patch.setattr(snapshots.subprocess, "run", altered)
            load = snapshots.read_snapshot_blobs(root, tree, ("a.txt",))

        assert load.snapshot is None
        assert load.required_gaps == (expected_gap,)


def test_blob_batch_rejects_response_order_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _repo(tmp_path)
    (root / "a.txt").write_text("a\n", encoding="utf-8")
    (root / "b.txt").write_text("b\n", encoding="utf-8")
    tree = snapshots.tree_snapshot(root, _commit(root)).snapshot
    assert tree is not None
    entries = {entry.relative_path: entry for entry in tree.entries}
    reversed_output = _batch_frame(entries["b.txt"].oid, b"b\n") + _batch_frame(
        entries["a.txt"].oid,
        b"a\n",
    )
    real_run = subprocess.run

    def altered(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        if "cat-file" in command and "--batch" in command:
            return subprocess.CompletedProcess(command, 0, stdout=reversed_output, stderr=b"")
        return real_run(command, **kwargs)

    monkeypatch.setattr(snapshots.subprocess, "run", altered)

    load = snapshots.read_snapshot_blobs(root, tree, ("a.txt", "b.txt"))

    assert load.snapshot is None
    assert load.required_gaps == ("git_snapshot_blob_batch_invalid",)


@pytest.mark.parametrize("failure", ["nonzero", "timeout"])
def test_blob_batch_rejects_command_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    root = _repo(tmp_path)
    (root / "a.txt").write_text("a\n", encoding="utf-8")
    tree = snapshots.tree_snapshot(root, _commit(root)).snapshot
    assert tree is not None
    real_run = subprocess.run

    def failed(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        if "cat-file" not in command or "--batch" not in command:
            return real_run(command, **kwargs)
        if failure == "timeout":
            raise subprocess.TimeoutExpired(command, timeout=30)
        return subprocess.CompletedProcess(command, 1, stdout=b"", stderr=b"failed")

    monkeypatch.setattr(snapshots.subprocess, "run", failed)

    load = snapshots.read_snapshot_blobs(root, tree, ("a.txt",))

    assert load.snapshot is None
    assert load.required_gaps == ("git_snapshot_blob_batch_failed",)


def test_worktree_snapshot_rejects_head_status_head_race(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _repo(tmp_path)
    (root / "a.txt").write_text("a\n", encoding="utf-8")
    _commit(root)
    real_run = subprocess.run
    head_reads = 0
    commands: list[list[str]] = []

    def raced(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        nonlocal head_reads
        commands.append(command)
        if command[-4:] == ["rev-parse", "--verify", "--end-of-options", "HEAD^{commit}"]:
            head_reads += 1
            if head_reads == 2:
                return subprocess.CompletedProcess(
                    command,
                    0,
                    stdout=b"f" * 40 + b"\n",
                    stderr=b"",
                )
        return real_run(command, **kwargs)

    monkeypatch.setattr(snapshots.subprocess, "run", raced)

    load = snapshots.worktree_snapshot(root)

    assert load.snapshot is None
    assert load.required_gaps == ("git_snapshot_head_changed",)
    assert head_reads == 2
    assert not any("ls-tree" in command for command in commands)


def test_worktree_snapshot_rejects_tracked_and_untracked_dirt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _repo(tmp_path)
    real_run = subprocess.run
    commands: list[list[str]] = []

    def recorded(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        commands.append(command)
        return real_run(command, **kwargs)

    monkeypatch.setattr(snapshots.subprocess, "run", recorded)
    path = root / "a.txt"
    path.write_text("a\n", encoding="utf-8")
    _commit(root)

    assert snapshots.worktree_snapshot(root).snapshot is not None
    status = next(command for command in commands if "status" in command)
    assert status[-4:] == ["status", "--porcelain=v2", "-z", "--untracked-files=all"]
    path.write_text("changed\n", encoding="utf-8")
    dirty = snapshots.worktree_snapshot(root)
    assert dirty.snapshot is None
    assert dirty.required_gaps == ("git_snapshot_worktree_dirty",)
    _git(root, "checkout", "--", "a.txt")
    (root / "new.txt").write_text("new\n", encoding="utf-8")
    untracked = snapshots.worktree_snapshot(root)
    assert untracked.snapshot is None
    assert untracked.required_gaps == ("git_snapshot_worktree_dirty",)


def test_snapshot_models_reject_forged_identity_order_digest_and_load_envelopes(
    tmp_path: Path,
) -> None:
    root = _repo(tmp_path)
    (root / "a.txt").write_text("a\n", encoding="utf-8")
    tree = snapshots.tree_snapshot(root, _commit(root)).snapshot
    assert tree is not None
    entry = tree.entries[0]

    with pytest.raises(ValueError, match="invalid Git tree entry"):
        snapshots.GitTreeEntry("link", "120000", "blob", entry.oid)
    with pytest.raises(ValueError, match="invalid Git tree entry"):
        snapshots.GitTreeEntry("a\x00b", entry.mode, entry.object_type, entry.oid)
    forged_entry = object.__new__(snapshots.GitTreeEntry)
    for field in ("relative_path", "mode", "object_type", "oid"):
        object.__setattr__(forged_entry, field, getattr(entry, field))
    object.__setattr__(forged_entry, "mode", "120000")
    forged_entries = (forged_entry,)
    forged_digest = _TREE_DIGEST(tree.commit_sha, tree.tree_sha, forged_entries)
    with pytest.raises(ValueError, match="invalid Git tree snapshot"):
        snapshots.GitTreeSnapshot(
            tree.commit_sha,
            tree.tree_sha,
            forged_entries,
            forged_digest,
        )
    forged_nested_tree = object.__new__(snapshots.GitTreeSnapshot)
    for field in ("commit_sha", "tree_sha", "entries", "snapshot_digest"):
        object.__setattr__(forged_nested_tree, field, getattr(tree, field))
    object.__setattr__(forged_nested_tree, "entries", forged_entries)
    object.__setattr__(forged_nested_tree, "snapshot_digest", forged_digest)
    with pytest.raises(ValueError, match="invalid Git tree snapshot load"):
        snapshots.GitTreeSnapshotLoad(forged_nested_tree, ())
    with pytest.raises(ValueError, match="invalid Git tree snapshot"):
        replace(tree, snapshot_digest="d" * 64)
    with pytest.raises(ValueError, match="invalid Git tree snapshot"):
        replace(tree, entries=(entry, entry))
    with pytest.raises(ValueError, match="invalid Git tree snapshot load"):
        snapshots.GitTreeSnapshotLoad(None, ())
    with pytest.raises(ValueError, match="invalid Git tree snapshot load"):
        snapshots.GitTreeSnapshotLoad(tree, ("gap",))

    class Gap(str):
        __slots__ = ()

    with pytest.raises(ValueError, match="non-empty strings"):
        snapshots.GitTreeSnapshotLoad(None, (Gap("gap"),))
    forged_tree = object.__new__(snapshots.GitTreeSnapshot)
    for field in ("commit_sha", "tree_sha", "entries", "snapshot_digest"):
        object.__setattr__(forged_tree, field, getattr(tree, field))
    object.__setattr__(forged_tree, "snapshot_digest", "0" * 64)
    with pytest.raises(ValueError, match="invalid Git tree snapshot load"):
        snapshots.GitTreeSnapshotLoad(forged_tree, ())
    for model in (
        snapshots.GitTreeEntry,
        snapshots.GitTreeSnapshot,
        snapshots.GitTreeSnapshotLoad,
        snapshots.SnapshotBytes,
        snapshots.SnapshotBytesLoad,
    ):
        with pytest.raises(TypeError, match="forbid subclasses"):
            type("BypassSnapshotModel", (model,), {"__slots__": ()})


def test_snapshot_bytes_reject_malformed_shapes_as_value_errors(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    (root / "a.txt").write_text("a\n", encoding="utf-8")
    tree = snapshots.tree_snapshot(root, _commit(root)).snapshot
    assert tree is not None
    blob_snapshot = snapshots.read_snapshot_blobs(root, tree, ("a.txt",)).snapshot
    assert blob_snapshot is not None
    malformed_contents = (
        None,
        [blob_snapshot.contents[0]],
        ((),),
        (object(),),
        (("a.txt", bytearray(b"a\n")),),
        ((1, b"a\n"),),
    )

    for contents in malformed_contents:
        with pytest.raises(ValueError, match="invalid snapshot bytes"):
            replace(
                blob_snapshot,
                contents=cast("tuple[tuple[str, bytes], ...]", contents),
            )
    with pytest.raises(ValueError, match="invalid snapshot bytes"):
        replace(blob_snapshot, tree_snapshot_digest=cast("str", None))
    with pytest.raises(ValueError, match="invalid snapshot bytes"):
        replace(blob_snapshot, content_digest=cast("str", None))
    nul_contents = (("a\x00b", b"a\n"),)
    nul_digest = _BYTES_DIGEST(nul_contents)
    with pytest.raises(ValueError, match="invalid snapshot bytes"):
        snapshots.SnapshotBytes(blob_snapshot.tree_snapshot_digest, nul_contents, nul_digest)
    with pytest.raises(ValueError, match="invalid snapshot bytes load"):
        snapshots.SnapshotBytesLoad(None, ())
    with pytest.raises(ValueError, match="invalid snapshot bytes load"):
        snapshots.SnapshotBytesLoad(blob_snapshot, ("gap",))
    forged_bytes = object.__new__(snapshots.SnapshotBytes)
    for field in ("tree_snapshot_digest", "contents", "content_digest"):
        object.__setattr__(forged_bytes, field, getattr(blob_snapshot, field))
    object.__setattr__(forged_bytes, "content_digest", "0" * 64)
    with pytest.raises(ValueError, match="invalid snapshot bytes load"):
        snapshots.SnapshotBytesLoad(forged_bytes, ())
    forged_nul_bytes = object.__new__(snapshots.SnapshotBytes)
    object.__setattr__(forged_nul_bytes, "tree_snapshot_digest", blob_snapshot.tree_snapshot_digest)
    object.__setattr__(forged_nul_bytes, "contents", nul_contents)
    object.__setattr__(forged_nul_bytes, "content_digest", nul_digest)
    with pytest.raises(ValueError, match="invalid snapshot bytes load"):
        snapshots.SnapshotBytesLoad(forged_nul_bytes, ())


def test_blob_selection_requires_unique_sorted_paths(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    (root / "a.txt").write_text("a\n", encoding="utf-8")
    (root / "b.txt").write_text("b\n", encoding="utf-8")
    tree = snapshots.tree_snapshot(root, _commit(root)).snapshot
    assert tree is not None

    for paths in (("b.txt", "a.txt"), ("a.txt", "a.txt")):
        load = snapshots.read_snapshot_blobs(root, tree, paths)
        assert load.snapshot is None
        assert load.required_gaps == ("git_snapshot_path_selection_invalid",)


def test_blob_reads_rebind_snapshot_to_exact_repository_and_reject_forgery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _repo(tmp_path)
    (root / "a.txt").write_text("a\n", encoding="utf-8")
    (root / "b.txt").write_text("b\n", encoding="utf-8")
    tree = snapshots.tree_snapshot(root, _commit(root)).snapshot
    assert tree is not None
    assert snapshots.read_snapshot_blobs(root, tree, ("a.txt",)).snapshot is not None

    other_parent = tmp_path / "other"
    other_parent.mkdir()
    other = _repo(other_parent)
    (other / "a.txt").write_text("a\n", encoding="utf-8")
    (other / "other.txt").write_text("different tree\n", encoding="utf-8")
    _commit(other)
    real_run = subprocess.run
    commands: list[list[str]] = []

    def recorded(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        commands.append(command)
        return real_run(command, **kwargs)

    monkeypatch.setattr(snapshots.subprocess, "run", recorded)
    cross_repo = snapshots.read_snapshot_blobs(other, tree, ("a.txt",))
    assert cross_repo.snapshot is None
    assert cross_repo.required_gaps == ("git_snapshot_identity_mismatch",)
    assert not any("cat-file" in command for command in commands)

    entries = (replace(tree.entries[0], oid=tree.entries[1].oid), tree.entries[1])
    forged = snapshots.GitTreeSnapshot(
        tree.commit_sha,
        tree.tree_sha,
        entries,
        _TREE_DIGEST(tree.commit_sha, tree.tree_sha, entries),
    )
    forged_load = snapshots.read_snapshot_blobs(root, forged, ("a.txt",))
    assert forged_load.snapshot is None
    assert forged_load.required_gaps == ("git_snapshot_identity_mismatch",)

    invalid_digest = object.__new__(snapshots.GitTreeSnapshot)
    for field in ("commit_sha", "tree_sha", "entries", "snapshot_digest"):
        object.__setattr__(invalid_digest, field, getattr(tree, field))
    object.__setattr__(invalid_digest, "snapshot_digest", "0" * 64)
    digest_load = snapshots.read_snapshot_blobs(root, invalid_digest, ("a.txt",))
    assert digest_load.snapshot is None
    assert digest_load.required_gaps == ("git_snapshot_identity_mismatch",)
