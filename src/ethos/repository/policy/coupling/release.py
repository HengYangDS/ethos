"""Release-profile coupling helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

from ethos.repository.release.configuration import REQUIRED_RELEASE_FILES
from ethos.repository.release.configuration import release_policy_report

if TYPE_CHECKING:
    from pathlib import Path


def release_report(root: Path) -> dict[str, Any]:
    """Return release policy only for a repository that declares its owner."""
    if not (root / ".ethos" / "release.toml").is_file():
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
