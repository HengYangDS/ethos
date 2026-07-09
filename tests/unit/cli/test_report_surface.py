from __future__ import annotations

from pathlib import Path

import ethos.domain.report as report_domain
import ethos.domain.reporting.scoring as reporting_scoring
import ethos.surface.cli.root.inspection as root_inspection
from ethos.domain.reporting.gaps import advisory_next_actions
from ethos.domain.reporting.gaps import gap_layers
from ethos.repository.adoption.planner import adoption_plan
from tests.support.ethos_cli_runner import run_ethos


def test_report_cli_preserves_domain_advisory_state(monkeypatch, tmp_path: Path) -> None:
    emitted = []

    def capture_emit(result, *, json_output: bool = False, enforce: bool = True) -> None:
        _ = (json_output, enforce)
        emitted.append(result.to_dict())

    monkeypatch.setattr(root_inspection, "emit", capture_emit)
    monkeypatch.setattr(root_inspection, "resolve_root", lambda root: root or Path.cwd())
    monkeypatch.setattr(
        root_inspection,
        "scorecard_report",
        lambda _repo, **_kwargs: {
            "ok": True,
            "state": "advisory",
            "summary": {"advisory_gap_count": 1},
            "required_gaps": (),
            "next_actions": ("ethos orient --json",),
            "data": {"governance_context": {"profile": "product"}},
        },
    )

    root_inspection.report(root=tmp_path, json_output=True)

    assert emitted[0]["ok"] is True
    assert emitted[0]["state"] == "advisory"
    assert emitted[0]["next_actions"] == ["ethos orient --json"]


def test_report_uses_adopter_scorecard_for_non_product_repo(tmp_path: Path) -> None:
    adoption_plan(tmp_path, profile="generic", apply=True)

    payload = run_ethos("report", "--root", tmp_path.as_posix(), "--json")

    assert payload["ok"] is True
    assert "self_audit" not in payload["data"]
    assert payload["data"]["repository_audit"]["mode"] == "repository"
    assert (
        payload["data"]["governance_context"]
        == payload["data"]["repository_audit"]["governance_context"]
    )
    assert "posture" not in payload["data"]["governance_context"]
    assert payload["summary"]["governance_gap_count"] == 0
    assert payload["data"]["scores"]["adopter_governance"] == 1
    assert payload["data"]["first_hour"] == {
        "proof_status": "ready",
        "evidence_gap_count": 0,
        "land_readiness": "local_readiness",
        "publish_readiness": "local_readiness",
        "hosted_ci_truth": "external-evidence",
        "next_action": "ethos prove",
    }


def test_report_advisory_layer_classifies_protected_openspec_residue() -> None:
    protected_residue_gap = (
        "openspec_protected_branch_active_change_unarchived:"
        "main:release_root:ethos-release-hardening"
    )
    next_actions = advisory_next_actions((protected_residue_gap,))
    layers = gap_layers(
        result_required_gaps=(),
        parity_gaps={"ok": True, "required_gaps": []},
        playbooks={"ok": True, "required_gaps": [], "advisory_gaps": []},
        advisory=((protected_residue_gap,), next_actions),
    )

    advisory_layer = layers["advisory_signals"]
    assert advisory_layer["blocking"] is False
    assert advisory_layer["invalid_states"] == {
        "categories": {"carrier_invalid": [protected_residue_gap]},
        "category_count": 1,
        "gap_count": 1,
    }
    assert advisory_layer["next_actions"] == [
        "git ls-tree -r --name-only main -- openspec/changes/ethos-release-hardening",
        "ethos explain openspec_protected_branch_active_change_unarchived:main:release_root:ethos-release-hardening --json",
    ]


def test_report_scorecard_is_derived_from_governance_checks(monkeypatch) -> None:
    monkeypatch.setattr(
        reporting_scoring,
        "coverage_quality_report",
        lambda _repo: {"ok": True, "state": "clean", "required_gaps": []},
    )

    def clean_parity_gaps_report(**_kwargs):
        return {"ok": True, "required_gaps": [], "pending_packages": []}

    monkeypatch.setattr(report_domain, "parity_gaps_report", clean_parity_gaps_report)

    payload = run_ethos("report", "--json")

    assert payload["ok"] is True
    assert payload["data"]["scores"]["distribution_adapter"] == 1
    assert payload["data"]["scores"]["claims"] == 1
    assert payload["data"]["scores"]["docs"] == 1
    assert payload["data"]["scores"]["assistant_projection"] == 1
    assert payload["data"]["scores"]["openspec"] == 1
    assert payload["data"]["scores"]["playbooks"] == 1
    assert payload["data"]["scores"]["adoption_scaffold"] == 1
    assert payload["data"]["scores"]["parity_ledger"] == 1
    scorecards = {item["id"]: item for item in payload["data"]["scorecards"]}
    assert scorecards["skills-v2"]["ok"] is True
    assert scorecards["skills-v2"]["mode"] == "v2-strict"
    assert scorecards["skills-v2"]["score"] == scorecards["skills-v2"]["max_score"]
    assert payload["data"]["parity"]["ledger"]["summary"]["unclassified_count"] == 0
    assert payload["data"]["parity"]["gaps"]["ok"] is True
    assert payload["data"]["parity"]["gaps"]["required_gaps"] == []
    assert payload["summary"]["parity_pending_count"] == len(
        payload["data"]["parity"]["gaps"]["required_gaps"]
    )
    assert payload["summary"]["parity_pending_count"] == 0
    assert payload["data"]["parity"]["gaps"]["pending_packages"] == []
    assert payload["summary"]["governance_gap_count"] == 0
    advisory_layer = payload["data"]["gap_layers"]["advisory_signals"]
    assert advisory_layer["blocking"] is False
    assert advisory_layer["gap_count"] == payload["summary"]["advisory_gap_count"]
    assert advisory_layer["advisory_gaps"] == payload["data"]["advisory_signals"]["advisory_gaps"]
    assert advisory_layer["next_actions"] == payload["data"]["advisory_signals"]["next_actions"]
    assert "self_audit" not in payload["data"]
    assert (
        payload["data"]["governance_context"]
        == payload["data"]["repository_audit"]["governance_context"]
    )
    assert "posture" not in payload["data"]["governance_context"]
    assert payload["data"]["gap_layers"]["governance_audit"] == {
        "scope": "governance_audit",
        "blocking": True,
        "ok": True,
        "required_gaps": [],
        "gap_count": 0,
        "invalid_states": {"categories": {}, "category_count": 0, "gap_count": 0},
    }
    assert payload["data"]["gap_layers"]["capability_parity"] == {
        "scope": "capability_parity",
        "blocking": False,
        "ok": True,
        "required_gaps": payload["data"]["parity"]["gaps"]["required_gaps"],
        "gap_count": payload["summary"]["parity_pending_count"],
        "invalid_states": {"categories": {}, "category_count": 0, "gap_count": 0},
    }
    assert payload["data"]["invalid_states"] == {
        "categories": {},
        "category_count": 0,
        "gap_count": 0,
    }
    parity_note = payload["data"]["parity"]["scope"]["note"].lower()
    assert "adopter-domain storage" not in parity_note
    assert "backend retirement" not in parity_note
    assert "domain profile parity" in parity_note
    if payload["summary"]["advisory_gap_count"]:
        assert payload["state"] == "advisory"
        assert payload["next_actions"] == advisory_layer["next_actions"]
    else:
        assert payload["state"] == "ready"
        assert payload["next_actions"] == ["ethos prove --full"]
