from __future__ import annotations

from typing import TYPE_CHECKING

import ethos.repository.evidence.freshness as freshness

if TYPE_CHECKING:
    from pathlib import Path


def test_evidence_freshness_surfaces_configured_generic_parity_gap(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        freshness,
        "claims_report",
        lambda *_args, **_kwargs: {"ok": True, "required_gaps": []},
    )
    monkeypatch.setattr(
        freshness,
        "evolution_report",
        lambda _root: {"ok": True, "required_gaps": [], "active_count": 0},
    )
    monkeypatch.setattr(
        freshness,
        "evidence_topology_report",
        lambda _root: {"ok": True, "required_gaps": []},
    )
    monkeypatch.setattr(freshness, "profile_relative_root", lambda *_args: "evidence")
    monkeypatch.setattr(freshness.git_adapter, "current_tracked_head", lambda _root: "head-1")
    evidence = tmp_path / "evidence" / "parity" / "generic-shadow.json"
    evidence.parent.mkdir(parents=True)
    evidence.write_text("{}\n", encoding="utf-8")
    expected = {
        "ok": False,
        "required_gaps": [
            "parity_evidence_invalid:generic",
            "parity_evidence_invalid:generic:product_head",
        ],
        "evidence": {
            "refresh_package": {
                "lifecycle": {"stage": "work_lane_before_proof"},
            }
        },
    }
    monkeypatch.setattr(freshness, "parity_gaps_report", lambda **_kwargs: expected)

    report = freshness.evidence_freshness_report(tmp_path, current_head="head-1")

    assert report["ok"] is False
    assert report["summary"]["parity_issue_count"] == 2
    assert report["required_gaps"] == expected["required_gaps"]
    assert report["data"]["stale"] == expected["required_gaps"]
    assert report["data"]["parity"] == expected


def test_evidence_freshness_skips_unconfigured_generic_parity(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        freshness,
        "claims_report",
        lambda *_args, **_kwargs: {"ok": True, "required_gaps": []},
    )
    monkeypatch.setattr(
        freshness,
        "evolution_report",
        lambda _root: {"ok": True, "required_gaps": [], "active_count": 0},
    )
    monkeypatch.setattr(
        freshness,
        "evidence_topology_report",
        lambda _root: {"ok": True, "required_gaps": []},
    )
    monkeypatch.setattr(freshness, "profile_relative_root", lambda *_args: "evidence")

    report = freshness.evidence_freshness_report(tmp_path, current_head="head-1")

    assert report["ok"] is True
    assert report["summary"]["parity_issue_count"] == 0
    assert report["data"]["parity"] == {
        "ok": True,
        "state": "not_configured",
        "required_gaps": [],
        "evidence_path": "evidence/parity/generic-shadow.json",
    }
