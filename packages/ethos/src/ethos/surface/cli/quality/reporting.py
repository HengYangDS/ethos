"""Declarative helpers for simple quality report commands."""

from __future__ import annotations

from collections.abc import Callable
from collections.abc import Mapping
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

from pydantic import BaseModel
from pydantic import ConfigDict

from ethos.surface.cli._base import JsonFlag
from ethos.surface.cli._base import RootOption
from ethos.surface.cli._base import emit
from ethos.surface.cli._base import resolve_root
from ethos_core.contracts.commands import load_command_registry_declaration
from ethos_core.result import EthosResult

if TYPE_CHECKING:
    from ethos_core.contracts.commands import CommandDeclaration
    from ethos_core.contracts.commands import ReportHandlerDeclaration

ReportPayload = Mapping[str, object]
ReportLoader = Callable[[Path], ReportPayload]
ValueProjection = Callable[[ReportPayload], object]
SummaryProjection = Callable[[ReportPayload], Mapping[str, object]]
DataProjection = Callable[[ReportPayload], Mapping[str, object]]
ActionsProjection = Callable[[ReportPayload], Sequence[str]]
EmitFunction = Callable[[EthosResult], None]
StateProjection = Callable[[ReportPayload, object], str]
HeadProvider = Callable[[Path], str]
PayloadLoader = Callable[[Path], object]
ReportCommandRegistry = Mapping[str, tuple[str, "ReportCommandSpec", bool, bool]]
ReportHandlerRegistry = Mapping[str, "CompiledReportCommand"]
ReportHandler = Callable[..., None]


def module_report(
    namespace: Mapping[str, object],
    name: str,
    *,
    current_head: HeadProvider | None = None,
) -> ReportLoader:
    """Return a late-bound report loader, optionally passing current-head fact."""

    def load(root: Path) -> ReportPayload:
        report = namespace[name]
        if not callable(report):
            msg = f"report binding is not callable: {name}"
            raise TypeError(msg)
        if current_head:
            return cast("Callable[..., ReportPayload]", report)(
                root,
                current_head=current_head(root),
            )
        return cast("ReportLoader", report)(root)

    return load


def head_bound_report(
    report: Callable[..., ReportPayload], *, current_head: HeadProvider
) -> ReportLoader:
    """Return a report loader that passes an explicit current-head fact."""
    return lambda root: report(root, current_head=current_head(root))


def payload_report(loader: PayloadLoader, *, state: str = "clean") -> ReportLoader:
    """Wrap a payload loader as an always-clean report declaration."""
    return lambda root: {"ok": True, "state": state, "payload": loader(root)}


def project_summary(**fields: ValueProjection) -> SummaryProjection:
    """Compose a summary projection from declared field projections."""
    return lambda report: {name: projection(report) for name, projection in fields.items()}


def path_value(*path: str, default: object = None) -> ValueProjection:
    """Return a nested mapping value, with an optional default for missing leaves."""

    def project(report: ReportPayload) -> object:
        current: object = report
        for part in path:
            if not isinstance(current, Mapping):
                return default
            mapping = cast("Mapping[str, object]", current)
            if part not in mapping:
                return default
            current = mapping[part]
        return current

    return project


def count_at(*path: str) -> ValueProjection:
    """Return the length of a nested sequence or mapping field."""
    return lambda report: len(
        cast("Sequence[object] | Mapping[str, object]", path_value(*path)(report))
    )


def count_of(field: str) -> ValueProjection:
    """Return the length of a sequence or mapping field."""
    return count_at(field)


def field_data(field: str) -> DataProjection:
    """Project one mapping field as command result data."""
    return lambda report: cast("Mapping[str, object]", report[field])


def advisory_state(field: str) -> StateProjection:
    """Return advisory when an otherwise-clean report carries advisory gaps."""
    return lambda report, ok: (
        "advisory" if ok and _sequence(report.get(field)) else "clean" if ok else "blocked"
    )


def constant_actions(*actions: str) -> ActionsProjection:
    """Return a next-action projection that ignores report payload details."""
    return lambda _report: actions


