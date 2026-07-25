"""Strict declaration contracts for registry-backed facts."""

from __future__ import annotations

import tomllib
from functools import lru_cache
from pathlib import Path
from typing import NoReturn
from typing import Self

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import model_validator

from ethos_core._resources import declaration_text
from ethos_core._resources import resolve_declaration_path

COUPLING_DECLARATION_PATH = Path("system/coupling.toml")
STANDARDS_DECLARATION_PATH = Path("system/standards.toml")
_COUPLING_RESOURCE = "data/coupling.toml"
_STANDARDS_RESOURCE = "data/standards.toml"


def _raise_declaration_error(message: str) -> NoReturn:
    """Raise a stable declaration-validation error."""
    raise ValueError(message)


class AdapterAdmission(BaseModel):
    """Immutable admission record required for a profile or adapter binding."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    authority_ref: str = Field(min_length=1)
    truth_boundary: str = Field(min_length=1)
    decision_state: str = Field(min_length=1)


class OpenSpecGovernance(BaseModel):
    """Immutable OpenSpec relationship projection."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    required: bool
    layer: str = Field(min_length=1)
    capability: str = Field(min_length=1)
    execution_surface: str = Field(min_length=1)
    not_a_second_command_plane: bool


class NativeProtocols(BaseModel):
    """Immutable native protocol projection."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    layer: str = Field(min_length=1)
    formats: tuple[str, ...]
    provider_optional: bool


class CouplingBinding(BaseModel):
    """One strict, declaration-first coupling binding."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1)
    layer: str = Field(min_length=1)
    required: bool
    owns_product_semantics: bool
    adapter_replaceable: bool
    config_source: str | None = None
    config_keys: tuple[str, ...] = ()
    commands: tuple[str, ...] = ()
    forbidden_workflow_state: tuple[str, ...] = ()
    mandatory_paths: tuple[str, ...] = ()
    declared_executables: tuple[str, ...] = ()
    audit_root_bound: bool = False
    not_a_second_command_plane: bool = False
    not_product_substrate: bool = False
    required_for: tuple[str, ...] = Field(min_length=1)
    replaceability: str = Field(min_length=1)
    degradation_state: str = Field(min_length=1)
    proof_gate: str = Field(min_length=1)
    admission: AdapterAdmission | None = None
    surfaces: tuple[str, ...] = ()
    formats: tuple[str, ...] = ()
    toolchains: tuple[str, ...] = ()
    gates: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_admission_boundary(self) -> Self:
        """Require complete admission only for profile or adapter bindings."""
        is_adapter = self.layer == "profile_or_adapter_binding"
        if is_adapter and self.admission is None:
            _raise_declaration_error("adapter binding admission missing")
        if not is_adapter and self.admission is not None:
            _raise_declaration_error("binding admission outside adapter layer")
        return self

    @model_validator(mode="after")
    def validate_executable_audit_boundary(self) -> Self:
        """Require one closed active or inactive executable-audit state."""
        if self.audit_root_bound:
            if not self.mandatory_paths:
                _raise_declaration_error("executable audit root requires mandatory paths")
        elif self.mandatory_paths or self.declared_executables:
            _raise_declaration_error(
                "inactive executable audit cannot declare paths or executables"
            )
        return self

    def projection(self) -> dict[str, object]:
        """Project only declared, non-default public binding fields."""
        return self.model_dump(mode="json", exclude_none=True, exclude_defaults=True)


