"""Unavailable, malformed and contradictory budget inputs cannot produce green reports."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

import ethos.domain.source_budget.measurement as source_budget
from tests.support.source_budget import budget_repository
from tests.support.source_budget import write_budget_selection
from tests.support.subprocesses import completed as cp

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    ("before", "after"),
    [
        ("immutable_record_roots =", "invalid_record_roots ="),
        ('  "toml", "json", "yaml", "ini", "shell",\n', ""),
        (
            'python_total = ["python_product", "python_tests", "python_tools", "python_other"]',
            'python_total = ["python_tests", "python_product", "python_tools", "python_other"]',
        ),
        ("python_product = 1000", "python_unknown = 1000"),
        ('shebangs = ["sh", "bash", "zsh"]', 'shebangs = "sh"'),
        ('comment_prefixes = ["#"]', 'comment_prefixes = "#"'),
        ('extensions = [".py"]', 'extensions = ["py"]'),
        ('extensions = [".py"]', 'extensions = [".py", ".py"]'),
        (
            "[source_budget.aggregates]\n",
            '[source_budget.aggregates]\nextra_total = ["python_product"]\n',
        ),
        (
            'global_total = [\n  "python_product",',
            'global_total = [\n  "python_product", "python_product",',
        ),
        (
            'category = "python_other", measure = "python_ast"',
            'category = "python_other", measure = "lines"',
        ),
        ("timeout_seconds = 5", "timeout_seconds = true"),
        ('comment_prefixes = ["#"]', 'comment_prefixes = ["#", ""]'),
        ('comment_prefixes = ["#"]', 'comment_wrappers = [["/*", "*/", "extra"]]'),
    ],
)
def test_malformed_or_incomplete_policy_fails_closed(
    tmp_path: Path,
    before,
    after,
) -> None:
    selection, _ = budget_repository(tmp_path)
    source = selection.read_text()
    assert before in source
    selection.write_text(source.replace(before, after, 1), encoding="utf-8")

    report = source_budget.source_budget_report(tmp_path)

    assert report["verdict"] == "block"
    assert "ok" not in report
    assert report["metrics"] == {}
    assert report["required_gaps"] == ["source_budget_policy_invalid:shape"]


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("", "source_budget_policy_invalid:FileNotFoundError"),
        ("source_budget = [", "source_budget_policy_invalid:TOMLDecodeError"),
    ],
)
def test_missing_or_malformed_policy_is_a_closed_report(
    tmp_path: Path,
    content: str,
    expected: str,
) -> None:
    path = tmp_path / ".config/checks/format/selection.toml"
    if content:
        path.parent.mkdir(parents=True)
        path.write_text(content, encoding="utf-8")

    report = source_budget.source_budget_report(tmp_path)

    assert report["verdict"] == "block"
    assert report["state"] == "blocked"
    assert report["required_gaps"] == [expected]
    assert report["inventory"] == {"file_count": 0}


@pytest.mark.parametrize("inventory", ["", "malformed"])
def test_inventory_failure_prevents_measurement(tmp_path, monkeypatch, inventory):
    budget_repository(tmp_path)
    monkeypatch.setattr(source_budget.git_adapter, "git_stdout", lambda *_args: inventory)
    report = source_budget.source_budget_report(tmp_path)
    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["source_budget_inventory_unavailable"]


@pytest.mark.parametrize(
    "fault",
    ["malformed", "warning", "nonzero", "duplicate", "noninteger", "duplicate-invalid", "missing"],
)
def test_native_cross_check_failures_block_the_report(tmp_path, monkeypatch, fault):
    """Invalid native observations cannot certify source accounting."""
    budget_repository(tmp_path)
    location = (tmp_path / "src/ethos/demo.py").as_posix()
    records = [{"Location": location, "Code": 2}]
    if fault in {"duplicate", "duplicate-invalid"}:
        records.append({"Location": location, "Code": 2 if fault == "duplicate" else True})
    elif fault == "noninteger":
        records[0]["Code"] = True
    payload = (
        "not-json"
        if fault == "malformed"
        else json.dumps({"languageSummary": [{"Files": records}]})
    )
    real_which, real_run = source_budget.shutil.which, source_budget.subprocess.run
    monkeypatch.setattr(
        source_budget.shutil,
        "which",
        lambda command, **kwargs: (
            (None if fault == "missing" else "/fake-scc")
            if command == "fake-scc"
            else real_which(command, **kwargs)
        ),
    )
    monkeypatch.setattr(
        source_budget.subprocess,
        "run",
        lambda command, **kwargs: (
            cp(
                stdout=payload,
                stderr="warn" if fault == "warning" else "",
                returncode=2 if fault == "nonzero" else 0,
                command="scc",
            )
            if command[0] == "/fake-scc"
            else real_run(command, **kwargs)
        ),
    )
    report = source_budget.source_budget_report(tmp_path)
    assert report["verdict"] == "block"
    assert report["cross_check"] == {}
    expected = (
        "source_budget_scc_unavailable:fake-scc"
        if fault == "missing"
        else "source_budget_scc_invalid"
    )
    assert report["required_gaps"] == [expected]


def test_source_budget_public_report_preserves_measure_and_cross_check_gaps(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_budget_selection(tmp_path, terminal=(10, 10, 10, 10, 20), tolerance=(0, 0))
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
    monkeypatch.setattr(source_budget, "_paths", lambda _root: ((("src/demo.py", False),), ()))
    monkeypatch.setattr(
        source_budget,
        "_measure",
        lambda *_a, **_k: (
            metrics,
            {"file_count": 1},
            {},
            ("source_budget_carrier_unreadable:src/demo.py",),
        ),
    )
    monkeypatch.setattr(
        source_budget,
        "_cross_check",
        lambda *_a, **_k: ({}, ("source_budget_scc_invalid", "source_budget_scc_invalid")),
    )

    report = source_budget.source_budget_report(tmp_path)

    assert report["required_gaps"] == [
        "source_budget_carrier_unreadable:src/demo.py",
        "source_budget_scc_invalid",
        "source_budget_terminal_exceeded:python_product:11>10",
    ]
