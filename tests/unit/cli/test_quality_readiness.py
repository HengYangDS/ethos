from __future__ import annotations

from pathlib import Path

from ethos.surface.cli.boundary import readiness as q_readiness


def _capture(monkeypatch):
    emitted = []

    def capture_emit(result, *, json_output=False, enforce=True):
        _ = (json_output, enforce)
        emitted.append(result.to_dict())

    monkeypatch.setattr(q_readiness, "emit", capture_emit)
    monkeypatch.setattr(q_readiness, "resolve_root", lambda root: root or Path.cwd())
    return emitted


def test_quality_enterprise_readiness_reports_layer_closure(monkeypatch, tmp_path: Path):
    emitted = _capture(monkeypatch)
    monkeypatch.setattr(
        q_readiness,
        "enterprise_readiness_report",
        lambda _repo: {
            "ok": True,
            "state": "clean",
            "summary": {"layer_count": 9, "closed_layer_count": 9, "gap_count": 0},
            "required_gaps": [],
        },
    )

    q_readiness.enterprise_readiness(root=tmp_path, json_output=True)

    assert emitted[0]["command"] == "quality enterprise-readiness"
    assert emitted[0]["state"] == "clean"
    assert emitted[0]["next_actions"] == [
        "ethos prove --execute --expect-head $(git rev-parse HEAD) --json"
    ]


def test_quality_governance_kernel_reports_single_kernel(monkeypatch, tmp_path: Path):
    emitted = _capture(monkeypatch)
    monkeypatch.setattr(
        q_readiness,
        "governance_kernel_report",
        lambda _repo: {
            "ok": True,
            "state": "clean",
            "summary": {"check_count": 4, "closed_check_count": 4, "gap_count": 0},
            "required_gaps": [],
        },
    )

    q_readiness.governance_kernel(root=tmp_path, json_output=True)

    assert emitted[0]["command"] == "quality governance-kernel"
    assert emitted[0]["state"] == "clean"
    assert emitted[0]["next_actions"] == ["ethos quality enterprise-readiness --json"]
