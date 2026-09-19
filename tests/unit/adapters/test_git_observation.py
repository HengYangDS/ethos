"""Bind Git observations to current executables, identity and explicit inputs."""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import UTC
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

import pytest

import ethos.adapters.process as process_adapter
import ethos.adapters.repo.git as git_adapter
import ethos.adapters.repo.git_object as objects
from ethos.adapters.repo.git import ref_progress
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_effect_observation import observe_git_effect
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.subprocesses import completed


def _completed(returncode: int, stdout: bytes = b"") -> subprocess.CompletedProcess[bytes]:
    return subprocess.CompletedProcess((), returncode, stdout, b"")


def test_ref_progress_retains_native_history_and_missing_ref(tmp_path):
    """Native reflog observations distinguish advances from an unavailable ref."""
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")
    git(repo, "branch", "candidate/dev", head)
    first = commit_fixture_file(repo, "first.txt", "first\n", "first")
    second = commit_fixture_file(repo, "second.txt", "second\n", "second")
    git(repo, "update-ref", "-m", "first", "refs/heads/candidate/dev", first, head)
    git(repo, "update-ref", "-m", "second", "refs/heads/candidate/dev", second, first)
    observed = ref_progress(repo, "candidate/dev", observed_at=datetime.now(UTC))
    assert (observed["observation"], observed["ref"], observed["advance_count"]) == (
        "git_reflog",
        "candidate/dev",
        2,
    )
    intervals = (
        "interval_seconds",
        "latest_interval_seconds",
        "latest_advance_age_seconds",
        "advances_per_hour",
    )
    assert all(observed[key] >= 0 for key in intervals)
    assert not {"history", "recorded_at"} & observed.keys()
    observed = ref_progress(repo, "candidate/missing", observed_at=datetime(2026, 8, 6, tzinfo=UTC))
    assert observed == {
        "observation": "git_reflog",
        "ref": "candidate/missing",
        "advance_count": 0,
        **dict.fromkeys(intervals),
    }


@pytest.mark.parametrize("object_format", ["sha1", "sha256"])
def test_batched_effect_observation_preserves_native_queries(tmp_path, monkeypatch, object_format):
    """One fresh batch handles duplicate, missing and native-width refs without caching."""
    repo = init_git_repo(tmp_path / "repo", object_format=object_format)
    head = git(repo, "rev-parse", "HEAD")
    missing = "refs/heads/next"
    effect = GitEffect(updates={missing: GitRefUpdate(expected="0" * len(head), desired=head)})
    calls = Mock(wraps=objects.run_git)
    monkeypatch.setattr(objects, "run_git", calls)
    assert observe_git_effect(repo, effect)["refs"] == {missing: "0" * len(head)}
    assert calls.call_count == 2
    git(repo, "update-ref", missing, head)
    assert objects.resolve_revisions(repo, (missing, missing, "HEAD")) == {
        missing: head,
        "HEAD": head,
    }
    assert calls.call_count == 3
    assert objects.resolve_revisions(repo, ()) == {}
    (repo / ".git" / missing).write_text("a" * len(head) + "\n")
    with pytest.raises(ValueError, match="git_revision_batch_invalid"):
        objects.resolve_revisions(repo, (missing,))
    for code, output in (
        (1, ""),
        (0, ""),
        (0, f"{head} commit 1\n"),
        (0, "not-oid commit 0\n"),
        (0, f"{head} unknown 0\n"),
    ):
        monkeypatch.setattr(
            objects,
            "run_git",
            lambda *_a, output=output, code=code, **_kw: completed(stdout=output, returncode=code),
        )
        with pytest.raises(ValueError, match="git_revision_batch_invalid"):
            objects.resolve_revisions(repo, ("HEAD",))
    with pytest.raises(ValueError, match="git_revision_batch_invalid"):
        objects.resolve_revisions(repo, ("HEAD\nother",))


def test_run_git_resolves_git_from_the_execution_environment_not_import_time(
    tmp_path: Path,
) -> None:
    """Import under an empty PATH without replacing classes held by other tests."""
    repo = init_git_repo(tmp_path / "repo")
    git = git_adapter.shutil.which("git")
    assert git is not None
    script = (
        "import os,sys; from pathlib import Path; os.environ['PATH']=''; "
        "from ethos.adapters.repo.git import run_git; os.environ['PATH']=sys.argv[1]; "
        "assert run_git(Path(sys.argv[2]),'rev-parse','HEAD').returncode == 0"
    )
    process_adapter.run_command(
        repo,
        (sys.executable, "-B", "-c", script, str(Path(git).resolve().parent), str(repo)),
        check=True,
        timeout=10,
    )


def test_run_git_distinguishes_missing_executable_and_working_directory(tmp_path, monkeypatch):
    """Unavailable executable and working directory retain distinct native failures."""
    repo = init_git_repo(tmp_path / "repo")
    with pytest.raises(ValueError, match=r"^git_process_spawn_failed$") as error:
        run_git(repo / "missing", "rev-parse", "HEAD")
    assert getattr(error.value, "reason", "") == "working_directory_unavailable"
    monkeypatch.setenv("PATH", str(tmp_path / "empty-bin"))
    with pytest.raises(ValueError, match=r"^git_executable_unavailable$"):
        run_git(repo, "rev-parse", "HEAD")


