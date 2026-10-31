"""Installed supply must outlive its package-manager carrier."""

from __future__ import annotations

import os
import shutil
import stat
import sys
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest

import ethos.adapters.repo.runtime.host_store as host_store
import ethos.adapters.repo.runtime.materialization.effect as materialization
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.runtime.selection import activate_runtime
from ethos.adapters.repo.runtime.selection import require_selected_runtime
from tests.support.runtime_scenarios import REPOSITORY_ROOT
from tests.support.runtime_scenarios import git_process
from tests.support.runtime_scenarios import materialize_runtime_case
from tests.support.runtime_scenarios import runtime_build

if TYPE_CHECKING:
    from ethos.repository.release.identity import BuildIdentity


def _host_case(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Select one materialized runtime and direct host supply into a test-owned store."""
    repo, python = materialize_runtime_case(tmp_path, monkeypatch)
    selected = require_selected_runtime(python.parent)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "user-data"))
    return repo, selected, tmp_path / "user-data/ethos/installations"


def _materialized(root: Path, monkeypatch: pytest.MonkeyPatch, **options: object):
    """Materialize and select one runtime case in its own fresh directory."""
    root.mkdir()
    repo, python = materialize_runtime_case(root, monkeypatch, **options)
    return repo, require_selected_runtime(python.parent)


def _package_supply(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Copy another repository's selected runtime into a package-manager carrier."""
    source_repo, selected = _materialized(tmp_path / "source", monkeypatch)
    package = tmp_path / "package/ethos"
    shutil.copytree(Path(git_common_dir(source_repo)) / "ethos", package, symlinks=True)
    return require_selected_runtime(package / "runtime" / selected.digest)


def _adopter(root: Path) -> Path:
    """Initialize one fresh repository that has selected no runtime."""
    root.mkdir()
    assert git_process(root, "init", "--quiet", "--initial-branch=dev").returncode == 0
    return root


def _pin(repo: Path, build: BuildIdentity, **options: Path) -> Path:
    """Materialize ``build`` for ``repo`` through the public runtime selection effect."""
    return materialization.materialize_runtime(
        repo, Path(sys.executable), expected_build=build, **options
    )


@pytest.mark.parametrize("name", ["digest", "index", "foreign index"])
def test_explicit_installed_supply_is_pinned_before_repository_selection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    """Removing the package carrier cannot delete a repository's selected bytes.

    A carrier names its runtime by the digest or by the digest's index, and the store pins it by
    the digest. An index that the manifest's digest does not begin with is refused before any pin.
    """
    repo, selected, store = _host_case(tmp_path, monkeypatch)
    index = selected.digest[:16]
    carrier = {"digest": selected.digest, "index": index}.get(name, f"{int(index, 16) ^ 1:016x}")
    package = tmp_path / "package/ethos"
    shutil.copytree(Path(git_common_dir(repo)) / "ethos/packages", package / "packages")
    supplied = package / "runtime" / carrier
    shutil.copytree(selected.root, supplied, symlinks=True)
    if name == "foreign index":
        with pytest.raises(ValueError, match="hook_runtime_manifest_invalid"):
            _pin(repo, selected.build, installed_runtime=supplied)
        assert not store.exists()
        return

    pinned_python = _pin(repo, selected.build, installed_runtime=supplied)
    installation = store / index
    expected = installation / "runtime" / selected.digest
    assert pinned_python == expected / "python"
    assert {item.name for item in installation.iterdir()} == {
        "OWNER",
        "consumers",
        "runtime",
        "packages",
    }
    materialization.remove_generated_tree(package)
    assert require_selected_runtime(expected).digest == selected.digest
    assert _pin(repo, selected.build, installed_runtime=expected) == pinned_python


def _writable_entries(root: Path) -> list[str]:
    """List payload entries that still grant any write permission."""
    return [
        path.relative_to(root).as_posix()
        for path in [root, *root.rglob("*")]
        if not path.is_symlink() and stat.S_IMODE(path.stat().st_mode) & 0o222
    ]


def test_pinned_installation_is_sealed_whatever_modes_its_carrier_restored(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An archive carrier that recreated writable directories still yields sealed supply."""
    repo, selected, store = _host_case(tmp_path, monkeypatch)
    package = tmp_path / "package"
    shutil.copytree(Path(git_common_dir(repo)) / "ethos", package / "ethos", symlinks=True)
    supplied = package / "ethos/runtime" / selected.digest
    for path in [supplied, *supplied.rglob("*")]:
        if path.is_dir() and not path.is_symlink():
            path.chmod(stat.S_IMODE(path.stat().st_mode) | stat.S_IWUSR)
    assert _writable_entries(supplied)

    pinned = _pin(repo, selected.build, installed_runtime=supplied).parent
    assert pinned == store / selected.digest[:16] / "runtime" / selected.digest
    assert _writable_entries(pinned) == []
    assert require_selected_runtime(pinned).digest == selected.digest


def test_reused_installation_is_resealed_without_changing_its_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reuse restores the seal that an earlier pin or an outside writer left open."""
    repo, selected, _store = _host_case(tmp_path, monkeypatch)
    consumer = Path(git_common_dir(repo))
    pinned = materialization.pin_installed_runtime(selected, consumer=consumer)
    opened = next(path for path in pinned.rglob("*") if path.is_dir() and not path.is_symlink())
    for path in (pinned, opened):
        path.chmod(stat.S_IMODE(path.stat().st_mode) | stat.S_IWUSR)

    assert materialization.pin_installed_runtime(selected, consumer=consumer) == pinned
    assert _writable_entries(pinned) == []
    assert require_selected_runtime(pinned).digest == selected.digest


def test_rollback_pins_a_predecessor_whose_entry_an_earlier_launcher_wrote(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The manifest binds an earlier ETHOS's launcher as exactly as the current one."""
    with monkeypatch.context() as earlier:
        earlier.setattr(materialization, "render_console_script", lambda _name: "#!/bin/sh\n")
        repo, selected, store = _host_case(tmp_path, monkeypatch)
    pinned = materialization.pin_installed_runtime(selected, consumer=Path(git_common_dir(repo)))
    assert pinned == store / selected.digest[:16] / "runtime" / selected.digest
    assert (pinned / "python/bin/ethos").read_text() == "#!/bin/sh\n"


def test_external_package_invoker_pins_shared_supply_without_an_explicit_runtime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The selected package executable is sufficient to reuse verified host supply."""
    supplied = _package_supply(tmp_path, monkeypatch)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "user-data"))
    monkeypatch.setattr(materialization, "selected_runtime_source", lambda _source: supplied)
    private_build = Mock(side_effect=AssertionError("private runtime build reached"))
    monkeypatch.setattr(materialization, "resolve_runtime_wheel", private_build)

    pinned = []
    for ordinal in range(2):
        repo = _adopter(tmp_path / f"adopter-{ordinal}")
        pinned.append(_pin(repo, supplied.build))
        assert not (Path(git_common_dir(repo)) / "ethos/runtime" / supplied.digest).exists()

    assert pinned[0] == pinned[1]
    store = tmp_path / "user-data/ethos/installations"
    assert pinned[0].parent == store / supplied.digest[:16] / "runtime" / supplied.digest
    assert require_selected_runtime(pinned[0].parent).digest == supplied.digest


@pytest.mark.parametrize("carrier", ["retained", "removed"])
def test_package_upgrade_selects_pinned_supply_instead_of_its_carrier(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, carrier: str
) -> None:
    """An upgrade selects sealed host supply, as a first bind does, never the carrier in place.

    A package manager may leave its installation writable, so an ordinary interpreter run
    could change the selected runtime; the predecessor's carrier may also have been removed.
    """
    old = runtime_build("a" * 40, "b" * 40)
    repo, previous = _materialized(tmp_path / "old", monkeypatch, package_identity=old)
    common = Path(git_common_dir(repo))
    shutil.copytree(common / "ethos", tmp_path / "carrier", symlinks=True)
    activate_runtime(common, tmp_path / "carrier/runtime" / previous.digest)
    if carrier == "removed":
        (tmp_path / "carrier").rename(tmp_path / "carrier-removed")
    supplied = _package_supply(tmp_path, monkeypatch)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "user-data"))
    monkeypatch.setattr(materialization, "selected_runtime_source", lambda _source: supplied)
    private_build = Mock(side_effect=AssertionError("private runtime build reached"))
    monkeypatch.setattr(materialization, "resolve_runtime_wheel", private_build)

    selected = _pin(repo, supplied.build).parent

    pinned = tmp_path / "user-data/ethos/installations" / supplied.digest[:16]
    assert selected == pinned / "runtime" / supplied.digest
    assert require_selected_runtime(selected).digest == supplied.digest
    assert _writable_entries(selected) == []


def test_missing_selector_does_not_pin_another_repository_private_runtime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A foreign Git-private runtime cannot become shared supply by inference."""
    _, private = _materialized(tmp_path / "source", monkeypatch)
    adopter = _adopter(tmp_path / "adopter")
    monkeypatch.setattr(materialization, "selected_runtime_source", lambda _source: private)
    pin = Mock(side_effect=AssertionError("foreign private runtime pinned"))
    monkeypatch.setattr(materialization, "pin_installed_runtime", pin)
    retained = Mock(side_effect=RuntimeError("private materialization retained"))
    monkeypatch.setattr(materialization, "resolve_runtime_wheel", retained)

    with pytest.raises(RuntimeError, match="private materialization retained"):
        _pin(adopter, private.build)
    pin.assert_not_called()


def test_missing_selector_explicit_source_build_does_not_reuse_package_supply(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A requested source build cannot be satisfied by an unrelated package invocation."""
    supplied = _package_supply(tmp_path, monkeypatch)
    adopter = _adopter(tmp_path / "adopter")
    monkeypatch.setattr(materialization, "selected_runtime_source", lambda _source: supplied)
    pin = Mock(side_effect=AssertionError("explicit source build reused package"))
    monkeypatch.setattr(materialization, "pin_installed_runtime", pin)
    source_build = Mock(side_effect=RuntimeError("source build selected"))
    monkeypatch.setattr(materialization, "resolve_locked_environment_python", source_build)

    with pytest.raises(RuntimeError, match="source build selected"):
        _pin(adopter, supplied.build, build_source=REPOSITORY_ROOT)
    pin.assert_not_called()


@pytest.mark.parametrize("lock_changed", [False, True])
def test_complete_external_predecessor_allows_new_source_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, lock_changed: bool
) -> None:
    """A valid old installation is not damaged merely because source advanced."""
    repo, python = materialize_runtime_case(tmp_path, monkeypatch)
    common = Path(git_common_dir(repo))
    previous = require_selected_runtime(python.parent)
    installed = tmp_path / "installed"
    shutil.copytree(common / "ethos", installed)
    selected = activate_runtime(common, installed / "runtime" / previous.digest)
    selector = common / "ethos/runtime/CURRENT"
    before = selector.read_bytes()
    successor = runtime_build("c" * 40, "d" * 40)
    if lock_changed:
        digest = materialization.file_sha256
        monkeypatch.setattr(
            materialization,
            "file_sha256",
            lambda path: "e" * 64 if path == REPOSITORY_ROOT / "uv.lock" else digest(path),
        )
    assert selected.build == previous.build != successor
    rebuild = Mock(side_effect=AssertionError("new runtime build reached"))
    monkeypatch.setattr(materialization, "resolve_locked_environment_python", rebuild)
    with pytest.raises(AssertionError, match="new runtime build reached"):
        _pin(repo, successor, build_source=REPOSITORY_ROOT)
    assert selector.read_bytes() == before

    wheel = next((installed / "packages" / selected.wheel_sha256).glob("ethos-*.whl"))
    wheel.unlink()
    with pytest.raises(ValueError, match="hook_runtime_installed_supply_invalid"):
        _pin(repo, successor, build_source=REPOSITORY_ROOT)
    rebuild.assert_called_once_with(REPOSITORY_ROOT)
    assert selector.read_bytes() == before


def test_valid_external_predecessor_rebuilds_instead_of_reusing_private_invoker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An old external selection may advance without selecting another repo's private runtime."""
    old_build = runtime_build("a" * 40, "b" * 40)
    repo, old = _materialized(tmp_path / "old", monkeypatch, package_identity=old_build)
    common = Path(git_common_dir(repo))
    installed = tmp_path / "installed"
    shutil.copytree(common / "ethos", installed)
    activate_runtime(common, installed / "runtime" / old.digest)
    selector = common / "ethos/runtime/CURRENT"
    before = selector.read_bytes()

    new_build = runtime_build("c" * 40, "d" * 40)
    _, invoking = _materialized(tmp_path / "new", monkeypatch, package_identity=new_build)
    monkeypatch.setattr(materialization, "selected_runtime_source", lambda _source: invoking)

    successor = _pin(repo, invoking.build, build_source=REPOSITORY_ROOT)

    assert successor.parent == common / "ethos/runtime" / invoking.digest
    assert successor.parent != invoking.root
    assert require_selected_runtime(successor.parent).build == invoking.build
    assert selector.read_bytes() == before


def test_pinned_runtime_path_leaves_room_for_native_windows_dependencies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The installed path must not repeat a full digest before loading native modules."""
    repo, selected, _ = _host_case(tmp_path, monkeypatch)

    pinned = _pin(repo, selected.build, installed_runtime=selected.root)
    relative = pinned.relative_to(tmp_path / "user-data").as_posix()
    assert len(relative) <= 128, relative
    assert relative.count(selected.digest) == 1


def test_host_store_recovery_preserves_unowned_directory_with_a_valid_looking_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A marker alone cannot make an arbitrary directory safe to delete."""
    repo, selected, store = _host_case(tmp_path, monkeypatch)
    monkeypatch.setattr(materialization, "_runtime_supply_current", lambda *_args: True)
    foreign = store / ".pin-foreign"
    foreign.mkdir(parents=True)
    marker = store / ".pin-foreign.owner"
    marker.write_text("a" * 64 + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="hook_runtime_host_store_residue_unreviewed"):
        _pin(repo, selected.build, installed_runtime=selected.root)
    assert foreign.is_dir()
    assert marker.is_file()


def test_interrupted_owned_import_is_recovered_before_new_selection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A released host lock permits exact cleanup of only its marked staging."""
    repo, selected, store = _host_case(tmp_path, monkeypatch)
    staging = store / (".pin-" + "a" * 32)
    staging.mkdir(parents=True)
    (staging / "OWNER").write_text(selected.digest + "\n", encoding="utf-8")
    (staging / "partial").write_bytes(b"incomplete")
    marker = staging.with_name(staging.name + ".owner")
    marker.write_text(selected.digest + "\n", encoding="utf-8")

    pinned = _pin(repo, selected.build, installed_runtime=selected.root)
    assert not staging.exists()
    assert not marker.exists()
    assert require_selected_runtime(pinned.parent).digest == selected.digest


@pytest.mark.parametrize("fault", ["invalid_owner", "missing_runtime", "prefix_collision"])
def test_occupied_installation_does_not_replace_unknown_content(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    """A matching name and owner marker cannot authorize damaged installed bytes."""
    repo, selected, store = _host_case(tmp_path, monkeypatch)
    installation = store / selected.digest[:16]
    installation.mkdir(parents=True)
    marker = installation / "OWNER"
    if fault == "missing_runtime":
        owner = selected.digest + "\n"
    elif fault == "prefix_collision":
        other_last_digit = "0" if selected.digest[-1] != "0" else "1"
        owner = selected.digest[:-1] + other_last_digit + "\n"
    else:
        owner = "foreign\n"
    marker.write_text(owner, encoding="utf-8")

    with pytest.raises(ValueError, match="hook_runtime_host_store_conflict"):
        _pin(repo, selected.build, installed_runtime=selected.root)
    assert marker.read_text(encoding="utf-8") == owner
    assert sorted(item.name for item in installation.iterdir()) == ["OWNER"]


def test_source_wheel_disappearing_after_admission_fails_without_partial_installation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An input race must not become an unhandled iterator error or selected supply."""
    repo, selected, store = _host_case(tmp_path, monkeypatch)
    wheel = Path(git_common_dir(repo)) / "ethos/packages" / selected.wheel_sha256 / "ethos-test.whl"
    observe = materialization.file_sha256

    def remove_after_observation(path):
        observed = observe(path)
        if path == wheel:
            wheel.unlink()
        return observed

    monkeypatch.setattr(materialization, "file_sha256", remove_after_observation)
    with pytest.raises(ValueError, match="hook_runtime_installed_supply_invalid"):
        _pin(repo, selected.build, installed_runtime=selected.root)
    assert not store.exists() or not any(path.is_dir() for path in store.iterdir())


def test_tests_declare_a_host_store_they_own(tmp_path: Path) -> None:
    """A fixture runtime pinned by any test cannot reach the user's installed supply."""
    assert Path(os.environ["XDG_DATA_HOME"]).is_relative_to(tmp_path)


@pytest.mark.parametrize("mode", ["relative", "native", "symlink"])
def test_host_store_location_is_explicit_and_does_not_follow_an_unsafe_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    """A native user location works; relative or redirected declarations do not."""
    repo, selected, store = _host_case(tmp_path, monkeypatch)
    if mode == "native":
        monkeypatch.delenv("XDG_DATA_HOME", raising=False)
        monkeypatch.setattr(
            host_store, "user_data_path", lambda *_args, **_kwargs: tmp_path / "native-data"
        )
        pinned = _pin(repo, selected.build, installed_runtime=selected.root)
        assert pinned.parent.is_relative_to(tmp_path / "native-data/installations")
        return
    if mode == "relative":
        monkeypatch.setenv("XDG_DATA_HOME", "relative-data")
    else:
        store.parent.mkdir(parents=True)
        foreign = tmp_path / "foreign"
        foreign.mkdir()
        store.symlink_to(foreign, target_is_directory=True)
    with pytest.raises(ValueError, match="hook_runtime_host_store_invalid"):
        _pin(repo, selected.build, installed_runtime=selected.root)
    if mode == "symlink":
        assert store.is_symlink()
        assert not tuple(foreign.iterdir())


def test_existing_host_installation_reuses_valid_bytes_and_rejects_damaged_wheel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A second import reuses one generation, but wheel drift cannot pass as reuse."""
    repo, selected, _ = _host_case(tmp_path, monkeypatch)
    first = _pin(repo, selected.build, installed_runtime=selected.root)
    assert _pin(repo, selected.build, installed_runtime=selected.root) == first
    installation = first.parent.parents[1]
    wheel = next((installation / "packages" / selected.wheel_sha256).glob("ethos-*.whl"))
    wheel.write_bytes(b"tampered wheel")
    with pytest.raises(ValueError, match="hook_runtime_host_store_conflict"):
        _pin(repo, selected.build, installed_runtime=selected.root)
    assert wheel.read_bytes() == b"tampered wheel"


@pytest.mark.parametrize("fault", ["copy", "postcopy"])
def test_failed_host_import_cleans_only_its_own_staging(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    """A failed copy or verification leaves no selected or half-installed generation."""
    repo, selected, store = _host_case(tmp_path, monkeypatch)
    copyfile = materialization.shutil.copyfile

    def faulty_copy(source, target, *, follow_symlinks=True):
        wheel = Path(source).suffix == ".whl"
        if wheel and fault == "copy":
            message = "wheel copy failed"
            raise OSError(message)
        result = copyfile(source, target, follow_symlinks=follow_symlinks)
        if wheel:
            Path(target).write_bytes(b"damaged copied wheel")
        return result

    monkeypatch.setattr(materialization.shutil, "copyfile", faulty_copy)
    reason = "installed_supply_invalid" if fault == "copy" else "host_store_copy_invalid"
    with pytest.raises(ValueError, match=f"hook_runtime_{reason}"):
        _pin(repo, selected.build, installed_runtime=selected.root)
    assert not any(path.is_dir() for path in store.iterdir())
    assert not list(store.glob(".pin-*"))


@pytest.mark.parametrize("paired", [False, True])
def test_malformed_interrupted_import_is_preserved_for_review(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, paired: bool
) -> None:
    """An invalid ownership marker never authorizes deletion or installation."""
    repo, selected, store = _host_case(tmp_path, monkeypatch)
    store.mkdir(parents=True)
    staging = store / (".pin-" + "b" * 32)
    if paired:
        staging.mkdir()
        (staging / "partial").write_bytes(b"keep")
    marker = staging.with_name(staging.name + ".owner")
    marker.write_text("invalid\n", encoding="utf-8")
    with pytest.raises(ValueError, match="hook_runtime_host_store_residue_unreviewed"):
        _pin(repo, selected.build, installed_runtime=selected.root)
    assert marker.read_bytes() == b"invalid\n"
    assert staging.exists() is paired


def test_orphaned_valid_marker_is_recovered_without_touching_other_content(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A crash after atomic exposure leaves only an owned marker to remove."""
    repo, selected, store = _host_case(tmp_path, monkeypatch)
    store.mkdir(parents=True)
    marker = store / (".pin-" + "c" * 32 + ".owner")
    marker.write_text(selected.digest + "\n", encoding="utf-8")
    foreign = store / "user-owned.txt"
    foreign.write_text("preserve", encoding="utf-8")
    pinned = _pin(repo, selected.build, installed_runtime=selected.root)
    assert not marker.exists()
    assert foreign.read_text(encoding="utf-8") == "preserve"
    assert require_selected_runtime(pinned.parent).digest == selected.digest


def test_reusing_a_sealed_installation_keeps_every_file_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A seal that holds needs no change, so reuse keeps file states and inventory memos valid."""
    repo, selected, _store = _host_case(tmp_path, monkeypatch)
    consumer = Path(git_common_dir(repo))
    pinned = materialization.pin_installed_runtime(selected, consumer=consumer)
    before = {path: path.lstat().st_ctime_ns for path in pinned.rglob("*")}

    materialization.pin_installed_runtime(selected, consumer=consumer)

    assert {path: path.lstat().st_ctime_ns for path in pinned.rglob("*")} == before
