"""Focused regressions for strict YAML 1.2 mapping-key identity."""

from __future__ import annotations

import tomllib
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.repo.source_budget.measurement.native.core as native_core
from ethos.adapters.repo.source_budget.carriers import load_metric_contracts
from ethos.adapters.repo.source_budget.measurement.native._structured import measure_structured

if TYPE_CHECKING:
    from typing import Any

    from ethos_core.contracts.source_budget.metrics import MetricContract

ROOT = Path(__file__).resolve().parents[5]
CASES_PATH = ROOT / "tests" / "fixtures" / "source-budget-v2" / "cases.toml"


@lru_cache(maxsize=1)
def _cases() -> dict[str, dict[str, Any]]:
    payload = tomllib.loads(CASES_PATH.read_text(encoding="utf-8"))
    return {str(row["id"]): row for row in payload["case"]}


@lru_cache(maxsize=1)
def _registry():
    load = load_metric_contracts(ROOT)
    assert load.required_gaps == ()
    assert load.contracts is not None
    return load.contracts


def _content(case_id: str) -> bytes:
    case = _cases()[case_id]
    return str(case["text"]).encode() if "text" in case else bytes.fromhex(str(case["hex"]))


def _contracts(profile: str) -> tuple[MetricContract, ...]:
    return tuple(
        sorted(
            (item for item in _registry().contracts if item.metric_profile == profile),
            key=lambda item: (item.metric_id, item.unit, item.contract_id),
        )
    )


def _measure(case_id: str):
    case = _cases()[case_id]
    return native_core.measure_native(_content(case_id), _contracts(str(case["profile"])))


def _success(case_id: str):
    load = _measure(case_id)
    assert load.required_gaps == ()
    assert load.measurement is not None
    return load.measurement


def _failure(case_id: str, expected_gap: str) -> None:
    load = _measure(case_id)
    assert load.measurement is None
    assert load.required_gaps == (expected_gap,)


def _values(measurement) -> dict[str, int]:
    return {item.metric_id: item.value for item in measurement.values}


@pytest.mark.parametrize(
    "text",
    [
        "true: bool\n1: int\n",
        "1: int\n1.0: float\n",
        "-0.0: negative\n0.0: positive\n",
    ],
)
def test_yaml_mapping_preserves_tag_distinct_equal_python_keys(text: str) -> None:
    stream, nodes, _scalar_bytes = measure_structured("yaml", text)

    assert nodes == 5
    assert b"map" in stream


def test_yaml_mapping_rejects_same_tag_canonical_duplicate_keys() -> None:
    with pytest.raises(ValueError, match="structured parser rejected input"):
        measure_structured("yaml", "0xB: first\n11: second\n")


def test_yaml_mapping_wraps_non_finite_key_failure() -> None:
    with pytest.raises(ValueError, match="structured parser rejected input"):
        measure_structured("yaml", ".nan: value\n")


def test_yaml_uses_core_schema_and_rejects_explicit_timestamp_tag() -> None:
    plain = _success("yaml-date-plain")
    quoted = _success("yaml-date-quoted")
    assert plain.normalized_digest == quoted.normalized_digest
    assert plain.values == quoted.values
    _failure("yaml-timestamp-explicit", "source_budget_native_parse_failed:yaml")


@pytest.mark.parametrize(
    ("left", "right"),
    [
        ("yaml-legacy-octal-plain", "yaml-decimal-twelve"),
        ("yaml-leading-zero-eight", "yaml-decimal-eight"),
        ("yaml-core-octal", "yaml-decimal-ten"),
        ("yaml-core-hex", "yaml-decimal-fifty-eight"),
        ("yaml-sexagesimal-plain", "yaml-sexagesimal-quoted"),
        ("yaml-scientific", "yaml-float-thousand"),
        ("yaml-exponent", "yaml-float-thousand"),
        ("yaml-underscored-plain", "yaml-underscored-quoted"),
        ("yaml-negative-hex-plain", "yaml-negative-hex-quoted"),
        ("yaml-binary-plain", "yaml-binary-quoted"),
        ("yaml-merge-token-plain", "yaml-merge-token-quoted"),
        ("yaml-value-token-plain", "yaml-value-token-quoted"),
    ],
)
def test_yaml_uses_yaml_1_2_core_numeric_resolution(left: str, right: str) -> None:
    first = _success(left)
    second = _success(right)
    assert first.normalized_digest == second.normalized_digest
    assert first.values == second.values


def test_yaml_core_explicit_tags_versions_and_duplicate_keys_fail_closed() -> None:
    assert _success("yaml-explicit-core-valid").values
    assert _success("yaml-version-1-2").values
    for case_id in (
        "yaml-explicit-int-invalid",
        "yaml-explicit-float-invalid",
        "yaml-explicit-bool-invalid",
        "yaml-explicit-null-invalid",
        "yaml-leading-zero-duplicate",
        "yaml-version-1-1",
        "yaml-positive-inf",
        "yaml-negative-inf",
    ):
        _failure(case_id, "source_budget_native_parse_failed:yaml")
