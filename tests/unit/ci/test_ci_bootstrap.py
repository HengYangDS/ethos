"""Verify CI fixture supply, commit trust and the locked npm launcher."""

from __future__ import annotations

import shlex
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

import tools.ci.toolchain.environment as ci_environment
import tools.ci.toolchain.fixture_supply as fixture_supply
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tools.ci.toolchain import commit_trust
from tools.ci.toolchain import npm

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

    fixture_supply.provision(repo)

    assert {path: path.read_bytes() for path in fixture.iterdir()} == inputs
    assert not (fixture / ".venv").exists()
    assert not (tmp_path / "unrelated-environment").exists()


@pytest.mark.parametrize("case", ["valid", "inside", "unprotected", "missing"])
def test_ci_trust_projects_only_operator_supplied_protected_anchor(tmp_path, case):
    repo = init_git_repo(tmp_path / "repo")
    trust = (repo if case == "inside" else tmp_path) / "trust"
    trust.mkdir(mode=0o700)
    anchor = trust / "allowed-signers"
    anchor.write_text("operator-controlled public trust\n")
    anchor.chmod(0o666 if case == "unprotected" else 0o600)
    if case == "missing":
        anchor.unlink()
    before = git(repo, "config", "--local", "--list")
    if case != "valid":
        with pytest.raises(ValueError, match="git_object_trust_anchor_"):
            ci_environment.bind_commit_trust(repo, anchor)
        assert git(repo, "config", "--local", "--list") == before
    else:
        ci_environment.bind_commit_trust(repo, anchor)
        assert git(repo, "config", "--local", "--get", "gpg.ssh.allowedSignersFile") == str(anchor)
        first = (repo / ".git/config").read_bytes()
        ci_environment.bind_commit_trust(repo, anchor)
        assert (repo / ".git/config").read_bytes() == first
        assert anchor.read_text() == "operator-controlled public trust\n"


@pytest.mark.parametrize("state", ["absent", "declared", "material", "ambiguous"])
def test_commit_trust_binds_only_the_one_supplied_input(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, state: str
) -> None:
    """The operator supplies a protected anchor or its material; nothing else is bound."""
    repo = init_git_repo(tmp_path / "repo")
    anchor = tmp_path / "trust/allowed-signers"
    anchor.parent.mkdir(mode=0o700)
    anchor.write_text("fixture-controlled public trust\n")
    anchor.chmod(0o600)
    for name in ("ETHOS_COMMIT_TRUST_ANCHOR", "ETHOS_COMMIT_ALLOWED_SIGNERS"):
        monkeypatch.delenv(name, raising=False)
    if state in {"declared", "ambiguous"}:
        monkeypatch.setenv("ETHOS_COMMIT_TRUST_ANCHOR", str(anchor))
    if state in {"material", "ambiguous"}:
        monkeypatch.setenv("ETHOS_COMMIT_ALLOWED_SIGNERS", anchor.read_text().rstrip("\n"))
        monkeypatch.setenv("TMPDIR", str(tmp_path))
    monkeypatch.chdir(repo)
    before = git(repo, "config", "--local", "--list")
    if state == "ambiguous":
        with pytest.raises(ValueError, match="ci_commit_trust_inputs_ambiguous"):
            commit_trust.main()
        assert git(repo, "config", "--local", "--list") == before
        return
    assert commit_trust.main() == 0
    settings = git(repo, "config", "--local", "--list")
    if state == "absent":
        assert settings == before
    elif state == "declared":
        assert f"gpg.ssh.allowedsignersfile={anchor}" in settings
    else:
        selected = Path(git(repo, "config", "--path", "--get", "gpg.ssh.allowedSignersFile"))
        assert selected.read_text() == anchor.read_text().rstrip("\n")


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
