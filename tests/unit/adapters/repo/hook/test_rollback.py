"""A successful cutover must preserve exact predecessor supply before reclamation."""

from __future__ import annotations

import json
import shlex
import shutil
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import create_autospec

import pytest

import ethos.adapters.repo.hook.activation as activation
import ethos.adapters.repo.hook.rollback as rollback_proof
import ethos.adapters.repo.runtime.authority as runtime_authority
import ethos.adapters.repo.runtime.materialization.effect as materialization
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.hook.observation import hook_runtime_binding
from ethos.adapters.repo.runtime.authority import RuntimeBuild
from ethos.adapters.repo.runtime.authority import expected_runtime_build
from ethos.adapters.repo.runtime.interpreter import PYTHON_FLAGS
from ethos.adapters.repo.runtime.selection import activate_runtime
from ethos.adapters.repo.runtime.selection import current_runtime
from ethos.adapters.repo.runtime.selection import require_selected_runtime
from ethos.adapters.repo.runtime.selection import runtime_selection_bytes
from ethos.repository.release.identity import build_identity
from tests.support.governed_repository import git
from tests.support.governed_repository import write_tree
from tests.support.runtime_scenarios import git_process
from tests.support.runtime_scenarios import materialize_runtime_case
from tests.support.runtime_scenarios import mise_installs
from tests.support.runtime_scenarios import pinned_release_files
from tests.support.runtime_scenarios import runtime_build

if TYPE_CHECKING:
    from ethos.adapters.repo.runtime.selection import SelectedRuntime
    from ethos.repository.release.identity import BuildIdentity

_GIT = ("-c", "core.hooksPath=/dev/null", "-c", "user.name=test", "-c", "user.email=t@example.com")


def _adopter_build(selected: SelectedRuntime) -> RuntimeBuild:
    """What an adopter expects of a named runtime: that runtime's own build."""
    return RuntimeBuild(selected.build, None, invoking=True)


def _upgrade_case(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    successor_build: BuildIdentity | None = None,
) -> tuple[Path, Path, Path]:
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
        package_identity=successor_build or runtime_build("c" * 40, "d" * 40),
    )
    package = tmp_path / "package"
    shutil.copytree(Path(git_common_dir(successor_repo)) / "ethos", package / "ethos")
    supplied = package / "ethos/runtime" / successor_python.parent.name
    selected = require_selected_runtime(supplied)
    monkeypatch.setattr(
        activation,
        "expected_runtime_build",
        create_autospec(expected_runtime_build, return_value=_adopter_build(selected)),
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
    # Status names the one supported rollback: the CURRENT runtime selecting the preserved one.
    guidance = hook_runtime_binding(repo)["rollback"]
    command = shlex.split(guidance["command"])
    assert guidance["runtime"] == str(rollback)
    assert command[0] == current_runtime(Path(git_common_dir(repo))).python.as_posix()
    assert command[-7:] == [
        *("hook", "install", "--root", repo.resolve().as_posix()),
        *("--runtime", str(rollback), "--json"),
    ]
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
        create_autospec(expected_runtime_build, return_value=_adopter_build(selected)),
    )

    result = activation.install_hook_launchers(repo, installed_runtime=third)

    common = Path(git_common_dir(repo)).resolve()
    held = store / supplied.name[:16] / "runtime" / supplied.name
    assert current_runtime(common).digest == third.name
    assert (common / "ethos/runtime/ROLLBACK").read_bytes() == runtime_selection_bytes(common, held)
    assert not first.exists()
    assert result["host_store_cleanup"]["retired"] == [first.as_posix()]


