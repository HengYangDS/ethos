from __future__ import annotations

import json
from typing import TYPE_CHECKING
from typing import Any

import pytest

import ethos.surface.cli.hook.commands as commands
from tests.support.ethos_cli_runner import run_ethos_raw

if TYPE_CHECKING:
    from pathlib import Path


def _capture(monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    values: list[Any] = []
    monkeypatch.setattr(commands, "emit", lambda result, **_kwargs: values.append(result))
    return values


@pytest.mark.parametrize(
    ("report", "expected_action"),
    [
        (
            {
                "verdict": "block",
                "state": "blocked",
                "layer": "pre-tool",
                "role": "work_lane",
                "next_action": "set ETHOS_ACTOR=owner",
                "required_gaps": ["actor_missing"],
            },
            "set ETHOS_ACTOR=owner",
        ),
        (
            {
                "verdict": "block",
                "state": "blocked",
                "layer": "pre-tool",
                "role": "work_lane",
                "required_gaps": ["path_uncovered"],
            },
            "ethos lane prewrite <path>",
        ),
        (
            {
                "verdict": "pass",
                "state": "admitted",
                "layer": "pre-tool",
                "role": "work_lane",
                "required_gaps": [],
            },
            "",
        ),
    ],
)
def test_hook_admit_projects_report_action_before_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    report: dict[str, object],
    expected_action: str,
) -> None:
    monkeypatch.setattr(commands, "hook_admission_report", lambda **_kwargs: report)

    completed = run_ethos_raw(
        "hook",
        "admit",
        "pre-tool",
        "README.md",
        "--root",
        tmp_path.as_posix(),
        "--json",
        cwd=tmp_path,
    )

    payload = json.loads(completed.stdout)
    assert completed.returncode == (0 if report["verdict"] == "pass" else 1)
    assert payload["next_action"] == expected_action


def test_reconciliation_receipt_missing_refs_is_structured_and_nonwriting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    results = _capture(monkeypatch)
    monkeypatch.setattr(commands, "resolve_root", lambda _root: tmp_path)
    monkeypatch.setattr(commands, "git_stdout", lambda *_args: "")
    target = tmp_path.parent / "receipt.json"

    commands.reconciliation_receipt_command(
        "proposal/example", "a" * 40, target, root=tmp_path, json_output=True
    )

    result = results.pop()
    assert result.verdict == "block"
    assert len(result.required_gaps) == 4
    assert not target.exists()


def test_ref_transaction_policy_failure_emits_actionable_block(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    results = _capture(monkeypatch)
    monkeypatch.setattr(commands, "resolve_root", lambda _root: tmp_path)
    monkeypatch.setattr(
        commands,
        "resolve_ref_move_policy",
        lambda *_args: (_ for _ in ()).throw(ValueError("missing")),
    )
    commands.ref_transaction("refs/heads/dev", "a" * 40, "b" * 40, root=tmp_path, json_output=True)
    result = results.pop()
    assert result.verdict == "block"
    assert result.required_gaps == ("ref_move_policy_unavailable",)
    assert result.next_action == "ethos land --closeout"


def test_run_hook_rejects_unknown_name_before_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        commands,
        "execute_hook",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("runtime reached")),
    )
    with pytest.raises(SystemExit) as error:
        commands.run_hook("unknown")
    assert error.value.code == 1


def test_hook_install_failure_is_public_block(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    results = _capture(monkeypatch)
    monkeypatch.setattr(commands, "resolve_root", lambda _root: tmp_path)
    monkeypatch.setattr(
        commands,
        "install_hook_launchers",
        lambda _root: (_ for _ in ()).throw(OSError("read-only filesystem")),
    )
    commands.install(root=tmp_path, json_output=True)
    result = results.pop()
    assert result.verdict == "block"
    assert result.state == "blocked"
    assert result.required_gaps == ("hook_install_failed:read-only filesystem",)
    assert result.summary["wired"] is False


@pytest.mark.parametrize("decision", [None, "allow"])
def test_ref_transaction_summary_omits_non_mapping_decision(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    decision: object,
) -> None:
    results = _capture(monkeypatch)
    monkeypatch.setattr(commands, "resolve_root", lambda _root: tmp_path)
    monkeypatch.setattr(
        commands,
        "resolve_ref_move_policy",
        lambda *_args: type(
            "Policy",
            (),
            {"role_for_branch": lambda _self, _branch: "topic"},
        )(),
    )
    monkeypatch.setattr(
        commands,
        "ref_move_admission_report",
        lambda **_kwargs: {
            "verdict": "pass",
            "state": "admitted",
            "branch": "topic/example",
            "decision": decision,
            "required_gaps": [],
        },
    )

    commands.ref_transaction(
        "refs/heads/topic/example",
        "a" * 40,
        "b" * 40,
        root=tmp_path,
        json_output=True,
    )

    assert results.pop().summary["decision"] == ""
