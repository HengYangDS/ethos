from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest

import ethos.domain.source_budget.measurement as measurement
from ethos.domain.source_budget.measurement_policy import Policy

if TYPE_CHECKING:
    from pathlib import Path


def _policy() -> Policy:
    return Policy.model_validate(
        {
            "terminal": {
                "python_product": 10,
                "python_tests": 10,
                "python_tools": 10,
                "python_other": 10,
                "global_total": 20,
            },
            "immutable_record_roots": ("evidence/", "openspec/changes/archive/"),
            "line_width": 100,
            "cross_check": {
                "command": "scc",
                "args": (),
                "timeout_seconds": 1,
                "tolerance": {"python_total": 0, "global_total": 0},
            },
            "aggregates": {
                "python_total": ("python_product", "python_tests", "python_tools", "python_other"),
                "global_total": ("python_product", "python_tests", "python_tools", "python_other"),
            },
            "carriers": tuple(
                {
                    "category": category,
                    "extensions": (".py",),
                    "paths": (path,),
                    "measure": "python_ast",
                }
                for category, path in (
                    ("python_product", "src/*"),
                    ("python_tests", "tests/*"),
                    ("python_tools", "tools/*"),
                    ("python_other", "*.py"),
                )
            ),
        }
    )


@pytest.mark.parametrize(("function_name", "value"), [("_table", []), ("_sequence", {})])
def test_source_budget_strict_projection_rejects_wrong_container(
    function_name: str, value: object
) -> None:
    with pytest.raises(TypeError):
        getattr(measurement, function_name)(value)


@pytest.mark.parametrize(
    ("source", "expected"),
    [("#!/usr/bin/env -S python -I\n", "python"), ("#!/usr/bin/env python\n", "python")],
)
def test_interpreter_source_normalizes_env_forms(source: str, expected: str) -> None:
    assert measurement._interpreter_source(source) == expected  # noqa: SLF001


def test_structured_measurement_rejects_unknown_suffix() -> None:
    with pytest.raises(ValueError, match=re.escape("unsupported structured suffix: .unknown")):
        measurement._structured_value("value", ".unknown")  # noqa: SLF001


def test_measure_reports_missing_content_without_classification(tmp_path: Path) -> None:
    metrics, inventory, records, gaps = measurement._measure(  # noqa: SLF001
        tmp_path,
        (("src/missing.py", False),),
        _policy(),
        contents={},
    )

    assert gaps == ("source_budget_carrier_unreadable:src/missing.py",)
    assert records == {}
    assert inventory["file_count"] == 0
    assert metrics["python_product"] == 0


@pytest.mark.parametrize("location", [None, "", "/outside/root.py"])
def test_relative_location_rejects_invalid_or_external_paths(
    tmp_path: Path, location: object
) -> None:
    assert measurement._relative(tmp_path, location) is None  # noqa: SLF001


def test_cross_check_rejects_invalid_immutable_and_generated_counts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    policy = _policy()
    canonical = {"python_total": 0, "global_total": 0, "record_total": 1}
    records = {
        "src/ok.py": {"category": "python_product", "accounting": "source", "effective_lines": 1},
        "evidence/record.py": {
            "category": "python_product",
            "accounting": "record",
            "effective_lines": 1,
        },
    }
    calls = 0

    def counts(*_args: object) -> tuple[dict[str, int] | None, tuple[str, ...]]:
        nonlocal calls
        calls += 1
        return ({"src/ok.py": 1}, ()) if calls == 1 else (None, ("source_budget_scc_invalid",))

    monkeypatch.setattr(measurement, "_scc_counts", counts)
    assert measurement._cross_check(  # noqa: SLF001
        tmp_path, policy, records, canonical
    ) == ({}, ("source_budget_scc_invalid",))

    records = {
        "generated.json": {
            "category": "generated",
            "accounting": "generated_evidence",
            "effective_lines": True,
        }
    }
    monkeypatch.setattr(measurement, "_scc_counts", lambda *_args: ({}, ()))
    assert measurement._cross_check(  # noqa: SLF001
        tmp_path, policy, records, canonical
    ) == ({}, ("source_budget_scc_invalid",))
