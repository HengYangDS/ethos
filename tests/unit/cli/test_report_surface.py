from __future__ import annotations

from pathlib import Path

import ethos.domain.report as report_domain
import ethos.domain.reporting.scoring as reporting_scoring
import ethos.surface.cli.root.inspection as root_inspection
from ethos.domain.reporting.gaps import advisory_next_actions
from ethos.domain.reporting.gaps import gap_layers
from ethos.repository.adoption.planner import adoption_plan
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_raw


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


def test_report_json_compact_emits_agent_token_friendly_contract(
    monkeypatch,
    tmp_path: Path,
) -> None:
    emitted = []
    full_payload = {
        "ok": True,
        "state": "advisory",
        "summary": {
            "profile": "product",
            "score": 17,
            "max_score": 17,
            "advisory_gap_count": 2,
        },
        "required_gaps": (),
        "next_actions": ("ethos orient --json",),
        "data": {
            "governance_context": {"profile": "product"},
            "scores": {"docs": 1},
            "score_model": {"effective_score": 17},
            "first_hour": {"proof_status": "ready"},
            "gap_layers": {
                "advisory_signals": {
                    "blocking": False,
                    "ok": True,
                    "required_gaps": [],
                    "advisory_gaps": ["foreign_work_lane_present"],
                    "gap_count": 1,
                    "invalid_states": {
                        "categories": {"change_unbounded": ["foreign_work_lane_present"]},
                        "category_count": 1,
                        "gap_count": 1,
                    },
                }
            },
            "invalid_states": {
                "categories": {},
                "category_count": 0,
                "gap_count": 0,
            },
            "advisory_signals": {
                "blocking": False,
                "gap_count": 2,
                "next_actions": ["ethos explain foreign_work_lane_present --json"],
            },
            "parity": {
                "scope": {"generic_gap_count": 0},
                "gaps": {"required_gaps": [], "pending_packages": ["demo"]},
                "adopter_gaps": {"required_gaps": ["adopter:evidence_missing"]},
            },
            "repository_audit": {"heavy": True},
            "claims": {"heavy": True},
            "schema_validation": {"heavy": True},
            "playbooks": {"heavy": True},
            "hard_quality_floor": {"heavy": True},
        },
    }

    def capture_emit(result, *, json_output: bool = False, enforce: bool = True) -> None:
        _ = (json_output, enforce)
        emitted.append(result.to_dict())

    monkeypatch.setattr(root_inspection, "emit", capture_emit)
    monkeypatch.setattr(root_inspection, "resolve_root", lambda root: root or Path.cwd())
    monkeypatch.setattr(root_inspection, "scorecard_report", lambda _repo, **_kwargs: full_payload)

    root_inspection.report(root=tmp_path, json_output=True, compact=True)

    compact_payload = emitted[0]
    assert compact_payload["ok"] == full_payload["ok"]
    assert compact_payload["state"] == full_payload["state"]
    assert compact_payload["summary"] == {**full_payload["summary"], "compact": True}
    assert compact_payload["required_gaps"] == list(full_payload["required_gaps"])
    assert compact_payload["next_actions"] == list(full_payload["next_actions"])

    compact_data = compact_payload["data"]
    full_data = full_payload["data"]
    assert compact_data["compact"] is True
    assert compact_payload["governance_context"] == full_data["governance_context"]
    assert compact_data["scores"] == full_data["scores"]
    assert compact_data["score_model"] == full_data["score_model"]
    assert compact_data["first_hour"] == full_data["first_hour"]
    assert set(compact_data) == {
        "compact",
        "scores",
        "score_model",
        "first_hour",
        "gap_layers",
        "invalid_states",
        "advisory_signals",
        "parity",
    }
    assert "repository_audit" not in compact_data
    assert "claims" not in compact_data
    assert "schema_validation" not in compact_data
    assert "playbooks" not in compact_data
    assert "hard_quality_floor" not in compact_data
    assert compact_data["gap_layers"]["advisory_signals"] == {
        "blocking": False,
        "ok": True,
        "required_count": 0,
        "advisory_count": 1,
        "gap_count": 1,
        "invalid_states": {"category_count": 1, "gap_count": 1},
    }
    assert compact_data["advisory_signals"] == {
        "blocking": full_data["advisory_signals"]["blocking"],
        "gap_count": full_data["advisory_signals"]["gap_count"],
        "next_action_count": len(full_data["advisory_signals"]["next_actions"]),
    }
    assert compact_data["parity"] == {
        "scope": full_data["parity"]["scope"],
        "generic_gap_count": len(full_data["parity"]["gaps"]["required_gaps"]),
        "adopter_gap_count": len(full_data["parity"]["adopter_gaps"].get("required_gaps", [])),
        "pending_package_count": len(full_data["parity"]["gaps"].get("pending_packages", [])),
    }
    assert "advisory_gaps" not in compact_data["advisory_signals"]
    assert "next_actions" not in compact_data["advisory_signals"]
    for layer in compact_data["gap_layers"].values():
        assert "required_gaps" not in layer
        assert "advisory_gaps" not in layer
        assert "required_gap_count" not in layer
        assert "advisory_gap_count" not in layer
        assert "categories" not in layer["invalid_states"]
    assert len(str(compact_payload)) < len(str(full_payload))


