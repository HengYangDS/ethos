"""Keep each hosted job's name a function of its matrix coordinates on both forges."""

from __future__ import annotations

import re
import tomllib
from typing import TYPE_CHECKING

import pytest
import yaml

import tools.ci.ci_projection as owner
from ethos.adapters.projections.cue import compile_projections
from ethos.adapters.toolchain.mise import locked_tool
from ethos.repository.policy.projections import observe_projections

if TYPE_CHECKING:
    from pathlib import Path

ROOT = owner.ROOT


@pytest.fixture(scope="module")
def materials() -> tuple[dict, dict[str, str]]:
    """Read the projection declaration and every input it compiles from, once."""
    config = tomllib.loads((ROOT / owner.CONFIG_RELATIVE_PATH).read_text())
    paths = {path for relation in observe_projections(ROOT) for path in relation.materials}
    paths.update(path for entry in config["projection"] for path in entry["required_owner_scripts"])
    paths.update(entry["projection"] for entry in config["forge_surface"])
    return config, {path: (ROOT / path).read_text() for path in paths}


def test_each_projected_job_is_named_by_its_matrix_coordinates(tmp_path, materials) -> None:
    """A required check keeps its identity: only its own matrix axes vary a job's name."""
    config, files = materials
    node = config["compiler"]["inputs"]["node"]
    version = tomllib.loads(files[node])["tools"]["node"]
    probe = dict(files, **{node: files[node].replace(f'"{version}"', '"0.0.0"')})
    cue = locked_tool(ROOT, "cue")
    names = [
        _projected_job_names(tmp_path / label, inputs, cue)
        for label, inputs in (("locked", files), ("probe", probe))
    ]
    assert names[0] == names[1], "a supply version renamed a projected job"
    for (provider, job), (name, axes) in names[0].items():
        expressions = re.findall(r"\$\{\{\s*matrix\.(\w+)\s*\}\}", name)
        assert sorted(expressions) == sorted(axes), (provider, job, name)
    assert names[0]["github", "host-conformance"][0] == (
        "${{ matrix.os }} / Python ${{ matrix.python }}"
    )


def _projected_job_names(
    root: Path, files: dict[str, str], cue: Path
) -> dict[tuple[str, str], tuple[str, tuple[str, ...]]]:
    """Compile both forges from exact inputs and name each job with its matrix axes."""
    root.mkdir()
    compiled = compile_projections(root, owner.CONFIG_RELATIVE_PATH, dict(files), executable=cue)
    github, gitlab = (yaml.safe_load(compiled[provider]) for provider in ("github", "gitlab"))
    names = {
        ("github", job): (
            spec.get("name", job),
            tuple(axis for axis in spec.get("strategy", {}).get("matrix", {}) if axis != "include"),
        )
        for job, spec in github["jobs"].items()
    }
    # A GitLab job is its key; GitLab itself names any parallel matrix job from its values.
    names.update(
        {
            ("gitlab", job): (job, ())
            for job, spec in gitlab.items()
            if isinstance(spec, dict) and "script" in spec
        }
    )
    return names
