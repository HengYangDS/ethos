"""Hosted uv setup installs the uv that the repository's Mise configuration declares."""

from __future__ import annotations

import re
import tomllib
from typing import TYPE_CHECKING

import yaml

import tools.ci.ci_projection as owner
from ethos.adapters.projections.cue import compile_projections
from ethos.adapters.toolchain.mise import locked_tool
from ethos.repository.policy.projections import observe_projections

if TYPE_CHECKING:
    from pathlib import Path

ROOT = owner.ROOT
MISE = ".config/mise/config.toml"


def test_hosted_uv_setup_follows_the_mise_configuration(tmp_path: Path) -> None:
    materials = {path for relation in observe_projections(ROOT) for path in relation.materials}
    files = {path: (ROOT / path).read_text(encoding="utf-8") for path in materials}
    files[MISE] = re.sub(r'(?m)^uv = "[^"]+"$', 'uv = "9.8.7"', files[MISE])
    assert tomllib.loads(files[MISE])["tools"]["uv"] == "9.8.7"

    # The real lock still resolves the compiler; only the model's uv input changes.
    providers = compile_projections(
        tmp_path, owner.CONFIG_RELATIVE_PATH, files, executable=locked_tool(ROOT, "cue")
    )
    versions = [
        step["with"]["version"]
        for job in yaml.safe_load(providers["github"])["jobs"].values()
        for step in job.get("steps", ())
        if str(step.get("uses", "")).startswith("astral-sh/setup-uv@")
    ]
    assert versions
    assert set(versions) == {"9.8.7"}