def test_run_git_preserves_explicit_commit_identity_without_overriding_local_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    git(repo, "config", "user.name", "Canonical User")
    git(repo, "config", "user.email", "canonical@example.invalid")
    for role in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{role}_NAME", "Hosted Actor")
        monkeypatch.setenv(f"GIT_{role}_EMAIL", "hosted@example.invalid")

    (repo / "identity.txt").write_text("identity\n", encoding="utf-8")
    run_git(repo, "add", "identity.txt")
    run_git(repo, "commit", "-m", "test: preserve explicit identity")

    assert run_git(repo, "config", "user.name").stdout.strip() == "Canonical User"
    assert run_git(repo, "config", "user.email").stdout.strip() == "canonical@example.invalid"
    assert (
        run_git(repo, "show", "-s", "--format=%an <%ae>%n%cn <%ce>").stdout.splitlines()
        == ["Hosted Actor <hosted@example.invalid>"] * 2
    )


@pytest.mark.parametrize(
    ("explicit", "expected_tail"),
    [
        ({"GIT_INDEX_FILE": "/tmp/index"}, ()),
        (
            {
                "GIT_CONFIG_COUNT": "1",
                "GIT_CONFIG_KEY_0": "core.hooksPath",
                "GIT_CONFIG_VALUE_0": "/tmp/hooks",
            },
            (("core.hooksPath", "/tmp/hooks"),),
        ),
    ],
)
def test_run_git_preserves_one_complete_inherited_indexed_config_overlay(
    explicit: dict[str, str],
    expected_tail: tuple[tuple[str, str], ...],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    observed: dict[str, object] = {}
    for key in tuple(os.environ):
        if key == "GIT_CONFIG_COUNT" or key.startswith(("GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_")):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("GIT_DIR", "/untrusted/repository")
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    for index, (key, value) in enumerate((("safe.directory", repo.as_posix()),)):
        monkeypatch.setenv(f"GIT_CONFIG_KEY_{index}", key)
        monkeypatch.setenv(f"GIT_CONFIG_VALUE_{index}", value)
    monkeypatch.setattr(
        process_adapter,
        "run_command",
        lambda _root, command, **kwargs: observed.update(command=command, **kwargs) or completed(),
    )

    run_git(repo, "status", env=explicit)

    environment = observed["env"]
    assert "GIT_DIR" not in environment
    assert environment["GIT_TERMINAL_PROMPT"] == "0"
    assert environment["GIT_CONFIG_COUNT"] == str(1 + len(expected_tail))
    assert tuple(
        (environment[f"GIT_CONFIG_KEY_{index}"], environment[f"GIT_CONFIG_VALUE_{index}"])
        for index in range(1 + len(expected_tail))
    ) == (
        ("safe.directory", repo.as_posix()),
        *expected_tail,
    )
    if "GIT_INDEX_FILE" in explicit:
        assert environment["GIT_INDEX_FILE"] == "/tmp/index"


@pytest.mark.parametrize(
    "environment",
    [
        {"GIT_CONFIG_COUNT": "invalid"},
        {"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "safe.directory"},
        {"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_VALUE_0": "/repo"},
        {
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "credential.helper",
            "GIT_CONFIG_VALUE_0": "",
        },
        {
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "safe.directory",
            "GIT_CONFIG_VALUE_0": "*",
        },
        {
            "GIT_CONFIG_COUNT": "0",
            "GIT_CONFIG_KEY_0": "safe.directory",
            "GIT_CONFIG_VALUE_0": "/repo",
        },
    ],
)
def test_run_git_rejects_malformed_or_broad_inherited_indexed_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, environment: dict[str, str]
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    for key in tuple(os.environ):
        if key == "GIT_CONFIG_COUNT" or key.startswith(("GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_")):
            monkeypatch.delenv(key, raising=False)
    for key, value in environment.items():
        monkeypatch.setenv(key, value)

    with pytest.raises(ValueError, match=r"^git_config_overlay_invalid$"):
        run_git(repo, "status")


def test_network_git_preserves_effective_global_credentials(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    observed: dict[str, object] = {}
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/tmp/effective-global-gitconfig")
    monkeypatch.setattr(
        process_adapter,
        "run_command",
        lambda _root, command, **kwargs: observed.update(command=command, **kwargs) or completed(),
    )

    git_adapter.run_network_git(init_git_repo(tmp_path / "repo"), "ls-remote", "origin")

    environment = observed["env"]
    assert environment["GIT_CONFIG_GLOBAL"] == "/tmp/effective-global-gitconfig"
    assert environment["GIT_TERMINAL_PROMPT"] == "0"


def test_git_observations_fail_closed_on_unavailable_or_ambiguous_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert git_adapter.committed_file_bytes(tmp_path, "", "file") == b""
    monkeypatch.setattr(git_adapter, "run_git", lambda *_args, **_kwargs: _completed(1))
    assert git_adapter.committed_file_bytes(tmp_path, "a" * 40, "file") == b""
    assert git_adapter.git_files(tmp_path, "*.py") == []
    for returncode, payload in (
        (1, b""),
        (0, b"R100\0source"),
        (0, b"R100\0\xff\0target\0"),
        (0, b"C100\0source\0copy\0R100\0source\0target\0"),
    ):
        monkeypatch.setattr(
            git_adapter,
            "run_git",
            lambda *_args, outcome=(returncode, payload), **_kwargs: _completed(*outcome),
        )
        assert git_adapter.exact_rename_target(tmp_path, "old", "new", "source") == ""
    monkeypatch.setattr(git_adapter, "current_tracked_head", lambda _root: "a" * 40)
    assert git_adapter.remote_tracking_sync(tmp_path, "")["state"] == "branch_unknown"
    values = iter(("b" * 40, "not counts"))
    monkeypatch.setattr(git_adapter, "git_stdout", lambda *_args, **_kwargs: next(values))
    report = git_adapter.remote_tracking_sync(tmp_path, "dev")
    assert (report["state"], report["ahead"], report["behind"]) == ("synchronized", 0, 0)
