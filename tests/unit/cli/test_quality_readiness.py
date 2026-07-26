from __future__ import annotations

import json
from typing import TYPE_CHECKING

import ethos.repository.policy.governance.kernel as governance_kernel_policy

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

from ethos.surface.cli.boundary import readiness as q_readiness


def _json_output(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    return json.loads(capsys.readouterr().out)


def test_quality_governance_kernel_reports_single_kernel(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        governance_kernel_policy,
        "governance_kernel_report",
        lambda _repo: {
            "ok": True,
            "state": "clean",
            "summary": {"check_count": 4, "closed_check_count": 4, "gap_count": 0},
            "required_gaps": [],
        },
    )

    q_readiness.governance_kernel(root=tmp_path, json_output=True)
    payload = _json_output(capsys)

    assert payload["command"] == "quality governance-kernel"
    assert payload["state"] == "clean"
    assert payload["next_actions"] == ["ethos prove --json"]
