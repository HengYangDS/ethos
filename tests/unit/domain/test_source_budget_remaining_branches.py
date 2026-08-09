from __future__ import annotations

from typing import TYPE_CHECKING

import ethos.domain.source_budget.measurement as measurement
from ethos.domain.source_budget.measurement_policy import Policy

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


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


def test_source_budget_public_report_stops_when_inventory_is_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(measurement, "policy_for_root", lambda _root: (_policy(), ()))
    monkeypatch.setattr(measurement.git_adapter, "git_stdout", lambda *_a: "")

    report = measurement.source_budget_report(tmp_path)

    assert report["required_gaps"] == ["source_budget_inventory_unavailable"]


def test_source_budget_public_report_preserves_measure_and_cross_check_gaps(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    policy = _policy()
    metrics = {
        "python_product": 11,
        "python_tests": 0,
        "python_tools": 0,
        "python_other": 0,
        "python_total": 11,
        "global_total": 11,
        "record_total": 0,
        "generated_evidence_total": 0,
    }
    monkeypatch.setattr(measurement, "policy_for_root", lambda _root: (policy, ()))
    monkeypatch.setattr(measurement, "_paths", lambda _root: ((("src/demo.py", False),), ()))
    monkeypatch.setattr(
        measurement,
        "_measure",
        lambda *_a, **_k: (
            metrics,
            {"file_count": 1},
            {},
            ("source_budget_carrier_unreadable:src/demo.py",),
        ),
    )
    monkeypatch.setattr(
        measurement,
        "_cross_check",
        lambda *_a, **_k: ({}, ("source_budget_scc_invalid", "source_budget_scc_invalid")),
    )

    report = measurement.source_budget_report(tmp_path)

    assert report["required_gaps"] == [
        "source_budget_carrier_unreadable:src/demo.py",
        "source_budget_scc_invalid",
        "source_budget_terminal_exceeded:python_product:11>10",
    ]