def conditional_actions(*, when_blocked: str, when_clean: str) -> ActionsProjection:
    """Return next actions keyed by whether a report has required gaps."""
    return lambda report: (when_blocked if _sequence(report.get("required_gaps")) else when_clean,)


def field_summary(*fields: str) -> SummaryProjection:
    """Project selected report fields into an ``EthosResult`` summary."""
    return project_summary(**{field: path_value(field) for field in fields})


class ReportCommandSpec(BaseModel):
    """Declaration for a quality command that wraps a repository report."""

    model_config = ConfigDict(frozen=True)

    command: str
    report: ReportLoader
    summary: SummaryProjection | None = None
    data: DataProjection | None = None
    next_actions: ActionsProjection | None = None
    state: StateProjection | None = None
    clean_state: str = "clean"
    blocked_state: str = "blocked"


class ReportHandlerSpec(BaseModel):
    """Declaration for one native CLI handler generated from a report command."""

    model_config = ConfigDict(frozen=True)

    report: ReportCommandSpec
    enforce: bool
    bind_root: bool
    doc: str
    name: str = ""
    module: str = ""


class CompiledReportCommand(BaseModel):
    """Frozen handler plan compiled from one command declaration and report spec."""

    model_config = ConfigDict(frozen=True)

    function_name: str
    command_name: str
    handler: ReportHandlerSpec

    def make_handler(self) -> ReportHandler:
        """Compile the declared handler plan into a native Cyclopts callable."""
        return make_report_handler(self.handler)


def build_report_result(spec: ReportCommandSpec, root: Path) -> EthosResult:
    """Compile a report command declaration into an ``EthosResult``."""
    report = spec.report(root)
    ok = bool(report.get("ok"))
    state = (
        spec.state(report, ok)
        if spec.state
        else str(report.get("state") or (spec.clean_state if ok else spec.blocked_state))
    )
    required_gaps = tuple(str(gap) for gap in _sequence(report.get("required_gaps")))
    summary = dict(spec.summary(report) if spec.summary else _mapping(report.get("summary")))
    next_actions = tuple(
        str(action) for action in (spec.next_actions(report) if spec.next_actions else ())
    )
    data = dict(spec.data(report) if spec.data else report)
    return EthosResult(
        command=spec.command,
        ok=ok,
        state=state,
        summary=summary,
        required_gaps=required_gaps,
        next_actions=next_actions,
        data=data,
    )


def emit_report_command(
    spec: ReportCommandSpec,
    root: Path,
    *,
    emit_func: EmitFunction,
) -> None:
    """Emit a simple report command from its declaration."""
    emit_func(build_report_result(spec, root))


def make_report_handler(spec: ReportHandlerSpec) -> ReportHandler:
    """Compile a report specification into a native Cyclopts handler.

    This is the reusable command-envelope compiler for simple report commands:
    command declarations own enforce/bind-root/help metadata, while the report
    spec owns the pure report-to-``EthosResult`` projection.
    """

    def emit_spec(target: Path, *, json_output: bool) -> None:
        emit_report_command(
            spec.report,
            target,
            emit_func=lambda result: emit(result, json_output=json_output, enforce=spec.enforce),
        )

    if spec.bind_root:

        def handler(*, root: RootOption | None = None, json_output: JsonFlag = False) -> None:
            emit_spec(resolve_root(root), json_output=json_output)

    else:

        def handler(*, json_output: JsonFlag = False) -> None:
            emit_spec(Path.cwd(), json_output=json_output)

    handler.__doc__ = spec.doc
    if spec.name:
        handler.__name__ = spec.name
        handler.__qualname__ = spec.name
    if spec.module:
        handler.__module__ = spec.module
    return cast("ReportHandler", handler)


def declared_report_handler(
    *,
    module_name: str,
    function_name: str,
    spec_name: str,
    spec: ReportCommandSpec,
    group: str = "quality",
) -> ReportHandler:
    """Compile one command handler from ``system/commands.toml`` metadata."""
    return declared_report_handler_plan(
        module_name=module_name,
        function_name=function_name,
        spec_name=spec_name,
        spec=spec,
        group=group,
    ).make_handler()


