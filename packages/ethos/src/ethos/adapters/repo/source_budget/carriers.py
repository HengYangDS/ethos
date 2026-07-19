"""Repository loaders for Budget Contract v2 carrier and metric declarations."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import ValidationError

import ethos_core.contracts.source_budget.carriers as carrier_contracts
from ethos_core.contracts.source_budget.carriers import CarrierManifestLoad
from ethos_core.contracts.source_budget.carriers import validate_carrier_manifest
from ethos_core.contracts.source_budget.metrics import MetricContractSetLoad
from ethos_core.contracts.source_budget.metrics import validate_metric_contracts

if TYPE_CHECKING:
    from collections.abc import Iterable

CARRIER_MANIFEST_PATH = Path("system/policies/source-budget-carriers.toml")
METRIC_CONTRACTS_PATH = Path("system/policies/source-budget-metrics.toml")


def load_carrier_manifest(root: Path) -> CarrierManifestLoad:
    """Load the independent v2 carrier manifest or fail closed."""
    path = root / CARRIER_MANIFEST_PATH
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return CarrierManifestLoad(None, ("source_budget_carrier_manifest_missing",))
    except tomllib.TOMLDecodeError:
        return CarrierManifestLoad(None, ("source_budget_carrier_manifest_invalid_toml",))
    except (OSError, UnicodeError):
        return CarrierManifestLoad(None, ("source_budget_carrier_manifest_unreadable",))
    try:
        return CarrierManifestLoad(validate_carrier_manifest(payload), ())
    except (ValidationError, ValueError):
        return CarrierManifestLoad(None, ("source_budget_carrier_manifest_invalid",))


def load_metric_contracts(root: Path) -> MetricContractSetLoad:
    """Load the independent v2 metric registry or fail closed."""
    path = root / METRIC_CONTRACTS_PATH
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return MetricContractSetLoad(None, ("source_budget_metric_contracts_missing",))
    except tomllib.TOMLDecodeError:
        return MetricContractSetLoad(None, ("source_budget_metric_contracts_invalid_toml",))
    except (OSError, UnicodeError):
        return MetricContractSetLoad(None, ("source_budget_metric_contracts_unreadable",))
    try:
        return MetricContractSetLoad(validate_metric_contracts(payload), ())
    except (ValidationError, ValueError):
        return MetricContractSetLoad(None, ("source_budget_metric_contracts_invalid",))


def classify_carriers(
    paths: Iterable[str],
    manifest: carrier_contracts.CarrierManifest,
) -> carrier_contracts.CarrierInventory:
    """Classify one repository inventory through the typed manifest."""
    return carrier_contracts.classify_carriers(paths, manifest)
