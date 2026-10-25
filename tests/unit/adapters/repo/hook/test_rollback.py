"""A successful cutover must preserve exact predecessor supply before reclamation."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import create_autospec

import pytest

import ethos.adapters.repo.hook.activation as activation
import ethos.adapters.repo.runtime.materialization.effect as materialization
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.runtime.authority import RuntimeBuild
from ethos.adapters.repo.runtime.authority import expected_runtime_build
from ethos.adapters.repo.runtime.selection import activate_runtime
from ethos.adapters.repo.runtime.selection import current_runtime
from ethos.adapters.repo.runtime.selection import require_selected_runtime
from ethos.adapters.repo.runtime.selection import runtime_selection_bytes
from tests.support.runtime_scenarios import materialize_runtime_case
from tests.support.runtime_scenarios import runtime_build

if TYPE_CHECKING:
    from ethos.adapters.repo.runtime.selection import SelectedRuntime


def _upgrade_case(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path, Path]:
    """Keep native activation and supply effects, replacing only image construction."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "user-data"))
    original, successor = tmp_path / "original", tmp_path / "successor"
    original.mkdir()
    successor.mkdir()
    repo, previous_python = materialize_runtime_case(original, monkeypatch)
    activation.install_hook_launchers(repo)
    successor_repo, successor_python = materialize_runtime_case(
        successor,
        monkeypatch,
        package_identity=runtime_build("c" * 40, "d" * 40),
    )
    package = tmp_path / "package"
    shutil.copytree(Path(git_common_dir(successor_repo)) / "ethos", package / "ethos")
    supplied = package / "ethos/runtime" / successor_python.parent.name
    selected = require_selected_runtime(supplied)
    monkeypatch.setattr(
        activation,
        "expected_runtime_build",
        create_autospec(expected_runtime_build, return_value=RuntimeBuild(selected.build, None)),
    )
    return repo, previous_python.parent, supplied


def test_cutover_preserves_exact_predecessor_after_local_reclamation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Deleting the local old generation cannot remove the only rollback bytes."""
    repo, previous, supplied = _upgrade_case(tmp_path, monkeypatch)
    original = require_selected_runtime(previous)
    manifest = original.manifest.read_bytes()
    package = previous.parent.parent / "packages" / original.wheel_sha256
    wheel = next(package.glob("ethos-*.whl"))
    wheel_bytes = wheel.read_bytes()

    result = activation.install_hook_launchers(repo, installed_runtime=supplied)

    assert "rollback_supply" in result, "Successful cutover discarded the rollback supply"
    rollback = Path(result["rollback_supply"]["runtime"])
    assert rollback != previous
    assert require_selected_runtime(rollback).digest == original.digest
    assert (rollback / "manifest.json").read_bytes() == manifest
    retained_wheel = rollback.parent.parent / "packages" / original.wheel_sha256 / wheel.name
    assert retained_wheel.read_bytes() == wheel_bytes
    assert not previous.exists()
    assert str(previous) in result["generation_cleanup"]["removed"]
    assert current_runtime(Path(git_common_dir(repo))).digest == supplied.name
    assert result["required_gaps"] == []
    before = {path.name for path in rollback.parents[1].parent.iterdir()}
    for _ in range(2):
        repeated = activation.install_hook_launchers(repo, installed_runtime=supplied)
        assert repeated["required_gaps"] == []
        assert {path.name for path in rollback.parents[1].parent.iterdir()} == before
        assert require_selected_runtime(rollback).digest == original.digest


def test_failed_predecessor_pin_leaves_original_activation_untouched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unowned host content cannot turn a preservation failure into old deletion."""
    repo, previous, supplied = _upgrade_case(tmp_path, monkeypatch)
    common = Path(git_common_dir(repo))
    selector = common / "ethos/runtime/CURRENT"
    before = selector.read_bytes()
    occupied = tmp_path / "user-data/ethos/installations" / previous.name[:16]
    occupied.mkdir(parents=True)
    marker = occupied / "OWNER"
    marker.write_text("foreign installation\n", encoding="utf-8")

    with pytest.raises(ValueError, match="hook_runtime_host_store_conflict"):
        activation.install_hook_launchers(repo, installed_runtime=supplied)

    assert selector.read_bytes() == before
    assert current_runtime(common).root == previous
    assert marker.read_text(encoding="utf-8") == "foreign installation\n"


def test_failed_cutover_restores_original_selector_and_retains_both_supplies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Configuration failure rolls back without deleting retained immutable supply."""
    repo, previous, supplied = _upgrade_case(tmp_path, monkeypatch)
    common = Path(git_common_dir(repo))
    selector = common / "ethos/runtime/CURRENT"
    before = selector.read_bytes()
    hooks_before = activation.config_effects.config_values(repo, ("core.hooksPath",), scope="local")

    def reject_config(*_args: object, **_kwargs: object) -> None:
        message = "injected activation config failure"
        raise ValueError(message)

    monkeypatch.setattr(activation.config_effects, "set_common_config", reject_config)
    with pytest.raises(ValueError, match="injected activation config failure"):
        activation.install_hook_launchers(repo, installed_runtime=supplied)

    assert selector.read_bytes() == before
    assert current_runtime(common).root == previous
    assert (
        activation.config_effects.config_values(repo, ("core.hooksPath",), scope="local")
        == hooks_before
    )
    store = tmp_path / "user-data/ethos/installations"
    for source in (previous, supplied):
        pinned = store / source.name[:16] / "runtime" / source.name
        assert require_selected_runtime(pinned).digest == source.name


def test_concurrent_selection_cannot_be_overwritten_by_cutover(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Preservation must not authorize overwriting another install's selected identity."""
    repo, previous, supplied = _upgrade_case(tmp_path, monkeypatch)
    common = Path(git_common_dir(repo))
    external = tmp_path / "concurrent" / "ethos"
    shutil.copytree(previous.parent.parent, external)
    peer = external / "runtime" / previous.name
    pin = materialization.pin_installed_runtime

    def select_peer(selected: SelectedRuntime, **kwargs: Path) -> Path:
        result = pin(selected, **kwargs)
        if selected.root == previous:
            activate_runtime(common, peer)
        return result

    monkeypatch.setattr(materialization, "pin_installed_runtime", select_peer)
    with pytest.raises(ValueError, match="hook_runtime_current_stale") as failure:
        activation.install_hook_launchers(repo, installed_runtime=supplied)

    assert str(failure.value) == "hook_runtime_current_stale"
    assert current_runtime(common).root == peer
    assert require_selected_runtime(previous).digest == previous.name


