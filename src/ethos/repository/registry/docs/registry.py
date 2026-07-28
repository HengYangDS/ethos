"""Documentation registry metadata and taxonomy vocabulary."""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING

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
    "ledger",
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


def front_matter(path: Path) -> dict[str, str]:
    """Parse the compact front matter fields used by docs registry entries."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    header = text.split("---", 2)[1]
    values: dict[str, str] = {}
    current_key = ""
    nested: list[str] = []
    for line in header.splitlines():
        if line.startswith((" ", "\t")) and current_key:
            nested.append(line.strip())
            continue
        if current_key and nested:
            values[current_key] = "; ".join(nested)
            nested = []
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        current_key = key.strip()
        values[current_key] = value.strip()
    if current_key and nested:
        values[current_key] = "; ".join(nested)
    return values


def build_docs_registry(root: Path) -> list[dict[str, str]]:
    """Build the repository documentation registry from front matter."""
    entries = []
    for path in sorted(docs_root(root).rglob("*.md")):
        metadata = front_matter(path)
        relative = path.relative_to(root).as_posix()
        entries.append(
            {
                "path": relative,
                "subject": metadata.get("subject", ""),
                "role": metadata.get("role", ""),
                "state": metadata.get("state", ""),
                "relations": metadata.get("relations", ""),
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
