from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from ethos.adapters.repo.source_budget.carriers import load_metric_contracts
from ethos.adapters.repo.source_budget.measurement.native.identity import resolve_native_provider
from ethos.adapters.repo.source_budget.measurement.router import measure_native

if TYPE_CHECKING:
    from ethos_core.contracts.source_budget.metrics import MetricContract
    from ethos_core.contracts.source_budget.metrics import MetricContractSet

ROOT = Path.cwd()


@lru_cache(maxsize=1)
def _registry() -> MetricContractSet:
    load = load_metric_contracts(ROOT)
    assert load.contracts is not None
    assert load.required_gaps == ()
    return load.contracts


def _contracts(profile: str) -> tuple[MetricContract, ...]:
    result = tuple(
        sorted(
            (item for item in _registry().contracts if item.metric_profile == profile),
            key=lambda item: (item.metric_id, item.unit, item.contract_id),
        )
    )
    assert result
    return result


def _fit(content: bytes, ceiling: int, filler: bytes) -> bytes:
    assert content
    assert filler
    assert len(content) <= ceiling
    repeats, tail = divmod(ceiling - len(content), len(filler))
    result = content + (filler * repeats) + filler[:tail]
    assert len(result) == ceiling
    return result


def _wide_cases() -> tuple[tuple[str, str, bytes], ...]:
    python = _fit(b"x=[" + (b"1," * 16_000) + b"0]\n", 65_536, b"#x\n")
    json = _fit(b"[" + (b"0," * 15_000) + b"0]", 32_768, b" ")
    toml = _fit(
        b"".join(f"k{index:04d}={index}\n".encode() for index in range(2_300)),
        32_768,
        b"#x\n",
    )
    yaml = _fit(
        b"".join(f"- item-{index:04d}\n".encode() for index in range(2_000)),
        32_768,
        b"#x\n",
    )
    jinja = _fit(
        b"".join(f"{{{{ v{index:04d} }}}}\n".encode() for index in range(1_800)),
        32_768,
        b" ",
    )
    shell = _fit(
        b"".join(f"printf %s x{index:04d}\n".encode() for index in range(1_800)),
        32_768,
        b"#x\n",
    )
    diagram = _fit(
        b"".join(f'system S{index:04d} "description"\n'.encode() for index in range(1_000)),
        32_768,
        b"#x\n",
    )
    return (
        ("utf8-footprint", "documentation-footprint-v2", (b"a" * 262_143) + b"\n"),
        ("utf8-control", "control-source-v2", (b"a" * 32_767) + b"\n"),
        ("diagram", "diagram-source-v2", diagram),
        ("python", "python-source-v2", python),
        ("json", "json-source-v2", json),
        ("toml", "toml-source-v2", toml),
        ("yaml", "yaml-source-v2", yaml),
        ("jinja", "template-jinja-v2", jinja),
        ("shell", "shell-source-v2", shell),
    )


@pytest.mark.parametrize(("case_id", "profile", "content"), _wide_cases())
def test_exact_ceiling_wide_provider_cases_complete(
    case_id: str,
    profile: str,
    content: bytes,
) -> None:
    del case_id
    contracts = _contracts(profile)
    provider = resolve_native_provider(contracts, _registry())
    load = measure_native(content, provider, _registry())

    assert load.required_gaps == ()
    assert load.measurement is not None


@pytest.mark.parametrize(
    ("profile", "content", "expected_gap"),
    [
        (
            "python-source-v2",
            b"x=" + (b"(" * 500) + b"1" + (b")" * 500) + b"\n",
            "source_budget_native_parse_failed:python",
        ),
        (
            "json-source-v2",
            (b"[" * 1_000) + b"0" + (b"]" * 1_000),
            "source_budget_native_resource_exhausted",
        ),
        (
            "toml-source-v2",
            (".".join(f"k{index}" for index in range(500)) + "=1\n").encode(),
            "source_budget_native_resource_exhausted",
        ),
        (
            "yaml-source-v2",
            (("- " * 1_000) + "0\n").encode(),
            "source_budget_native_resource_exhausted",
        ),
        (
            "template-jinja-v2",
            (("{% if v %}" * 300) + "x" + ("{% endif %}" * 300)).encode(),
            "source_budget_native_resource_exhausted",
        ),
        (
            "shell-source-v2",
            ("echo " + ("$(" * 300) + "true" + (")" * 300) + "\n").encode(),
            "source_budget_native_resource_exhausted",
        ),
    ],
)
def test_deep_provider_cases_fail_closed_without_partial_measurement(
    profile: str,
    content: bytes,
    expected_gap: str,
) -> None:
    contracts = _contracts(profile)
    provider = resolve_native_provider(contracts, _registry())
    load = measure_native(content, provider, _registry())

    assert load.measurement is None
    assert load.required_gaps == (expected_gap,)


def test_exact_ceiling_ini_amplification_completes_or_fails_closed_atomically() -> None:
    content = b"".join(
        (
            b"[DEFAULT]\n",
            *(f"k{index:04d}=value{index:04d}\n".encode() for index in range(768)),
            *(f"[s{index:04d}]\n".encode() for index in range(768)),
        )
    )
    content = _fit(content, 32_768, b"#x\n")

    contracts = _contracts("ini-source-v2")
    provider = resolve_native_provider(contracts, _registry())
    load = measure_native(content, provider, _registry())

    if load.measurement is None:
        assert load.required_gaps == ("source_budget_worker_resource_exhausted",)
        return
    assert load.required_gaps == ()
    assert {item.contract_id for item in load.measurement.values} == {
        item.contract_id for item in contracts
    }