def test_repairing_invalid_local_predecessor_preserves_uncertainty_and_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Valid new supply can repair activation without pretending damaged old bytes work."""
    repo, previous, supplied = _upgrade_case(tmp_path, monkeypatch)
    damaged = previous / "python/lib/python3.14/site-packages/ethos/module.py"
    damaged.chmod(0o644)
    damaged.write_bytes(b"damaged predecessor\n")

    result = activation.install_hook_launchers(repo, installed_runtime=supplied)

    assert result["required_gaps"] == []
    assert current_runtime(Path(git_common_dir(repo))).digest == supplied.name
    assert result["rollback_supply"]["state"] == "unavailable"
    assert result["rollback_supply"]["runtime"] == previous.as_posix()
    assert result["rollback_supply"]["reason"] == "hook_runtime_payload_mismatch"
    assert str(previous) not in result["generation_cleanup"]["removed"]
    assert damaged.read_bytes() == b"damaged predecessor\n"


@pytest.mark.parametrize("missing", [True, False])
def test_valid_successor_repairs_unavailable_external_predecessor_without_deleting_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, missing: bool
) -> None:
    """An admitted successor does not depend on damaged or absent rollback supply."""
    repo, previous, supplied = _upgrade_case(tmp_path, monkeypatch)
    common = Path(git_common_dir(repo))
    external = tmp_path / "external" / "runtime" / previous.name
    if not missing:
        shutil.copytree(previous, external)
        manifest = external / "manifest.json"
        manifest.chmod(0o644)
        manifest.write_bytes(b"damaged predecessor\n")
    selector = common / "ethos/runtime/CURRENT"
    selector.write_bytes(runtime_selection_bytes(common, external))

    result = activation.install_hook_launchers(repo, installed_runtime=supplied)

    assert result["required_gaps"] == []
    assert current_runtime(common).digest == supplied.name
    assert result["rollback_supply"] == {
        "state": "unavailable",
        "runtime": external.as_posix(),
        "reason": "hook_runtime_current_target_invalid"
        if missing
        else "hook_runtime_manifest_invalid",
    }
    assert str(external) not in result["generation_cleanup"]["removed"]
    if missing:
        assert not external.exists()
    else:
        assert (external / "manifest.json").read_bytes() == b"damaged predecessor\n"


@pytest.mark.parametrize("selection", [b"", b"invalid\n\n", b"\xff\n"])
def test_admitted_successor_repairs_malformed_selection_without_reading_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, selection: bytes
) -> None:
    """Malformed selector bytes are an unavailable predecessor, never a successor veto."""
    repo, previous, supplied = _upgrade_case(tmp_path, monkeypatch)
    common = Path(git_common_dir(repo))
    (common / "ethos/runtime/CURRENT").write_bytes(selection)

    result = activation.install_hook_launchers(repo, installed_runtime=supplied)

    assert result["required_gaps"] == []
    assert current_runtime(common).digest == supplied.name
    assert result["rollback_supply"] == {
        "state": "unavailable",
        "reason": "hook_runtime_current_invalid",
    }
    cleanup = result["generation_cleanup"]
    assert cleanup["state"] == "complete"
    assert previous.name in {Path(path).name for path in cleanup["unproven_removals"]}
    assert previous.name not in {Path(path).name for path in cleanup["removed"]}
    assert previous.is_dir()


def test_a_superseded_rollback_installation_is_retired_by_the_next_cutover(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each cutover holds one rollback supply; the one it supersedes leaves the host store."""
    repo, previous, supplied = _upgrade_case(tmp_path, monkeypatch)
    activation.install_hook_launchers(repo, installed_runtime=supplied)
    store = (tmp_path / "user-data/ethos/installations").resolve()
    first = store / previous.name[:16]
    assert first.is_dir()
    (tmp_path / "third").mkdir()
    third_repo, third_python = materialize_runtime_case(
        tmp_path / "third", monkeypatch, package_identity=runtime_build("e" * 40, "f" * 40)
    )
    package = tmp_path / "third-package"
    shutil.copytree(Path(git_common_dir(third_repo)) / "ethos", package / "ethos")
    third = package / "ethos/runtime" / third_python.parent.name
    selected = require_selected_runtime(third)
    monkeypatch.setattr(
        activation,
        "expected_runtime_build",
        create_autospec(expected_runtime_build, return_value=RuntimeBuild(selected.build, None)),
    )

    result = activation.install_hook_launchers(repo, installed_runtime=third)

    common = Path(git_common_dir(repo)).resolve()
    held = store / supplied.name[:16] / "runtime" / supplied.name
    assert current_runtime(common).digest == third.name
    assert (common / "ethos/runtime/ROLLBACK").read_bytes() == runtime_selection_bytes(common, held)
    assert not first.exists()
    assert result["host_store_cleanup"]["retired"] == [first.as_posix()]
