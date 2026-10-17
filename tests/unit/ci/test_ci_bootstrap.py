"""Verify CI image identity, trust anchors, and native Python bootstrap."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import sys
from pathlib import Path

import pytest

import tools.ci.toolchain.environment as ci_environment
import tools.ci.toolchain.fixture_supply as fixture_supply
from ethos.adapters.process import run_command
from ethos.adapters.repo.runtime.materialization.node.supply import NodeSupply
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

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


@pytest.fixture(scope="module")
def bootstrap_tools(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Reuse immutable executables while each native bootstrap owns its case state."""
    tools = tmp_path_factory.mktemp("bootstrap-tools")
    bodies = {
        "with-python-runtime": '[ "$1" != -- ] || shift\nexec "$@"\n',
        "uname": 'printf "%s\\n" "$FIXTURE_SYSTEM"\n',
        "uv": (
            'printf "%s\\n" "$*" >>../uv.log\n'
            'case "$*" in\n'
            '  --version) printf "uv 0.12.10\\n" ;;\n'
            '  run*) cat >/dev/null; printf "0.12.10\\n" ;;\n'
            '  "python install --no-bin 3.14.7") : >../native-image ;;\n'
            '  "sync --locked --no-install-project --group dev") ;;\n'
            '  "sync --locked --group dev") ;;\n'
            "  *) exit 2 ;;\nesac\n"
        ),
        "apt-get": 'printf "%s\\n" "$*" >>../apt-get.log\n',
        "ssh-keygen": "exit 0\n",
        "ldconfig": "printf 'libatomic.so.1\\n'; awk 'BEGIN {for(i=0;i<100000;i++) print \"x\"}'\n",
        "node": (
            'printf "%s\\n" "$*" >>../node.log\n'
            '[ "$npm_config_engine_strict $npm_config_audit $npm_config_fund '
            '$npm_config_update_notifier" = "true false false false" ] || exit 2\n'
            'case "$*" in\n'
            '  "$FIXTURE_SEED_NPM ci --ignore-scripts") '
            "[ ! -e node_modules/.package-lock.json ] || exit 2\n"
            '    [ "${FIXTURE_SEED_EXIT:-0}" = 0 ] || exit "$FIXTURE_SEED_EXIT"\n'
            '    cat "$FIXTURE_NODE_LOCK" >node_modules/.package-lock.json ;;\n'
            '  "$FIXTURE_PRODUCT_NPM --version") '
            'printf "%s\\n" "$FIXTURE_NPM_VERSION" ;;\n'
            '  "$FIXTURE_OPENSPEC --version") '
            'printf "%s\\n" "$FIXTURE_OPENSPEC_VERSION" ;;\n'
            "  *) exit 2 ;;\nesac\n"
        ),
        "python": (
            f'[ "$1 $2" != "-B -" ] || exec {shlex.quote(sys.executable)} "$@"\n'
            'if [ "$#" = 4 ] && [ "$1 $2 $3" = "-B -I -c" ]; then\n'
            '  printf "3.14.7\\n"; exit 0\nfi\n'
            'case "$*" in\n'
            '  "-B $FIXTURE_REPO/tools/ci/toolchain/native.py '
            '--root $FIXTURE_REPO --mise vale") '
            'printf "%s\\n" "$*" >../native.log\n'
            '    printf "%s\\n" "$FIXTURE_NATIVE_BIN" ;;\n'
            "  '-B -I -') cat >/dev/null\n"
            '    [ "$FIXTURE_IMAGE_STATE" = available ] || [ -f ../native-image ] ;;\n'
            '  "-B -I tools/ci/toolchain/fixture_supply.py $FIXTURE_REPO") '
            'printf "%s\\n" "$4" >../fixture.log ;;\n'
            "  *) exit 2 ;;\nesac\n"
        ),
    }
    for name, body in bodies.items():
        path = tools / name
        path.write_text("#!/bin/sh\n" + body)
        path.chmod(0o555)
    return tools


