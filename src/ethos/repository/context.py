from __future__ import annotations

import tomllib
from pathlib import Path

from ethos._resources import declaration_text
from ethos.repository.profile import INVALID_PROFILE_ERROR
from ethos.repository.profile import load_repository_profile

_AUTHORITY_QUERY_AXES = ("subject", "predicate", "scope", "plane", "validity", "context")
_CURRENTNESS_REQUIREMENTS = (
    "integrity",
    "declared_authority",
    "binding_match",
    "validity",
    "no_more_specific_active_owner",
)
_AUTHORITY_PATH = Path("system/authority.toml")
_AUTHORITY_RESOURCE = "data/authority.toml"


def _contextual_authority(root: Path) -> dict[str, object]:
    """Project the executable authority query contract without inventing truth."""
    contract = tomllib.loads(
        declaration_text(
            root / _AUTHORITY_PATH,
            resource=_AUTHORITY_RESOURCE,
            canonical=_AUTHORITY_PATH,
        )
    )
    query = contract.get("query")
    currentness = contract.get("currentness")
    resolution = contract.get("resolution")
    if (
        not isinstance(query, dict)
        or not isinstance(currentness, dict)
        or not isinstance(resolution, dict)
    ):
        msg = "authority_contract_invalid"
        raise TypeError(msg)
    axes = query.get("required")
    requirements = currentness.get("requires")
    if tuple(axes) != _AUTHORITY_QUERY_AXES or tuple(requirements) != _CURRENTNESS_REQUIREMENTS:
        msg = "authority_contract_query_axes_invalid"
        raise ValueError(msg)
    if contract.get("resolver") != "contextual" or query.get("unknown_verdict") != "unknown":
        msg = "authority_contract_resolution_invalid"
        raise ValueError(msg)
    if any(
        currentness.get(key) is not False
        for key in ("history_is_current", "projection_is_authority", "adapter_is_authority")
    ):
        msg = "authority_contract_currentness_invalid"
        raise ValueError(msg)
    if (
        resolution.get("conflict") != "block"
        or resolution.get("novel_semantics") != "model_gap"
        or resolution.get("more_specific_owner") != "wins_only_within_same_query"
    ):
        msg = "authority_contract_resolution_invalid"
        raise ValueError(msg)
    return {
        "contract_ref": "system/authority.toml",
        "resolver": "contextual",
        "query_axes": list(_AUTHORITY_QUERY_AXES),
        "unknown_verdict": "unknown",
        "currentness_requirements": list(_CURRENTNESS_REQUIREMENTS),
        "conflict_verdict": "block",
        "novel_semantics": "model_gap",
    }


def repository_context(root: Path) -> dict[str, object]:
    """Project repository context from its explicit profile and authority contract."""
    profile = load_repository_profile(root)
    if profile.state == "invalid":
        raise ValueError(INVALID_PROFILE_ERROR)
    return {
        "contract": "governed_repository",
        "profile": profile.declaration.profile_id if profile.declaration else "unbound",
        "repository": str(root.resolve()),
        "authority": _contextual_authority(root),
        "reader_projection_commands": ["ethos status"],
        "truth_boundary": "repository",
        "profile_boundary": "profile_or_adapter",
    }
