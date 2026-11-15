"""A release run qualifies its published prerelease on the adopter journey on each declared host."""

from __future__ import annotations

from typing import Any

TAG = "${{ inputs.release_tag || inputs.journey_tag }}"


def test_the_journey_follows_publication_on_each_declared_host(github: dict[str, Any]) -> None:
    job = github["jobs"]["release-journey"]
    assert job["needs"] == "release-publish"
    # Each declared host runs on a runner of its own architecture.
    assert [(leg["host"], leg["os"]) for leg in job["strategy"]["matrix"]["include"]] == [
        ("linux-x64", "ubuntu-latest"),
        ("linux-arm64", "ubuntu-24.04-arm"),
        ("macos-arm64", "macos-latest"),
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


def test_a_journey_dispatch_runs_no_regular_job(github: dict[str, Any]) -> None:
    inputs = github["on"]["workflow_dispatch"]["inputs"]
    assert (inputs["journey_tag"]["default"], inputs["journey_previous"]["default"]) == ("", "")
    regular = [
        name for name, job in github["jobs"].items() if "!inputs.release_tag" in job.get("if", "")
    ]
    assert regular
    assert all("!inputs.journey_tag" in github["jobs"][name]["if"] for name in regular)
