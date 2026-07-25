"""Documentation registry metadata and taxonomy vocabulary."""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING

from ethos.contracts.docs.topology import ROLE_VALUES
from ethos.contracts.docs.topology import STATE_VALUES

if TYPE_CHECKING:
    from pathlib import Path

REQUIRED_FIELDS = ("subject", "role", "state", "relations")
VISIBLE_SECTION_LABELS = ("Status:", "Purpose:", "See also:")
# SSOT: derive the allowed-state vocabulary from the topology contract rather
# than re-listing it here, so a state added to STATE_VALUES cannot silently
# diverge from what the docs-registry gate accepts.
DEFAULT_ALLOWED_STATES = frozenset(STATE_VALUES)
# SSOT: the kernel role vocabulary comes from the contract; the taxonomy may add
# repo-specific roles on top (union), but never remove a kernel role.
DEFAULT_ALLOWED_ROLES = frozenset(ROLE_VALUES)


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
    entries: list[dict[str, str]] = []
    doc_paths = list((root / "docs").rglob("*.md"))
    doc_paths.extend((root / "distributions").glob("*/README.md"))
    for path in sorted(doc_paths):
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
    """Read docs taxonomy config, returning an empty mapping on absence or parse failure."""
    path = root / "docs" / "_meta" / "taxonomy.toml"
    if not path.exists():
        return {}
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return {}


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
    return configured or set(DEFAULT_ALLOWED_STATES)


def allowed_roles(root: Path) -> set[str]:
    """Return kernel roles plus taxonomy extension roles."""
    return set(DEFAULT_ALLOWED_ROLES) | taxonomy_allowed(root, "roles")