def test_report_compact_reduces_malformed_optional_sections(
    monkeypatch,
    tmp_path: Path,
) -> None:
    emitted = []
    malformed_payload = {
        "ok": True,
        "state": "ready",
        "summary": {},
        "required_gaps": (),
        "next_actions": (),
        "data": {
            "governance_context": {"profile": "product"},
            "gap_layers": "not-a-dict",
            "invalid_states": "not-a-dict",
            "advisory_signals": {},
            "parity": {},
        },
    }

    def capture_emit(result, *, json_output: bool = False, enforce: bool = True) -> None:
        _ = (json_output, enforce)
        emitted.append(result.to_dict())

    monkeypatch.setattr(root_inspection, "emit", capture_emit)
    monkeypatch.setattr(root_inspection, "resolve_root", lambda root: root or Path.cwd())
    monkeypatch.setattr(
        root_inspection,
        "scorecard_report",
        lambda _repo, **_kwargs: malformed_payload,
    )

    root_inspection.report(root=tmp_path, json_output=True, compact=True)

    compact = emitted[0]
    assert compact["summary"] == {"compact": True}
    assert compact["data"]["gap_layers"] == {}
    assert compact["data"]["invalid_states"] == {"category_count": 0, "gap_count": 0}
    assert compact["data"]["advisory_signals"] == {
        "blocking": False,
        "gap_count": 0,
        "next_action_count": 0,
    }

    emitted.clear()
    malformed_payload["data"]["gap_layers"] = {"clean": "not-a-layer"}

    root_inspection.report(root=tmp_path, json_output=True, compact=True)

    nested_compact = emitted[0]
    assert nested_compact["data"]["gap_layers"] == {}


def test_report_help_exposes_compact_flag_for_discoverability() -> None:
    completed = run_ethos_raw("report", "--help")

    assert completed.returncode == 0
    assert "--compact" in completed.stdout
    assert "--no-compact" in completed.stdout


def test_report_uses_adopter_scorecard_for_non_product_repo(tmp_path: Path) -> None:
    adoption_plan(tmp_path, apply=True)

    payload = run_ethos("report", "--root", tmp_path.as_posix(), "--json")

    assert payload["ok"] is False
    assert "self_audit" not in payload["data"]
    assert payload["data"]["repository_audit"]["mode"] == "repository"
    assert (
        payload["data"]["governance_context"]
        == payload["data"]["repository_audit"]["governance_context"]
    )
    assert "posture" not in payload["data"]["governance_context"]
    assert payload["summary"]["governance_gap_count"] == 0
    assert payload["summary"]["parity_pending_count"] > 0
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
    monkeypatch.setattr(
        reporting_scoring,
        "source_budget_report",
        lambda _repo: {"ok": True, "state": "clean", "required_gaps": []},
    )
    monkeypatch.setattr(
        reporting_scoring,
        "generated_artifact_topology_report",
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
    assert "adoption_scaffold" not in payload["data"]["scores"]
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
