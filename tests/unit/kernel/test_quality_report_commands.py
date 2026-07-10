from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from ethos.surface.cli.quality.reporting import ReportCommandSpec
from ethos.surface.cli.quality.reporting import build_report_result
from ethos.surface.cli.quality.reporting import conditional_actions
from ethos.surface.cli.quality.reporting import constant_actions
from ethos.surface.cli.quality.reporting import emit_report_command
from ethos.surface.cli.quality.reporting import field_summary
from ethos.surface.cli.quality.reporting import module_report


def test_report_command_spec_builds_ethos_result_from_report() -> None:
    spec = ReportCommandSpec(
        command="quality sample",
        report=lambda _root: {
            "ok": True,
            "state": "clean",
            "summary": {"item_count": 2},
            "required_gaps": [],
            "payload": "value",
        },
    )

    result = build_report_result(spec, Path("/repo"))

    assert result.command == "quality sample"
    assert result.ok is True
    assert result.state == "clean"
    assert result.summary == {"item_count": 2}
    assert result.required_gaps == ()
    assert result.data["payload"] == "value"


def test_report_command_spec_supports_summary_projection_and_next_actions() -> None:
    spec = ReportCommandSpec(
        command="quality blocked",
        report=lambda _root: {
            "ok": False,
            "state": "blocked",
            "required_gaps": ["sample_gap"],
            "count": 3,
        },
        summary=lambda report: {"count": report["count"]},
        next_actions=constant_actions("fix sample_gap"),
    )

    result = build_report_result(spec, Path("/repo"))

    assert result.ok is False
    assert result.state == "blocked"
    assert result.summary == {"count": 3}
    assert result.required_gaps == ("sample_gap",)
    assert result.next_actions == ("fix sample_gap",)


def test_report_command_spec_supports_field_summary_projection() -> None:
    spec = ReportCommandSpec(
        command="quality fields",
        report=lambda _root: {
            "ok": True,
            "state": "clean",
            "item_count": 4,
            "warning_count": 0,
        },
        summary=field_summary("item_count", "warning_count"),
    )

    result = build_report_result(spec, Path("/repo"))

    assert result.summary == {"item_count": 4, "warning_count": 0}


def test_report_command_spec_supports_conditional_next_actions() -> None:
    blocked = ReportCommandSpec(
        command="quality conditional",
        report=lambda _root: {"ok": False, "required_gaps": ["sample_gap"]},
        next_actions=conditional_actions(
            when_blocked="fix sample_gap",
            when_clean="keep monitoring",
        ),
    )
    clean = ReportCommandSpec(
        command="quality conditional",
        report=lambda _root: {"ok": True, "required_gaps": []},
        next_actions=conditional_actions(
            when_blocked="fix sample_gap",
            when_clean="keep monitoring",
        ),
    )

    assert build_report_result(blocked, Path("/repo")).next_actions == ("fix sample_gap",)
    assert build_report_result(clean, Path("/repo")).next_actions == ("keep monitoring",)


def test_emit_report_command_delegates_built_result_to_emit_function() -> None:
    emitted = []
    spec = ReportCommandSpec(
        command="quality emitted",
        report=lambda _root: {
            "ok": True,
            "state": "clean",
            "summary": {"item_count": 1},
        },
    )

    emit_report_command(spec, Path("/repo"), emit_func=emitted.append)

    assert len(emitted) == 1
    assert emitted[0].command == "quality emitted"
    assert emitted[0].summary == {"item_count": 1}


def test_simple_quality_commands_delegate_to_report_specs() -> None:
    source = Path("packages/ethos/src/ethos/surface/cli/quality/core.py").read_text(
        encoding="utf-8"
    )

    for function_name in (
        "code_size",
        "module_layout",
        "generated_artifacts",
        "command_surface",
        "projection_drift",
        "schemas",
        "command_registry",
        "docs_registry",
        "command_examples",
    ):
        start = source.index(f"def {function_name}(")
        next_function = source.find("\ndef ", start + 1)
        body = source[start:] if next_function == -1 else source[start:next_function]
        assert "emit_report_command(" in body
        assert "EthosResult(" not in body


def test_report_command_spec_is_frozen_pydantic_contract() -> None:
    spec = ReportCommandSpec(command="quality immutable", report=lambda _root: {"ok": True})

    with pytest.raises(ValidationError, match="frozen_instance"):
        spec.command = "quality changed"  # type: ignore[misc]


def test_report_command_spec_rejects_non_callable_report() -> None:
    with pytest.raises(ValidationError):
        ReportCommandSpec(command="quality invalid", report="not-callable")  # type: ignore[arg-type]


def test_module_report_resolves_latest_namespace_binding() -> None:
    calls: list[str] = []
    namespace: dict[str, object] = {"report": lambda _root: {"ok": True, "state": "first"}}
    loader = module_report(namespace, "report")
    namespace["report"] = lambda _root: (
        calls.append("second")
        or {
            "ok": True,
            "state": "second",
        }
    )

    assert loader(Path("/repo"))["state"] == "second"
    assert calls == ["second"]


def test_module_report_rejects_non_callable_namespace_binding() -> None:
    loader = module_report({"report": "not-callable"}, "report")

    with pytest.raises(TypeError, match="report binding is not callable: report"):
        loader(Path("/repo"))
