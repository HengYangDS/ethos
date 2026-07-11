"""Declaration-first compiler for read-only report command projections."""

from __future__ import annotations

from collections.abc import Callable
from collections.abc import Mapping
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from pydantic import BaseModel
from pydantic import ConfigDict

import ethos.adapters.repo.git as git_adapter
from ethos.surface.cli._base import JsonFlag
from ethos.surface.cli._base import RootOption
from ethos.surface.cli._base import emit
from ethos.surface.cli._base import resolve_root
from ethos_core.contracts.commands import CommandDeclaration
from ethos_core.contracts.commands import ReportHandlerDeclaration
from ethos_core.contracts.commands import ReportSummaryField
from ethos_core.contracts.commands import load_command_registry_declaration
from ethos_core.result import EthosResult

ReportPayload = Mapping[str, object]
ReportProvider = Callable[..., object]
ReportHandler = Callable[..., None]
ReportHandlerRegistry = Mapping[str, "CompiledReportCommand"]


class CompiledReportCommand(BaseModel):
    """Frozen command binding compiled from one report-handler declaration."""

    model_config = ConfigDict(frozen=True)

    function_name: str
    declaration: CommandDeclaration

    def make_handler(self) -> ReportHandler:
        """Bind the pure projection compiler to the CLI adapter."""
        handler = _report_handler(self.declaration)

        def emit_result(target: Path, *, json_output: bool) -> None:
            result = build_declarative_report_result(
                command=_command_name(self.declaration),
                handler=handler,
                report=_load_provider_report(handler, target),
            )
            emit(result, json_output=json_output, enforce=handler.enforce)

        if handler.bind_root:

            def command(*, root: RootOption | None = None, json_output: JsonFlag = False) -> None:
                emit_result(resolve_root(root), json_output=json_output)

        else:

            def command(*, json_output: JsonFlag = False) -> None:
                emit_result(Path.cwd(), json_output=json_output)

        command.__doc__ = self.declaration.help
        command.__name__ = self.function_name
        command.__qualname__ = self.function_name
        command.__module__ = self.declaration.import_path.rsplit(":", maxsplit=1)[0]
        return cast("ReportHandler", command)


def build_declarative_report_result(
    *,
    command: str,
    handler: ReportHandlerDeclaration,
    report: ReportPayload,
) -> EthosResult:
    """Purely project supplied report facts through an immutable declaration."""
    ok = bool(report.get("ok"))
    gaps = tuple(str(gap) for gap in _sequence(report.get("required_gaps")))
    return EthosResult(
        command=command,
        ok=ok,
        state=_state(handler, report, is_ok=ok),
        summary=_summary(handler.summary, report),
        diagnostics=_diagnostics(handler, report),
        required_gaps=gaps,
        next_actions=_next_actions(handler, report, gaps),
        governance_context=_governance_context(handler, report),
        data=_data(handler, report),
    )


def compile_report_handlers(
    *,
    declarations: Sequence[CommandDeclaration],
    import_path_prefix: str | None = None,
) -> ReportHandlerRegistry:
    """Compile all declared report command bindings in one command group."""
    return {
        _function_name(command): CompiledReportCommand(
            function_name=_function_name(command), declaration=command
        )
        for command in declarations
        if command.report_handler is not None
        and command.report_handler.provider
        and (import_path_prefix is None or command.import_path.startswith(import_path_prefix))
    }


def declared_report_handler(
    *,
    module_name: str,
    function_name: str,
    group: str = "quality",
) -> ReportHandler:
    """Compile one lazy-module command handler from the canonical registry."""
    declaration = _declared_command(
        module_name=module_name,
        function_name=function_name,
        group=group,
    )
    return CompiledReportCommand(
        function_name=function_name, declaration=declaration
    ).make_handler()


def declared_report_result(
    *,
    module_name: str,
    function_name: str,
    target: Path,
    group: str = "quality",
    provider_kwargs: Mapping[str, object] | None = None,
) -> tuple[ReportHandlerDeclaration, ReportPayload, EthosResult]:
    """Project one declared reader command while preserving its supplied facts."""
    declaration = _declared_command(
        module_name=module_name,
        function_name=function_name,
        group=group,
    )
    handler = _report_handler(declaration)
    report = _load_provider_report(handler, target, provider_kwargs=provider_kwargs)
    result = build_declarative_report_result(
        command=_command_name(declaration),
        handler=handler,
        report=report,
    )
    return handler, report, result


