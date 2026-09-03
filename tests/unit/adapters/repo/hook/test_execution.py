"""Tests for the concrete semantic owner named by this module path."""

from __future__ import annotations

import json
import subprocess
import sys
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

import pytest

import ethos.adapters.repo.hook_runtime as hook_runtime
import ethos.adapters.repo.hook_runtime as runtime
import ethos.adapters.repo.runtime.binding as runtime_binding_module
import ethos.adapters.repo.runtime.selection as runtime_selection
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.hook.binding import hook_launcher
from ethos.adapters.repo.hook_runtime import execute_hook
from ethos.contracts.branch.roles import BranchRolePolicy
from tests.support.runtime_scenarios import REPOSITORY_ROOT
from tests.support.runtime_scenarios import candidate_runtime
from tests.support.runtime_scenarios import git_process


def test_hook_launcher_uses_git_shell_and_current_runtime_selector() -> None:
    text = hook_launcher("pre-commit")

    assert 'HOOK_DIR=${0%/*}; [ "$HOOK_DIR" = "$0" ] && HOOK_DIR=.' in text
    assert 'HOOK_DIR=$(CDPATH= cd "$HOOK_DIR" && pwd)' in text
    assert 'RUNTIME_ROOT="$HOOK_DIR/../../runtime"' in text
    assert 'CURRENT="$RUNTIME_ROOT/CURRENT"' in text
    assert 'exec "$RUNTIME/python/bin/python" -B -I -m ethos.cli hook run pre-commit "$@"' in text


def test_hook_launcher_enters_the_selected_runtime_without_ambient_path(tmp_path: Path) -> None:
    digest = "a" * 64
    hooks = tmp_path / "ethos/hooks/generation"
    runtime = tmp_path / "ethos/runtime" / digest / "python/bin/python"
    hooks.mkdir(parents=True)
    runtime.parent.mkdir(parents=True)
    (tmp_path / "ethos/runtime/CURRENT").write_text(f"{digest}\n", encoding="ascii")
    runtime.write_text('#!/bin/sh\nprintf "%s\\n" "$*"\n', encoding="utf-8")
    runtime.chmod(0o755)
    launcher = hooks / "pre-commit"
    launcher.write_text(hook_launcher("pre-commit"), encoding="utf-8")
    launcher.chmod(0o755)

    completed = subprocess.run(
        (launcher.as_posix(), "argument"),
        check=False,
        capture_output=True,
        env={"PATH": ""},
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout == "-B -I -m ethos.cli hook run pre-commit argument\n"


def test_windows_hook_launcher_uses_the_standalone_runtime_python(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runtime_selection, "os", SimpleNamespace(name="nt"))

    text = hook_launcher("pre-commit")

    assert 'exec "$RUNTIME/python/python.exe" -B -I -m ethos.cli hook run pre-commit "$@"' in text
    assert "Scripts/python.exe" not in text


@pytest.mark.parametrize(
    ("name", "arguments", "stdin", "expected", "gap"),
    [
        ("pre-commit", (), "", 0, ""),
        ("pre-push", ("origin",), "invalid\n", 1, "push_update_invalid"),
        ("pre-push", ("origin",), f"refs/heads/x {'0' * 40} refs/heads/x {'a' * 40}\n", 0, ""),
        ("reference-transaction", ("unknown",), "", 0, ""),
        ("reference-transaction", ("prepared",), "invalid\n", 1, "ref_update_invalid"),
        (
            "reference-transaction",
            ("prepared",),
            f"{'a' * 40} {'b' * 40} refs/tags/v1\n",
            0,
            "",
        ),
    ],
)
def test_hook_runtime_public_input_matrix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    name: hook_runtime.HookName,
    arguments: tuple[str, ...],
    stdin: str,
    expected: int,
    gap: str,
) -> None:
    """Every Git protocol envelope either dispatches once or fails closed."""
    repo = tmp_path / "repo"
    repo.mkdir()
    assert git_process(repo, "init", "--quiet", "--initial-branch=dev").returncode == 0
    monkeypatch.setattr(hook_runtime, "current_runtime", lambda _common: None)

    result = execute_hook(repo, name, arguments, stdin=StringIO(stdin))

    assert result == expected
    error = capsys.readouterr().err
    assert (gap in error) if gap else not error


def test_hook_execution_observes_the_full_runtime_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    assert git_process(repo, "init", "--quiet", "--initial-branch=dev").returncode == 0
    selected_runtime = object()
    observations: list[Path] = []
    projections: list[object] = []

    def observe_runtime(common: Path) -> object:
        observations.append(common)
        return selected_runtime

    def project_runtime(
        _root: Path, *, selected_runtime: object | None = None
    ) -> dict[str, object]:
        projections.append(selected_runtime)
        return {"required_gaps": [], "python": sys.executable}

    monkeypatch.setattr(hook_runtime, "current_runtime", observe_runtime)
    monkeypatch.setattr(runtime_binding_module, "hook_runtime_binding", project_runtime)
    (repo / "README.md").write_text("changed\n", encoding="utf-8")
    assert git_process(repo, "add", "README.md").returncode == 0

    assert execute_hook(repo, "pre-commit", (), stdin=StringIO()) == 1
    assert observations == [Path(git_common_dir(repo))]
    assert projections
    assert all(projection is selected_runtime for projection in projections)


