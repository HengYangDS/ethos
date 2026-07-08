# ruff: noqa: ARG005
"""Coverage-closure v3: clidomain reachable branches (100% no-exemption)."""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING

import ethos.surface.cli.root.inspection as inspection_cli
import ethos.surface.cli.root.proof as proof_cli
from ethos.adapters.mutation.core import MutationDecision
from ethos.domain import land_support
from ethos.domain import orient
from ethos.domain import report
from ethos.domain import status
from ethos.surface.cli import hook

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def _init_git_repo(path: Path) -> Path:
    """Init a throwaway git repo with a deterministic identity and one commit."""
    subprocess.run(["git", "init", "-b", "main", str(path)], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(path), "config", "user.name", "cov"], check=True, capture_output=True
    )
    subprocess.run(
        ["git", "-C", str(path), "config", "user.email", "cov@example.test"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "commit", "--allow-empty", "-m", "init"],
        check=True,
        capture_output=True,
    )
    return path


# --------------------------------------------------------------------------- #
# ethos.surface.cli.root.proof.missing_gate_dependency_next_actions (lines 81, 84, 94)
# --------------------------------------------------------------------------- #


def test_missing_gate_dependency_revisits_shared_dependency() -> None:
    # build depends on (unit-architecture, ruff); selecting build+ruff means ruff is
    # already in `seen` when the top loop reaches it, taking the early return at line 81.
    command = proof_cli.missing_gate_dependency_next_actions(
        selected_gate_ids=("build", "ruff"),
        validation_gaps=("missing_dependency:build->unit-architecture",),
        current_head="HEADSHA",
    )
    assert command == (
        "ethos prove --execute --gate unit-architecture --gate ruff "
        "--gate build --expect-head HEADSHA --json",
    )


def test_missing_gate_dependency_unknown_gate_and_absent_dependency() -> None:
    # An unknown gate id -> registry.get returns None -> line 84 return; ordered stays
    # empty so the missing dependency is not in it -> line 93 True -> line 94 return ().
    command = proof_cli.missing_gate_dependency_next_actions(
        selected_gate_ids=("ghost-gate",),
        validation_gaps=("missing_dependency:foo->schemas",),
        current_head="HEADSHA",
    )
    assert command == ()


# --------------------------------------------------------------------------- #
# ethos.cli status/orient human output loops (lines 140-141, 183-184)
# --------------------------------------------------------------------------- #


