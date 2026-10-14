"""Admit commits only through the exact staged native policy closure."""

from __future__ import annotations

import subprocess
from io import StringIO
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.repo.hook.admission as hook_runtime
from ethos.adapters.repo.hook.protocol import execute_hook
from tests.support.runtime_scenarios import git_process

if TYPE_CHECKING:
    from pathlib import Path

_FORMAT_POLICY = ".config/checks/ruff/ruff.toml"
_SECRET_POLICY = ".config/checks/gitleaks/gitleaks.toml"
_SECRET_IGNORE = ".config/checks/gitleaks/gitleaksignore"


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Provide an empty repository whose selected runtime and prewrite owner are neutral."""
    assert git_process(tmp_path, "init", "--quiet", "--initial-branch=dev").returncode == 0
    monkeypatch.setattr(hook_runtime, "current_runtime", lambda _common: None)
    monkeypatch.setattr(
        "ethos.adapters.admission.prewrite.prewrite_guard", lambda **_kwargs: {"verdict": "pass"}
    )
    return tmp_path


def _commit_fixture(repo: Path, message: str) -> None:
    """Record fixture history without signing, hooks or ambient identity."""
    assert (
        git_process(
            repo,
            "-c",
            "user.name=ETHOS Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "-c",
            "core.hooksPath=/dev/null",
            "commit",
            "--no-verify",
            "--quiet",
            "--allow-empty",
            "-m",
            message,
        ).returncode
        == 0
    )


@pytest.mark.parametrize(
    ("extend", "gap"),
    [
        ('extend = "base.toml"\n', ""),
        ("extend = 1\n", f"pre_commit_native_policy_invalid_dependency:{_FORMAT_POLICY}"),
        (
            'extend = "../../../../outside.toml"\n',
            f"pre_commit_native_policy_outside_root:{_FORMAT_POLICY}",
        ),
        (
            'extend = "missing.toml"\n',
            "pre_commit_native_policy_unavailable:.config/checks/ruff/missing.toml",
        ),
    ],
    ids=["closure", "type", "outside", "missing"],
)
def test_pre_commit_projects_the_exact_staged_formatter_closure(
    repo: Path, capsys: pytest.CaptureFixture[str], extend: str, gap: str
) -> None:
    """Formatter includes resolve once inside the staged policy closure or fail closed."""
    (repo / "change.py").write_text("VALUE = 1\n")
    policy = repo / _FORMAT_POLICY
    policy.parent.mkdir(parents=True)
    policy.write_text(extend + "line-length = 100\n")
    (policy.parent / "base.toml").write_text("indent-width = 4\n")
    assert git_process(repo, "add", "change.py", ".config").returncode == 0
    assert execute_hook(repo, "pre-commit", (), stdin=StringIO()) == int(bool(gap))
    error = capsys.readouterr().err
    assert (gap in error) if gap else not error


@pytest.mark.parametrize("retained", [".gitleaks.toml", "ruff.toml", ".gitleaksignore"])
def test_pre_commit_names_native_policy_left_at_the_root(
    repo: Path, capsys: pytest.CaptureFixture[str], retained: str
) -> None:
    """A root policy carrier is a named gap, never a silently skipped check."""
    (repo / retained).write_text("line-length = 100\n")
    (repo / "notes.txt").write_text("staged\n")
    assert git_process(repo, "add", retained, "notes.txt").returncode == 0
    assert execute_hook(repo, "pre-commit", (), stdin=StringIO()) == 1
    assert f"pre_commit_native_policy_noncanonical:{retained}" in capsys.readouterr().err


def test_pre_commit_does_not_format_a_staged_deletion(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A committed Python source staged for deletion has no index bytes to format."""
    (repo / "change.py").write_text("VALUE=1\n")
    policy = repo / _FORMAT_POLICY
    policy.parent.mkdir(parents=True)
    policy.write_text("line-length = 100\n")
    assert git_process(repo, "add", "change.py", _FORMAT_POLICY).returncode == 0
    _commit_fixture(repo, "record formatter and source")
    assert git_process(repo, "rm", "--quiet", "change.py").returncode == 0

    def formatter(*_args: object, **_options: object) -> None:
        pytest.fail("a staged deletion has no index bytes to format")

    monkeypatch.setattr(hook_runtime, "run_command", formatter)
    assert execute_hook(repo, "pre-commit", (), stdin=StringIO()) == 0
    assert not capsys.readouterr().err


@pytest.mark.parametrize("outcome", ["clean", "finding", "head-moved"])
def test_pre_commit_scans_the_staged_secret_policy_closure(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    outcome: str,
) -> None:
    """Gitleaks reads the staged policy closure and ignore file, never working-tree policy."""
    policy = repo / _SECRET_POLICY
    policy.parent.mkdir(parents=True)
    policy.write_text('[extend]\npath = "config/base.toml"\n')
    (repo / "config").mkdir()
    (repo / "config/base.toml").write_text(f'[extend]\npath = "{_SECRET_POLICY}"\n')
    (repo / _SECRET_IGNORE).write_text("fixture:ignored\n")
    (repo / "notes.txt").write_text("staged\n")
    assert git_process(repo, "add", ".").returncode == 0
    policy.write_text("title = 'unstaged working policy'\n")
    monkeypatch.setattr(
        hook_runtime, "shutil", SimpleNamespace(which=lambda _name: "/fixture/gitleaks")
    )
    scans = []

    def scan(cwd: Path, command: tuple[str, ...], **options: object):
        projected = {
            path.relative_to(cwd).as_posix(): path.read_text()
            for path in cwd.rglob("*")
            if path.is_file()
        }
        scans.append((cwd, command, options["env"], projected))
        if outcome == "head-moved":
            _commit_fixture(repo, "concurrent history")
        return subprocess.CompletedProcess(command, int(outcome == "finding"), "", "")

    monkeypatch.setattr(hook_runtime, "run_command", scan)
    gap = {
        "clean": "",
        "finding": "staged_secret_scan_failed",
        "head-moved": "pre_commit_native_policy_head_changed",
    }[outcome]
    assert execute_hook(repo, "pre-commit", (), stdin=StringIO()) == int(bool(gap))
    error = capsys.readouterr().err
    assert (gap in error) if gap else not error
    [(cwd, command, env, projected)] = scans
    assert command[:3] == ("/fixture/gitleaks", "git", "--staged")
    assert env["GIT_WORK_TREE"] == str(cwd)
    assert projected == {
        _SECRET_POLICY: '[extend]\npath = "config/base.toml"\n',
        _SECRET_IGNORE: "fixture:ignored\n",
        "config/base.toml": f'[extend]\npath = "{_SECRET_POLICY}"\n',
    }
