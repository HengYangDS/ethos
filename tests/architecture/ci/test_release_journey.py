"""A release run qualifies its published prerelease on the adopter journey on macOS and Linux."""

from __future__ import annotations

from typing import Any

import pytest
import yaml

import tools.ci.ci_projection as owner

ROOT = owner.ROOT
TAG = "${{ inputs.release_tag || inputs.journey_tag }}"


@pytest.fixture(scope="module")
def workflow() -> dict[str, Any]:
    return yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))


def test_the_journey_follows_publication_on_macos_and_linux(workflow: dict[str, Any]) -> None:
    job = workflow["jobs"]["release-journey"]
    assert job["needs"] == "release-publish"
    assert [leg["os"] for leg in job["strategy"]["matrix"]["include"]] == [
        "ubuntu-latest",
        "macos-latest",
    ]
    assert "needs.release-publish.result == 'success'" in job["if"]
    assert "inputs.journey_tag != ''" in job["if"]
    (step,) = (step for step in job["steps"] if "release_journey" in str(step.get("run", "")))
    assert step["run"] == (
        f"uv run --frozen python -m nox -s release_journey -- --tag {TAG}"
        ' --previous "$JOURNEY_PREVIOUS"'
    )
    # A dispatch value reaches the shell only through the environment, never the script text.
    assert step["env"] == {"JOURNEY_PREVIOUS": "${{ inputs.journey_previous }}"}
    (upload,) = (
        step
        for step in job["steps"]
        if str(step.get("uses", "")).startswith("actions/upload-artifact@")
    )
    assert upload["if"] == "always()"
    assert upload["with"]["path"] == "build/evidence/release-journey/"


def test_a_journey_dispatch_runs_no_regular_job(workflow: dict[str, Any]) -> None:
    inputs = workflow["on"]["workflow_dispatch"]["inputs"]
    assert (inputs["journey_tag"]["default"], inputs["journey_previous"]["default"]) == ("", "")
    regular = [
        name for name, job in workflow["jobs"].items() if "!inputs.release_tag" in job.get("if", "")
    ]
    assert regular
    assert all("!inputs.journey_tag" in workflow["jobs"][name]["if"] for name in regular)