def _bootstrap_source_fixture(
    repo: Path, tools: Path, monkeypatch: pytest.MonkeyPatch
) -> dict[str, str]:
    """Expose contained native and lock-bound build inputs to unchanged Python."""
    repo = repo.resolve()
    for relative in ("src/ethos", "system", ".config/mise"):
        shutil.copytree(
            ROOT / relative, repo / relative, ignore=shutil.ignore_patterns("__pycache__")
        )
    cache = repo.parent / "native-cache"
    monkeypatch.setenv("ETHOS_CI_TOOL_CACHE_DIR", str(cache))
    monkeypatch.delenv("ETHOS_CI_PERSISTENT_TOOL_CACHE_DIR", raising=False)
    native = NodeSupply.read(repo).installed_root(repo)
    node = native / "bin/node"
    node.parent.mkdir(parents=True)
    shutil.copy2(tools / "node", node)
    seed_npm = native / "lib/node_modules/npm/bin/npm-cli.js"
    seed_npm.parent.mkdir(parents=True)
    seed_npm.write_text("// test-owned archive seed npm\n", encoding="utf-8")
    dependencies = json.loads((ROOT / "package.json").read_text())["dependencies"]
    selected = {name: dependencies[name] for name in ("npm", "@fission-ai/openspec")}
    packages = {f"node_modules/{name}": {"version": version} for name, version in selected.items()}
    (repo / "package.json").write_text(json.dumps({"dependencies": selected}) + "\n")
    lock = {"lockfileVersion": 3, "packages": {"": {"dependencies": selected}, **packages}}
    (repo / "package-lock.json").write_text(json.dumps(lock) + "\n")
    hidden = repo.parent / "prepared-node-lock.json"
    hidden.write_text(json.dumps({"lockfileVersion": 3, "packages": packages}) + "\n")
    for name, version in selected.items():
        package = repo / "node_modules" / name
        (package / "bin").mkdir(parents=True)
        (package / "package.json").write_text(json.dumps({"name": name, "version": version}) + "\n")
    product_npm = repo / "node_modules/npm/bin/npm-cli.js"
    openspec = repo / "node_modules/@fission-ai/openspec/bin/openspec.js"
    product_npm.write_text("// test-owned product npm\n", encoding="utf-8")
    openspec.write_text("// test-owned OpenSpec entrypoint\n", encoding="utf-8")
    (repo / ".venv/bin").mkdir(parents=True)
    (repo / ".venv/bin/python").symlink_to(tools / "python")
    (repo / "pyproject.toml").write_text(
        '[dependency-groups]\ndev = ["uv>=0.12.10"]\n', encoding="utf-8"
    )
    return {
        "ETHOS_CI_TOOL_CACHE_DIR": str(cache),
        "FIXTURE_REPO": str(repo),
        "FIXTURE_NATIVE_BIN": str(node.parent),
        "FIXTURE_SEED_NPM": str(seed_npm),
        "FIXTURE_PRODUCT_NPM": str(product_npm),
        "FIXTURE_OPENSPEC": str(openspec),
        "FIXTURE_NODE_LOCK": str(hidden),
        "FIXTURE_NPM_VERSION": selected["npm"],
        "FIXTURE_OPENSPEC_VERSION": selected["@fission-ai/openspec"],
    }


def _bootstrap_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bootstrap_tools: Path,
    *,
    system: str,
    image_state: str,
) -> tuple[Path, dict[str, str]]:
    """Prepare one contained bootstrap journey without ambient tool or Git state."""
    repo = init_git_repo(tmp_path / "repo")
    script_dir = repo / "tools/ci/scripts"
    script_dir.mkdir(parents=True)
    shutil.copy2(ROOT / "tools/ci/scripts/bootstrap-python.sh", script_dir)
    (script_dir / "with-python-runtime.sh").symlink_to(bootstrap_tools / "with-python-runtime")
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    for source in bootstrap_tools.iterdir():
        if source.name != "node" and (
            source.name not in {"ssh-keygen", "ldconfig"} or system == "Linux"
        ):
            (fake_bin / source.name).symlink_to(source)
    for name in ("awk", "cat", "dirname", "grep", "git"):
        executable = shutil.which(name)
        assert executable is not None, name
        (fake_bin / name).symlink_to(executable)
    native_environment = _bootstrap_source_fixture(repo, bootstrap_tools, monkeypatch)
    environment = {
        "PATH": str(fake_bin),
        "FIXTURE_SYSTEM": system,
        "FIXTURE_IMAGE_STATE": image_state,
        "PYTHONPATH": str(ROOT),
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_TERMINAL_PROMPT": "0",
        **native_environment,
    }
    return repo, environment


