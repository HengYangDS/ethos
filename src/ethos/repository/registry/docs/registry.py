"""Documentation registry metadata and taxonomy vocabulary."""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING
from typing import Any
from typing import override

import yaml
from yaml.constructor import ConstructorError

from ethos.repository.profile import profile_root

if TYPE_CHECKING:
    from pathlib import Path

DEFAULT_STATE_VALUES = (
    "canonical",
    "active",
    "planned",
    "experimental",
    "superseded",
    "archived",
)
DEFAULT_ROLE_VALUES = (
    "index",
    "explanation",
    "reference",
    "decision",
    "policy",
    "evidence",
    "history",
    "template",
    "plan",
    "research",
    "findings",
    "progress",
    "how-to",
)

REQUIRED_FIELDS = ("subject", "role", "state", "relations")
VISIBLE_SECTION_LABELS = ("Status:", "Purpose:", "See also:")
DEFAULT_ALLOWED_STATES = frozenset(DEFAULT_STATE_VALUES)
DEFAULT_ALLOWED_ROLES = frozenset(DEFAULT_ROLE_VALUES)
RESERVED_STATE_VALUES = frozenset({"current", "future"})
TAXONOMY_INVALID = "docs_taxonomy_invalid"


def docs_root(root: Path) -> Path:
    """Resolve the one adopter-declared documentation root."""
    return profile_root(root, "docs")


class _UniqueSafeLoader(yaml.SafeLoader):
    """Use native safe YAML while rejecting duplicate explicit mapping keys."""

    @override
    def construct_mapping(self, node: yaml.MappingNode, deep: bool = False) -> dict:
        keys = [
            self.construct_object(key, deep=deep)
            for key, _value in node.value
            if key.tag != "tag:yaml.org,2002:merge"
        ]
        if any(key in keys[:index] for index, key in enumerate(keys)):
            message = "duplicate mapping key"
            raise ConstructorError(None, None, message, node.start_mark)
        return super().construct_mapping(node, deep=deep)


def front_matter(path: Path) -> dict[str, Any]:
    """Read native YAML metadata without flattening its structured values."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        return {}
    try:
        end = lines.index("---", 1)
        payload = yaml.load("\n".join(lines[1:end]), Loader=_UniqueSafeLoader)
    except (ValueError, yaml.YAMLError) as exc:
        message = f"docs_metadata_invalid:{path}:syntax"
        raise ValueError(message) from exc
    if not isinstance(payload, dict) or not all(isinstance(key, str) for key in payload):
        message = f"docs_metadata_invalid:{path}:mapping"
        raise ValueError(message)
    return payload


def build_docs_registry(root: Path) -> list[dict[str, Any]]:
    """Retain typed metadata and reject invalid native declarations."""
    root = root.resolve()
    entries = []
    for path in sorted(docs_root(root).rglob("*.md")):
        relative = path.relative_to(root).as_posix()
        try:
            metadata = front_matter(path)
        except ValueError as exc:
            message = f"docs_metadata_invalid:{relative}:syntax"
            raise ValueError(message) from exc
        for field in ("subject", "role", "state"):
            if field in metadata and not isinstance(metadata[field], str):
                message = f"docs_metadata_invalid:{relative}:{field}"
                raise ValueError(message)
        relations = metadata.get("relations", {})
        if not isinstance(relations, dict) or any(
            not isinstance(key, str)
            or not key
            or not (
                isinstance(value, str)
                or (isinstance(value, list) and all(isinstance(item, str) for item in value))
            )
            for key, value in relations.items()
        ):
            message = f"docs_metadata_invalid:{relative}:relations"
            raise ValueError(message)
        entries.append(
            {
                "path": relative,
                **{field: metadata[field] for field in REQUIRED_FIELDS if field in metadata},
            }
        )
    return entries


def taxonomy(root: Path) -> dict[str, object]:
    """Read the optional taxonomy, failing closed when the declaration is invalid."""
    path = docs_root(root) / "_meta" / "taxonomy.toml"
    if not path.exists():
        return {}
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        relative = path.relative_to(root).as_posix()
        gap = f"{TAXONOMY_INVALID}:{relative}"
        raise ValueError(gap) from exc


def taxonomy_allowed(root: Path, section: str) -> set[str]:
    """Return the `allowed` string list under a taxonomy section."""
    payload = taxonomy(root)
    block = payload.get(section)
    if not isinstance(block, dict):
        return set()
    allowed = block.get("allowed")
    if not isinstance(allowed, list):
        return set()
    return {item for item in allowed if isinstance(item, str)}


def allowed_states(root: Path) -> set[str]:
    """Return allowed docs states from taxonomy or the kernel contract default."""
    configured = taxonomy_allowed(root, "states")
    return (configured or set(DEFAULT_ALLOWED_STATES)) - RESERVED_STATE_VALUES


def allowed_roles(root: Path) -> set[str]:
    """Return kernel roles plus taxonomy extension roles."""
    return set(DEFAULT_ALLOWED_ROLES) | taxonomy_allowed(root, "roles")
