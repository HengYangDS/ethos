from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

import ethos.repository.policy.boundary.product as product_policy

if TYPE_CHECKING:
    from pathlib import Path

from ethos.surface.cli.boundary import product as q_boundary


def _json_output(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    return json.loads(capsys.readouterr().out)


def test_quality_boundary_cli_commands_emit_policy_reports(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        product_policy,
        "product_boundary_report",
        lambda _root: {
            "ok": False,
            "state": "blocked",
            "summary": {"finding_count": 1},
            "required_gaps": ["product-boundary:README.md:1"],
        },
    )
    monkeypatch.setattr(
        product_policy,
        "contributor_policy_report",
        lambda _root: {
            "ok": True,
            "state": "clean",
            "summary": {"finding_count": 0},
            "required_gaps": [],
        },
    )

    with pytest.raises(SystemExit):
        q_boundary.product_boundary(root=tmp_path, json_output=True)
    product_payload = _json_output(capsys)
    q_boundary.contributor_policy(root=tmp_path, json_output=True)
    contributor_payload = _json_output(capsys)

    assert product_payload["command"] == "quality product-boundary"
    assert product_payload["ok"] is False
    assert product_payload["next_actions"] == [
        (
            "neutralize product and release-visible historical surfaces; keep "
            "private provenance in adopter repositories or ignored local state"
        )
    ]
    assert contributor_payload["command"] == "quality contributor-policy"
    assert contributor_payload["ok"] is True
    assert contributor_payload["next_actions"] == [
        "declare role-based humans, teams, and automation identities"
    ]