@pytest.mark.parametrize("anchor_state", ["absent", "declared", "material"])
@pytest.mark.parametrize(
    ("system", "image_state"),
    [("Linux", "available"), ("Darwin", "missing"), ("Darwin", "available")],
)
def test_python_bootstrap_supplies_platform_prerequisites(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    anchor_state: str,
    system: str,
    image_state: str,
    bootstrap_tools: Path,
) -> None:
    monkeypatch.setenv("ETHOS_COMMIT_TRUST_ANCHOR", str(tmp_path / "ambient-unknown-anchor"))
    repo, environment = _bootstrap_environment(
        tmp_path, monkeypatch, bootstrap_tools, system=system, image_state=image_state
    )
    anchor = tmp_path / "trust/allowed-signers"
    anchor.parent.mkdir(mode=0o700)
    anchor.write_text("fixture-controlled public trust\n")
    anchor.chmod(0o600)
    if anchor_state == "declared":
        environment["ETHOS_COMMIT_TRUST_ANCHOR"] = str(anchor)
    if anchor_state == "material":
        environment["ETHOS_COMMIT_ALLOWED_SIGNERS"] = anchor.read_text().rstrip("\n")
        environment["TMPDIR"] = str(tmp_path)
        environment["GITHUB_PATH"] = str(tmp_path / "github-path")

    result = run_command(
        repo,
        ("/bin/bash", str(repo / "tools/ci/scripts/bootstrap-python.sh")),
        env=environment,
        inherit_environment=False,
        timeout=30,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert (tmp_path / "fixture.log").read_text() == f"{repo}\n"
    settings = git(repo, "config", "--local", "--list")
    assert (f"gpg.ssh.allowedsignersfile={anchor}" in settings) == (anchor_state == "declared")
    if anchor_state == "material":
        selected = Path(git(repo, "config", "--path", "--get", "gpg.ssh.allowedSignersFile"))
        assert selected.is_relative_to(tmp_path)
        assert selected.read_text() == environment["ETHOS_COMMIT_ALLOWED_SIGNERS"]
        assert not Path(environment["GITHUB_PATH"]).exists()
    assert "ambient-unknown-anchor" not in settings
    apt_log, uv_log = tmp_path / "apt-get.log", tmp_path / "uv.log"
    observed_apt = apt_log.read_text().splitlines() if apt_log.exists() else None
    assert observed_apt == (
        [
            "update -o APT::Update::Error-Mode=any",
            "install -y --no-install-recommends procps lsof util-linux",
        ]
        if system == "Linux"
        else None
    )
    assert not (tmp_path / "mise.log").exists()
    observed_uv = uv_log.read_text(encoding="utf-8").splitlines()
    stages = [command for command in observed_uv if command.startswith("sync ")]
    assert stages == [
        "sync --locked --no-install-project --group dev",
        "sync --locked --group dev",
    ]
    assert (tmp_path / "native.log").read_text().strip() == (
        f"-B {environment['FIXTURE_REPO']}/tools/ci/toolchain/native.py "
        f"--root {environment['FIXTURE_REPO']} --mise vale"
    )
    assert (tmp_path / "node.log").read_text().splitlines() == [
        f"{environment['FIXTURE_SEED_NPM']} ci --ignore-scripts",
        f"{environment['FIXTURE_PRODUCT_NPM']} --version",
        f"{environment['FIXTURE_OPENSPEC']} --version",
    ]
    assert (tmp_path / "fixture.log").read_text().strip() == environment["FIXTURE_REPO"]
    if image_state == "missing":
        assert observed_uv.index("sync --locked --group dev") < observed_uv.index(
            "python install --no-bin 3.14.7"
        )
    else:
        assert not any(command.startswith("python install ") for command in observed_uv)


def test_python_bootstrap_stops_after_seed_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bootstrap_tools: Path
) -> None:
    """A seed failure must precede product probes, final sync and trust mutation."""
    repo, environment = _bootstrap_environment(
        tmp_path, monkeypatch, bootstrap_tools, system="Darwin", image_state="missing"
    )
    anchor = tmp_path / "allowed-signers"
    anchor.write_text("fixture-controlled public trust\n")
    anchor.chmod(0o600)
    environment.update(ETHOS_COMMIT_TRUST_ANCHOR=str(anchor), FIXTURE_SEED_EXIT="37")
    settings = git(repo, "config", "--local", "--list")

    result = run_command(
        repo,
        ("/bin/bash", str(repo / "tools/ci/scripts/bootstrap-python.sh")),
        env=environment,
        inherit_environment=False,
        timeout=30,
    )

    assert result.returncode != 0, result.stdout + result.stderr
    assert (tmp_path / "node.log").read_text().splitlines() == [
        f"{environment['FIXTURE_SEED_NPM']} ci --ignore-scripts"
    ]
    observed_uv = (tmp_path / "uv.log").read_text().splitlines()
    assert [command for command in observed_uv if command.startswith("sync ")] == [
        "sync --locked --no-install-project --group dev"
    ]
    assert not any(command.startswith("python install ") for command in observed_uv)
    assert not (repo / "node_modules/.package-lock.json").exists()
    assert not (tmp_path / "fixture.log").exists()
    assert not (tmp_path / "native-image").exists()
    assert git(repo, "config", "--local", "--list") == settings
