"""Typed declarations for ETHOS-owned OpenSpec companion configuration."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Annotated

from pydantic import BaseModel
from pydantic import BeforeValidator
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator

_INVALID_METADATA_FILENAME = "spec metadata must be an exact native data filename"
_INVALID_METADATA_AUTHORITY = "metadata authority must be a repository-relative file"
_DOT_SEGMENT_METADATA_AUTHORITY = "metadata authority must not contain dot segments"
_DUPLICATE_METADATA_FILENAMES = "spec metadata filenames must be unique within their placement"


class SpecMetadata(BaseModel):
    """Bind one supplemental data filename to its existing native authority."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    file_name: str
    authority_ref: str

    @field_validator("file_name")
    @classmethod
    def validate_file_name(cls, value: str) -> str:
        path = PurePosixPath(value)
        if (
            not _native_metadata_path_text(value)
            or value != path.name
            or path.suffix not in {".toml", ".json", ".yaml", ".yml"}
        ):
            raise ValueError(_INVALID_METADATA_FILENAME)
        return value

    @field_validator("authority_ref")
    @classmethod
    def validate_authority_ref(cls, value: str) -> str:
        if not _native_metadata_path_text(value) or value.startswith(("/", "./")):
            raise ValueError(_INVALID_METADATA_AUTHORITY)
        if any(part in {"", ".", ".."} for part in value.split("/")):
            raise ValueError(_DOT_SEGMENT_METADATA_AUTHORITY)
        return value


def _native_metadata_path_text(value: str) -> bool:
    """Require a portable literal path, never a pattern or ambiguous control sequence."""
    return bool(value) and not any(
        character.isspace() or not character.isprintable() or character in '\\:*?"<>|[]'
        for character in value
    )


_DUPLICATE_MATERIAL_PATHS = "material paths must be unique"
_INVALID_SCOPE_PATTERN = "scope path must be a non-empty relative POSIX pattern"
_DOT_SEGMENT_SCOPE_PATTERN = "scope path must not contain dot segments"


class OpenSpecPolicy(BaseModel):
    """Profile-owned material-path declaration for one repository."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    material_paths: Annotated[
        tuple[str, ...],
        BeforeValidator(lambda value: tuple(value) if isinstance(value, list) else value),
    ] = Field(min_length=1)
    capability_metadata: Annotated[
        tuple[SpecMetadata, ...],
        BeforeValidator(lambda value: tuple(value) if isinstance(value, list) else value),
    ] = ()
    specs_root_metadata: Annotated[
        tuple[SpecMetadata, ...],
        BeforeValidator(lambda value: tuple(value) if isinstance(value, list) else value),
    ] = ()

    @field_validator("capability_metadata", "specs_root_metadata")
    @classmethod
    def validate_metadata(cls, value: tuple[SpecMetadata, ...]) -> tuple[SpecMetadata, ...]:
        if len({item.file_name for item in value}) != len(value):
            raise ValueError(_DUPLICATE_METADATA_FILENAMES)
        return value

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
