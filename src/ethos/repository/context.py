"""Derive repository context from the selected explicit adoption profile."""

import hashlib
from importlib.resources import files
from pathlib import Path

from ethos.repository.profile import INVALID_PROFILE_ERROR
from ethos.repository.profile import load_repository_profile


def repository_context(root: Path) -> dict[str, object]:
    """Project repository context from its explicit profile."""
    profile = load_repository_profile(root)
    if profile.state == "invalid":
        raise ValueError(INVALID_PROFILE_ERROR)
    guidance_resource = files("ethos").joinpath("data/skills/ethos-repository-work/SKILL.md")
    guidance = guidance_resource.read_bytes()
    return {
        "contract": "governed_repository",
        "profile": profile.declaration.profile_id if profile.declaration else "unbound",
        "repository": str(root.resolve()),
        "reader_projection_commands": ["ethos status"],
        "truth_boundary": "repository",
        "profile_boundary": "profile_or_adapter",
        "agent_guidance": {
            "authority": "product_projection",
            "media_type": "text/markdown",
            "sha256": hashlib.sha256(guidance).hexdigest(),
            "path": str(guidance_resource),
        },
    }
