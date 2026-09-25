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


def test_occupied_installation_does_not_replace_unknown_content(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A matching name and owner marker cannot authorize damaged installed bytes."""
    repo, python = materialize_runtime_case(tmp_path, monkeypatch)
    selected = require_selected_runtime(python.parent)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "user-data"))
    installation = tmp_path / "user-data/ethos/installations" / selected.digest
    installation.mkdir(parents=True)
    marker = installation / "OWNER"
    marker.write_text(selected.digest + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="hook_runtime_host_store_conflict"):
        materialization.materialize_runtime(
            repo,
            Path(sys.executable),
            expected_build=selected.build,
            installed_runtime=selected.root,
        )
    assert marker.read_text(encoding="utf-8") == selected.digest + "\n"
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