def declared_report_handler_plan(
    *,
    module_name: str,
    function_name: str,
    spec_name: str,
    spec: ReportCommandSpec,
    group: str = "quality",
) -> CompiledReportCommand:
    """Compile one command declaration into a frozen report handler plan."""
    import_path = f"{module_name}:{function_name}"
    declaration = _declared_command(import_path=import_path, group=group)
    if declaration.report_handler is None:
        msg = f"report handler declaration missing: {import_path}"
        raise KeyError(msg)
    if declaration.report_handler.spec != spec_name:
        msg = (
            "report handler spec mismatch: "
            f"{import_path} declares {declaration.report_handler.spec}, expected {spec_name}"
        )
        raise ValueError(msg)
    return _compiled_report_command(
        declaration=declaration,
        spec=spec,
        function_name=function_name,
        module_name=module_name,
    )


def compile_report_handlers(
    *,
    declarations: Sequence[CommandDeclaration],
    specs: Mapping[str, ReportCommandSpec],
    import_path_prefix: str | None = None,
) -> ReportHandlerRegistry:
    """Compile report command declarations into frozen native handler plans."""
    return {
        _function_name(command): _compiled_report_command(
            declaration=command,
            spec=specs[_report_spec_name(command)],
            function_name=_function_name(command),
            module_name=_module_name(command),
        )
        for command in _report_handler_declarations(declarations, import_path_prefix)
    }


def compile_report_commands(
    *,
    declarations: Sequence[CommandDeclaration],
    specs: Mapping[str, ReportCommandSpec],
    import_path_prefix: str | None = None,
) -> ReportCommandRegistry:
    """Compile quality command declarations into native handler metadata."""
    return {
        function_name: (
            command.command_name,
            command.handler.report,
            command.handler.enforce,
            command.handler.bind_root,
        )
        for function_name, command in compile_report_handlers(
            declarations=declarations,
            specs=specs,
            import_path_prefix=import_path_prefix,
        ).items()
    }


def _report_handler_declarations(
    declarations: Sequence[CommandDeclaration],
    import_path_prefix: str | None,
) -> tuple[CommandDeclaration, ...]:
    return tuple(
        command
        for command in declarations
        if command.report_handler is not None
        and (import_path_prefix is None or command.import_path.startswith(import_path_prefix))
    )


def _function_name(command: CommandDeclaration) -> str:
    return command.import_path.rsplit(":", maxsplit=1)[1]


def _module_name(command: CommandDeclaration) -> str:
    return command.import_path.rsplit(":", maxsplit=1)[0]


def _report_spec_name(command: CommandDeclaration) -> str:
    return cast("ReportHandlerDeclaration", command.report_handler).spec


def _declared_command(*, import_path: str, group: str) -> CommandDeclaration:
    declaration = next(
        (
            command
            for command in load_command_registry_declaration().group(group)
            if command.import_path == import_path
        ),
        None,
    )
    if declaration is None:
        msg = f"command declaration missing: {import_path}"
        raise KeyError(msg)
    return declaration


def _compiled_report_command(
    *,
    declaration: CommandDeclaration,
    spec: ReportCommandSpec,
    function_name: str,
    module_name: str,
) -> CompiledReportCommand:
    report_handler = cast("ReportHandlerDeclaration", declaration.report_handler)
    if spec.command != f"{declaration.group} {declaration.name}":
        msg = f"report command mismatch: {spec.command} != {declaration.group} {declaration.name}"
        raise ValueError(msg)
    return CompiledReportCommand(
        function_name=function_name,
        command_name=declaration.name,
        handler=ReportHandlerSpec(
            report=spec,
            enforce=report_handler.enforce,
            bind_root=report_handler.bind_root,
            doc=declaration.help,
            name=function_name,
            module=module_name,
        ),
    )


def _mapping(value: object) -> Mapping[str, object]:
    return cast("Mapping[str, object]", value) if isinstance(value, Mapping) else {}


def _sequence(value: object) -> Sequence[object]:
    return value if isinstance(value, Sequence) and not isinstance(value, str) else ()
