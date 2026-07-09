from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:
    from pathlib import Path

from ethos.domain import report as report_domain
from ethos_core.contracts.context.projection import ASSISTANT_TRUTH_BOUNDARY


def test_terminal_control_is_partial_when_stage_gate_blocks() -> None:
    assert (
        report_domain._terminal_control(
            result_required_gaps=(),
            hard_quality_gap_count=0,
            stage_gates={"authoring_allowed": True, "integration_allowed": False},
        )
        == "partial"
    )


def test_scorecard_next_actions_route_module_layout_and_unknown_quality_gaps() -> None:
    """Hard quality gaps should route to the narrowest available owner command."""

    assert report_domain._scorecard_next_actions(
        parity_pending_count=0,
        hard_quality_floor={"required_gaps": ["module_layout_flat_growth:pkg"]},
    ) == ("ethos quality module-layout --json",)
    assert report_domain._scorecard_next_actions(
        parity_pending_count=0,
        hard_quality_floor={"required_gaps": ["quality_gap_without_specific_owner"]},
    ) == ("ethos quality --json",)


def test_adopter_product_root_resolves_runtime_and_profile_fallback(
    monkeypatch, tmp_path: Path
) -> None:
    repo = tmp_path / "adopter"
    product = tmp_path / "product"
    configured_product = tmp_path / "configured-product"
    repo.mkdir()
    product.mkdir()
    configured_product.mkdir()

    runtime_payload = {"runtime_binding": {"runner_source_root": product.as_posix()}}
    assert report_domain.adopter_product_root(repo, runtime_payload, None) == product.resolve()

    same_repo_payload = {"runtime_binding": {"runner_source_root": repo.as_posix()}}
    empty_runtime_payload = {"runtime_binding": {"runner_source_root": ""}}

    class Profile:
        def __init__(self) -> None:
            self.tables = {"external_backend": {"product_root": "../configured-product"}}

    monkeypatch.setattr(report_domain, "load_repository_profile", lambda _repo: Profile())

    assert (
        report_domain.adopter_product_root(repo, same_repo_payload, None)
        == configured_product.resolve()
    )
    assert (
        report_domain.adopter_product_root(repo, empty_runtime_payload, None)
        == configured_product.resolve()
    )
    assert report_domain.adopter_product_root(repo, {}, product) == product.resolve()


def test_scorecard_next_actions_route_parity_gaps() -> None:
    assert report_domain._scorecard_next_actions(
        parity_pending_count=1,
        hard_quality_floor={"required_gaps": []},
    ) == ("ethos parity gaps --adopter <adopter>",)


