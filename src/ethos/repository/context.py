from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING

from ethos.contracts.lifecycle.declaration import load_lifecycle_declaration
from ethos.contracts.system.contracts import load_system_contract
from ethos.repository.profile import INVALID_PROFILE_ERROR
from ethos.repository.profile import load_repository_profile

if TYPE_CHECKING:
    from pathlib import Path


LIFECYCLE_COMMANDS = tuple(f"ethos {node.id}" for node in load_lifecycle_declaration().node)


def _authority_order(root: Path) -> tuple[str, ...]:
    """Load the authority order (rank-sorted sources) from system/authority.toml."""
    try:
        contract = load_system_contract(root, "authority")
    except (FileNotFoundError, ValueError):
        return ()
    order = contract.get("order")
    if not isinstance(order, list):
        return ()
    ranked = sorted(
        (item for item in order if isinstance(item, dict) and "rank" in item),
        key=lambda item: int(item["rank"]),
    )
    return tuple(str(item.get("source", "")) for item in ranked if item.get("source"))


def is_product_root(root: Path) -> bool:
    """Return True when ``root`` is the ETHOS product repository.

    The governed subject is still a repository in both cases. This predicate only
    selects the profile used by the shared governance context; it does not create a
    second subject kind or command plane.
    """
    try:
        project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    except (FileNotFoundError, KeyError, tomllib.TOMLDecodeError):
        return False
    return (
        project.get("name") == "ethos"
        and (root / "src" / "ethos").is_dir()
        and (root / "system" / "schemas" / "kernel").is_dir()
    )


def governance_profile(root: Path) -> str:
    """Return the profile for a governed repository without changing command semantics."""
    if is_product_root(root):
        return "product"
    state = load_repository_profile(root).state
    if state == "invalid":
        raise ValueError(INVALID_PROFILE_ERROR)
    return "adopter" if state == "valid" else "unbound"


def context_for_root(root: Path) -> dict[str, object]:
    """Project the governed-repository context for a product or adopted repository."""
    return governance_context(root, profile=governance_profile(root))


def governance_context(root: Path, *, profile: str) -> dict[str, object]:
    """Project repository authority and subject facts without semantic shadow models."""
    return {
        "contract": "governed_repository",
        "profile": profile,
        "repository": str(root.resolve()),
        "authority_refs": list(_authority_order(root)),
        "shared_commands": list(LIFECYCLE_COMMANDS),
        "transition_commands": list(LIFECYCLE_COMMANDS),
        "reader_projection_commands": ["ethos status"],
        "truth_boundary": "repository",
        "profile_boundary": "profile_or_adapter",
    }
