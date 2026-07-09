from __future__ import annotations

from pathlib import Path

from ethos.repository.policy.layout.core import module_layout_report

ROOT = Path(__file__).resolve().parents[2]


def test_module_layout_ratchet_has_no_remaining_steady_state_debt() -> None:
    """Keep semantic subpackages mandatory instead of preserving baseline debt."""
    report = module_layout_report(ROOT)

    assert report["summary"]["debt_count"] == 0
    assert report["baseline_gap_count"] == 0
    assert report["baseline_limit"] == 0
    assert report["ratchet"]["state"] == "clear"
    assert report["ratchet"]["baseline_gap_count"] == 0
    assert report["ratchet"]["baseline_limit"] == 0
    assert set(report["ratchet"]["debt_kinds"]) == set()


CONTEXT_PROJECTION_DEBT = (
    "module_layout_suffix_module:"
    "packages/ethos-core/src/ethos_core/contracts/context_projection.py:context_projection"
)


def test_context_projection_contract_lives_in_semantic_subpackage_not_suffix_module() -> None:
    """Keep context projection under contracts/context/ instead of suffix-flat debt."""
    report = module_layout_report(ROOT)
    suffix_gaps = {finding["gap"] for finding in report["suffix_module_findings"]}
    policy_text = ROOT.joinpath(report["policy"]).read_text(encoding="utf-8")

    assert CONTEXT_PROJECTION_DEBT not in suffix_gaps
    assert CONTEXT_PROJECTION_DEBT not in policy_text
    assert ROOT.joinpath(
        "packages/ethos-core/src/ethos_core/contracts/context/projection.py"
    ).is_file()
    assert not ROOT.joinpath(
        "packages/ethos-core/src/ethos_core/contracts/context_projection.py"
    ).exists()


CAPABILITY_PARITY_DEBT = (
    "module_layout_suffix_module:"
    "packages/ethos-core/src/ethos_core/contracts/capability_parity.py:capability_parity"
)


def test_capability_parity_contract_lives_in_semantic_subpackage_not_suffix_module() -> None:
    """Keep capability parity under contracts/capability/ instead of suffix-flat debt."""
    report = module_layout_report(ROOT)
    suffix_gaps = {finding["gap"] for finding in report["suffix_module_findings"]}
    policy_text = ROOT.joinpath(report["policy"]).read_text(encoding="utf-8")

    assert CAPABILITY_PARITY_DEBT not in suffix_gaps
    assert CAPABILITY_PARITY_DEBT not in policy_text
    assert ROOT.joinpath(
        "packages/ethos-core/src/ethos_core/contracts/capability/parity.py"
    ).is_file()
    assert not ROOT.joinpath(
        "packages/ethos-core/src/ethos_core/contracts/capability_parity.py"
    ).exists()


SYSTEM_CONTRACTS_DEBT = (
    "module_layout_suffix_module:"
    "packages/ethos-core/src/ethos_core/contracts/system_contracts.py:system_contracts"
)


def test_system_contracts_live_in_semantic_subpackage_not_suffix_module() -> None:
    """Keep system contracts under contracts/system/ instead of suffix-flat debt."""
    report = module_layout_report(ROOT)
    suffix_gaps = {finding["gap"] for finding in report["suffix_module_findings"]}
    policy_text = ROOT.joinpath(report["policy"]).read_text(encoding="utf-8")

    assert SYSTEM_CONTRACTS_DEBT not in suffix_gaps
    assert SYSTEM_CONTRACTS_DEBT not in policy_text
    assert ROOT.joinpath(
        "packages/ethos-core/src/ethos_core/contracts/system/contracts.py"
    ).is_file()
    assert not ROOT.joinpath(
        "packages/ethos-core/src/ethos_core/contracts/system_contracts.py"
    ).exists()


PACKAGE_ONTOLOGY_DEBT = (
    "module_layout_suffix_module:"
    "packages/ethos-core/src/ethos_core/contracts/package_ontology.py:package_ontology"
)


def test_package_ontology_contract_lives_in_semantic_subpackage_not_suffix_module() -> None:
    """Keep package ontology under contracts/package/ instead of suffix-flat debt."""
    report = module_layout_report(ROOT)
    suffix_gaps = {finding["gap"] for finding in report["suffix_module_findings"]}
    policy_text = ROOT.joinpath(report["policy"]).read_text(encoding="utf-8")

    assert PACKAGE_ONTOLOGY_DEBT not in suffix_gaps
    assert PACKAGE_ONTOLOGY_DEBT not in policy_text
    assert ROOT.joinpath(
        "packages/ethos-core/src/ethos_core/contracts/package/ontology.py"
    ).is_file()
    assert not ROOT.joinpath(
        "packages/ethos-core/src/ethos_core/contracts/package_ontology.py"
    ).exists()


SKILL_ACTIVATION_DEBT = (
    "module_layout_suffix_module:"
    "packages/ethos-core/src/ethos_core/contracts/skill_activation.py:skill_activation"
)


def test_skill_activation_contract_lives_in_semantic_subpackage_not_suffix_module() -> None:
    """Keep skill activation under contracts/skill/ instead of suffix-flat debt."""
    report = module_layout_report(ROOT)
    suffix_gaps = {finding["gap"] for finding in report["suffix_module_findings"]}
    policy_text = ROOT.joinpath(report["policy"]).read_text(encoding="utf-8")

    assert SKILL_ACTIVATION_DEBT not in suffix_gaps
    assert SKILL_ACTIVATION_DEBT not in policy_text
    assert ROOT.joinpath(
        "packages/ethos-core/src/ethos_core/contracts/skill/activation.py"
    ).is_file()
    assert not ROOT.joinpath(
        "packages/ethos-core/src/ethos_core/contracts/skill_activation.py"
    ).exists()