def test_scorecard_blocks_product_hard_quality_floor(monkeypatch, tmp_path):
    """Report must not claim ready when standalone hard quality gates are blocked."""

    monkeypatch.setattr(
        report_domain.status_domain,
        "audit_for_root",
        lambda _repo, **_kwargs: {
            "ok": True,
            "required_gaps": [],
            "governance_context": {"profile": "product"},
            "package_ontology": {"ok": True, "adapter_missing": []},
            "schemas": {"ok": True},
            "openspec": {"ok": True, "advisory_gaps": []},
        },
    )
    monkeypatch.setattr(report_domain, "docs_health_report", lambda _repo: {"ok": True})
    monkeypatch.setattr(
        report_domain,
        "claims_report",
        lambda _repo, **_kwargs: {"ok": True, "required_gaps": [], "advisory_gaps": []},
    )
    monkeypatch.setattr(report_domain, "command_registry_report", lambda _repo: {"ok": True})
    monkeypatch.setattr(
        report_domain,
        "projection_contract",
        lambda: {"truth": ASSISTANT_TRUTH_BOUNDARY},
    )
    monkeypatch.setattr(report_domain, "schema_validation_report", lambda _repo: {"ok": True})
    monkeypatch.setattr(report_domain, "evolution_report", lambda _repo: {"ok": True})
    monkeypatch.setattr(report_domain, "signature_policy_report", lambda _repo: {"ok": True})
    monkeypatch.setattr(
        report_domain,
        "playbooks_report",
        lambda _repo, mode="v2-strict": {
            "ok": True,
            "mode": mode,
            "required_gaps": [],
            "advisory_gaps": [],
            "v2_compliance": {"score": 1, "max_score": 1},
        },
    )
    monkeypatch.setattr(report_domain, "adoption_scaffold_report", lambda: {"ok": True})
    monkeypatch.setattr(
        report_domain,
        "parity_ledger_report",
        lambda: {"ok": True, "summary": {"unclassified_count": 0}},
    )
    monkeypatch.setattr(report_domain.git_adapter, "current_tracked_head", lambda _repo: "head")
    monkeypatch.setattr(
        report_domain,
        "parity_gaps_report",
        lambda **_kwargs: {"ok": True, "required_gaps": [], "pending_packages": []},
    )
    monkeypatch.setattr(
        report_domain,
        "context_projection_contract",
        lambda: {
            "authority": "projection",
            "can_close_required_gaps": False,
            "can_satisfy_proof": False,
        },
    )
    monkeypatch.setattr(report_domain, "available_profiles", lambda: ())
    monkeypatch.setattr(
        report_domain,
        "code_size_report",
        lambda _repo: {
            "ok": False,
            "required_gaps": ["code_size_exceeded:tests/unit/product/test_flat.py:999>800"],
        },
    )
    monkeypatch.setattr(
        report_domain,
        "module_layout_report",
        lambda _repo: {"ok": True, "state": "clean", "required_gaps": []},
    )
    monkeypatch.setattr(
        report_domain, "product_boundary_report", lambda _repo: {"required_gaps": []}
    )
    monkeypatch.setattr(
        report_domain, "contributor_policy_report", lambda _repo: {"required_gaps": []}
    )
    monkeypatch.setattr(
        report_domain,
        "standard_adapter_registry",
        lambda: {"std": {"boundary": "b", "fallback": "f", "exit_strategy": "e"}},
    )

    payload: dict[str, Any] = report_domain.scorecard_report(tmp_path)

    assert payload["ok"] is False
    assert payload["required_gaps"] == (
        "code_size_exceeded:tests/unit/product/test_flat.py:999>800",
    )
    assert payload["summary"]["governance_gap_count"] == 1
    assert payload["next_actions"] == ("ethos quality code-size --json",)
    quality_floor = payload["data"]["gap_layers"]["hard_quality_floor"]
    assert quality_floor["blocking"] is True
    assert quality_floor["ok"] is False
    assert quality_floor["required_gaps"] == [
        "code_size_exceeded:tests/unit/product/test_flat.py:999>800"
    ]


def test_scorecard_surfaces_work_lane_coordination_advisories(monkeypatch, tmp_path: Path) -> None:
    """Report should not hide non-blocking Work Lane residue coordination signals."""

    monkeypatch.setattr(
        report_domain,
        "workspace_status",
        lambda _repo: {
            "coordination": {
                "advisory_gaps": [
                    "foreign_work_lane_present",
                    "work_lane_missing_lease:work/orphan",
                ],
            },
        },
    )
    monkeypatch.setattr(
        report_domain.status_domain,
        "audit_for_root",
        lambda _repo, **_kwargs: {
            "ok": True,
            "required_gaps": [],
            "governance_context": {"profile": "product"},
            "package_ontology": {"ok": True, "adapter_missing": []},
            "schemas": {"ok": True},
            "openspec": {"ok": True, "advisory_gaps": []},
        },
    )
    monkeypatch.setattr(report_domain, "docs_health_report", lambda _repo: {"ok": True})
    monkeypatch.setattr(
        report_domain,
        "claims_report",
        lambda _repo, **_kwargs: {"ok": True, "required_gaps": [], "advisory_gaps": []},
    )
    monkeypatch.setattr(report_domain, "command_registry_report", lambda _repo: {"ok": True})
    monkeypatch.setattr(
        report_domain,
        "projection_contract",
        lambda: {"truth": ASSISTANT_TRUTH_BOUNDARY},
    )
    monkeypatch.setattr(report_domain, "schema_validation_report", lambda _repo: {"ok": True})
    monkeypatch.setattr(report_domain, "evolution_report", lambda _repo: {"ok": True})
    monkeypatch.setattr(report_domain, "signature_policy_report", lambda _repo: {"ok": True})
    monkeypatch.setattr(
        report_domain,
        "playbooks_report",
        lambda _repo, mode="v2-strict": {
            "ok": True,
            "mode": mode,
            "required_gaps": [],
            "advisory_gaps": [],
            "v2_compliance": {"score": 1, "max_score": 1},
        },
    )
    monkeypatch.setattr(report_domain, "adoption_scaffold_report", lambda: {"ok": True})
    monkeypatch.setattr(
        report_domain,
        "parity_ledger_report",
        lambda: {"ok": True, "summary": {"unclassified_count": 0}},
    )
    monkeypatch.setattr(report_domain.git_adapter, "current_tracked_head", lambda _repo: "head")
    monkeypatch.setattr(
        report_domain,
        "parity_gaps_report",
        lambda **_kwargs: {"ok": True, "required_gaps": [], "pending_packages": []},
    )
    monkeypatch.setattr(
        report_domain,
        "context_projection_contract",
        lambda: {
            "authority": "projection",
            "can_close_required_gaps": False,
            "can_satisfy_proof": False,
        },
    )
    monkeypatch.setattr(report_domain, "available_profiles", lambda: ())
    monkeypatch.setattr(
        report_domain,
        "_hard_quality_floor_report",
        lambda _repo: {"ok": True, "required_gaps": []},
    )
    monkeypatch.setattr(
        report_domain,
        "standard_adapter_registry",
        lambda: {"std": {"boundary": "b", "fallback": "f", "exit_strategy": "e"}},
    )

    payload: dict[str, Any] = report_domain.scorecard_report(tmp_path)

    assert payload["ok"] is True
    assert payload["required_gaps"] == ()
    assert payload["summary"]["advisory_gap_count"] == 2
    advisory = payload["data"]["advisory_signals"]
    assert advisory["blocking"] is False
    assert advisory["advisory_gaps"] == [
        "foreign_work_lane_present",
        "work_lane_missing_lease:work/orphan",
    ]
    assert advisory["next_actions"] == ["ethos orient --json", "ethos lane status --json"]


