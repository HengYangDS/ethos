"""Installed-package fixtures shared by delivery acceptance tests."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from ethos.repository.release.resources import GUIDANCE_RESOURCE

if TYPE_CHECKING:
    from pathlib import Path


def installed_guidance(
    package: Path, content: str = "Run ethos status.\n", *, directory: str = "resources"
):
    """Materialize one installed guidance fixture with its exact status identity."""
    guide = package / directory / GUIDANCE_RESOURCE
    guide.parent.mkdir(parents=True)
    guide.write_text(content, encoding="utf-8")
    origin = package / "__init__.py"
    origin.write_text("", encoding="utf-8")
    guidance = {
        "authority": "product_projection",
        "media_type": "text/markdown",
        "path": str(guide),
        "sha256": hashlib.sha256(guide.read_bytes()).hexdigest(),
    }
    return guide, origin, {"governance_context": {"agent_guidance": guidance}}
