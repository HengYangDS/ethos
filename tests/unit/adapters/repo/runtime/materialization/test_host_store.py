"""Installed supply must outlive its package-manager carrier."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

import ethos.adapters.repo.runtime.materialization.effect as materialization
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.runtime.selection import require_selected_runtime
from tests.support.runtime_scenarios import materialize_runtime_case


def test_explicit_installed_supply_is_pinned_before_repository_selection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Removing the package carrier cannot delete a repository's selected bytes."""
    repo, python = materialize_runtime_case(tmp_path, monkeypatch)
    selected = require_selected_runtime(python.parent)
    package = tmp_path / "package"
    shutil.copytree(Path(git_common_dir(repo)) / "ethos", package / "ethos", symlinks=True)
    supplied = package / "ethos/runtime" / selected.digest
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "user-data"))

    pinned_python = materialization.materialize_runtime(
        repo,
        Path(sys.executable),
        expected_build=selected.build,
        installed_runtime=supplied,
    )
    expected = (
        tmp_path
        / "user-data/ethos/installations"
        / selected.digest
        / "ethos/runtime"
        / selected.digest
    )
    assert pinned_python == expected / "python"
    assert {item.name for item in expected.parents[2].iterdir()} == {"OWNER", "ethos"}
    materialization.remove_generated_tree(package)
    assert require_selected_runtime(expected).digest == selected.digest
    assert (
        materialization.materialize_runtime(
            repo,
            Path(sys.executable),
            expected_build=selected.build,
            installed_runtime=expected,
        )
        == pinned_python
    )


def test_host_store_recovery_preserves_unowned_directory_with_a_valid_looking_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A marker alone cannot make an arbitrary directory safe to delete."""
    repo, python = materialize_runtime_case(tmp_path, monkeypatch)
    selected = require_selected_runtime(python.parent)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "user-data"))
    monkeypatch.setattr(materialization, "_runtime_supply_current", lambda *_args: True)
    store = tmp_path / "user-data/ethos/installations"
    foreign = store / ".pin-foreign"
    foreign.mkdir(parents=True)
    marker = store / ".pin-foreign.owner"
    marker.write_text("a" * 64 + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="hook_runtime_host_store_residue_unreviewed"):
        materialization.materialize_runtime(
            repo,
            Path(sys.executable),
            expected_build=selected.build,
            installed_runtime=selected.root,
        )
    assert foreign.is_dir()
    assert marker.is_file()


def test_interrupted_owned_import_is_recovered_before_new_selection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A released host lock permits exact cleanup of only its marked staging."""
    repo, python = materialize_runtime_case(tmp_path, monkeypatch)
    selected = require_selected_runtime(python.parent)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "user-data"))
    store = tmp_path / "user-data/ethos/installations"
    staging = store / (".pin-" + "a" * 32)
    staging.mkdir(parents=True)
    (staging / "OWNER").write_text(selected.digest + "\n", encoding="utf-8")
    (staging / "partial").write_bytes(b"incomplete")
    marker = staging.with_name(staging.name + ".owner")
    marker.write_text(selected.digest + "\n", encoding="utf-8")

    pinned = materialization.materialize_runtime(
        repo,
        Path(sys.executable),
        expected_build=selected.build,
        installed_runtime=selected.root,
    )
    assert not staging.exists()
    assert not marker.exists()
    assert require_selected_runtime(pinned.parent).digest == selected.digest


@pytest.mark.parametrize("fault", ["invalid_owner", "missing_runtime"])
def test_occupied_installation_does_not_replace_unknown_content(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    """A matching name and owner marker cannot authorize damaged installed bytes."""
    repo, python = materialize_runtime_case(tmp_path, monkeypatch)
    selected = require_selected_runtime(python.parent)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "user-data"))
    installation = tmp_path / "user-data/ethos/installations" / selected.digest
    installation.mkdir(parents=True)
    marker = installation / "OWNER"
    owner = selected.digest + "\n" if fault == "missing_runtime" else "foreign\n"
    marker.write_text(owner, encoding="utf-8")

    with pytest.raises(ValueError, match="hook_runtime_host_store_conflict"):
        materialization.materialize_runtime(
            repo,
            Path(sys.executable),
            expected_build=selected.build,
            installed_runtime=selected.root,
        )
    assert marker.read_text(encoding="utf-8") == owner
    assert sorted(item.name for item in installation.iterdir()) == ["OWNER"]