def test_scorecard_next_actions_route_module_layout_gaps() -> None:
    """Module-layout hard floor gaps should point at the module-layout gate."""

    assert report_domain._scorecard_next_actions(
        parity_pending_count=0,
        hard_quality_floor={
            "required_gaps": [
                "module_layout_baseline_suffix_module_limit:23!=22",
            ],
        },
    ) == ("ethos quality module-layout --json",)


def test_product_hard_quality_floor_includes_product_boundary(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(report_domain, "code_size_report", lambda _repo: {"required_gaps": []})
    monkeypatch.setattr(report_domain, "module_layout_report", lambda _repo: {"required_gaps": []})
    monkeypatch.setattr(
        report_domain,
        "product_boundary_report",
        lambda _repo: {"required_gaps": ["product-boundary:README.md:1"]},
    )
    monkeypatch.setattr(
        report_domain, "contributor_policy_report", lambda _repo: {"required_gaps": []}
    )

    floor = report_domain._hard_quality_floor_report(tmp_path)

    assert floor["ok"] is False
    assert "product-boundary:README.md:1" in floor["required_gaps"]
    assert report_domain._scorecard_next_actions(
        parity_pending_count=0, hard_quality_floor=floor
    ) == ("ethos quality product-boundary --json",)


def test_scorecard_next_actions_route_contributor_policy_gaps() -> None:
    assert report_domain._scorecard_next_actions(
        parity_pending_count=0,
        hard_quality_floor={"required_gaps": ["identity_mode_missing:.ethos/workspace.toml:1"]},
    ) == ("ethos quality contributor-policy --json",)


def test_scorecard_next_actions_route_clean_ready_state_to_full_proof() -> None:
    assert report_domain._scorecard_next_actions(
        parity_pending_count=0,
        hard_quality_floor={"required_gaps": []},
    ) == ("ethos prove --full",)


def test_advisory_next_actions_route_closeout_residue_signal() -> None:
    actions = report_domain._advisory_next_actions(("work_lane_closeout_residue_present",))

    assert actions == ("ethos orient --json", "ethos lane status --json")


def test_adopter_scorecard_reports_profile_shadow_parity_without_generic_next_action(
    monkeypatch, tmp_path: Path
) -> None:
    """Adopter report should not route to generic parity when profile shadow is clean."""

    monkeypatch.setattr(report_domain, "workspace_status", lambda _repo: {"coordination": {}})
    monkeypatch.setattr(
        report_domain.status_domain,
        "audit_for_root",
        lambda _repo, **_kwargs: {
            "ok": True,
            "required_gaps": [],
            "governance_context": {"profile": "gitlab"},
            "adopter": {
                "adopter": {
                    "governance": {
                        "claims": True,
                        "evidence": True,
                        "docs": True,
                    }
                }
            },
            "schemas": {"ok": True},
            "openspec": {"ok": True, "advisory_gaps": []},
        },
    )
    monkeypatch.setattr(report_domain, "docs_health_report", lambda _repo: {"ok": True})
    monkeypatch.setattr(
        report_domain,
        "claims_report",
        lambda _repo: {"ok": True, "required_gaps": [], "advisory_gaps": []},
    )
    monkeypatch.setattr(report_domain, "command_registry_report", lambda _repo: {"ok": True})
    monkeypatch.setattr(
        report_domain,
        "projection_contract",
        lambda: {"truth": ASSISTANT_TRUTH_BOUNDARY},
    )
    monkeypatch.setattr(report_domain, "schema_validation_report", lambda _repo: {"ok": True})
    monkeypatch.setattr(report_domain, "evolution_report", lambda _repo: {"ok": True})
    monkeypatch.setattr(report_domain, "signature_policy_report", lambda _repo: {"ok": True})
    monkeypatch.setattr(
        report_domain,
        "playbooks_report",
        lambda _repo, mode="v2-strict": {
            "ok": False,
            "mode": mode,
            "required_gaps": ["playbooks_v2_missing_skill_ids"],
            "advisory_gaps": [],
            "v2_compliance": {"score": 0, "max_score": 1},
        },
    )
    monkeypatch.setattr(report_domain, "adoption_scaffold_report", lambda: {"ok": True})
    monkeypatch.setattr(
        report_domain,
        "parity_ledger_report",
        lambda: {"ok": True, "summary": {"unclassified_count": 0}},
    )
    monkeypatch.setattr(report_domain.git_adapter, "current_tracked_head", lambda _repo: "head")

    def fake_parity_gaps_report(**kwargs):
        if kwargs.get("adopter") == "domain-adopter":
            return {
                "ok": True,
                "adopter": "domain-adopter",
                "required_gaps": [],
                "pending_packages": [],
                "evidence": {"path": "docs/evidence/parity/domain-adopter-shadow.json"},
            }
        return {
            "ok": False,
            "adopter": "generic",
            "required_gaps": ["parity_pending:work-lane-lifecycle"],
            "pending_packages": [{"gap": "parity_pending:work-lane-lifecycle"}],
            "evidence": {},
        }

    monkeypatch.setattr(report_domain, "parity_gaps_report", fake_parity_gaps_report)
    monkeypatch.setattr(
        report_domain,
        "context_projection_contract",
        lambda: {
            "authority": "projection",
            "can_close_required_gaps": False,
            "can_satisfy_proof": False,
        },
    )
    monkeypatch.setattr(report_domain, "available_profiles", lambda: ())
    monkeypatch.setattr(
        report_domain,
        "profile_identity",
        lambda _repo: "domain-adopter",
    )
    monkeypatch.setattr(
        report_domain,
        "standard_adapter_registry",
        lambda: {"std": {"boundary": "b", "fallback": "f", "exit_strategy": "e"}},
    )

    payload: dict[str, Any] = report_domain.scorecard_report(tmp_path)

    assert payload["summary"]["parity_pending_count"] == 0
    assert payload["next_actions"] == ("ethos playbooks check --mode v2-strict --json",)
    assert payload["data"]["parity"]["scope"] == {
        "generic_gap_count": 1,
        "adopter": "domain-adopter",
        "adopter_gap_count": 0,
        "domain_profile_parity_closed": True,
        "note": (
            "Adopter shadow parity is profile-specific evidence. Generic command parity "
            "remains a product migration signal and does not block adopter report routing."
        ),
    }
    assert payload["data"]["parity"]["adopter_gaps"]["evidence"]["path"] == (
        "docs/evidence/parity/domain-adopter-shadow.json"
    )


def test_adopter_scorecard_binds_shadow_parity_to_external_product_root(
    monkeypatch, tmp_path: Path
) -> None:
    """Adopter report should validate shadow evidence against the external product root."""

    product_root = tmp_path / "product"
    adopter_root = tmp_path / "adopter"
    product_root.mkdir()
    adopter_root.mkdir()
    calls: list[dict[str, object]] = []

    monkeypatch.setattr(report_domain, "workspace_status", lambda _repo: {"coordination": {}})
    monkeypatch.setattr(
        report_domain.status_domain,
        "audit_for_root",
        lambda _repo, **_kwargs: {
            "ok": True,
            "required_gaps": [],
            "governance_context": {"profile": "gitlab"},
            "adopter": {
                "adopter": {
                    "governance": {
                        "claims": True,
                        "evidence": True,
                        "docs": True,
                    }
                }
            },
            "schemas": {"ok": True},
            "openspec": {"ok": True, "advisory_gaps": []},
        },
    )
    monkeypatch.setattr(report_domain, "docs_health_report", lambda _repo: {"ok": True})
    monkeypatch.setattr(
        report_domain,
        "claims_report",
        lambda _repo: {"ok": True, "required_gaps": [], "advisory_gaps": []},
    )
    monkeypatch.setattr(report_domain, "command_registry_report", lambda _repo: {"ok": True})
    monkeypatch.setattr(
        report_domain,
        "projection_contract",
        lambda: {"truth": ASSISTANT_TRUTH_BOUNDARY},
    )
    monkeypatch.setattr(report_domain, "schema_validation_report", lambda _repo: {"ok": True})
    monkeypatch.setattr(report_domain, "evolution_report", lambda _repo: {"ok": True})
    monkeypatch.setattr(report_domain, "signature_policy_report", lambda _repo: {"ok": True})
    monkeypatch.setattr(
        report_domain,
        "playbooks_report",
        lambda _repo, mode="v2-strict": {
            "ok": True,
            "mode": mode,
            "required_gaps": [],
            "advisory_gaps": [],
            "v2_compliance": {"score": 1, "max_score": 1},
        },
    )
    monkeypatch.setattr(report_domain, "adoption_scaffold_report", lambda: {"ok": True})
    monkeypatch.setattr(
        report_domain,
        "parity_ledger_report",
        lambda: {"ok": True, "summary": {"unclassified_count": 0}},
    )
    monkeypatch.setattr(
        report_domain.git_adapter,
        "current_tracked_head",
        lambda repo: "product-head" if repo == product_root else "adopter-head",
    )

    def fake_parity_gaps_report(**kwargs):
        calls.append(kwargs)
        if kwargs.get("adopter") == "domain-adopter":
            return {
                "ok": bool(kwargs["root"] == product_root),
                "adopter": "domain-adopter",
                "required_gaps": []
                if kwargs["root"] == product_root
                else ["parity_evidence_invalid:domain-adopter:product_head"],
                "pending_packages": [],
                "evidence": {"path": "docs/evidence/parity/domain-adopter-shadow.json"},
            }
        return {
            "ok": False,
            "adopter": "generic",
            "required_gaps": ["parity_pending:work-lane-lifecycle"],
            "pending_packages": [{"gap": "parity_pending:work-lane-lifecycle"}],
            "evidence": {},
        }

    monkeypatch.setattr(report_domain, "parity_gaps_report", fake_parity_gaps_report)
    monkeypatch.setattr(
        report_domain,
        "context_projection_contract",
        lambda: {
            "authority": "projection",
            "can_close_required_gaps": False,
            "can_satisfy_proof": False,
        },
    )
    monkeypatch.setattr(report_domain, "available_profiles", lambda: ())
    monkeypatch.setattr(report_domain, "profile_identity", lambda _repo: "domain-adopter")
    monkeypatch.setattr(
        report_domain,
        "standard_adapter_registry",
        lambda: {"std": {"boundary": "b", "fallback": "f", "exit_strategy": "e"}},
    )

    payload: dict[str, Any] = report_domain.scorecard_report(
        adopter_root,
        product_root=product_root,
    )

    adopter_call = next(call for call in calls if call.get("adopter") == "domain-adopter")
    assert adopter_call["root"] == product_root
    assert adopter_call["target"] == adopter_root
    assert adopter_call["current_product_head"] == "product-head"
    assert adopter_call["current_target_head"] == "adopter-head"
    assert payload["summary"]["parity_pending_count"] == 0
    assert payload["data"]["parity"]["scope"]["domain_profile_parity_closed"] is True
