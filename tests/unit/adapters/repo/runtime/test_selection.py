"""Tests for the concrete semantic owner named by this module path."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from ethos.adapters.repo.attestation_set import ATTESTATION_SET_REF
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.runtime.manifest import runtime_digest
from ethos.adapters.repo.runtime.manifest import runtime_environment
from ethos.adapters.repo.runtime.manifest import runtime_file_inventory
from ethos.adapters.repo.runtime.manifest import runtime_manifest_bytes
from ethos.adapters.repo.runtime.selection import activate_runtime
from ethos.adapters.repo.runtime.selection import current_runtime
from ethos.adapters.repo.runtime.selection import restore_runtime_selection
from tests.support.runtime_scenarios import git_process
from tests.support.runtime_scenarios import materialize_runtime_case
from tests.support.runtime_scenarios import runtime_build


def test_hook_runtime_rejects_tampered_installed_package_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, venv = materialize_runtime_case(tmp_path, monkeypatch)
    runtime = venv.parent
    package = runtime / "python/lib/python3.14/site-packages/ethos/module.py"
    activate_runtime(Path(git_common_dir(repo)), runtime)

    package.write_text("tampered\n", encoding="utf-8")

    with pytest.raises(ValueError, match="hook_runtime_manifest_invalid"):
        current_runtime(Path(git_common_dir(repo)))


def test_hook_runtime_manifest_and_current_selector_bind_exact_package(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, venv = materialize_runtime_case(tmp_path, monkeypatch)
    selected = activate_runtime(Path(git_common_dir(repo)), venv.parent)

    assert selected.root == venv.parent
    assert selected.python.is_file()
    assert current_runtime(Path(git_common_dir(repo))) == selected


def test_accepted_runtime_activation_requires_canonical_identity_attestations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = runtime_build("a" * 40, "b" * 40, accepted=True)
    repo, venv = materialize_runtime_case(
        tmp_path,
        monkeypatch,
        package_identity=identity,
    )
    assert git_process(repo, "update-ref", "-d", ATTESTATION_SET_REF).returncode == 0

    with pytest.raises(ValueError, match="accepted_release_identity_unattested"):
        activate_runtime(Path(git_common_dir(repo)), venv.parent)

    assert not (Path(git_common_dir(repo)) / "ethos/runtime/CURRENT").exists()


def test_runtime_selection_compensation_is_exact_cas(tmp_path: Path) -> None:
    common = tmp_path / "common"
    selector = common / "ethos/runtime/CURRENT"
    selector.parent.mkdir(parents=True)
    previous = f"{'a' * 64}\n".encode()
    operation_selection = f"{'b' * 64}\n".encode()
    concurrent_selection = f"{'c' * 64}\n".encode()
    selector.write_bytes(concurrent_selection)

    with pytest.raises(ValueError, match="hook_runtime_current_stale"):
        restore_runtime_selection(
            common,
            previous,
            expected_current=operation_selection,
        )

    assert selector.read_bytes() == concurrent_selection


def test_current_runtime_rejects_symlinked_ethos_ancestor(tmp_path: Path) -> None:
    common = tmp_path / "common"
    external = tmp_path / "external"
    external.mkdir()
    (common / "ethos").parent.mkdir(parents=True)
    (common / "ethos").symlink_to(external, target_is_directory=True)

    with pytest.raises(ValueError, match="hook_runtime_current_target_invalid"):
        current_runtime(common)


def test_accepted_runtime_identity_rejects_a_second_closure_for_the_same_release(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    identity = runtime_build("a" * 40, "b" * 40, accepted=True)
    repo, venv = materialize_runtime_case(
        tmp_path,
        monkeypatch,
        package_identity=identity,
    )
    common = Path(git_common_dir(repo))
    first = venv.parent
    activate_runtime(common, first)
    second_staging = tmp_path / "second-runtime"
    shutil.copytree(first, second_staging)
    package = second_staging / "python/lib/python3.14/site-packages/ethos/module.py"
    package.write_text("different accepted closure\n", encoding="utf-8")
    selected = current_runtime(common)
    environment = runtime_environment(
        python_abi=selected.python_abi,
        python_version=selected.python_version,
        python_implementation=selected.python_implementation,
        dependency_lock_sha256=selected.dependency_lock_sha256,
        platform_name=selected.platform,
    )
    files = runtime_file_inventory(second_staging)
    digest = runtime_digest(
        wheel_sha256=selected.wheel_sha256,
        build=identity,
        environment=environment,
        runtime_files=files,
    )
    second = common / "ethos/runtime" / digest
    shutil.move(second_staging, second)
    (second / "manifest.json").write_bytes(
        runtime_manifest_bytes(
            digest=digest,
            wheel_sha256=selected.wheel_sha256,
            build=identity,
            environment=environment,
            runtime_files=runtime_file_inventory(second),
        )
    )

    with pytest.raises(ValueError, match="accepted_runtime_identity_conflict"):
        activate_runtime(common, second)

    assert current_runtime(common).root == first
