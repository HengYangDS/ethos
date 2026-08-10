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
    observed = []
    monkeypatch.setattr(
        runtime,
        "run_git",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], returncode, stdout, ""),
    )
    receipt = tmp_path / "reconciliation.json"
    monkeypatch.setenv("ETHOS_RECONCILIATION_RECEIPT", receipt.as_posix())
    monkeypatch.setattr(
        runtime,
        "_declared_peer_heads",
        lambda _root: (("gitlab", expected, expected), ("github", expected, expected)),
    )
    monkeypatch.setattr(
        runtime,
        "push_admission_report",
        lambda **kwargs: (
            observed.append(kwargs["reconciliation"].peer_heads)
            or {
                "verdict": "pass",
                "state": "admitted",
                "required_gaps": [],
            }
        ),
    )

    result = runtime.execute_hook(
        tmp_path,
        "pre-push",
        ("origin",),
        stdin=StringIO(f"refs/heads/dev {'a' * 40} refs/heads/dev {'b' * 40}\n"),
    )

    assert result == 0
    assert observed == [(("gitlab", expected, expected), ("github", expected, expected))]


def test_reference_transition_policy_failure_is_blocked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        runtime,
        "resolve_ref_move_policy",
        lambda *_args: (_ for _ in ()).throw(TypeError("bad policy")),
    )
    result = runtime.execute_hook(
        tmp_path,
        "reference-transaction",
        ("prepared",),
        stdin=StringIO(f"{'a' * 40} {'b' * 40} refs/heads/work/example\n"),
    )
    assert result == 1


def test_candidate_report_rejects_dirty_or_unbound_candidate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    policy = type(
        "Policy",
        (),
        {
            "candidate_branch": "candidate/dev",
            "accepted_branch": "dev",
            "release_branch": "main",
            "release_mirror": "independent",
            "role_for_branch": lambda _self, _branch: "accepted",
        },
    )()
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
    result = runtime.execute_hook(
        tmp_path,
        "reference-transaction",
        ("prepared",),
        stdin=StringIO(f"{'a' * 40} {'b' * 40} refs/heads/dev\n"),
    )

    assert result == 1
    assert json.loads(capsys.readouterr().err)["required_gaps"] == [
        "candidate_semantic_runner_unavailable"
    ]


@pytest.mark.parametrize(
    "binding",
    [
        {"required_gaps": ["binding_stale"], "python": ""},
        {"required_gaps": [], "python": "missing"},
    ],
)
def test_candidate_runner_requires_clean_binding_and_real_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    binding: dict[str, object],
) -> None:
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    if binding["python"]:
        binding["python"] = str(tmp_path / str(binding["python"]))
    policy = type(
        "Policy",
        (),
        {
            "candidate_branch": "candidate/dev",
            "accepted_branch": "dev",
            "release_branch": "main",
            "release_mirror": "independent",
            "role_for_branch": lambda _self, _branch: "accepted",
        },
    )()
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
        "hook_runtime_binding",
        lambda _root: binding,
    )
    monkeypatch.setattr(
        runtime,
        "run_git",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, "", ""),
    )

    result = runtime.execute_hook(
        tmp_path,
        "reference-transaction",
        ("prepared",),
        stdin=StringIO(f"{'a' * 40} {'b' * 40} refs/heads/dev\n"),
    )

    assert result == 1
    assert "candidate_semantic_runner_unavailable" in capsys.readouterr().err


def test_execute_hook_converts_runtime_exception_to_json_gap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        runtime,
        "run_git",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("state unavailable")),
    )
    assert runtime.execute_hook(tmp_path, "pre-commit", (), stdin=StringIO()) == 1
    assert json.loads(capsys.readouterr().err)["required_gaps"] == ["state unavailable"]
