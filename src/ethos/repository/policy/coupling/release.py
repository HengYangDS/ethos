"""Release-profile coupling helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

from ethos.contracts.registry.declarations import load_coupling_declaration
from ethos.repository.profile import load_repository_profile
from ethos.repository.release.configuration import REQUIRED_RELEASE_FILES
from ethos.repository.release.configuration import release_policy_report

if TYPE_CHECKING:
    from pathlib import Path


def release_report(root: Path) -> dict[str, Any]:
    """Return release policy only for a repository that declares its owner."""
    profile = load_repository_profile(root)
    coupling = root / "system" / "coupling.toml"
    product_policy = False
    if (
        profile.declaration is not None
        and profile.declaration.proof.gate_registry
        and coupling.is_file()
    ):
        try:
            product_policy = bool(load_coupling_declaration(coupling).product_repository_gates)
        except (OSError, UnicodeError, ValueError):
            product_policy = False
    if not product_policy:
        return {
            "required_files": list(REQUIRED_RELEASE_FILES),
            "host_profile": {
                "provider": "",
                "layer": "profile_or_adapter_binding",
                "surfaces": {},
            },
            "required_gaps": [],
        }
    return release_policy_report(root)


def release_host_profile(root: Path) -> dict[str, object]:
    """Return the release host profile annotated as an adapter binding."""
    profile = dict(release_report(root)["host_profile"])
    profile["layer"] = "profile_or_adapter_binding"
    return profile
