from __future__ import annotations

from pathlib import Path

from ethos.repository.policy.governance import kernel as governance_kernel
from ethos.repository.policy.governance.kernel import governance_kernel_report


def test_governance_kernel_report_closes_runtime_docs_profiles_and_generic_scaffold() -> None:
    report = governance_kernel_report(Path(__file__).resolve().parents[3])

    assert report["ok"] is True, report["required_gaps"]
    assert report["summary"]["check_count"] == 4
    assert report["summary"]["closed_check_count"] == 4
    assert report["boundary"]["subject_kind"] == "repository"
    assert report["boundary"]["product_and_adopters"] == (
        "same_kernel_profile_or_adapter_differences_only"
    )
    assert report["boundary"]["transition_commands"] == [
        "ethos status",
        "ethos plan",
        "ethos prove",
        "ethos land",
        "ethos publish",
    ]


def test_governance_kernel_blocks_second_command_plane_context() -> None:
    check = governance_kernel._runtime_context_check(
        {
            "contract": "governed_repository",
            "single_kernel": False,
            "kernel_chain": ["Authority"],
            "transition_commands": ["ethos status"],
            "shared_commands": ["ethos status"],
            "reader_view_commands": [],
            "scorecard_commands": [],
            "subject": {"kind": "workspace"},
            "truth_boundary": "host",
            "profile_boundary": "forked_kernel",
            "authority": {"policy_refs": []},
        }
    )

    gaps = "\n".join(check["required_gaps"])
    assert check["ok"] is False
    assert "governance_kernel_single_kernel_missing" in gaps
    assert "governance_kernel_chain_mismatch" in gaps
    assert "governance_kernel_transition_commands_mismatch" in gaps
    assert "governance_kernel_subject_not_repository" in gaps
    assert "governance_kernel_truth_boundary_mismatch" in gaps
    assert "governance_kernel_profile_boundary_mismatch" in gaps


def test_governance_kernel_blocks_profile_field_drift(monkeypatch) -> None:
    drifted = {
        "ok": True,
        "isomorphic": True,
        "required_gaps": [],
        "allowed_differences": list(governance_kernel.ALLOWED_DIFFERENCE_FIELDS),
        "shared_kernel": {"kernel_chain": list(governance_kernel.KERNEL_CHAIN)},
        "profiles": {
            "product-adopter": {
                "capability_graph": ["source_truth"],
                "kernel_chain": list(governance_kernel.KERNEL_CHAIN),
                "trust_lifecycle": ["Claim"],
                "run_steps": ["objective"],
                "truth_sources": ["source"],
                "advisory_projections": [".ethos/state"],
                "authority_binding": "adopter",
                "profile_config": ["profile"],
                "adapter_binding": ["adapter"],
                "strictness": "profile",
                "rollout": "adopt",
            },
            "self-governance": {
                "capability_graph": ["different"],
                "kernel_chain": list(governance_kernel.KERNEL_CHAIN),
                "trust_lifecycle": ["Claim"],
                "run_steps": ["objective"],
                "truth_sources": ["source"],
                "advisory_projections": [".ethos/state"],
                "authority_binding": "product",
                "profile_config": ["profile"],
                "adapter_binding": ["adapter"],
                "strictness": "full",
                "rollout": "lane",
            },
        },
    }

    check = governance_kernel._profile_isomorphism_check(drifted)

    assert check["ok"] is False
    assert (
        "governance_kernel_profile_field_mismatch:self-governance:capability_graph"
        in check["required_gaps"]
    )


def test_governance_kernel_blocks_missing_profiles_allowed_differences_and_shared_kernel() -> None:
    check = governance_kernel._profile_isomorphism_check(
        {
            "ok": False,
            "isomorphic": False,
            "required_gaps": ["profile_report_gap"],
            "allowed_differences": [],
            "shared_kernel": {"kernel_chain": ["Authority"]},
            "profiles": {
                "product-adopter": {
                    "capability_graph": ["source_truth"],
                    "kernel_chain": list(governance_kernel.KERNEL_CHAIN),
                    "trust_lifecycle": ["Claim"],
                    "run_steps": ["objective"],
                    "truth_sources": ["source"],
                    "advisory_projections": [".ethos/state"],
                    "authority_binding": "adopter",
                    "profile_config": [],
                    "adapter_binding": "adapter",
                    "strictness": "profile",
                    "rollout": "adopt",
                }
            },
        }
    )

    gaps = set(check["required_gaps"])
    assert check["ok"] is False
    assert "profile_report_gap" in gaps
    assert "governance_kernel_profile_missing:self-governance" in gaps
    assert "governance_kernel_profiles_not_isomorphic" in gaps
    assert "governance_kernel_allowed_difference_missing:product-adopter:profile_config" in gaps
    assert "governance_kernel_shared_kernel_chain_mismatch" in gaps


def test_governance_kernel_blocks_docs_and_generic_scaffold_gaps(tmp_path: Path) -> None:
    docs_check = governance_kernel._product_docs_check(tmp_path)
    assert docs_check["ok"] is False
    assert "governance_kernel_doc_missing:README.md" in docs_check["required_gaps"]

    readme = tmp_path / "README.md"
    readme.write_text("Isomorphic Governance only", encoding="utf-8")
    phrase_check = governance_kernel._product_docs_check(tmp_path)
    assert any(
        str(gap).startswith("governance_kernel_doc_phrase_missing:README.md")
        for gap in phrase_check["required_gaps"]
    )

    scaffold = governance_kernel._generic_adoption_scaffold_check(
        {
            "profile": "python",
            "applied": True,
            "planned_files": ["AGENTS.md"],
            "required_gaps": ["adoption_plan_gap"],
        }
    )

    gaps = set(scaffold["required_gaps"])
    assert scaffold["ok"] is False
    assert "adoption_plan_gap" in gaps
    assert "governance_kernel_generic_profile_mismatch" in gaps
    assert "governance_kernel_generic_probe_mutated" in gaps
    assert "governance_kernel_generic_scaffold_missing:.ethos/workspace.toml" in gaps
    assert any(str(gap).startswith("governance_kernel_generic_docs_path_missing:") for gap in gaps)


def test_governance_kernel_helpers_cover_non_sequence_and_dedupe_edges() -> None:
    assert governance_kernel._dedupe(["a", "b", "a"]) == ["a", "b"]
