from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.repository.policy.readiness import enterprise as readiness

if TYPE_CHECKING:
    from pathlib import Path


def test_enterprise_readiness_report_closes_all_planning_layers(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        readiness,
        "workspace_status",
        lambda _root: {
            "role": "work_lane",
            "dirty": False,
            "required_gaps": [],
            "foreign_work_lanes": [{"branch": "work/other"}],
            "coordination": {"blocking": False},
        },
    )
    monkeypatch.setattr(
        readiness,
        "scorecard_report",
        lambda _root: {
            "ok": True,
            "summary": {
                "score": 16,
                "max_score": 16,
                "governance_gap_count": 0,
                "parity_pending_count": 0,
            },
            "required_gaps": [],
        },
    )

    def clean(_root: Path) -> dict[str, object]:
        return {"ok": True, "state": "clean", "summary": {}, "required_gaps": []}

    monkeypatch.setattr(readiness, "product_boundary_report", clean)
    monkeypatch.setattr(readiness, "docs_topology_report", clean)
    monkeypatch.setattr(readiness, "contributor_policy_report", clean)
    monkeypatch.setattr(readiness, "generated_artifact_topology_report", clean)
    monkeypatch.setattr(readiness, "release_policy_report", clean)
    monkeypatch.setattr(readiness.git_adapter, "current_tracked_head", lambda _root: "abc")
    monkeypatch.setattr(
        readiness,
        "parity_gaps_report",
        lambda **_kwargs: {"ok": True, "state": "clean", "summary": {}, "required_gaps": []},
    )
    monkeypatch.setattr(
        readiness,
        "claims_report",
        lambda *_args, **_kwargs: {"ok": True, "required_gaps": []},
    )
    monkeypatch.setattr(
        readiness,
        "context_for_root",
        lambda _root: {
            "profile": "product",
            "single_kernel": True,
            "subject": {"kind": "repository"},
            "transition_commands": list(readiness.PUBLIC_WORKFLOW_COMMANDS),
            "reader_view_commands": ["ethos orient"],
            "scorecard_commands": ["ethos report"],
        },
    )
    for claim in readiness.CLOSURE_CLAIMS:
        path = tmp_path / "evidence" / "claims" / f"{claim}.toml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("[claim]\n", encoding="utf-8")

    report = readiness.enterprise_readiness_report(tmp_path)

    assert report["ok"] is True
    assert report["summary"] == {
        "layer_count": 9,
        "closed_layer_count": 9,
        "gap_count": 0,
        "local_closeout_boundary": "remote publication not required by this gate",
    }
    assert [layer["id"] for layer in report["layers"]] == [
        "L0-local-state-baseline",
        "L1-product-boundary-neutrality",
        "L2-semantic-docs-topology",
        "L3-organization-native-identity",
        "L4-shared-command-plane",
        "L5-profile-and-parity-boundary",
        "L6-release-distribution-boundary",
        "L7-enterprise-operability",
        "L8-self-improvement-loop",
    ]
    assert report["boundary"]["foreign_work_lanes"] == "observe_only_without_handoff_or_break_glass"
    assert report["boundary"]["identity_model"] == "external_role_policy"


def test_enterprise_readiness_reports_blocking_gaps(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        readiness,
        "workspace_status",
        lambda _root: {
            "role": "accepted_root",
            "dirty": True,
            "required_gaps": ["status_gap"],
            "foreign_work_lanes": [],
            "coordination": {"blocking": True},
        },
    )
    monkeypatch.setattr(
        readiness,
        "scorecard_report",
        lambda _root: {
            "ok": False,
            "summary": {"governance_gap_count": 1, "parity_pending_count": 2},
            "required_gaps": ["report_gap"],
        },
    )
    monkeypatch.setattr(
        readiness,
        "product_boundary_report",
        lambda _root: {
            "ok": False,
            "state": "blocked",
            "summary": {},
            "required_gaps": ["personal_identity_literal:README.md:1"],
        },
    )

    def clean(_root: Path) -> dict[str, object]:
        return {"ok": True, "state": "clean", "summary": {}, "required_gaps": []}

    monkeypatch.setattr(readiness, "docs_topology_report", clean)
    monkeypatch.setattr(readiness, "contributor_policy_report", clean)
    monkeypatch.setattr(readiness, "generated_artifact_topology_report", clean)
    monkeypatch.setattr(readiness, "release_policy_report", clean)
    monkeypatch.setattr(readiness.git_adapter, "current_tracked_head", lambda _root: "abc")
    monkeypatch.setattr(
        readiness,
        "parity_gaps_report",
        lambda **_kwargs: {"ok": False, "required_gaps": ["parity_evidence_refresh:generic"]},
    )
    monkeypatch.setattr(
        readiness,
        "claims_report",
        lambda *_args, **_kwargs: {
            "ok": False,
            "required_gaps": ["active-claim:active_claim_private_coupling:private_adopter_literal"],
        },
    )
    monkeypatch.setattr(
        readiness,
        "context_for_root",
        lambda _root: {
            "profile": "product",
            "single_kernel": False,
            "subject": {"kind": "workspace"},
            "transition_commands": ["ethos status"],
            "reader_view_commands": [],
            "scorecard_commands": [],
        },
    )

    report = readiness.enterprise_readiness_report(tmp_path)

    gaps = "\n".join(report["required_gaps"])
    assert report["ok"] is False
    assert "status_gap" in gaps
    assert "enterprise_readiness_coordination_blocking" in gaps
    assert "enterprise_readiness_governance_gaps:1" in gaps
    assert "enterprise_readiness_parity_pending:2" in gaps
    assert "personal_identity_literal:README.md:1" in gaps
    assert "parity_evidence_refresh:generic" in gaps
    assert "enterprise_readiness_single_kernel_missing" in gaps
    assert "enterprise_readiness_subject_not_repository" in gaps
    assert "enterprise_readiness_claim_missing:enterprise-product-boundary-20260709" in gaps
    assert "active-claim:active_claim_private_coupling:private_adopter_literal" in gaps


def test_enterprise_readiness_helpers_normalize_malformed_values() -> None:
    status = readiness._workspace_status_check(
        {
            "role": "work_lane",
            "dirty": False,
            "required_gaps": ("status_gap",),
            "foreign_work_lanes": (object(), object()),
            "coordination": "not-a-mapping",
        }
    )
    assert status["required_gaps"] == ["status_gap"]
    assert status["summary"]["coordination_blocking"] is False
    assert status["summary"]["foreign_work_lane_count"] == 2

    scorecard = readiness._scorecard_check(
        {
            "ok": True,
            "summary": {
                "governance_gap_count": True,
                "parity_pending_count": "not-an-int",
            },
            "required_gaps": "not-a-list",
        }
    )
    assert scorecard["ok"] is False
    assert scorecard["required_gaps"] == ["enterprise_readiness_governance_gaps:1"]

    simple = readiness._simple_report_check({"ok": True, "summary": "not-a-mapping"})
    assert simple["ok"] is True
    assert simple["summary"] == {}

    context = readiness._governance_context_check(
        {
            "single_kernel": True,
            "subject": "not-a-mapping",
            "transition_commands": tuple(readiness.PUBLIC_WORKFLOW_COMMANDS),
            "reader_view_commands": ("ethos orient",),
            "scorecard_commands": ("ethos report",),
        }
    )
    assert context["ok"] is False
    assert context["required_gaps"] == ["enterprise_readiness_subject_not_repository"]

    assert readiness._int_field({"value": 3}, "value") == 3
    assert readiness._int_field({"value": "4"}, "value") == 4
    assert readiness._int_field({"value": object()}, "value") == 0
