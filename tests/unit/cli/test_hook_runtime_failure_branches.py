from __future__ import annotations

import json
import subprocess
from io import StringIO
from pathlib import Path

import pytest

import ethos.adapters.repo.hook_runtime as runtime


def test_install_rejects_nonexistent_and_relative_python(tmp_path: Path) -> None:
    for python in (Path("python"), tmp_path / "missing-python"):
        with pytest.raises(ValueError, match="hook_runtime_python_invalid"):
            runtime.install_hook_launchers(tmp_path, python=python)


@pytest.mark.parametrize(
    ("returncode", "stdout", "expected"), [(0, "abc\tref\n", "abc"), (2, "", "")]
)
def test_remote_head_is_empty_unless_ls_remote_succeeds(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    returncode: int,
    stdout: str,
    expected: str,
) -> None:
    monkeypatch.setattr(
        runtime,
        "run_git",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], returncode, stdout, ""),
    )
    assert runtime._remote_head(tmp_path, "origin", "refs/heads/dev") == expected  # noqa: SLF001


def test_reference_transition_policy_failure_is_blocked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        runtime,
        "resolve_ref_move_policy",
        lambda *_args: (_ for _ in ()).throw(TypeError("bad policy")),
    )
    report = runtime._reference_transition_report(  # noqa: SLF001
        tmp_path, "prepared", "refs/heads/work/example", "a" * 40, "b" * 40
    )
    assert report["required_gaps"] == ["ref_move_policy_unavailable"]
    assert report["branch"] == "work/example"


def test_candidate_report_rejects_dirty_or_unbound_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    policy = type("Policy", (), {"candidate_branch": "candidate/dev"})()
    monkeypatch.setattr(runtime, "resolve_ref_move_policy", lambda *_args: policy)
    monkeypatch.setattr(
        runtime,
        "worktree_records",
        lambda *_args, **_kwargs: [
            {"branch": "candidate/dev", "path": candidate, "head": "b" * 40}
        ],
    )
    monkeypatch.setattr(
        runtime,
        "run_git",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, "dirty\n", ""),
    )
    report = runtime._candidate_report(  # noqa: SLF001
        tmp_path,
        "candidate/dev",
        "refs/heads/dev",
        "a" * 40,
        "b" * 40,
        "prepared",
    )
    assert report["required_gaps"] == ["candidate_semantic_runner_unavailable"]


def test_candidate_python_requires_clean_binding_and_real_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        runtime,
        "hook_runtime_binding",
        lambda _root: {"required_gaps": ["binding_stale"], "python": ""},
    )
    assert runtime._candidate_python(tmp_path) is None  # noqa: SLF001
    monkeypatch.setattr(
        runtime,
        "hook_runtime_binding",
        lambda _root: {"required_gaps": [], "python": str(tmp_path / "missing")},
    )
    assert runtime._candidate_python(tmp_path) is None  # noqa: SLF001


def test_execute_hook_converts_runtime_exception_to_json_gap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        runtime,
        "_pre_commit",
        lambda _root: (_ for _ in ()).throw(RuntimeError("state unavailable")),
    )
    assert runtime.execute_hook(tmp_path, "pre-commit", (), stdin=StringIO()) == 1
    assert json.loads(capsys.readouterr().err)["required_gaps"] == ["state unavailable"]