def test_repository_does_not_track_host_specific_hook_launchers() -> None:
    completed = git_process(REPOSITORY_ROOT, "ls-files", ".githooks")

    assert completed.returncode == 0
    assert completed.stdout == ""


def test_pre_commit_skips_unselected_staged_secret_capability(monkeypatch, tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    assert git_process(repo, "init", "--quiet", "--initial-branch=dev").returncode == 0
    monkeypatch.setattr(hook_runtime, "current_runtime", lambda _common: None)
    monkeypatch.setattr(
        hook_runtime, "hook_admission_report", lambda **_kwargs: {"verdict": "pass"}
    )
    (repo / "README.md").write_text("# governed work lane\n", encoding="utf-8")
    assert git_process(repo, "add", "README.md").returncode == 0

    assert execute_hook(repo, "pre-commit", (), stdin=StringIO()) == 0


@pytest.mark.parametrize(
    ("runner", "stdout", "gap"),
    [
        ("missing", "", "candidate_semantic_runner_unavailable"),
        ("invalid-json", "not-json", "candidate_semantic_runner_invalid"),
        ("invalid-envelope", "{}", "candidate_semantic_runner_invalid"),
        ("pass", '{"data":{"verdict":"pass","state":"admitted","required_gaps":[]}}', ""),
    ],
)
def test_candidate_transition_requires_one_bound_semantic_runner(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    runner: str,
    stdout: str,
    gap: str,
) -> None:
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    python = candidate / "runtime-python"
    python.write_text("runtime", encoding="utf-8")
    policy = BranchRolePolicy()
    selected_runtime = object()
    projections: list[object | None] = []
    monkeypatch.setattr(
        hook_runtime,
        "current_runtime",
        lambda _common: selected_runtime,
    )
    monkeypatch.setattr(hook_runtime, "resolve_ref_move_policy", lambda *_args: policy)
    monkeypatch.setattr(
        hook_runtime,
        "worktree_records",
        lambda *_args, **_kwargs: (
            []
            if runner == "missing"
            else [{"branch": policy.candidate_branch, "path": candidate, "head": "b" * 40}]
        ),
    )

    def project_runtime(
        _root: Path, *, selected_runtime: object | None = None, **_kwargs: object
    ) -> dict[str, object]:
        projections.append(selected_runtime)
        return {"required_gaps": [], "python": python.as_posix()}

    monkeypatch.setattr(hook_runtime, "hook_runtime_binding", project_runtime)
    monkeypatch.setattr(
        hook_runtime,
        "run_git",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, "", ""),
    )
    commands: list[tuple[str, ...]] = []

    def execute(_root: Path, command: tuple[str, ...], **_kwargs) -> subprocess.CompletedProcess:
        commands.append(command)
        return subprocess.CompletedProcess([], 0, stdout, "")

    monkeypatch.setattr(hook_runtime, "run_command", execute)
    update = f"{'a' * 40} {'b' * 40} refs/heads/dev\n"

    result = execute_hook(
        tmp_path,
        "reference-transaction",
        ("prepared",),
        stdin=StringIO(update),
    )

    assert result == (1 if gap else 0)
    error = capsys.readouterr().err
    assert (gap in error) if gap else not error
    if runner != "missing":
        assert commands[0][1:3] == ("-B", "-I")
        assert projections
        assert all(projection is selected_runtime for projection in projections)


