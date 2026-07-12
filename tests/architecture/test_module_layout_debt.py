from __future__ import annotations

from pathlib import Path

import pytest

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


@pytest.mark.parametrize(
    ("debt", "replacement", "retired"),
    [
        pytest.param(
            "module_layout_suffix_module:"
            "packages/ethos-core/src/ethos_core/contracts/context_projection.py:context_projection",
            "packages/ethos-core/src/ethos_core/contracts/context/projection.py",
            "packages/ethos-core/src/ethos_core/contracts/context_projection.py",
            id="context-projection",
        ),
        pytest.param(
            "module_layout_suffix_module:"
            "packages/ethos-core/src/ethos_core/contracts/capability_parity.py:capability_parity",
            "packages/ethos-core/src/ethos_core/contracts/capability/parity.py",
            "packages/ethos-core/src/ethos_core/contracts/capability_parity.py",
            id="capability-parity",
        ),
        pytest.param(
            "module_layout_suffix_module:"
            "packages/ethos-core/src/ethos_core/contracts/system_contracts.py:system_contracts",
            "packages/ethos-core/src/ethos_core/contracts/system/contracts.py",
            "packages/ethos-core/src/ethos_core/contracts/system_contracts.py",
            id="system-contracts",
        ),
        pytest.param(
            "module_layout_suffix_module:"
            "packages/ethos-core/src/ethos_core/contracts/package_ontology.py:package_ontology",
            "packages/ethos-core/src/ethos_core/contracts/package/ontology.py",
            "packages/ethos-core/src/ethos_core/contracts/package_ontology.py",
            id="package-ontology",
        ),
        pytest.param(
            "module_layout_suffix_module:"
            "packages/ethos-core/src/ethos_core/contracts/skill_activation.py:skill_activation",
            "packages/ethos-core/src/ethos_core/contracts/skill/activation.py",
            "packages/ethos-core/src/ethos_core/contracts/skill_activation.py",
            id="skill-activation",
        ),
    ],
)
def test_semantic_subpackages_replace_suffix_module(
    debt: str,
    replacement: str,
    retired: str,
) -> None:
    """Keep declared contracts in semantic subpackages without suffix-flat debt."""
    report = module_layout_report(ROOT)
    suffix_gaps = {finding["gap"] for finding in report["suffix_module_findings"]}
    policy_text = ROOT.joinpath(report["policy"]).read_text(encoding="utf-8")

    assert debt not in suffix_gaps
    assert debt not in policy_text
    assert ROOT.joinpath(replacement).is_file()
    assert not ROOT.joinpath(retired).exists()
