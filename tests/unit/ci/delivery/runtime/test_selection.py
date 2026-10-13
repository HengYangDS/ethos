"""Installed package identity follows the selected runtime, not guessed placement."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

import ethos.adapters.repo.runtime.selection as selection
import tools.ci.delivery.distribution as distribution
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.runtime.manifest import runtime_file_inventory
from ethos.adapters.repo.runtime.selection import activate_runtime
from ethos.adapters.repo.runtime.selection import current_runtime
from ethos.adapters.repo.runtime.selection import require_selected_runtime
from ethos.adapters.repo.runtime.selection import runtime_selection_bytes
from tests.support.governed_repository import init_git_repo
from tests.support.runtime_scenarios import fixture_runtime_generation
from tests.support.runtime_scenarios import materialize_runtime_case
from tools.ci.delivery.acceptance import runtime as runtime_acceptance


@pytest.mark.parametrize(
    "case",
    [
        "private",
        "legacy",
        "external",
        "unselected",
        "foreign-private",
        "reported-source-drift",
        "payload-drift",
    ],
)
def test_package_manifest_acceptance_uses_selected_runtime_owner(tmp_path: Path, case: str) -> None:
    """Accept only the exact selected supply, independent of its physical installation."""
    repo = init_git_repo(tmp_path / "adopter")
    common = Path(git_common_dir(repo))
    runtime_root = common / "ethos/runtime"
    runtime_root.mkdir(parents=True)
    external = case in {"external", "foreign-private"}
    supply = (
        Path(git_common_dir(init_git_repo(tmp_path / "foreign"))) / "ethos/runtime"
        if case == "foreign-private"
        else tmp_path / "installation"
        if external
        else runtime_root
    )
    supply.mkdir(parents=True, exist_ok=True)
    generation = fixture_runtime_generation(
        supply / "selected", "package", repository_private=case in {"private", "foreign-private"}
    )
    selected = require_selected_runtime(generation)
    active = (
        fixture_runtime_generation(runtime_root / "successor", "successor")
        if case == "unselected"
        else generation
    )
    (runtime_root / "CURRENT").write_bytes(runtime_selection_bytes(common, active))
    report = {
        "runtime_manifest_path": selected.manifest.as_posix(),
        "runtime_digest": selected.digest,
        "python": selected.python.as_posix(),
        "wheel_sha256": selected.wheel_sha256,
        **selected.build._asdict(),
    }
    if case == "reported-source-drift":
        report["source_commit"] = "0" * 40
    elif case == "payload-drift":
        (generation / "payload").write_bytes(b"changed")

    if case.endswith("drift") or case in {"unselected", "foreign-private"}:
        with pytest.raises(RuntimeError, match="package_runtime_identity_mismatch"):
            runtime_acceptance.require_manifest(
                report, repo, build=selected.build, wheel_sha256=selected.wheel_sha256
            )
    else:
        assert (
            runtime_acceptance.require_manifest(
                report, repo, build=selected.build, wheel_sha256=selected.wheel_sha256
            )
            == selected.python
        )


@pytest.mark.parametrize("outcome", ["success", "input-drift", "cancellation"])
def test_distribution_carries_fresh_runtime_and_retains_publication_custody(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, outcome: str
) -> None:
    """Reuse the immediate validation; never publish changed inputs or partial output."""
    repo, python = materialize_runtime_case(tmp_path, monkeypatch)
    common = Path(git_common_dir(repo))
    selected = activate_runtime(common, python.parent)
    wheel = common / "ethos/packages" / selected.wheel_sha256 / "ethos-test.whl"
    original_wheel, original_manifest = wheel.read_bytes(), selected.manifest.read_bytes()
    destination = tmp_path / "ethos.tar.gz"
    cask = tmp_path / "homebrew/Casks/ethos.rb"
    cask.parent.mkdir(parents=True)
    cask.write_bytes(b"previous Cask")
    destination.write_bytes(b"previous archive")
    add = distribution.tarfile.TarFile.add

    def archive(self, name, *args, **kwargs):
        add(self, name, *args, **kwargs)
        if Path(name) == selected.root:
            if outcome == "input-drift":
                selected.manifest.chmod(0o644)
                selected.manifest.write_bytes(original_manifest + b" ")
            elif outcome == "cancellation":
                raise KeyboardInterrupt

    monkeypatch.setattr(distribution.tarfile.TarFile, "add", archive)
    with patch.object(selection, "runtime_file_inventory", wraps=runtime_file_inventory) as scans:
        observed = current_runtime(common)
        if outcome == "success":
            result = distribution.package_runtime(observed, wheel, destination)
            assert scans.call_count == 2
            assert result["runtime_digest"] == observed.digest
            assert result["wheel_sha256"] == observed.wheel_sha256
        else:
            with pytest.raises(ValueError if outcome == "input-drift" else KeyboardInterrupt):
                distribution.package_runtime(observed, wheel, destination)
            assert destination.read_bytes() == b"previous archive"
            assert cask.read_bytes() == b"previous Cask"
    assert not list(tmp_path.glob(".ethos-distribution-*"))
    assert wheel.read_bytes() == original_wheel
    if outcome != "input-drift":
        assert selected.manifest.read_bytes() == original_manifest
