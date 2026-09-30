"""Verify CI image identity, trust anchors, and native Python bootstrap."""

from __future__ import annotations

import os
import shlex
import shutil
import sys
from pathlib import Path

import pytest

import tools.ci.toolchain.environment as ci_environment
from ethos.adapters.process import run_command
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

ROOT = Path(__file__).resolve().parents[3]


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
            '  "sync --locked --group dev") ;;\n'
            "  *) exit 2 ;;\nesac\n"
        ),
        "npx": "exit 0\n",
        "apt-get": 'printf "%s\\n" "$*" >>../apt-get.log\n',
        "ssh-keygen": "exit 0\n",
        "ldconfig": "printf 'libatomic.so.1\\n'; awk 'BEGIN {for(i=0;i<100000;i++) print \"x\"}'\n",
        "openspec": "printf '1.12.0\\n'\n",
        "python": (
            f'[ "$1 $2" != "-B -" ] || exec {shlex.quote(sys.executable)} "$@"\n'
            'case "$*" in\n'
            "  *platform.python_version*) printf '3.14.7\\n' ;;\n"
            "  '-B -I -') cat >/dev/null\n"
            '    [ "$FIXTURE_IMAGE_STATE" = available ] || [ -f ../native-image ] ;;\n'
            '  "-B -I tools/ci/toolchain/fixture_supply.py "*) '
            'printf "%s\\n" "$4" >../fixture.log ;;\n'
            "  *) exit 2 ;;\nesac\n"
        ),
    }
    for name, body in bodies.items():
        path = tools / name
        path.write_text("#!/bin/sh\n" + body)
        path.chmod(0o555)
    return tools


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
    repo = init_git_repo(tmp_path / "repo")
    script_dir = repo / "tools/ci/scripts"
    script_dir.mkdir(parents=True)
    shutil.copy2(ROOT / "tools/ci/scripts/bootstrap-python.sh", script_dir)
    (script_dir / "with-python-runtime.sh").symlink_to(bootstrap_tools / "with-python-runtime")
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    for source in bootstrap_tools.iterdir():
        if source.name not in {"ssh-keygen", "ldconfig"} or system == "Linux":
            (fake_bin / source.name).symlink_to(source)
    for name in ("awk", "cat", "dirname", "grep", "git"):
        executable = shutil.which(name)
        assert executable is not None, name
        (fake_bin / name).symlink_to(executable)
    openspec = repo / "node_modules/.bin/openspec"
    openspec.parent.mkdir(parents=True)
    openspec.symlink_to(bootstrap_tools / "openspec")
    (repo / ".venv/bin").mkdir(parents=True)
    (repo / ".venv/bin/python").symlink_to(bootstrap_tools / "python")
    (repo / "pyproject.toml").write_text(
        '[dependency-groups]\ndev = ["uv>=0.12.10"]\n', encoding="utf-8"
    )
    environment = {
        "PATH": str(fake_bin),
        "FIXTURE_SYSTEM": system,
        "FIXTURE_IMAGE_STATE": image_state,
        "PYTHONPATH": str(ROOT),
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_TERMINAL_PROMPT": "0",
    }
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
        ("/bin/bash", str(script_dir / "bootstrap-python.sh")),
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
    if image_state == "missing":
        assert observed_uv.index("sync --locked --group dev") < observed_uv.index(
            "python install --no-bin 3.14.7"
        )
    else:
        assert not any(command.startswith("python install ") for command in observed_uv)
