from __future__ import annotations

from pathlib import Path

from ethos.surface.cli.boundary import product as q_boundary


def _capture(monkeypatch):
    emitted = []

    def capture_emit(result, *, json_output=False, enforce=True):
        _ = (json_output, enforce)
        emitted.append(result.to_dict())

    monkeypatch.setattr(q_boundary, "emit", capture_emit)
    monkeypatch.setattr(q_boundary, "resolve_root", lambda root: root or Path.cwd())
    return emitted


def test_quality_boundary_cli_commands_emit_policy_reports(monkeypatch, tmp_path: Path) -> None:
    emitted = _capture(monkeypatch)
    monkeypatch.setattr(
        q_boundary,
        "product_boundary_report",
        lambda _root: {
            "ok": False,
            "state": "blocked",
            "summary": {"finding_count": 1},
            "required_gaps": ["product-boundary:README.md:1"],
        },
    )
    monkeypatch.setattr(
        q_boundary,
        "contributor_policy_report",
        lambda _root: {
            "ok": True,
            "state": "clean",
            "summary": {"finding_count": 0},
            "required_gaps": [],
        },
    )

    q_boundary.product_boundary(root=tmp_path, json_output=True)
    q_boundary.contributor_policy(root=tmp_path, json_output=True)

    assert emitted[0]["command"] == "quality product-boundary"
    assert emitted[0]["ok"] is False
    assert emitted[0]["next_actions"] == [
        (
            "neutralize product and release-visible historical surfaces; keep "
            "private provenance in adopter repositories or ignored local state"
        )
    ]
    assert emitted[1]["command"] == "quality contributor-policy"
    assert emitted[1]["ok"] is True
    assert emitted[1]["next_actions"] == [
        "declare role-based humans, teams, and automation identities"
    ]
