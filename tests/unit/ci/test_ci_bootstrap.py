"""Verify CI fixture supply and the locked npm launcher."""

from __future__ import annotations

import shlex
import shutil
import tomllib
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING

from uv import find_uv_bin

import tools.ci.toolchain.fixture_supply as fixture_supply
from ethos.adapters.process import run_command
from ethos.adapters.repo.git import git_files
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tools.ci.toolchain import npm

if TYPE_CHECKING:
    import pytest

ROOT = Path(__file__).resolve().parents[3]


def test_fixture_supply_preserves_native_project_policy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Warm one tracked lock without ambient activation or retained environments."""
    repo = init_git_repo(tmp_path / "repo")
    relative = Path("tests/fixtures/quality-sample")
    fixture = repo / relative
    shutil.copytree(ROOT / relative, fixture)
    inputs = {path: path.read_bytes() for path in fixture.iterdir()}
    git(repo, "add", "tests")
    monkeypatch.setenv("UV_OFFLINE", "1")
    monkeypatch.setenv("VIRTUAL_ENV", str(tmp_path / "unrelated-environment"))
    monkeypatch.setenv("UV_PYTHON", str(tmp_path / "unrelated-interpreter"))

    fixture_supply.provision(repo)

    assert {path: path.read_bytes() for path in fixture.iterdir()} == inputs
    assert not (fixture / ".venv").exists()
    assert not (tmp_path / "unrelated-environment").exists()


def test_tracked_fixture_projects_build_offline_from_an_empty_cache(tmp_path: Path) -> None:
    """A fixture build needs nothing that a refresh of uv's shared index could make unavailable."""
    projects = [ROOT / relative for relative in git_files(ROOT, "tests/fixtures/**/pyproject.toml")]
    assert projects
    for index, declaration in enumerate(projects):
        copy = tmp_path / str(index)
        shutil.copytree(declaration.parent, copy)
        declared = tomllib.loads(declaration.read_text(encoding="utf-8"))
        backend = declared.get("tool", {}).get("uv", {}).get("build-backend", {})
        module = backend.get("module-name") or declared["project"]["name"].replace("-", "_")
        (copy / "src" / module).mkdir(parents=True)
        (copy / "src" / module / "__init__.py").write_text("")
        built = run_command(
            copy,
            (find_uv_bin(), "build", "--wheel", "--offline", "--no-config", "--out-dir", "dist"),
            env={"UV_CACHE_DIR": str(tmp_path / f"empty-cache-{index}")},
            timeout=120,
        )
        assert built.returncode == 0, (declaration, built.stderr)
        assert len(list((copy / "dist").glob("*.whl"))) == 1


def test_npm_uses_the_archive_seed_only_for_the_first_install(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The seed npm installs once; later npm commands run the package-lock-owned npm."""
    log = tmp_path / "node.log"
    node = tmp_path / "node/bin/node"
    node.parent.mkdir(parents=True)
    node.write_text(
        "#!/bin/sh\n"
        f'printf "%s|%s %s %s %s\\n" "$*" "$npm_config_engine_strict" "$npm_config_audit" '
        f'"$npm_config_fund" "$npm_config_update_notifier" >> {shlex.quote(str(log))}\n'
        "exit 3\n"
    )
    node.chmod(0o755)
    seed = SimpleNamespace(executable=node, npm=tmp_path / "seed-npm.js")
    product = SimpleNamespace(executable=node, npm=tmp_path / "node_modules/npm/bin/npm-cli.js")
    supply = SimpleNamespace(installed_root=lambda _root: tmp_path / "node")
    monkeypatch.setattr(npm.NodeSupply, "read", lambda _root: supply)
    monkeypatch.setattr(npm.NodeRuntime, "read", lambda _installed, **_options: seed)
    monkeypatch.setattr(npm, "resolve_node_runtime", lambda: product)
    monkeypatch.chdir(tmp_path)

    assert npm.main(["--seed", "ci", "--ignore-scripts"]) == 3
    assert npm.main(["run", "ethos", "--", "--version"]) == 3

    assert log.read_text().splitlines() == [
        f"{seed.npm} ci --ignore-scripts|true false false false",
        f"{product.npm} run ethos -- --version|true false false false",
    ]
