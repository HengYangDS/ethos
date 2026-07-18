from __future__ import annotations

# ruff: noqa: ARG005, TC003
from pathlib import Path

import pytest

import ethos.surface.cli.root.lifecycle as root_lifecycle
from ethos_core.contracts.lifecycle.core import MutationEvaluation


def test_closeout_rechecks_control_receipt_before_effect(tmp_path: Path, monkeypatch) -> None:
    reports = iter(
        (
            {"verdict": "allow", "required_gaps": []},
            {"verdict": "defer", "required_gaps": ["fresh_control_gap"]},
        )
    )
    monkeypatch.setattr(root_lifecycle, "resolve_root", lambda _root: tmp_path)
    monkeypatch.setattr(root_lifecycle.git, "current_head", lambda _root: "a" * 40)
    monkeypatch.setattr(
        root_lifecycle,
        "evaluate_closeout_mutation",
        lambda *args, **kwargs: MutationEvaluation(ok=True, state="ready"),
    )
    monkeypatch.setattr(root_lifecycle.land_core, "closeout_audit_root", lambda *args: tmp_path)
    monkeypatch.setattr(
        root_lifecycle.land_core,
        "repository_audit_after_admission",
        lambda *args: {"ok": True, "required_gaps": [], "governance_context": {}},
    )
    monkeypatch.setattr(
        root_lifecycle,
        "completed_active_changes_report",
        lambda _root: {"ok": True, "required_gaps": []},
    )
    monkeypatch.setattr(
        root_lifecycle,
        "workspace_status",
        lambda _root, **_kwargs: {"candidate": {"head": "b" * 40}},
    )
    monkeypatch.setattr(
        root_lifecycle, "control_replacement_report", lambda **kwargs: next(reports)
    )
    monkeypatch.setattr(
        root_lifecycle,
        "apply_candidate_to_accepted",
        lambda **kwargs: pytest.fail("effect must not run after fresh control gap"),
    )
    emitted: list[object] = []
    monkeypatch.setattr(root_lifecycle, "emit", lambda result, **kwargs: emitted.append(result))
    monkeypatch.setattr(
        root_lifecycle,
        "_closeout_result",
        lambda payload: payload,
    )

    root_lifecycle.land(
        apply=True,
        authorize=True,
        expect_head="a" * 40,
        closeout=True,
        root=tmp_path,
        json_output=True,
    )
    assert emitted[0].ok is False
    assert emitted[0].gaps == ("fresh_control_gap",)
