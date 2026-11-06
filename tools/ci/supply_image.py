"""Whether the bound CI supply image still matches the files its manifest hashes.

The supply image's Dockerfile hashes a fixed list of inputs into `input.sha256`, and each GitLab
job checks that manifest before anything else. The binding in `.config/ci/pipeline.cue` names the
image's digest and the commit it was built from. The image's smoke stage proves that its manifest
matches that commit, so an input whose working-tree bytes differ from its bytes at that commit means
the bound image is stale, and every GitLab job would refuse the head.
"""

from __future__ import annotations

import hashlib
import re
import shlex
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

DOCKERFILE = ".config/ci/supply/Dockerfile"
PIPELINE = ".config/ci/pipeline.cue"
_IMAGE = re.compile(r'^let gitlabImage = "[^"@]+@(sha256:[0-9a-f]{64})"$', re.MULTILINE)
_SOURCE = re.compile(r'^let gitlabImageSource = "([0-9a-f]{40})"$', re.MULTILINE)
ROUTE = (
    "rebuild the supply image on the lane's GitHub proposal ref (supply_image dispatch), then bind "
    "its digest and source commit in .config/ci/pipeline.cue"
)


def manifest_inputs(root: Path) -> tuple[str, ...]:
    """Return the paths that the image's native checksum command hashes, in its order."""
    source = (root / DOCKERFILE).read_text(encoding="utf-8")
    section = source.split("&& sha256sum ", 1)[1].split(" > input.sha256", 1)[0]
    paths = tuple(shlex.split(section.replace("\\\n", " ")))
    # The Dockerfile itself is an input: editing the list changes the image.
    return tuple(dict.fromkeys((DOCKERFILE, *paths)))


def binding(root: Path) -> tuple[str, str]:
    """Return the bound image digest and the commit it was built from."""
    text = (root / PIPELINE).read_text(encoding="utf-8")
    image, source = _IMAGE.findall(text), _SOURCE.findall(text)
    if len(image) != 1 or len(source) != 1:
        message = "supply_image_binding_invalid"
        raise ValueError(message)
    return image[0], source[0]


def stale_inputs(root: Path, source: str) -> list[str]:
    """Name each manifest input whose working-tree bytes differ from its bytes at `source`."""
    stale = []
    for path in manifest_inputs(root):
        built = subprocess.run(
            ("git", "show", f"{source}:{path}"),
            cwd=root,
            capture_output=True,
            check=False,
            stdin=subprocess.DEVNULL,
            timeout=60,
        )
        if built.returncode:
            return ["supply_image_source_unavailable"]
        current = root / path
        current_digest = (
            hashlib.sha256(current.read_bytes()).hexdigest() if current.is_file() else ""
        )
        if hashlib.sha256(built.stdout).hexdigest() != current_digest:
            stale.append(f"supply_image_stale:{path}")
    return stale
