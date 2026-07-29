from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING

from ethos.repository.profile import INVALID_PROFILE_ERROR
from ethos.repository.profile import load_repository_profile

if TYPE_CHECKING:
    from pathlib import Path

_AUTHORITY_QUERY_AXES = ("subject", "predicate", "scope", "plane", "validity", "context")
_CURRENTNESS_REQUIREMENTS = (
    "integrity",
    "declared_authority",
    "binding_match",
    "validity",
    "no_more_specific_active_owner",
)


def _contextual_authority(root: Path) -> dict[str, object]:
    """Project the executable authority query contract without inventing truth."""
    contract = tomllib.loads((root / "system" / "authority.toml").read_text(encoding="utf-8"))
    query = contract.get("query")
    currentness = contract.get("currentness")
    resolution = contract.get("resolution")
    if not all(isinstance(value, dict) for value in (query, currentness, resolution)):
        raise ValueError("authority_contract_invalid")
    axes = query.get("required")
    requirements = currentness.get("requires")
    if tuple(axes) != _AUTHORITY_QUERY_AXES or tuple(requirements) != _CURRENTNESS_REQUIREMENTS:
        raise ValueError("authority_contract_query_axes_invalid")
    if contract.get("resolver") != "contextual" or query.get("unknown_verdict") != "block":
        raise ValueError("authority_contract_resolution_invalid")
    if any(
        currentness.get(key) is not False
        for key in ("history_is_current", "projection_is_authority", "adapter_is_authority")
    ):
        raise ValueError("authority_contract_currentness_invalid")
    if (
        resolution.get("conflict") != "block"
        or resolution.get("novel_semantics") != "model_gap"
        or resolution.get("more_specific_owner") != "wins_only_within_same_query"
    ):
        raise ValueError("authority_contract_resolution_invalid")
    return {
        "contract_ref": "system/authority.toml",
        "resolver": "contextual",
        "query_axes": list(_AUTHORITY_QUERY_AXES),
        "unknown_verdict": "block",
        "currentness_requirements": list(_CURRENTNESS_REQUIREMENTS),
        "conflict_verdict": "block",
        "novel_semantics": "model_gap",
    }


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
    """Project repository context and its executable contextual-authority query."""
    return {
        "contract": "governed_repository",
        "profile": profile,
        "repository": str(root.resolve()),
        "authority": _contextual_authority(root),
        "reader_projection_commands": ["ethos status"],
        "truth_boundary": "repository",
        "profile_boundary": "profile_or_adapter",
    }
