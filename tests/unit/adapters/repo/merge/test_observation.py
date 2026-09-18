"""Native merge observation rejects unsafe metadata and unrecoverable preimages."""

import errno
from pathlib import Path
from types import SimpleNamespace

import pytest

import ethos.adapters.repo.merge.observation as observation
import ethos.adapters.repo.merge.recovery as recovery
from ethos.adapters.repo.merge.recovery import preserve_merge
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo


@pytest.mark.parametrize("kind", ["missing", "directory", "symlink"])
def test_metadata_never_reads_missing_or_redirected_native_content(tmp_path: Path, kind: str):
    """Replacing no-follow regular-file admission would expose redirected metadata."""
    path = tmp_path / "MERGE_HEAD"
    if kind == "missing":
        assert observation.metadata_bytes(path) is None
        return
    if kind == "directory":
        path.mkdir()
        with pytest.raises((IsADirectoryError, ValueError)):
            observation.metadata_bytes(path)
    else:
        outside = tmp_path / "outside"
        outside.write_bytes(b"must not become merge metadata")
        path.symlink_to(outside)
        with pytest.raises(ValueError, match="merge_metadata_unsafe"):
            observation.metadata_bytes(path)
        assert outside.read_bytes() == b"must not become merge metadata"


@pytest.mark.parametrize("boundary", ["unsafe", "open-replacement", "read-replacement"])
def test_rejected_metadata_releases_descriptors_and_preserves_replacement(
    tmp_path, monkeypatch, boundary
):
    """Unsafe handles and either replacement window fail without leaking descriptors."""
    path, replacement = tmp_path / "MERGE_HEAD", tmp_path / "replacement"
    path.write_bytes(b"unchanged bytes")
    replacement.write_bytes(b"unchanged bytes")
    native_open, native_fstat = observation.os.open, observation.os.fstat
    descriptors, calls = [], []

    def opened(*args, **kwargs):
        if boundary == "open-replacement":
            replacement.replace(path)
        descriptor = native_open(*args, **kwargs)
        descriptors.append(descriptor)
        return descriptor

    def observed(descriptor):
        calls.append(descriptor)
        if boundary == "unsafe":
            return SimpleNamespace(st_mode=0)
        if boundary == "read-replacement" and len(calls) == 2:
            replacement.replace(path)
        return native_fstat(descriptor)

    with monkeypatch.context() as patch:
        patch.setattr(observation.os, "open", opened)
        patch.setattr(observation.os, "fstat", observed)
        error = "merge_metadata_unsafe" if boundary == "unsafe" else "merge_metadata_changed"
        with pytest.raises(ValueError, match=error):
            observation.metadata_bytes(path)
    assert len(descriptors) == 1
    try:
        with pytest.raises(OSError, match="Bad file descriptor") as error:
            native_fstat(descriptors[0])
        assert error.value.errno == errno.EBADF
        assert path.read_bytes() == b"unchanged bytes"
    finally:
        try:
            observation.os.close(descriptors[0])
        except OSError as error:
            if error.errno != errno.EBADF:
                raise


@pytest.mark.parametrize("drift", ["none", "descriptor", "path", "access-time"])
def test_metadata_compares_changes_within_each_native_observation_channel(
    tmp_path, monkeypatch, drift
):
    """Different stable path/handle ctime meanings never weaken same-channel drift checks."""
    path = tmp_path / "MERGE_HEAD"
    path.write_bytes(b"native bytes")
    fstat, path_stat = observation.os.fstat, Path.stat
    calls = {"descriptor": 0, "path": 0}

    def observed(channel, value):
        calls[channel] += 1
        fields = {name: getattr(value, name) for name in dir(value) if name.startswith("st_")}
        fields["st_ctime_ns"] += 1000 if channel == "descriptor" else 0
        fields["st_ctime_ns"] += int(drift == channel and calls[channel] == 2)
        fields["st_atime_ns"] += calls[channel] if drift == "access-time" else 0
        return SimpleNamespace(**fields)

    monkeypatch.setattr(observation.os, "fstat", lambda fd: observed("descriptor", fstat(fd)))
    monkeypatch.setattr(
        Path,
        "stat",
        lambda p, **kw: observed("path", path_stat(p, **kw)) if p == path else path_stat(p, **kw),
    )
    if drift in {"none", "access-time"}:
        assert observation.metadata_bytes(path) == b"native bytes"
    else:
        with pytest.raises(ValueError, match="merge_metadata_changed"):
            observation.metadata_bytes(path)


def test_parent_must_resolve_to_its_exact_commit_identity(tmp_path: Path):
    """An arbitrary forty-digit spelling cannot masquerade as an existing parent."""
    root = init_git_repo(tmp_path / "repo")
    metadata = observation.git_path(root, "MERGE_HEAD")
    metadata.write_text("0" * 40 + "\n")
    with pytest.raises(ValueError, match="merge_parent_invalid"):
        observation.observe_merge(root)
    assert metadata.read_text() == "0" * 40 + "\n"


def test_recovery_does_not_follow_a_redirected_parent_directory(tmp_path: Path):
    """A tracked path replaced by a directory symlink cannot read external content."""
    root = init_git_repo(tmp_path / "repo")
    folder = root / "nested"
    folder.mkdir()
    (folder / "value").write_bytes(b"staged value")
    git(root, "add", "nested/value")
    before = observation.observe_merge(root)
    (folder / "value").unlink()
    folder.rmdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "value").write_bytes(b"outside value")
    folder.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="merge_recovery_parent_unsafe"):
        preserve_merge(root, before)
    assert (outside / "value").read_bytes() == b"outside value"
    assert folder.is_symlink()


def test_recovery_rejects_submodule_without_losing_the_native_index(tmp_path: Path):
    """A gitlink is a commit reference, not an ordinary restorable blob."""
    root = init_git_repo(tmp_path / "repo")
    parent = git(root, "rev-parse", "HEAD")
    git(root, "update-index", "--add", "--cacheinfo", f"160000,{parent},submodule")
    before = observation.observe_merge(root)
    with pytest.raises(ValueError, match="merge_submodule_recovery_unsupported"):
        preserve_merge(root, before)
    assert observation.observe_merge(root) == before


def test_disappearing_recovery_file_is_not_recorded_as_valid_content(tmp_path: Path, monkeypatch):
    """A disappearance between lstat and read invalidates preservation."""
    root = init_git_repo(tmp_path / "repo")
    path = root / "README.md"
    path.write_text("valuable uncommitted edit\n")
    before = observation.observe_merge(root)
    original = recovery.metadata_bytes

    def disappear(selected):
        if selected == path:
            path.unlink()
        return original(selected)

    monkeypatch.setattr(recovery, "metadata_bytes", disappear)
    with pytest.raises(ValueError, match="merge_state_stale"):
        preserve_merge(root, before)
