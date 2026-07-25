"""Typed declaration contract for ETHOS command registries."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import model_validator

from ethos_core._resources import declaration_text
from ethos_core._resources import resolve_declaration_path

DECLARATION_PATH = Path("system/commands.toml")
_DECLARATION_RESOURCE = "data/commands.toml"
_DUPLICATE_COMMAND_NAME = "duplicate command name"


class CommandSets(BaseModel):
    """Immutable command classifications shared by repository projections."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    public_workflow: tuple[str, ...]
    setup: tuple[str, ...]
    maintainer_reference: tuple[str, ...]
    governance_gate: tuple[str, ...]
    local_closeout: tuple[str, ...]
    evidence_refresh: tuple[str, ...]
    retired_public_roots: tuple[str, ...]
    retired_public_command_prefixes: tuple[str, ...]
    historical_exempt_roots: tuple[str, ...]


class ReportSummaryField(BaseModel):
    """One immutable, pure field projection in a report command summary."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1)
    path: tuple[str, ...] = ()
    reducer: Literal["value", "count"] = "value"
    default: str | int | float | bool | None = None


class ReportDataField(BaseModel):
    """One immutable named field selected into a report result data payload."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1)
    path: tuple[str, ...] = ()


class ReportHandlerDeclaration(BaseModel):
    """One immutable reader projection compiler declaration."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    provider: str = Field(default="", pattern=r"^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*:[A-Za-z_]\w*$")
    provider_mode: Literal["report", "payload"] = "report"
    bind_current_head: bool = False
    summary: tuple[ReportSummaryField, ...] = ()
    diagnostics_path: tuple[str, ...] | None = None
    data_path: tuple[str, ...] | None = None
    data_fields: tuple[ReportDataField, ...] = ()
    governance_context_path: tuple[str, ...] | None = None
    state_mode: Literal["report", "advisory_gaps"] = "report"
    advisory_gaps_path: tuple[str, ...] = ("advisory_gaps",)
    clean_state: str = "clean"
    blocked_state: str = "blocked"
    next_actions: tuple[str, ...] = ()
    next_actions_path: tuple[str, ...] | None = None
    when_blocked: str = ""
    when_clean: str = ""
    enforce: bool = False
    bind_root: bool = True


class ToolHandlerDeclaration(BaseModel):
    """One immutable quality-tool binding compiled from the command registry."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    gate_id: str = Field(min_length=1)
    tool: str = Field(min_length=1)
    command: tuple[str, ...] = Field(min_length=1)
    file_globs: tuple[str, ...] = ()
    exclude_prefixes: tuple[str, ...] = ()
    append_files: bool = True


class CommandDeclaration(BaseModel):
    """One immutable native Cyclopts command declaration."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1)
    group: str = Field(min_length=1)
    import_path: str = Field(pattern=r"^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*:[A-Za-z_]\w*$")
    help: str = Field(min_length=1)
    show: bool = True
    report_handler: ReportHandlerDeclaration | None = None
    tool_handler: ToolHandlerDeclaration | None = None


class CommandRegistryDeclaration(BaseModel):
    """Validated source declaration for command sets and lazy handlers."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1)
    schema_version: int = 1
    source_refs: tuple[str, ...] = ()
    actions: dict[str, tuple[str, ...]]
    sets: CommandSets
    commands: tuple[CommandDeclaration, ...]

    @model_validator(mode="after")
    def validate_unique_names(self) -> CommandRegistryDeclaration:
        """Reject duplicate command names within one command group."""
        keys = tuple((command.group, command.name) for command in self.commands)
        if len(keys) != len(set(keys)):
            raise ValueError(_DUPLICATE_COMMAND_NAME)
        return self

    def group(self, name: str) -> tuple[CommandDeclaration, ...]:
        """Project a command group in declaration order."""
        return tuple(command for command in self.commands if command.group == name)


def load_command_registry_declaration(
    path: Path | str | None = None,
) -> CommandRegistryDeclaration:
    """Load and validate the tracked command registry declaration."""
    declaration_path = resolve_declaration_path(
        path, canonical=DECLARATION_PATH, module_file=__file__
    )
    return CommandRegistryDeclaration.model_validate(
        tomllib.loads(
            declaration_text(
                declaration_path,
                resource=_DECLARATION_RESOURCE,
                canonical=DECLARATION_PATH,
            )
        )
    )