class CouplingDeclaration(BaseModel):
    """Validated coupling declaration with ordered pure projections."""

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    id: str = Field(min_length=1)
    schema_version: int = 1
    layers: dict[str, str] = Field(min_length=1)
    ui_projection_fields: tuple[str, ...] = ()
    product_semantic_docs: tuple[str, ...] = ()
    product_vendor_terms: tuple[str, ...] = ()
    product_host_projection_terms: tuple[str, ...] = ()
    git_native_terms: tuple[str, ...] = ()
    native_protocol_formats: tuple[str, ...] = ()
    product_repository_gates: tuple[str, ...] = ()
    openspec_governance: OpenSpecGovernance
    native_protocols: NativeProtocols
    bindings: tuple[CouplingBinding, ...] = Field(alias="binding", min_length=1)

    @model_validator(mode="after")
    def validate_bindings(self) -> Self:
        """Reject duplicate ids and records outside the declared taxonomy."""
        ids = tuple(binding.id for binding in self.bindings)
        if len(ids) != len(set(ids)):
            _raise_declaration_error("duplicate coupling binding id")
        unknown = sorted({binding.layer for binding in self.bindings} - set(self.layers))
        if unknown:
            _raise_declaration_error(f"unknown coupling binding layer:{','.join(unknown)}")
        return self

    def binding(self, binding_id: str) -> CouplingBinding:
        """Return one declared binding by stable identifier."""
        return next(binding for binding in self.bindings if binding.id == binding_id)

    def binding_projection(self) -> tuple[dict[str, object], ...]:
        """Project all binding records in declaration order."""
        return tuple(binding.projection() for binding in self.bindings)


class StandardsAdapter(BaseModel):
    """Immutable standards-adapter declaration."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1)
    mode: str = Field(min_length=1)
    lifecycle: str = Field(min_length=1)
    reference: str = Field(min_length=1)
    boundary: str = Field(min_length=1)
    input_contract: str = Field(min_length=1)
    output_contract: str = Field(min_length=1)
    fallback: str = Field(min_length=1)
    exit_strategy: str = Field(min_length=1)

    def projection(self) -> dict[str, str]:
        """Project the legacy adapter payload without duplicating its identifier."""
        return self.model_dump(mode="json", exclude={"id"})


class StandardsDeclaration(BaseModel):
    """Validated standards registry in declaration order."""

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    id: str = Field(min_length=1)
    schema_version: int = 1
    adapters: tuple[StandardsAdapter, ...] = Field(alias="adapter", min_length=1)

    @model_validator(mode="after")
    def validate_adapter_ids(self) -> Self:
        """Reject duplicate standards adapter identifiers."""
        ids = tuple(adapter.id for adapter in self.adapters)
        if len(ids) != len(set(ids)):
            _raise_declaration_error("duplicate standards adapter id")
        return self

    def registry(self) -> dict[str, dict[str, str]]:
        """Project the adapter registry in declaration order."""
        return {adapter.id: adapter.projection() for adapter in self.adapters}


def _read_coupling_declaration(path: Path) -> CouplingDeclaration:
    return CouplingDeclaration.model_validate(
        tomllib.loads(
            declaration_text(
                path,
                resource=_COUPLING_RESOURCE,
                canonical=COUPLING_DECLARATION_PATH,
            )
        )
    )


def _read_standards_declaration(path: Path) -> StandardsDeclaration:
    return StandardsDeclaration.model_validate(
        tomllib.loads(
            declaration_text(
                path,
                resource=_STANDARDS_RESOURCE,
                canonical=STANDARDS_DECLARATION_PATH,
            )
        )
    )


@lru_cache
def _default_coupling_declaration() -> CouplingDeclaration:
    return _read_coupling_declaration(
        resolve_declaration_path(
            None,
            canonical=COUPLING_DECLARATION_PATH,
            module_file=__file__,
        )
    )


@lru_cache
def _default_standards_declaration() -> StandardsDeclaration:
    return _read_standards_declaration(
        resolve_declaration_path(
            None,
            canonical=STANDARDS_DECLARATION_PATH,
            module_file=__file__,
        )
    )


def load_coupling_declaration(path: Path | str | None = None) -> CouplingDeclaration:
    """Load and validate the coupling declaration or its packaged fallback."""
    if path is None:
        return _default_coupling_declaration()
    return _read_coupling_declaration(
        resolve_declaration_path(
            path,
            canonical=COUPLING_DECLARATION_PATH,
            module_file=__file__,
        )
    )


def load_standards_declaration(path: Path | str | None = None) -> StandardsDeclaration:
    """Load and validate the standards declaration or packaged fallback."""
    if path is None:
        return _default_standards_declaration()
    return _read_standards_declaration(
        resolve_declaration_path(
            path,
            canonical=STANDARDS_DECLARATION_PATH,
            module_file=__file__,
        )
    )
