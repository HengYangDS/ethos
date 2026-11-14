"""Keep each hosted job's name a function of its matrix coordinates on both forges."""

from __future__ import annotations

import re
import tomllib
from typing import TYPE_CHECKING

import yaml

import tools.ci.ci_projection as owner
from ethos.adapters.projections.cue import compile_projections
from ethos.adapters.toolchain.mise import locked_tool

if TYPE_CHECKING:
    from pathlib import Path

ROOT = owner.ROOT


def test_each_projected_job_is_named_by_its_matrix_coordinates(tmp_path, ci_materials) -> None:
    """A required check keeps its identity: only its own matrix axes vary a job's name."""
    config, files = ci_materials
    mise = config["compiler"]["inputs"]["mise"]
    tools = tomllib.loads(files[mise])["tools"]
    changed = files[mise]
    for tool in ("node", "uv"):
        changed = changed.replace(f'"{tools[tool]}"', '"0.0.0"')
    probe = dict(files, **{mise: changed})
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
        "${{ matrix.platform }} / Python ${{ matrix.python }}"
    )


def _coordinates(matrix: dict[str, object]) -> tuple[str, ...]:
    """A tiered leg is named by its platform id and Python version, never by its runner label."""
    if isinstance(matrix.get("include"), str):
        return ("platform", "python")
    return tuple(axis for axis in matrix if axis != "include")


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
            _coordinates(spec.get("strategy", {}).get("matrix", {})),
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