def test_hook_execution_rejects_a_noncanonical_current_selector(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    assert git_process(repo, "init", "--quiet", "--initial-branch=dev").returncode == 0
    selector = Path(git_common_dir(repo)) / "ethos" / "runtime" / "CURRENT"
    selector.parent.mkdir(parents=True)
    selector.write_text("invalid\n", encoding="utf-8")

    assert execute_hook(repo, "pre-commit", (), stdin=StringIO()) == 1
    assert "hook_runtime_current_invalid" in capsys.readouterr().err


def test_pre_push_binds_named_remote_and_observed_remote_head(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(hook_runtime, "current_runtime", lambda _common: None)
    monkeypatch.setattr(
        hook_runtime,
        "push_admission_report",
        lambda **kwargs: (
            calls.append(kwargs) or {"verdict": "pass", "state": "admitted", "required_gaps": []}
        ),
    )
    update = f"refs/heads/dev {'a' * 40} refs/heads/dev {'b' * 40}\n"

    assert execute_hook(tmp_path, "pre-push", ("github",), stdin=StringIO(update)) == 0

    assert calls[0]["remote_name"] == "github"
    assert calls[0]["remote_head"] == "b" * 40
    assert "reconciliation" not in calls[0]


@pytest.mark.parametrize(
    ("capability", "gap"),
    [
        ("secrets", "staged_secret_gitleaks_missing"),
        ("format", "pre_commit_python_format_failed"),
    ],
)
def test_pre_commit_fails_closed_when_a_selected_capability_cannot_prove_clean(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    capability: str,
    gap: str,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    assert git_process(repo, "init", "--quiet", "--initial-branch=dev").returncode == 0
    staged = repo / "change.py"
    staged.write_text("VALUE=1\n", encoding="utf-8")
    assert git_process(repo, "add", "change.py").returncode == 0
    monkeypatch.setattr(hook_runtime, "current_runtime", lambda _common: None)
    if capability == "secrets":
        (repo / ".gitleaks.toml").write_text("title = 'policy'\n", encoding="utf-8")
        which = hook_runtime.shutil.which
        monkeypatch.setattr(
            hook_runtime.shutil,
            "which",
            lambda name, **kwargs: None if name == "gitleaks" else which(name, **kwargs),
        )
    else:
        (repo / "ruff.toml").write_text("line-length = 100\n", encoding="utf-8")
        monkeypatch.setattr(
            hook_runtime,
            "run_command",
            lambda *_args, **_kwargs: subprocess.CompletedProcess([], 1, "", "format drift"),
        )

    assert execute_hook(repo, "pre-commit", (), stdin=StringIO()) == 1
    assert gap in capsys.readouterr().err


@pytest.mark.parametrize(
    ("branch", "phase", "decision", "expected", "state"),
    [
        ("work/change", "prepared", "allow", 0, "work-prepared"),
        ("topic", "prepared", "allow", 0, "unprotected_ref"),
        ("topic", "prepared", "block", 1, "topic-blocked"),
        ("topic", "aborted", "block", 0, "aborted_observed"),
        ("topic", "committed", "allow", 0, "topic-committed"),
    ],
)
def test_reference_transaction_dispatch_preserves_role_and_phase_semantics(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    branch: str,
    phase: str,
    decision: str,
    expected: int,
    state: str,
) -> None:
    policy = BranchRolePolicy()
    monkeypatch.setattr(hook_runtime, "current_runtime", lambda _common: None)
    monkeypatch.setattr(hook_runtime, "resolve_ref_move_policy", lambda *_args: policy)
    monkeypatch.setattr(
        hook_runtime,
        "work_lane_ref_transition_report",
        lambda **_kwargs: {"verdict": "pass", "state": "work-prepared", "required_gaps": []},
    )
    monkeypatch.setattr(
        hook_runtime,
        "ref_move_admission_report",
        lambda **_kwargs: {
            "verdict": "block" if decision == "block" else "pass",
            "state": f"topic-{phase}" if decision == "allow" else "topic-blocked",
            "decision": {"action": decision},
            "required_gaps": ["raw_ref_blocked"] if decision == "block" else [],
        },
    )
    update = f"{'a' * 40} {'b' * 40} refs/heads/{branch}\n"

    result = execute_hook(
        tmp_path,
        "reference-transaction",
        (phase,),
        stdin=StringIO(update),
    )

    assert result == expected
    error = capsys.readouterr().err
    if expected:
        assert state in error
    else:
        assert not error


def test_execute_hook_converts_runtime_exception_to_json_gap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(runtime, "current_runtime", lambda _common: None)
    monkeypatch.setattr(
        runtime,
        "run_git",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("state unavailable")),
    )
    assert runtime.execute_hook(tmp_path, "pre-commit", (), stdin=StringIO()) == 1
    assert json.loads(capsys.readouterr().err)["required_gaps"] == ["state unavailable"]


def test_candidate_report_rejects_dirty_or_unbound_candidate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(runtime, "current_runtime", lambda _common: None)
    candidate_runtime(monkeypatch, tmp_path, status="dirty\n")
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
    monkeypatch.setattr(runtime, "current_runtime", lambda _common: None)
    candidate_runtime(monkeypatch, tmp_path, status="")
    if binding["python"]:
        binding["python"] = str(tmp_path / str(binding["python"]))
    monkeypatch.setattr(
        runtime,
        "hook_runtime_binding",
        lambda _root, **_kwargs: binding,
    )
    result = runtime.execute_hook(
        tmp_path,
        "reference-transaction",
        ("prepared",),
        stdin=StringIO(f"{'a' * 40} {'b' * 40} refs/heads/dev\n"),
    )

    assert result == 1
    assert "candidate_semantic_runner_unavailable" in capsys.readouterr().err


def test_reference_transition_policy_failure_is_blocked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(runtime, "current_runtime", lambda _common: None)
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
