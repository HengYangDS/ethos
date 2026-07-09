from __future__ import annotations

from pathlib import Path

from ethos.repository.policy.layout.core import module_layout_report

ROOT = Path(__file__).resolve().parents[2]
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
