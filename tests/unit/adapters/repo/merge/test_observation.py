"""Native merge observation rejects unsafe metadata and unrecoverable preimages."""

import errno
from pathlib import Path

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
        with pytest.raises(OSError, match="symbolic links") as failure:
            observation.metadata_bytes(path)
        assert failure.value.errno == errno.ELOOP
        assert outside.read_bytes() == b"must not become merge metadata"


def test_rejected_metadata_releases_its_open_descriptor(tmp_path: Path, monkeypatch):
    """Repeated unsafe observations must not leak native descriptors."""
    path = tmp_path / "MERGE_HEAD"
    path.mkdir()
    descriptors = []
    original = observation.os.open

    def remember_descriptor(*args, **kwargs):
        descriptor = original(*args, **kwargs)
        descriptors.append(descriptor)
        return descriptor

    monkeypatch.setattr(observation.os, "open", remember_descriptor)
    with pytest.raises((IsADirectoryError, ValueError)):
        observation.metadata_bytes(path)
    assert len(descriptors) == 1
    descriptor = descriptors[0]
    try:
        with pytest.raises(OSError, match="Bad file descriptor") as failure:
            observation.os.fstat(descriptor)
        assert failure.value.errno == errno.EBADF
    finally:
        try:
            observation.os.close(descriptor)
        except OSError as failure:
            if failure.errno != errno.EBADF:
                raise


def test_metadata_replacement_during_read_is_rejected(tmp_path: Path, monkeypatch):
    """A replaced inode with identical bytes is not the admitted file observation."""
    path = tmp_path / "MERGE_HEAD"
    path.write_bytes(b"unchanged bytes")
    replacement = tmp_path / "replacement"
    replacement.write_bytes(b"unchanged bytes")
    original = observation.os.fstat
    calls = 0

    def replace_after_read(descriptor):
        nonlocal calls
        calls += 1
        if calls == 2:
            replacement.replace(path)
        return original(descriptor)

    monkeypatch.setattr(observation.os, "fstat", replace_after_read)
    with pytest.raises(ValueError, match="merge_metadata_changed"):
        observation.metadata_bytes(path)
    assert path.read_bytes() == b"unchanged bytes"


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