def test_a_predecessor_that_no_install_would_admit_is_neither_pinned_nor_held(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Where the accepted source names the one expected build, no predecessor is a rollback."""
    repo, previous, supplied = _upgrade_case(tmp_path, monkeypatch)
    accepted = RuntimeBuild(require_selected_runtime(supplied).build, None)
    monkeypatch.setattr(activation, "expected_runtime_build", lambda *_a, **_k: accepted)
    refused = "hook_runtime_manifest_invalid"
    with pytest.raises(ValueError, match=refused):
        activation.install_hook_launchers(repo, installed_runtime=previous)

    result = activation.install_hook_launchers(repo, installed_runtime=supplied)

    assert (result["required_gaps"], result["rollback_supply"]) == (
        [],
        {"state": "unrunnable", "runtime": str(previous), "reason": refused},
    )
    assert not (Path(git_common_dir(repo)) / "ethos/runtime/ROLLBACK").exists()
    assert not (tmp_path / "user-data/ethos/installations" / previous.name[:16]).exists()
    assert "rollback" not in hook_runtime_binding(repo, prove_rollback=True)


@pytest.mark.parametrize("cause", ["lost", "another-build"])
def test_status_reports_a_rollback_that_cannot_run_and_the_next_install_releases_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cause: str
) -> None:
    """A held rollback that no install can admit has one repair: the current console's install."""
    repo, _previous, supplied = _upgrade_case(tmp_path, monkeypatch)
    cutover = activation.install_hook_launchers(repo, installed_runtime=supplied)
    held = Path(cutover["rollback_supply"]["runtime"])
    common = Path(git_common_dir(repo))
    console = (current_runtime(common).python.as_posix(), *PYTHON_FLAGS, "-m", "ethos.cli")
    assert "command" in hook_runtime_binding(repo, prove_rollback=True)["rollback"]
    if cause == "lost":
        materialization.remove_generated_tree(held.parents[1])
    else:
        # The accepted source now names the one build an install admits, as a product's own does.
        accepted = RuntimeBuild(require_selected_runtime(supplied).build, None)
        for owner in (activation, runtime_authority):
            monkeypatch.setattr(owner, "expected_runtime_build", lambda *_a, **_k: accepted)
    gap = (
        "hook_runtime_current_target_invalid"
        if cause == "lost"
        else "hook_runtime_manifest_invalid"
    )
    lost = {"runtime": str(held), "reason": gap}

    assert hook_runtime_binding(repo, prove_rollback=True)["rollback"] == lost | {
        "state": "unrunnable",
        "next_action": shlex.join((*console, "hook", "install", "--root", str(repo), "--json")),
    }
    # Only an inspection proves the rollback; any other reader names the command as before.
    assert "command" in hook_runtime_binding(repo)["rollback"]
    released = activation.install_hook_launchers(repo, installed_runtime=supplied)
    assert (released["rollback_released"], (common / "ethos/runtime/ROLLBACK").exists()) == (
        lost,
        False,
    )
    assert "rollback" not in released
    assert "rollback" not in hook_runtime_binding(repo, prove_rollback=True)


def test_activation_selects_the_pinned_install_and_a_lane_rolls_back_with_a_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A fixture adopter moves forward to its accepted pin, then holds a receipted rollback."""
    source = {"source_commit": "c" * 40, "source_tree": "d" * 40}
    pinned = build_identity(product="9.3.0", release=True, **source)
    repo, previous, supplied = _upgrade_case(tmp_path, monkeypatch, pinned)
    monkeypatch.setattr(activation, "expected_runtime_build", expected_runtime_build)
    probed: list[Path] = []
    monkeypatch.setattr(
        activation, "rollback_preflight", lambda _root, target, **_k: probed.append(target.root)
    )
    write_tree(repo, pinned_release_files("9.3.0"))
    git(repo, "add", ".config")
    assert git_process(repo, *_GIT, "commit", "-m", "chore: pin").returncode == 0
    mise_installs(monkeypatch, {"9.3.0": supplied.parents[1]})
    common, lane = Path(git_common_dir(repo)).resolve(), tmp_path / "lane"
    selector, receipt = (
        common / "ethos/runtime/CURRENT",
        common / "ethos/receipts/runtime-selection",
    )

    forward = activation.install_hook_launchers(repo)

    assert forward["runtime_pin"] == {"state": "followed", "next_action": ""}
    assert (current_runtime(common).digest, probed) == (supplied.name, [supplied])
    rollback = Path(forward["rollback_supply"]["runtime"])
    git(repo, "worktree", "add", "-qb", "work/back", lane.as_posix())
    with pytest.raises(rollback_proof.RollbackRefusalError, match="receipt_required"):
        activation.install_hook_launchers(lane, installed_runtime=rollback)
    assert current_runtime(common).digest == supplied.name
    native, kinds = materialization.materialize_runtime, []

    def materialize(*arguments: object, **named: object) -> Path:
        """Read the receipt at the first effect: it is written before anything is pinned."""
        kinds.append(json.loads((receipt / "9.3.0.json").read_bytes())["kind"])
        return native(*arguments, **named)

    monkeypatch.setattr(materialization, "materialize_runtime", materialize)
    back = activation.install_hook_launchers(lane, installed_runtime=rollback, reason="a defect")

    assert (kinds, back["selection_receipt"]["kind"]) == (["rollback"], "rollback")
    assert current_runtime(common).digest == previous.name
    before = selector.read_bytes()
    held = activation.install_hook_launchers(repo)
    assert held["runtime_pin"] == {"state": "runtime_selection_open", "next_action": ""}
    assert (selector.read_bytes(), kinds) == (before, ["rollback"])
    # The lane's ref closes the receipt: the next transition deletes it and follows the pin.
    git(repo, "worktree", "remove", "--force", lane.as_posix())
    git(repo, "branch", "-D", "work/back")
    monkeypatch.setattr(materialization, "materialize_runtime", native)
    again = activation.install_hook_launchers(repo)
    assert (again["runtime_pin"]["state"], list(receipt.glob("*"))) == ("followed", [])
    assert current_runtime(common).digest == supplied.name
