"""Typed declarations for ETHOS-owned OpenSpec companion configuration."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Annotated
from typing import Literal

from pydantic import BaseModel
from pydantic import BeforeValidator
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator

_DUPLICATE_SCOPE_PATHS = "scope paths must be unique"
_DUPLICATE_MATERIAL_PATHS = "material paths must be unique"
_INVALID_SCOPE_PATTERN = "scope path must be a non-empty relative POSIX pattern"
_DOT_SEGMENT_SCOPE_PATTERN = "scope path must not contain dot segments"


class _OpenSpecScopeModel(BaseModel):
    """Strict immutable base for portable OpenSpec scope declarations."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class ChangeScopeDeclaration(_OpenSpecScopeModel):
    """ETHOS companion scope for one unarchived OpenSpec Change."""

    schema_version: Literal[1]
    paths: tuple[str, ...] = Field(min_length=1)

    @field_validator("paths")
    @classmethod
    def normalize_paths(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        """Reject ambiguous or escaping repository-relative glob patterns."""
        normalized = tuple(_scope_pattern(path) for path in value)
        if len(set(normalized)) != len(normalized):
            raise ValueError(_DUPLICATE_SCOPE_PATHS)
        return normalized


class AdopterOpenSpecPolicy(BaseModel):
    """The profile-owned material-path declaration for one adopted repository."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    material_paths: Annotated[
        tuple[str, ...],
        BeforeValidator(lambda value: tuple(value) if isinstance(value, list) else value),
    ] = Field(min_length=1)

    @field_validator("material_paths")
    @classmethod
    def normalize_material_paths(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        """Compile profile material paths through the same portable pattern rules."""
        normalized = tuple(_scope_pattern(path) for path in value)
        if len(set(normalized)) != len(normalized):
            raise ValueError(_DUPLICATE_MATERIAL_PATHS)
        return normalized


def _scope_pattern(value: str) -> str:
    """Return one safe repository-relative POSIX glob pattern."""
    pattern = value.strip()
    if not pattern or pattern.startswith("/") or "\\" in pattern:
        raise ValueError(_INVALID_SCOPE_PATTERN)
    parts = PurePosixPath(pattern).parts
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError(_DOT_SEGMENT_SCOPE_PATTERN)
    return pattern
