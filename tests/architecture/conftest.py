"""Read the hosted CI projections and the inputs they compile from once per architecture module."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

import pytest
import yaml

import tools.ci.ci_projection as owner
from ethos.repository.policy.projections import observe_projections

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def ci_materials() -> tuple[dict[str, Any], dict[str, str]]:
    """Read the projection declaration and every input it compiles from, once.

    The inputs are shared and immutable; every fault case gets its own mutable copy.
    """
    config = tomllib.loads((ROOT / owner.CONFIG_RELATIVE_PATH).read_text())
    paths = {path for relation in observe_projections(ROOT) for path in relation.materials}
    paths.update(path for entry in config["projection"] for path in entry["required_owner_scripts"])
    paths.update(entry["projection"] for entry in config["forge_surface"])
    return config, {path: (ROOT / path).read_text() for path in paths}


@pytest.fixture(scope="module")
def github() -> dict[str, Any]:
    """Read the actual hosted projection once; source parity is checked separately."""
    return yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def gitlab() -> dict[str, Any]:
    """Read the actual GitLab projection consumed by its native runner."""
    return yaml.safe_load((ROOT / ".gitlab-ci.yml").read_text(encoding="utf-8"))