def test_source_wheel_disappearing_after_admission_fails_without_partial_installation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An input race must not become an unhandled iterator error or selected supply."""
    repo, python = materialize_runtime_case(tmp_path, monkeypatch)
    selected = require_selected_runtime(python.parent)
    wheel = Path(git_common_dir(repo)) / "ethos/packages" / selected.wheel_sha256 / "ethos-test.whl"
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "user-data"))

    def remove_after_observation(runtime, project):
        assert runtime.root == selected.root
        assert project.is_dir()
        wheel.unlink()
        return True

    monkeypatch.setattr(materialization, "_runtime_supply_current", remove_after_observation)
    with pytest.raises(ValueError, match="hook_runtime_installed_supply_invalid"):
        materialization.materialize_runtime(
            repo,
            Path(sys.executable),
            expected_build=selected.build,
            installed_runtime=selected.root,
        )
    store = tmp_path / "user-data/ethos/installations"
    assert not any(path.is_dir() for path in store.iterdir())


@pytest.mark.parametrize("mode", ["relative", "native", "symlink"])
def test_host_store_location_is_explicit_and_does_not_follow_an_unsafe_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    """A native user location works; relative or redirected declarations do not."""
    repo, python = materialize_runtime_case(tmp_path, monkeypatch)
    selected = require_selected_runtime(python.parent)
    if mode == "relative":
        monkeypatch.setenv("XDG_DATA_HOME", "relative-data")
    elif mode == "native":
        monkeypatch.delenv("XDG_DATA_HOME", raising=False)
        monkeypatch.setattr(
            materialization, "user_data_path", lambda *_args, **_kwargs: tmp_path / "native-data"
        )
    else:
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "user-data"))
        store = tmp_path / "user-data/ethos/installations"
        store.parent.mkdir(parents=True)
        foreign = tmp_path / "foreign"
        foreign.mkdir()
        store.symlink_to(foreign, target_is_directory=True)

    if mode == "native":
        pinned = materialization.materialize_runtime(
            repo,
            Path(sys.executable),
            expected_build=selected.build,
            installed_runtime=selected.root,
        )
        assert pinned.parent.is_relative_to(tmp_path / "native-data/installations")
        return
    with pytest.raises(ValueError, match="hook_runtime_host_store_invalid"):
        materialization.materialize_runtime(
            repo,
            Path(sys.executable),
            expected_build=selected.build,
            installed_runtime=selected.root,
        )
    if mode == "symlink":
        assert store.is_symlink()
        assert not tuple(foreign.iterdir())


def test_existing_host_installation_reuses_valid_bytes_and_rejects_damaged_wheel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A second import reuses one generation, but wheel drift cannot pass as reuse."""
    repo, python = materialize_runtime_case(tmp_path, monkeypatch)
    selected = require_selected_runtime(python.parent)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "user-data"))
    first = materialization.materialize_runtime(
        repo,
        Path(sys.executable),
        expected_build=selected.build,
        installed_runtime=selected.root,
    )
    second = materialization.materialize_runtime(
        repo,
        Path(sys.executable),
        expected_build=selected.build,
        installed_runtime=selected.root,
    )
    assert second == first
    installation = first.parent.parents[2]
    wheel = next((installation / "ethos/packages" / selected.wheel_sha256).glob("ethos-*.whl"))
    wheel.write_bytes(b"tampered wheel")
    with pytest.raises(ValueError, match="hook_runtime_host_store_conflict"):
        materialization.materialize_runtime(
            repo,
            Path(sys.executable),
            expected_build=selected.build,
            installed_runtime=selected.root,
        )
    assert wheel.read_bytes() == b"tampered wheel"


@pytest.mark.parametrize("fault", ["copy", "postcopy"])
def test_failed_host_import_cleans_only_its_own_staging(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    """A failed copy or verification leaves no selected or half-installed generation."""
    repo, python = materialize_runtime_case(tmp_path, monkeypatch)
    selected = require_selected_runtime(python.parent)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "user-data"))
    if fault == "copy":
        copyfile = materialization.shutil.copyfile

        def fail_copy(source, target, *, follow_symlinks=True):
            if Path(source).suffix == ".whl":
                message = "wheel copy failed"
                raise OSError(message)
            return copyfile(source, target, follow_symlinks=follow_symlinks)

        monkeypatch.setattr(materialization.shutil, "copyfile", fail_copy)
        reason = "hook_runtime_installed_supply_invalid"
    else:
        monkeypatch.setattr(
            materialization,
            "_runtime_supply_current",
            lambda runtime, _project: runtime.root == selected.root,
        )
        reason = "hook_runtime_host_store_copy_invalid"
    with pytest.raises(ValueError, match=reason):
        materialization.materialize_runtime(
            repo,
            Path(sys.executable),
            expected_build=selected.build,
            installed_runtime=selected.root,
        )
    store = tmp_path / "user-data/ethos/installations"
    assert not any(path.is_dir() for path in store.iterdir())
    assert not list(store.glob(".pin-*"))


@pytest.mark.parametrize("paired", [False, True])
def test_malformed_interrupted_import_is_preserved_for_review(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, paired: bool
) -> None:
    """An invalid ownership marker never authorizes deletion or installation."""
    repo, python = materialize_runtime_case(tmp_path, monkeypatch)
    selected = require_selected_runtime(python.parent)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "user-data"))
    store = tmp_path / "user-data/ethos/installations"
    store.mkdir(parents=True)
    staging = store / (".pin-" + "b" * 32)
    if paired:
        staging.mkdir()
        (staging / "partial").write_bytes(b"keep")
    marker = staging.with_name(staging.name + ".owner")
    marker.write_text("invalid\n", encoding="utf-8")
    with pytest.raises(ValueError, match="hook_runtime_host_store_residue_unreviewed"):
        materialization.materialize_runtime(
            repo,
            Path(sys.executable),
            expected_build=selected.build,
            installed_runtime=selected.root,
        )
    assert marker.read_bytes() == b"invalid\n"
    assert staging.exists() is paired


def test_orphaned_valid_marker_is_recovered_without_touching_other_content(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A crash after atomic exposure leaves only an owned marker to remove."""
    repo, python = materialize_runtime_case(tmp_path, monkeypatch)
    selected = require_selected_runtime(python.parent)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "user-data"))
    store = tmp_path / "user-data/ethos/installations"
    store.mkdir(parents=True)
    marker = store / (".pin-" + "c" * 32 + ".owner")
    marker.write_text(selected.digest + "\n", encoding="utf-8")
    foreign = store / "user-owned.txt"
    foreign.write_text("preserve", encoding="utf-8")
    pinned = materialization.materialize_runtime(
        repo,
        Path(sys.executable),
        expected_build=selected.build,
        installed_runtime=selected.root,
    )
    assert not marker.exists()
    assert foreign.read_text(encoding="utf-8") == "preserve"
    assert require_selected_runtime(pinned.parent).digest == selected.digest
