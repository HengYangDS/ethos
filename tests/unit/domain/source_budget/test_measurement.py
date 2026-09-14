"""Source-budget laws distinguish authored implementation, records and generated evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

import ethos.domain.source_budget.measurement as source_budget
from ethos.domain.source_budget.measurement_policy import PYTHON_CATEGORIES
from tests.support.literal_cases import literal_case
from tests.support.source_budget import budget_repository
from tests.support.source_budget import fake_scc
from tests.support.source_budget import measure_budget
from tests.support.source_budget import tracked_budget_file


@pytest.mark.parametrize(
    ("text", "expected"),
    [('"padding"; value = 1\n', 1), ('payload = """first\n# literal\nlast"""\n', 3)],
)
def test_aggregate_python_budget_uses_the_same_semantic_measurement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, text: str, expected: int
) -> None:
    """Aggregate budgets cannot retain a different interpretation of Python source."""
    _, source = budget_repository(tmp_path)
    source.write_text(text, encoding="utf-8")
    fake_scc(monkeypatch, tmp_path)
    report = source_budget.source_budget_report(tmp_path)
    assert report["metrics"]["python_product"] == expected, report


def test_aggregate_python_budget_rejects_invalid_syntax(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A broken source file remains an explicit gap, not a passing small file."""
    _, source = budget_repository(tmp_path)
    source.write_text("def invalid(\n", encoding="utf-8")
    fake_scc(monkeypatch, tmp_path)
    report = source_budget.source_budget_report(tmp_path)
    assert report["verdict"] == "block", report
    assert "source_budget_carrier_unreadable:src/ethos/demo.py" in report["required_gaps"]


def test_product_policy_counts_markdown_in_global_budget() -> None:
    root = Path(__file__).resolve().parents[4]
    report = source_budget.source_budget_report(root)

    assert report["inventory"]["category_counts"]["markdown"] > 0
    assert report["metrics"]["global_total"] >= report["metrics"]["markdown"]


@pytest.mark.parametrize("category", ["python_product", "python_tests"])
@pytest.mark.parametrize("lines", [2, 3])
def test_only_declared_limits_block_at_exact_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    category: str,
    lines: int,
) -> None:
    selection, source = budget_repository(tmp_path)
    selection.write_text(
        selection.read_text().replace(
            "python_product = 1000, python_tests = 1000, python_tools = 1000, "
            "python_other = 1000, global_total = 2000",
            "python_product = 2, python_tests = 2",
        ),
    )
    target = source if category == "python_product" else tmp_path / "tests/test_demo.py"
    target.parent.mkdir(exist_ok=True)
    target.write_text("".join(f"VALUE_{index} = {index}\n" for index in range(lines)))
    tracked_budget_file(tmp_path, "tools/demo.py", "TOOL = 1\n")
    report = measure_budget(monkeypatch, tmp_path)

    assert report["terminal"] == {"python_product": 2, "python_tests": 2}
    assert set(report["enforced_metrics"]) == {"python_product", "python_tests"}
    assert report["metrics"]["global_total"] > 4
    assert report["required_gaps"] == (
        [f"source_budget_terminal_exceeded:{category}:3>2"] if lines == 3 else []
    )
    assert report["verdict"] == ("block" if lines == 3 else "pass")


def test_product_generated_projection_is_not_maintained_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selection, _ = budget_repository(tmp_path)
    root = Path(__file__).resolve().parents[4]
    selection.write_bytes((root / ".config/checks/format/selection.toml").read_bytes())
    tracked_budget_file(
        tmp_path, ".config/checks/architecture/models/model.c4", "model { system x }\n"
    )
    before = measure_budget(monkeypatch, tmp_path)
    tracked_budget_file(tmp_path, "docs/architecture/_generated/model.mmd", "graph TD; A-->B\n")
    tracked_budget_file(tmp_path, "openspec/changes/archive/closed/design.md", "## Past intent\n")
    after = source_budget.source_budget_report(tmp_path)

    assert after["metrics"]["global_total"] == before["metrics"]["global_total"]
    assert after["metrics"]["diagram"] == before["metrics"]["diagram"] > 0
    assert after["metrics"]["generated_evidence_total"] > 0
    assert after["metrics"]["record_total"] > 0
    tracked_budget_file(tmp_path, "openspec/changes/active/design.md", "## Current intent\n")
    assert (
        source_budget.source_budget_report(tmp_path)["metrics"]["global_total"]
        > after["metrics"]["global_total"]
    )


def test_direct_measurement_is_clean_when_bounded_counters_agree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    budget_repository(tmp_path)
    deleted = tracked_budget_file(tmp_path, "deleted.py", "VALUE = 1\n")
    deleted.unlink()
    report = measure_budget(monkeypatch, tmp_path)

    assert (report["verdict"], report["state"], report["required_gaps"]) == (
        "pass",
        "clean",
        [],
    )
    assert "ok" not in report
    assert report["metrics"]["python_total"] == 2
    assert report["inventory"]["file_count"] == 3
    assert "digest" not in report["inventory"]


def test_retired_evidence_path_does_not_exempt_maintained_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A legacy location cannot hide current source from its ordinary budget."""
    budget_repository(tmp_path)
    tracked_budget_file(tmp_path, "evidence/decision.py", "FIRST = 1\nSECOND = 2\n")
    report = measure_budget(monkeypatch, tmp_path)
    assert report["metrics"]["python_total"] == 4
    assert report["metrics"]["record_total"] == 0


def test_measurement_separates_exact_immutable_record_roots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    budget_repository(tmp_path)
    tracked_budget_file(
        tmp_path, "openspec/changes/archive/closed/decision.py", "FIRST = 1\nSECOND = 2\n"
    )
    tracked_budget_file(
        tmp_path, "openspec/changes/archive/closed/receipt.json", '{"closed": true}\n'
    )
    report = measure_budget(monkeypatch, tmp_path)

    assert report["required_gaps"] == []
    assert report["metrics"]["python_total"] == 2
    assert report["metrics"]["record_total"] == 3
    assert report["cross_check"]["file_count"] == report["inventory"]["file_count"]


def test_report_exposes_implementation_and_record_cross_check_totals(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    budget_repository(tmp_path)
    tracked_budget_file(tmp_path, "openspec/changes/archive/closed/decision.py", "RECORDED = 1\n")
    report = measure_budget(
        monkeypatch,
        tmp_path,
        {
            ".config/checks/format/selection.toml": 15,
            ".ethos/rules.toml": 1,
            "src/ethos/demo.py": 2,
            "openspec/changes/archive/closed/decision.py": 1,
        },
    )

    assert report["required_gaps"] == []
    assert report["cross_check"]["python_total"] == report["metrics"]["python_total"]
    assert report["cross_check"]["global_total"] <= report["metrics"]["global_total"]
    assert report["metrics"]["record_total"] == 1
    assert report["cross_check"]["record_total"] == 1
    assert report["cross_check"]["file_count"] == report["inventory"]["file_count"]


def test_generated_lock_is_dependency_evidence_not_owned_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    budget_repository(tmp_path)
    before = measure_budget(monkeypatch, tmp_path)
    tracked_budget_file(tmp_path, "package-lock.json", '{\n  "lockfileVersion": 3\n}\n')
    report = source_budget.source_budget_report(tmp_path)

    assert report["required_gaps"] == []
    assert report["inventory"]["category_counts"]["dependency_resolution"] == 1
    assert report["metrics"]["global_total"] == before["metrics"]["global_total"]
    assert report["cross_check"]["global_total"] == before["cross_check"]["global_total"]
    assert report["metrics"]["generated_evidence_total"] > 0
    assert report["cross_check"]["file_count"] == report["inventory"]["file_count"]


@pytest.mark.parametrize(
    "relative",
    cast(
        "tuple[str, ...]",
        literal_case(
            "domain.source_budget.test_measurement:parametrize:test_ecosystem_lockfile_patterns_share_one_evidence_class:0"
        ),
    ),
)
def test_ecosystem_lockfile_patterns_share_one_evidence_class(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    relative: str,
) -> None:
    budget_repository(tmp_path)
    tracked_budget_file(tmp_path, relative, "resolved dependency graph\n")
    report = measure_budget(monkeypatch, tmp_path)

    assert report["inventory"]["category_counts"]["dependency_resolution"] == 1


def test_ordinary_structured_files_cannot_impersonate_lockfile_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    budget_repository(tmp_path)
    tracked_budget_file(tmp_path, "system/clock.json", '{"source": true}\n')
    report = measure_budget(monkeypatch, tmp_path)

    assert report["inventory"]["category_counts"].get("dependency_resolution", 0) == 0
    assert report["inventory"]["category_counts"]["json"] == 1


def test_record_growth_is_visible_without_increasing_implementation_totals(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    budget_repository(tmp_path)
    record = tracked_budget_file(
        tmp_path, "openspec/changes/archive/closed/decision.py", "FIRST = 1\n"
    )
    before = measure_budget(monkeypatch, tmp_path)

    record.write_text("FIRST = 1\nSECOND = 2\nTHIRD = 3\n", encoding="utf-8")
    after = source_budget.source_budget_report(tmp_path)

    assert after["metrics"]["record_total"] == before["metrics"]["record_total"] + 2
    assert after["metrics"]["python_total"] == before["metrics"]["python_total"]
    assert after["metrics"]["global_total"] == before["metrics"]["global_total"]


def test_record_root_does_not_hide_an_unclassified_executable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    budget_repository(tmp_path)
    tracked_budget_file(
        tmp_path, "openspec/changes/archive/closed/opaque", "opaque\n", executable=True
    )
    report = measure_budget(monkeypatch, tmp_path)

    expected = "source_budget_executable_unclassified:openspec/changes/archive/closed/opaque"
    assert expected in report["required_gaps"]


def test_terminal_verdict_uses_canonical_effective_lines_not_physical_cross_check(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    budget_repository(tmp_path, terminal=(2, 1_000, 1_000, 1_000, 2_000))
    report = measure_budget(monkeypatch, tmp_path, {"src/ethos/demo.py": 3})

    assert report["metrics"]["python_total"] == 2
    assert report["cross_check"]["python_total"] == 3
    assert report["enforced_metrics"]["python_product"] == 2
    assert not any("terminal_exceeded:python_product" in gap for gap in report["required_gaps"])


@pytest.mark.parametrize(
    ("category", "relative", "terminal"),
    cast(
        "tuple[tuple[str, str | None, tuple[int, int, int, int, int]], ...]",
        literal_case(
            "domain.source_budget.test_measurement:parametrize:test_python_carrier_roles_cannot_compensate_for_one_another:1"
        ),
    ),
)
def test_python_carrier_roles_cannot_compensate_for_one_another(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    category: str,
    relative: str | None,
    terminal: tuple[int, int, int, int, int],
) -> None:
    budget_repository(tmp_path, terminal=terminal)
    if relative is not None:
        tracked_budget_file(tmp_path, relative, "FIRST = 1\nSECOND = 2\n")
    report = measure_budget(monkeypatch, tmp_path)

    assert report["enforced_metrics"][category] == 2
    assert f"source_budget_terminal_exceeded:{category}:2>1" in report["required_gaps"]
    assert not any("terminal_exceeded:global_total" in gap for gap in report["required_gaps"])


def test_python_role_partition_is_complete_and_non_overlapping(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    budget_repository(tmp_path)
    for relative in ("tests/test_demo.py", "tools/demo.py", "demo.py"):
        tracked_budget_file(tmp_path, relative, "FIRST = 1\nSECOND = 2\n")
    report = measure_budget(monkeypatch, tmp_path)

    assert {role: report["metrics"][role] for role in PYTHON_CATEGORIES} == {
        "python_product": 2,
        "python_tests": 2,
        "python_tools": 2,
        "python_other": 2,
    }
    assert report["metrics"]["python_total"] == 8


def test_overlapping_python_role_patterns_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selection, _ = budget_repository(tmp_path)
    selection.write_text(
        selection.read_text().replace(
            'category = "python_product", paths = ["src/*"]',
            'category = "python_product", paths = ["src/*", "tests/*"]',
        ),
        encoding="utf-8",
    )
    tracked_budget_file(tmp_path, "tests/test_demo.py", "FIRST = 1\nSECOND = 2\n")
    report = measure_budget(monkeypatch, tmp_path)

    assert report["verdict"] == "block"
    assert (
        "source_budget_python_role_ambiguous:tests/test_demo.py:python_product,python_tests"
        in report["required_gaps"]
    )


def test_global_total_blocks_without_any_python_role_exceeding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    budget_repository(tmp_path, terminal=(1_000, 1_000, 1_000, 1_000, 1))
    report = measure_budget(monkeypatch, tmp_path)

    assert "source_budget_terminal_exceeded:global_total:" in "\n".join(report["required_gaps"])
    assert not any(
        f"terminal_exceeded:{category}" in gap
        for category in PYTHON_CATEGORIES
        for gap in report["required_gaps"]
    )


def test_extensionless_hook_is_counted_and_unknown_executable_blocks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    budget_repository(tmp_path)
    tracked_budget_file(tmp_path, ".githooks/pre-push", "#!/bin/sh\necho ready\n", executable=True)
    tracked_budget_file(tmp_path, "bin/tool", "opaque\n", executable=True)
    report = measure_budget(monkeypatch, tmp_path)

    assert report["metrics"]["shell"] >= 1
    assert "source_budget_executable_unclassified:bin/tool" in report["required_gaps"]


def test_scc_cross_check_accepts_a_stricter_physical_markdown_count(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    budget_repository(tmp_path, tolerance=(0, 0))
    report = measure_budget(
        monkeypatch,
        tmp_path,
        {
            ".config/checks/format/selection.toml": 20,
            ".ethos/rules.toml": 1,
            "src/ethos/demo.py": 2,
        },
    )

    assert report["cross_check"]["global_total"] > report["metrics"]["global_total"]
    assert not any("global_total_disagrees" in gap for gap in report["required_gaps"])


def test_scc_file_set_and_canonical_overcount_disagreement_block(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    budget_repository(tmp_path, tolerance=(0, 0))
    report = measure_budget(
        monkeypatch,
        tmp_path,
        {"src/ethos/demo.py": 4},
        include_all=False,
    )

    assert any(gap.startswith("source_budget_scc_file_missing:") for gap in report["required_gaps"])
    assert any("_disagrees:" in gap for gap in report["required_gaps"])


def test_structured_measurement_cannot_be_reduced_by_minifying_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    budget_repository(tmp_path)
    value = {"items": [{"name": f"item-{index}", "enabled": True} for index in range(20)]}
    data = tracked_budget_file(tmp_path, "system/data.json", json.dumps(value, indent=2) + "\n")
    pretty = measure_budget(monkeypatch, tmp_path)["metrics"]["json"]

    data.write_text(json.dumps(value, separators=(",", ":")) + "\n", encoding="utf-8")
    compact = source_budget.source_budget_report(tmp_path)["metrics"]["json"]

    assert compact == pretty


@pytest.mark.parametrize(
    ("category", "suffix", "first", "second"),
    cast(
        "tuple[tuple[str, str, str, str], ...]",
        literal_case(
            "domain.source_budget.test_measurement:parametrize:test_structured_measurement_is_formatting_and_order_invariant:2"
        ),
    ),
)
def test_structured_measurement_is_formatting_and_order_invariant(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    category: str,
    suffix: str,
    first: str,
    second: str,
) -> None:
    budget_repository(tmp_path)
    path = tracked_budget_file(tmp_path, f"system/data{suffix}", first)
    before = measure_budget(monkeypatch, tmp_path)["metrics"][category]

    path.write_text(second, encoding="utf-8")
    after = source_budget.source_budget_report(tmp_path)["metrics"][category]

    assert after == before


def test_yaml_measurement_accepts_native_mixed_scalar_keys(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    budget_repository(tmp_path)
    tracked_budget_file(tmp_path, "system/data.yaml", "on: enabled\ntrue: boolean-key\n")
    report = measure_budget(monkeypatch, tmp_path)

    assert report["metrics"]["yaml"] > 0