def test_status_human_output_prints_orientation_lines(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Non-json status drives the human-orientation print loop at cli.py lines 140-141.
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/dev/null")
    repo = _init_git_repo(tmp_path)

    inspection_cli.status(root=repo, json_output=False)

    printed = capsys.readouterr().out
    assert printed.strip()
    assert "capability=" in printed


def test_orient_human_output_prints_orientation_lines(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Non-json orient drives the human-orientation print loop at cli.py lines 183-184.
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/dev/null")
    repo = _init_git_repo(tmp_path)

    inspection_cli.orient(root=repo, json_output=False)

    printed = capsys.readouterr().out
    assert printed.strip()
    assert "capability=" in printed


# --------------------------------------------------------------------------- #
# ethos.cli doctor init_state falsy branch (569->571)
# --------------------------------------------------------------------------- #


def test_doctor_skips_state_init_when_flag_false(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # init_state=False takes the branch 569->571 (skip initialize_state); the reported
    # state db must therefore not exist.
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/dev/null")
    repo = _init_git_repo(tmp_path)

    inspection_cli.doctor(root=repo, init_state=False, json_output=True)

    printed = capsys.readouterr().out
    assert '"initialized": false' in printed
    assert not (repo / ".ethos" / "state" / "state.sqlite").exists()


def test_doctor_reports_missing_host_wrapper(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _init_git_repo(tmp_path / "repo")
    monkeypatch.setattr(
        inspection_cli.shutil,
        "which",
        lambda command: "" if command == "ethos" else command,
    )

    inspection_cli.doctor(root=repo, init_state=False, json_output=True)

    payload = json.loads(capsys.readouterr().out)
    wrapper = payload["data"]["host_wrapper"]
    assert wrapper["state"] == "not_found"
    assert wrapper["advisory_gaps"] == ["host_wrapper_not_found"]


def test_doctor_reports_fixed_root_host_wrapper(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _init_git_repo(tmp_path / "repo")
    fixed = tmp_path / "bin" / "ethos"
    fixed.parent.mkdir()
    fixed.write_text(
        "#!/usr/bin/env bash\n"
        'ETHOS_ROOT="${ETHOS_ROOT:-$HOME/projects/ethos}"\n'
        'cd "$ETHOS_ROOT"\n'
        'exec npm run -s ethos -- "$@"\n',
        encoding="utf-8",
    )
    fixed.chmod(0o755)
    original_path = __import__("os").environ.get("PATH", "")
    monkeypatch.setenv("PATH", f"{fixed.parent.as_posix()}:{original_path}")

    inspection_cli.doctor(root=repo, init_state=False, json_output=True)

    payload = json.loads(capsys.readouterr().out)
    wrapper = payload["data"]["host_wrapper"]
    assert wrapper["state"] == "fixed_root_wrapper"
    assert "host_wrapper_fixed_root" in wrapper["advisory_gaps"]
    assert wrapper["path"] == fixed.as_posix()


def test_doctor_accepts_explicit_ethos_root_for_host_wrapper(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _init_git_repo(tmp_path / "repo")
    fixed = tmp_path / "bin" / "ethos"
    fixed.parent.mkdir()
    fixed.write_text(
        "#!/usr/bin/env bash\n"
        'ETHOS_ROOT="${ETHOS_ROOT:-$HOME/projects/ethos}"\n'
        'cd "$ETHOS_ROOT"\n'
        'exec npm run -s ethos -- "$@"\n',
        encoding="utf-8",
    )
    fixed.chmod(0o755)
    original_path = __import__("os").environ.get("PATH", "")
    monkeypatch.setenv("PATH", f"{fixed.parent.as_posix()}:{original_path}")
    monkeypatch.setenv("ETHOS_ROOT", repo.as_posix())

    inspection_cli.doctor(root=repo, init_state=False, json_output=True)

    payload = json.loads(capsys.readouterr().out)
    wrapper = payload["data"]["host_wrapper"]
    assert wrapper["state"] == "ok"
    assert wrapper["env_ethos_root"] == repo.as_posix()
    assert wrapper["advisory_gaps"] == []


# --------------------------------------------------------------------------- #
# ethos.domain.land_support.closeout_audit_root (lines 122, 126-127)
# --------------------------------------------------------------------------- #


def test_closeout_audit_root_returns_repo_when_decision_blocked(tmp_path: Path) -> None:
    # decision.ok is False -> early return of the passed repo at line 122.
    result = land_support.closeout_audit_root(tmp_path, MutationDecision(ok=False, state="blocked"))
    assert result == tmp_path


def test_closeout_audit_root_resolves_candidate_when_admitted(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # decision.ok True with a real repo whose candidate has an empty worktree_path drives
    # lines 126-127 (candidate_path derived, then the else branch returns repo).
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/dev/null")
    repo = _init_git_repo(tmp_path)

    result = land_support.closeout_audit_root(repo, MutationDecision(ok=True, state="accepted"))

    assert result == repo


# --------------------------------------------------------------------------- #
# ethos.domain.orient._next_actions report fallback (line 346)
# --------------------------------------------------------------------------- #


def test_next_actions_falls_back_to_report_next_actions() -> None:
    # A non-work-lane/accepted/candidate role with no dirty state and no gaps falls to the
    # report-payload branch at line 346, adopting the report's own next_actions.
    actions = orient._next_actions(
        {
            "role": "release_root",
            "dirty": False,
            "gaps": [],
            "closeout": {},
            "report_payload": {"next_actions": ["ethos report --json"]},
            "advisory_next_actions": [],
        }
    )
    assert actions == ["ethos report --json"]


# --------------------------------------------------------------------------- #
# ethos.domain.report._advisory_next_actions non-matching gap (branch 257->255)
# --------------------------------------------------------------------------- #


def test_advisory_next_actions_skips_non_matching_gap() -> None:
    # A gap that is not a 4-part openspec-unarchived signal fails the guard at line 257,
    # taking the branch 257->255 back to the loop head and yielding no actions.
    assert report._advisory_next_actions(("some_unrelated_gap",)) == ()


# --------------------------------------------------------------------------- #
# ethos.domain.status reducers (lines 30, 52, 131)
# --------------------------------------------------------------------------- #


def test_string_list_returns_empty_for_non_list() -> None:
    # A non-list value takes the guard at line 30 and returns [].
    assert status.string_list("not-a-list") == []


def test_adoption_mutation_gaps_flags_head_mismatch() -> None:
    # apply+authorize with a tracked head and a mismatching expect_head reaches the elif
    # at line 51-52 and appends expected_head_mismatch.
    gaps = status.adoption_mutation_gaps(
        apply=True, authorize=True, expect_head="abc123", current_head="def456"
    )
    assert gaps == ("expected_head_mismatch",)


def test_status_worktree_gaps_mergescloseout_support_gaps() -> None:
    # closeout_support is a dict, so line 131 extends the gap list with its required_gaps.
    gaps = status.status_worktree_gaps(
        {"required_gaps": ["g1"], "closeout_support": {"required_gaps": ["c1"]}}
    )
    assert gaps == ["g1", "c1"]


# --------------------------------------------------------------------------- #
# ethos.surface.cli.hook.admit non-dict decision (branch 48->50)
# --------------------------------------------------------------------------- #


def test_hook_admit_handles_non_dict_decision(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # A report whose `decision` is not a dict fails the isinstance guard at line 48,
    # taking branch 48->50 and leaving decision_action empty.
    monkeypatch.setattr(hook, "resolve_root", lambda root: tmp_path)
    monkeypatch.setattr(
        hook,
        "hook_admission_report",
        lambda **kwargs: {
            "ok": True,
            "state": "admitted",
            "layer": "pre-commit",
            "role": "work_lane",
            "required_gaps": [],
            "decision": None,
        },
    )
    emitted: list[object] = []
    monkeypatch.setattr(
        hook, "emit", lambda result, json_output, enforce=True: emitted.append(result)
    )

    hook.admit("pre-commit", root=tmp_path, json_output=True)

    result = emitted[-1]
    assert result.summary["decision"] == ""


def test_cli_module_entrypoint_invokes_main() -> None:
    completed = subprocess.run(
        ["python", "-m", "ethos.cli", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    assert "Usage:" in completed.stdout
