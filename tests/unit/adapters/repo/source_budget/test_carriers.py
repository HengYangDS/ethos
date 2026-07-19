from __future__ import annotations

from pathlib import Path

from ethos.adapters.repo.source_budget.carriers import classify_carriers
from ethos.adapters.repo.source_budget.carriers import load_carrier_manifest
from ethos.adapters.repo.source_budget.carriers import load_metric_contracts
from ethos.adapters.repo.source_budget.core import present_worktree_paths
from ethos_core.contracts.source_budget.metrics import resolve_metric_contracts

ROOT = Path(__file__).resolve().parents[5]


def test_carrier_and_metric_loaders_fail_closed_on_missing_or_invalid_toml(
    tmp_path: Path,
) -> None:
    carrier_load = load_carrier_manifest(tmp_path)
    assert carrier_load.manifest is None
    assert carrier_load.required_gaps == ("source_budget_carrier_manifest_missing",)

    metric_load = load_metric_contracts(tmp_path)
    assert metric_load.contracts is None
    assert metric_load.required_gaps == ("source_budget_metric_contracts_missing",)

    policy_root = tmp_path / "system" / "policies"
    policy_root.mkdir(parents=True)
    (policy_root / "source-budget-carriers.toml").write_text("[[broken", encoding="utf-8")
    (policy_root / "source-budget-metrics.toml").write_text("[[broken", encoding="utf-8")

    carrier_load = load_carrier_manifest(tmp_path)
    assert carrier_load.manifest is None
    assert carrier_load.required_gaps == ("source_budget_carrier_manifest_invalid_toml",)

    metric_load = load_metric_contracts(tmp_path)
    assert metric_load.contracts is None
    assert metric_load.required_gaps == ("source_budget_metric_contracts_invalid_toml",)


def test_current_manifest_classifies_present_inventory_deterministically() -> None:
    carrier_load = load_carrier_manifest(ROOT)
    metric_load = load_metric_contracts(ROOT)

    assert carrier_load.required_gaps == ()
    assert carrier_load.manifest is not None
    assert metric_load.required_gaps == ()
    assert metric_load.contracts is not None

    paths = present_worktree_paths(ROOT)
    assert paths

    forward = classify_carriers(paths, carrier_load.manifest)
    reverse = classify_carriers(reversed(paths), carrier_load.manifest)

    assert forward.required_gaps == ()
    assert forward.manifest_digest == reverse.manifest_digest
    assert forward.inventory_digest == reverse.inventory_digest
    assert forward.matches == reverse.matches

    measured = tuple(
        match.identity
        for match in forward.matches
        if match.state == "classified" and match.identity is not None
    )
    assert measured
    for identity in measured:
        assert resolve_metric_contracts(identity, metric_load.contracts)


def test_inventory_preserves_ambiguous_matches_instead_of_first_match() -> None:
    carrier_load = load_carrier_manifest(ROOT)
    assert carrier_load.manifest is not None

    python_rule = next(
        item
        for item in carrier_load.manifest.carriers
        if item.disposition == "measure" and ".py" in item.extensions
    )
    overlap = python_rule.model_copy(
        update={
            "carrier_id": f"{python_rule.carrier_id}-overlap",
            "include": ("packages/**",),
            "exclude": (),
        }
    )
    manifest = carrier_load.manifest.model_copy(
        update={"carriers": (*carrier_load.manifest.carriers, overlap)}
    )

    inventory = classify_carriers(("packages/ethos/src/ethos/__init__.py",), manifest)

    assert inventory.matches[0].state == "ambiguous"
    assert overlap.carrier_id in inventory.matches[0].matched_carrier_ids
    assert inventory.required_gaps
