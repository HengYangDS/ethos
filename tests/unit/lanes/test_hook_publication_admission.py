from __future__ import annotations

from typing import TYPE_CHECKING

import ethos.surface.cli.hook.commands as hook_commands

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
                "ok": True,
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