def _load_provider_report(
    handler: ReportHandlerDeclaration,
    root: Path,
    *,
    provider_kwargs: Mapping[str, object] | None = None,
) -> ReportPayload:
    provider = _provider(handler.provider)
    kwargs = dict(provider_kwargs or {})
    value = (
        provider(root, current_head=git_adapter.current_head(root), **kwargs)
        if handler.bind_current_head
        else provider(root, **kwargs)
    )
    if handler.provider_mode == "payload":
        return {"ok": True, "state": handler.clean_state, "payload": value}
    if not isinstance(value, Mapping):
        msg = f"report provider must return a mapping: {handler.provider}"
        raise TypeError(msg)
    return cast("ReportPayload", value)


def _provider(reference: str) -> ReportProvider:
    module_name, separator, attribute = reference.partition(":")
    if not separator or not module_name.startswith("ethos."):
        msg = f"invalid report provider: {reference}"
        raise ValueError(msg)
    module = __import__(module_name, fromlist=[attribute])
    candidate = getattr(module, attribute, None)
    if not callable(candidate):
        msg = f"report provider is not callable: {reference}"
        raise TypeError(msg)
    return cast("ReportProvider", candidate)


def _state(handler: ReportHandlerDeclaration, report: ReportPayload, *, is_ok: bool) -> str:
    if handler.state_mode == "advisory_gaps":
        return (
            "advisory"
            if is_ok and _sequence(_value_at(report, handler.advisory_gaps_path))
            else handler.clean_state
            if is_ok
            else handler.blocked_state
        )
    return str(report.get("state") or (handler.clean_state if is_ok else handler.blocked_state))


def _summary(fields: tuple[ReportSummaryField, ...], report: ReportPayload) -> dict[str, object]:
    if not fields:
        return dict(_mapping(report.get("summary")))
    return {
        field.name: _reduce(_value_at(report, field.path, field.default), field.reducer)
        for field in fields
    }


def _diagnostics(
    handler: ReportHandlerDeclaration,
    report: ReportPayload,
) -> tuple[dict[str, object], ...]:
    if handler.diagnostics_path is None:
        return ()
    return tuple(
        dict(_mapping(item)) for item in _sequence(_value_at(report, handler.diagnostics_path))
    )


def _data(handler: ReportHandlerDeclaration, report: ReportPayload) -> dict[str, object]:
    if handler.data_fields:
        return {field.name: _value_at(report, field.path) for field in handler.data_fields}
    if handler.data_path is not None:
        return dict(_mapping(_value_at(report, handler.data_path)))
    return dict(report)


def _governance_context(
    handler: ReportHandlerDeclaration,
    report: ReportPayload,
) -> dict[str, object] | None:
    if handler.governance_context_path is None:
        return None
    return dict(_mapping(_value_at(report, handler.governance_context_path)))


def _next_actions(
    handler: ReportHandlerDeclaration,
    report: ReportPayload,
    gaps: tuple[str, ...],
) -> tuple[str, ...]:
    if handler.when_blocked or handler.when_clean:
        return (handler.when_blocked if gaps else handler.when_clean,)
    if handler.next_actions_path is not None:
        return tuple(
            str(action) for action in _sequence(_value_at(report, handler.next_actions_path))
        )
    return handler.next_actions


def _reduce(value: object, reducer: str) -> object:
    if reducer == "count":
        return len(cast("Sequence[object] | Mapping[str, object]", value))
    return value


def _value_at(report: ReportPayload, path: tuple[str, ...], default: object = None) -> object:
    current: object = report
    for part in path:
        if not isinstance(current, Mapping) or part not in current:
            return default
        current = cast("Mapping[str, object]", current)[part]
    return current


def _report_handler(declaration: CommandDeclaration) -> ReportHandlerDeclaration:
    if declaration.report_handler is None or not declaration.report_handler.provider:
        msg = f"report handler declaration missing provider: {declaration.import_path}"
        raise ValueError(msg)
    return declaration.report_handler


def _declared_command(
    *,
    module_name: str,
    function_name: str,
    group: str,
) -> CommandDeclaration:
    import_path = f"{module_name}:{function_name}"
    declaration = next(
        (
            item
            for item in load_command_registry_declaration().group(group)
            if item.import_path == import_path
        ),
        None,
    )
    if declaration is None:
        msg = f"command declaration missing: {import_path}"
        raise KeyError(msg)
    return declaration


def _function_name(command: CommandDeclaration) -> str:
    return command.import_path.rsplit(":", maxsplit=1)[1]


def _command_name(command: CommandDeclaration) -> str:
    return command.name if command.group == "root" else f"{command.group} {command.name}"


def _mapping(value: object) -> Mapping[str, object]:
    return cast("Mapping[str, object]", value) if isinstance(value, Mapping) else {}


def _sequence(value: object) -> Sequence[object]:
    return value if isinstance(value, Sequence) and not isinstance(value, str) else ()
