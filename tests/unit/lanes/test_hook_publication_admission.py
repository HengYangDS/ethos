from __future__ import annotations

from typing import TYPE_CHECKING

import ethos.surface.cli.hook.commands as hook_commands
from ethos.contracts.branch.roles import BranchRolePolicy

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_pre_push_forwards_named_remote_to_plan_bound_admission(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[dict[str, object]] = []
    emitted: list[object] = []
    monkeypatch.setattr(hook_commands, "resolve_root", lambda _root: tmp_path)
    monkeypatch.setattr(hook_commands, "emit", lambda result, **_kwargs: emitted.append(result))
    monkeypatch.setattr(
        hook_commands,
        "push_admission_report",
        lambda **kwargs: (
            calls.append(kwargs)
            or {
                "verdict": "pass",
                "state": "admitted",
                "target_branch": "dev",
                "role": "accepted_root",
                "remote_name": kwargs["remote_name"],
                "decision": {"action": "allow", "reason": "push_admitted"},
                "required_gaps": [],
            }
        ),
    )
    hook_commands.pre_push(
        "refs/heads/dev",
        "head",
        options=hook_commands.PushReconciliationOptions(
            remote_head="", remote="github", json_output=True
        ),
    )

    assert [call["remote_name"] for call in calls] == ["github"]
    assert emitted[-1].summary["remote"] == "github"


def test_pre_push_public_envelope_and_effect_gate_use_declared_verdict(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    emitted: list[object] = []
    monkeypatch.setattr(hook_commands, "resolve_root", lambda _root: tmp_path)
    monkeypatch.setattr(hook_commands, "emit", lambda result, **_kwargs: emitted.append(result))
    monkeypatch.setattr(
        hook_commands,
        "push_admission_report",
        lambda **_kwargs: {
            "verdict": "unknown",
            "state": "observed",
            "target_branch": "dev",
            "role": "accepted_root",
            "remote_name": "origin",
            "decision": {"action": "allow", "reason": "legacy_observation"},
            "required_gaps": [],
        },
    )

    hook_commands.pre_push("refs/heads/dev", "head")

    result = emitted[-1]
    payload = result.to_dict()
    assert result.verdict == "unknown"
    assert result.schema_version == 2
    assert result.next_action == "ethos prove --execute --expect-head <head>"
    assert "ok" not in payload
    assert "ok" not in payload["data"]


def test_committed_ref_move_report_declares_verdict_without_top_level_ok(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    emitted: list[object] = []
    monkeypatch.setattr(hook_commands, "resolve_root", lambda _root: tmp_path)
    monkeypatch.setattr(hook_commands, "emit", lambda result, **_kwargs: emitted.append(result))
    monkeypatch.setattr(hook_commands, "resolve_ref_move_policy", lambda *_args: BranchRolePolicy())
    monkeypatch.setattr(
        hook_commands,
        "ref_move_admission_report",
        lambda **kwargs: {
            "verdict": "pass",
            "state": "admitted",
            "branch": kwargs["ref_name"].removeprefix("refs/heads/"),
            "decision": {"action": "allow", "reason": "ref_move_admitted"},
            "required_gaps": [],
        },
    )

    hook_commands.ref_transaction(
        "refs/heads/dev",
        "a" * 40,
        "b" * 40,
        phase="committed",
    )

    result = emitted[-1]
    assert result.verdict == "pass"
    assert result.schema_version == 2
    assert result.next_action == ""
    assert result.data["verdict"] == "pass"
    assert "ok" not in result.data


def test_ref_move_policy_unavailable_preserves_the_ref_transaction_shape(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    emitted: list[object] = []
    monkeypatch.setattr(hook_commands, "resolve_root", lambda _root: tmp_path)
    monkeypatch.setattr(hook_commands, "emit", lambda result, **_kwargs: emitted.append(result))

    def unavailable(*_args: object) -> BranchRolePolicy:
        raise ValueError("ref_move_policy_unavailable")

    monkeypatch.setattr(hook_commands, "resolve_ref_move_policy", unavailable)

    hook_commands.ref_transaction(
        "refs/heads/work/example",
        "0" * 40,
        "a" * 40,
        phase="prepared",
    )

    result = emitted[-1]
    assert result.verdict == "block"
    assert result.data == {
        "verdict": "block",
        "state": "blocked",
        "phase": "prepared",
        "hook": "reference-transaction",
        "ref": "refs/heads/work/example",
        "branch": "work/example",
        "old_value": "0" * 40,
        "new_value": "a" * 40,
        "decision": {"action": "block", "reason": "ref_move_policy_unavailable"},
        "required_gaps": ("ref_move_policy_unavailable",),
    }
