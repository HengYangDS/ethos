from __future__ import annotations

import pytest

from ethos.surface.cli.quality import reporting
from ethos.surface.cli.quality.reporting import CompiledReportCommand
from ethos.surface.cli.quality.reporting import build_declarative_report_result
from ethos.surface.cli.quality.reporting import compile_report_handlers
from ethos.surface.cli.quality.reporting import declared_report_handler
from ethos.surface.cli.results.tool import compile_quality_tool_handlers
from ethos_core.contracts.commands import CommandDeclaration
from ethos_core.contracts.commands import ReportHandlerDeclaration
from ethos_core.contracts.commands import ReportSummaryField
from ethos_core.contracts.commands import ToolHandlerDeclaration
from ethos_core.contracts.commands import load_command_registry_declaration


def test_declarative_report_projection_compiles_paths_counts_and_actions() -> None:
    handler = ReportHandlerDeclaration(
        provider="ethos.test:sample",
        summary=(ReportSummaryField(name="item_count", path=("items",), reducer="count"),),
        diagnostics_path=("diagnostics",),
        data_path=("payload",),
        governance_context_path=("governance_context",),
        next_actions_path=("next_actions",),
    )

    result = build_declarative_report_result(
        command="quality sample",
        handler=handler,
        report={
            "ok": True,
            "items": ["a", "b"],
            "diagnostics": [{"kind": "sample"}],
            "payload": {"id": "sample"},
            "governance_context": {"profile": "product"},
            "next_actions": ["ethos prove --json"],
        },
    )

    assert result.to_dict()["summary"] == {"item_count": 2}
    assert result.to_dict()["diagnostics"] == [{"kind": "sample"}]
    assert result.to_dict()["next_actions"] == ["ethos prove --json"]
    assert result.to_dict()["governance_context"] == {"profile": "product"}
    assert result.to_dict()["data"] == {"id": "sample"}


def test_declarative_projection_selects_advisory_state_and_conditional_actions() -> None:
    handler = ReportHandlerDeclaration(
        provider="ethos.test:sample",
        state_mode="advisory_gaps",
        when_blocked="repair",
        when_clean="prove",
    )

    advisory = build_declarative_report_result(
        command="quality sample",
        handler=handler,
        report={"ok": True, "advisory_gaps": ["observe"]},
    )
    blocked = build_declarative_report_result(
        command="quality sample",
        handler=handler,
        report={"ok": False, "required_gaps": ["repair"]},
    )

    assert advisory.state == "advisory"
    assert advisory.next_actions == ("prove",)
    assert blocked.state == "blocked"
    assert blocked.next_actions == ("repair",)


def test_report_handler_declarations_compile_without_python_specs() -> None:
    declaration = load_command_registry_declaration()
    commands = declaration.group("quality")
    handlers = compile_report_handlers(declarations=commands)
    expected = {
        command.import_path.rsplit(":", maxsplit=1)[1]
        for command in commands
        if command.report_handler is not None
    }

    assert set(handlers) == expected
    assert all(isinstance(handler, CompiledReportCommand) for handler in handlers.values())
    assert all(handler.declaration.report_handler.provider for handler in handlers.values())
    assert "performance" not in handlers


def test_tool_handler_declarations_compile_from_the_command_registry() -> None:
    commands = load_command_registry_declaration().group("quality")
    handlers = compile_quality_tool_handlers(declarations=commands)

    assert set(handlers) == {
        "markdown_links",
        "npm_quality",
        "shell_quality",
        "toml_quality",
        "yaml_quality",
    }
    assert next(
        command for command in commands if command.name == "markdown-links"
    ).tool_handler == ToolHandlerDeclaration(
        gate_id="markdown-links",
        tool="lychee",
        command=("lychee", "--config", ".config/checks/lychee/lychee.toml", "--no-progress"),
        file_globs=("*.md",),
        exclude_prefixes=("evidence/", "docs/archive/"),
    )


def test_compiled_report_commands_keep_provider_reference_in_the_declaration() -> None:
    assert "provider" not in CompiledReportCommand.model_fields
    assert not hasattr(CompiledReportCommand, "with_provider")


def test_declared_report_handler_rejects_missing_declaration() -> None:
    with pytest.raises(KeyError, match="command declaration missing"):
        declared_report_handler(
            module_name="ethos.surface.cli.quality.core",
            function_name="missing_report",
        )


@pytest.mark.parametrize(
    ("reference", "expected_error"),
    [
        ("not.ethos:sample", "invalid report provider"),
        ("ethos.surface.cli.quality.reporting:not_callable", "not callable"),
    ],
)
def test_provider_resolution_rejects_invalid_or_non_callable_references(
    monkeypatch: pytest.MonkeyPatch, reference: str, expected_error: str
) -> None:
    monkeypatch.setattr(reporting, "not_callable", object(), raising=False)

    with pytest.raises((TypeError, ValueError), match=expected_error):
        reporting._provider(reference)


def test_report_provider_rejects_non_mapping_report(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(reporting, "non_mapping_report", lambda _root: object(), raising=False)
    command = CommandDeclaration(
        name="sample",
        group="quality",
        import_path="ethos.surface.cli.quality.reporting:sample",
        help="Sample report.",
        report_handler=ReportHandlerDeclaration(
            provider="ethos.surface.cli.quality.reporting:non_mapping_report"
        ),
    )

    with pytest.raises(TypeError, match="report provider must return a mapping"):
        CompiledReportCommand(function_name="sample", declaration=command).make_handler()()


def test_report_handler_rejects_declaration_without_provider() -> None:
    command = CommandDeclaration(
        name="sample",
        group="quality",
        import_path="ethos.surface.cli.quality.reporting:sample",
        help="Sample report.",
        report_handler=ReportHandlerDeclaration(),
    )

    with pytest.raises(ValueError, match="missing provider"):
        CompiledReportCommand(function_name="sample", declaration=command).make_handler()
