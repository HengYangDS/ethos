"""Installed package identity follows the selected runtime, not guessed placement."""

from __future__ import annotations

from pathlib import Path

import pytest

from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.runtime.selection import require_selected_runtime
from ethos.adapters.repo.runtime.selection import runtime_selection_bytes
from tests.support.governed_repository import init_git_repo
from tests.support.runtime_scenarios import fixture_runtime_generation
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
