"""Git observation and executable public failure matrix."""

from __future__ import annotations

import subprocess
from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.process as process_adapter
import ethos.adapters.repo.git as git

if TYPE_CHECKING:
    from pathlib import Path


def _completed(code: int, stdout="", stderr=""):
    return subprocess.CompletedProcess((), code, stdout, stderr)


def test_git_executable_rejects_resolved_non_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    directory = tmp_path / "git"
    directory.mkdir()
    monkeypatch.setattr(git.shutil, "which", lambda *_args, **_kwargs: directory.as_posix())

    with pytest.raises(ValueError, match="git_executable_unavailable") as error:
        git.git_executable({"PATH": tmp_path.as_posix()})

    assert error.value.reason == "resolved_executable_invalid"


def test_observation_rejects_environment_override(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="git_observation_environment_override_forbidden"):
        git.run_git(tmp_path, "status", observation=True, env={"CUSTOM": "value"})


def test_run_git_supports_text_and_binary_public_overloads(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(git, "git_executable", lambda _environment: "/git")
    observed = []

    def execute(root, command, **kwargs):
        observed.append((root, command, kwargs))
        return _completed(0, b"bytes" if kwargs["text"] is False else "text")

    monkeypatch.setattr(process_adapter, "run_command", execute)

    assert git.run_git(tmp_path, "show", text=True).stdout == "text"
    assert git.run_git(tmp_path, "show", text=False).stdout == b"bytes"
    assert [call[2]["text"] for call in observed] == [True, False]


def test_committed_bytes_and_git_files_preserve_unavailable(monkeypatch, tmp_path: Path) -> None:
    assert git.committed_file_bytes(tmp_path, "", "file") == b""
    monkeypatch.setattr(git, "run_git", lambda *_args, **_kwargs: _completed(1, b""))
    assert git.committed_file_bytes(tmp_path, "a" * 40, "file") == b""
    assert git.git_files(tmp_path, "*.py") == []


def test_exact_rename_rejects_failed_truncated_and_non_utf8(monkeypatch, tmp_path: Path) -> None:
    outcomes = iter(
        (
            _completed(1, b""),
            _completed(0, b"R100\0source"),
            _completed(0, b"R100\0\xff\0target\0"),
        )
    )
    monkeypatch.setattr(git, "run_git", lambda *_args, **_kwargs: next(outcomes))

    assert git.exact_rename_target(tmp_path, "old", "new", "source") == ""
    assert git.exact_rename_target(tmp_path, "old", "new", "source") == ""
    assert git.exact_rename_target(tmp_path, "old", "new", "source") == ""


def test_exact_rename_rejects_copy_ambiguity(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    payload = b"C100\0source\0copy\0R100\0source\0target\0"
    monkeypatch.setattr(git, "run_git", lambda *_args, **_kwargs: _completed(0, payload))

    assert git.exact_rename_target(tmp_path, "old", "new", "source") == ""


def test_exact_rename_rejects_unexpected_diff_records(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    payload = b"M\0other\0R100\0source\0target\0"
    monkeypatch.setattr(git, "run_git", lambda *_args, **_kwargs: _completed(0, payload))

    assert git.exact_rename_target(tmp_path, "old", "new", "source") == ""


def test_remote_tracking_reports_unknown_and_malformed_counts(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(git, "current_tracked_head", lambda _root: "a" * 40)
    assert git.remote_tracking_sync(tmp_path, "")["state"] == "branch_unknown"

    values = iter(("b" * 40, "not counts"))
    monkeypatch.setattr(git, "git_stdout", lambda *_args, **_kwargs: next(values))
    report = git.remote_tracking_sync(tmp_path, "dev")
    assert (report["state"], report["ahead"], report["behind"]) == ("synchronized", 0, 0)


def test_ref_progress_ignores_malformed_reflog_selector(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(git, "git_stdout", lambda *_args, **_kwargs: "a" * 40 + "\0malformed")

    report = git.ref_progress(
        tmp_path,
        "candidate/dev",
        observed_at=datetime(2026, 8, 10, tzinfo=UTC),
    )

    assert report["advance_count"] == 0
    assert report["latest_advance_age_seconds"] is None


def test_remote_availability_reports_unconfigured_timeout_success_and_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(git, "git_stdout", lambda *_args, **_kwargs: "")
    assert git.remote_availability(tmp_path)["state"] == "unconfigured"

    monkeypatch.setattr(git, "git_stdout", lambda *_args, **_kwargs: "ssh://origin")
    monkeypatch.setattr(git, "git_executable", lambda _env: "/git")
    monkeypatch.setattr(
        process_adapter,
        "run_command",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(subprocess.TimeoutExpired("git", 3)),
    )
    assert git.remote_availability(tmp_path)["reason"] == "timeout"

    monkeypatch.setattr(process_adapter, "run_command", lambda *_args, **_kwargs: _completed(0))
    assert git.remote_availability(tmp_path)["state"] == "available"
    monkeypatch.setattr(
        process_adapter,
        "run_command",
        lambda *_args, **_kwargs: _completed(1, stderr="offline"),
    )
    failed = git.remote_availability(tmp_path)
    assert (failed["state"], failed["reason"], failed["stderr"]) == (
        "unavailable",
        "ls_remote_failed",
        "offline",
    )
