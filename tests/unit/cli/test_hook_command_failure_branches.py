from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

import pytest

import ethos.surface.cli.hook.commands as commands

if TYPE_CHECKING:
    from pathlib import Path


def _capture(monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    values: list[Any] = []
    monkeypatch.setattr(commands, "emit", lambda result, **_kwargs: values.append(result))
    return values


def test_hook_admit_block_uses_report_action_before_fallback() -> None:
    assert (
        commands._hook_admit_next_action(  # noqa: SLF001
            {"next_action": "set ETHOS_ACTOR=owner"}, "block"
        )
        == "set ETHOS_ACTOR=owner"
    )
    assert commands._hook_admit_next_action({}, "block") == "ethos lane prewrite <path>"  # noqa: SLF001
    assert commands._hook_admit_next_action({}, "pass") == ""  # noqa: SLF001


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


def test_decision_action_is_empty_without_mapping() -> None:
    assert commands._decision_action({}) == ""  # noqa: SLF001
    assert commands._decision_action({"decision": "allow"}) == ""  # noqa: SLF001
