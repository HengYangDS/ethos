"""Typed declaration contract for ETHOS command registries."""

from __future__ import annotations

import tomllib
from importlib import resources
from pathlib import Path
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import model_validator

DECLARATION_PATH = Path("system/commands.toml")
_DECLARATION_RESOURCE = "data/commands.toml"
_DUPLICATE_COMMAND_NAME = "duplicate command name"


class CommandSets(BaseModel):
    """Immutable command classifications shared by repository projections."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    public_workflow: tuple[str, ...]
    reader_view: tuple[str, ...]
    scorecard: tuple[str, ...]
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
    """One immutable quality report handler compiler declaration."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    provider: str = Field(default="", pattern=r"^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*:[A-Za-z_]\w*$")
    provider_mode: Literal["report", "payload"] = "report"
    bind_current_head: bool = False
    summary: tuple[ReportSummaryField, ...] = ()
    data_path: tuple[str, ...] | None = None
    data_fields: tuple[ReportDataField, ...] = ()
    state_mode: Literal["report", "advisory_gaps"] = "report"
    advisory_gaps_path: tuple[str, ...] = ("advisory_gaps",)
    clean_state: str = "clean"
    blocked_state: str = "blocked"
    next_actions: tuple[str, ...] = ()
    when_blocked: str = ""
    when_clean: str = ""
    enforce: bool = False
    bind_root: bool = True


class CommandDeclaration(BaseModel):
    """One immutable native Cyclopts command declaration."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1)
    group: str = Field(min_length=1)
    import_path: str = Field(pattern=r"^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*:[A-Za-z_]\w*$")
    help: str = Field(min_length=1)
    show: bool = True
    report_handler: ReportHandlerDeclaration | None = None


class CommandRegistryDeclaration(BaseModel):
    """Validated source declaration for command sets and lazy handlers."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1)
    schema_version: int = 1
    source_refs: tuple[str, ...] = ()
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


def _default_declaration_path() -> Path:
    cwd_candidate = Path.cwd() / DECLARATION_PATH
    if cwd_candidate.exists():
        return cwd_candidate
    for parent in Path(__file__).resolve().parents:
        candidate = parent / DECLARATION_PATH
        if candidate.exists():
            return candidate
    return DECLARATION_PATH


def _declaration_text(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8")
    return resources.files("ethos_core").joinpath(_DECLARATION_RESOURCE).read_text(encoding="utf-8")


def load_command_registry_declaration(
    path: Path | str | None = None,
) -> CommandRegistryDeclaration:
    """Load and validate the tracked command registry declaration."""
    declaration_path = Path(path) if path is not None else _default_declaration_path()
    return CommandRegistryDeclaration.model_validate(
        tomllib.loads(_declaration_text(declaration_path))
    )
