"""The suite runs once per release on every operating system, architecture and Python version."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import Any

import pytest

import tools.ci.ci_projection as owner
from ethos.adapters.projections.cue import compile_projections
from ethos.adapters.toolchain.mise import locked_tool
from tests.support.registries import repository_registry_path

# Job name, runner, Python version and whether the leg may fail; the aggregate's own test names
# the legs it needs. With the quality job on Linux arm64 and the local proof on macOS arm64, both
# at Python 3.14, these legs complete three operating systems, two architectures and three Python
# versions.
LEGS = {
    "suite-linux-x64-py312": ("suite linux-x64 / Python 3.12", "ubuntu-latest", "3.12", False),
    "suite-linux-x64-py313": ("suite linux-x64 / Python 3.13", "ubuntu-latest", "3.13", False),
    "suite-windows-x64-py314": ("suite windows-x64 / Python 3.14", "windows-latest", "3.14", True),
}
FULL = "(github.event_name == 'workflow_dispatch' && inputs.qualify_head != '')"
REPORTS = "build/evidence/quality/tests/"
ROOT = Path(__file__).resolve().parents[3]


def test_a_full_run_adds_the_suite_legs_and_only_the_linux_legs_block(
    github: dict[str, Any],
) -> None:
    jobs = github["jobs"]
    legs = {name: job for name, job in jobs.items() if name.startswith("suite-")}
    assert {
        name: (
            job["name"],
            job["runs-on"],
            job["steps"][1]["with"]["python-version"],
            job.get("continue-on-error", False),
        )
        for name, job in legs.items()
    } == LEGS
    gates = tomllib.loads(repository_registry_path().read_text(encoding="utf-8"))["gates"]
    (deadline,) = (gate["timeout_seconds"] for gate in gates if gate["id"] == "unit-architecture")
    commit = jobs["quality"]["if"][4:-3]
    model = (ROOT / ".config/ci/pipeline.cue").read_text(encoding="utf-8")
    (margin,) = re.findall(r"^let suiteSetupSeconds = (\d+)$", model, flags=re.MULTILINE)
    for name, job in legs.items():
        # A push or pull request runs no leg; a batch head or the drift schedule runs each.
        assert job["if"] == f"${{{{ ({commit}) && ({FULL} || github.event_name == 'schedule') }}}}"
        # The test gate's deadline bounds the leg's suite, and each generated job outlives it
        # by the model's own setup margin; the test below drives the model to its refusal.
        assert job["timeout-minutes"] * 60 >= deadline + int(margin)
        suite, upload = job["steps"][-2:]
        assert suite["run"] == f"uv run --frozen python -m nox -s suite_leg -- {deadline}"
        # The probe copies the leg's reports to the root that the upload reads, also on failure.
        assert suite["env"]["ETHOS_NATIVE_OUTPUT_DIR"].endswith("/" + REPORTS[:-1])
        assert all(path.startswith(REPORTS) for path in upload["with"]["path"].splitlines())
        assert (upload["if"], upload["with"]["name"]) == ("always()", name)


def test_the_model_refuses_a_suite_job_that_does_not_outlive_the_deadline_by_its_margin(
    tmp_path: Path, ci_materials: tuple[dict[str, Any], dict[str, str]]
) -> None:
    """Five minutes above the deadline outlive the gate, and not the leg's supply steps too."""
    config, materials = ci_materials
    files, model = dict(materials), config["compiler"]["source"]
    declared = "\tsuite:       130\n"
    assert files[model].count(declared) == 1
    files[model] = files[model].replace(declared, "\tsuite:       125\n")
    with pytest.raises(ValueError, match=r"cue_compilation_failed:.*timeout-setup:suite"):
        compile_projections(
            tmp_path, owner.CONFIG_RELATIVE_PATH, files, executable=locked_tool(ROOT, "cue")
        )
