"""Installed package identity follows the selected runtime, not guessed placement."""

from __future__ import annotations

from pathlib import Path

import pytest

from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.runtime.selection import require_selected_runtime
from ethos.adapters.repo.runtime.selection import runtime_selection_bytes
from ethos.repository.release.identity import BuildIdentity
from tests.support.governed_repository import init_git_repo
from tests.support.runtime_scenarios import fixture_runtime_generation
from tests.support.runtime_scenarios import runtime_build
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


@pytest.mark.parametrize("distinct", [False, True])
def test_upgrade_requires_a_distinct_build_not_a_different_runtime_digest(tmp_path, distinct):
    """Environment or payload differences alone do not constitute an upgrade."""
    predecessor = require_selected_runtime(fixture_runtime_generation(tmp_path / "prior", "prior"))
    build = runtime_build("b" * 40, "b" * 40) if distinct else predecessor.build
    successor = require_selected_runtime(
        fixture_runtime_generation(tmp_path / "next", "next", build=build)
    )
    assert predecessor.digest != successor.digest
    if distinct:
        assert (
            runtime_acceptance.require_upgrade_predecessor(predecessor.root, build=successor.build)
            == predecessor
        )
    else:
        with pytest.raises(ValueError, match="package_upgrade_predecessor_not_distinct"):
            runtime_acceptance.require_upgrade_predecessor(predecessor.root, build=successor.build)


@pytest.mark.parametrize("foreign_identity", [False, True])
def test_package_version_acceptance_binds_exact_repository(monkeypatch, tmp_path, foreign_identity):
    """Native console dispatch gets the repository before identity is judged."""
    repository = tmp_path / "adopter"
    python = tmp_path / "unrelated-repository/runtime/python/bin/python"
    build = BuildIdentity("0.2.0-alpha.5", "0.2.0a5.dev0+ga.ta", "a" * 40, "b" * 40)
    expected = {
        "schema_version": 2,
        "product_version": "0.2.0-alpha.5",
        "distribution_version": "0.2.0a5.dev0+ga.ta",
        "source_commit": "a" * 40,
        "source_tree": "b" * 40,
        "wheel_sha256": "c" * 64,
        "runtime_digest": "d" * 64,
    }

    def invoke(root, command, *, environment):
        assert root == repository
        assert command[-2:] == ("--root", repository.as_posix())
        assert environment == {"PATH": "native-only"}
        identity = expected | ({"source_commit": "e" * 40} if foreign_identity else {})
        return 0, {"data": {"identity": identity}}, ""

    monkeypatch.setattr(runtime_acceptance, "invoke", invoke)
    arguments = {
        "build": build,
        "wheel_sha256": "c" * 64,
        "runtime_digest": "d" * 64,
        "environment": {"PATH": "native-only"},
    }
    if foreign_identity:
        with pytest.raises(RuntimeError, match="package_runtime_version_identity_mismatch"):
            runtime_acceptance.require_version_identity(python, repository, **arguments)
    else:
        assert runtime_acceptance.require_version_identity(python, repository, **arguments) == {
            "state": "passed",
            "identity": expected,
        }
