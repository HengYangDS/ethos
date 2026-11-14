"""GitHub verifies each commit once while every push and pull request keeps its own admission."""

from __future__ import annotations

from typing import Any

import pytest

COMMIT_SCOPED_JOBS = ("host-conformance", "quality", "external-links")
REGULAR = "!inputs.supply_image && !inputs.release_tag && !inputs.journey_tag && !inputs.scan_tag"
MAIN_PUSH = "github.event_name == 'push' && github.ref == 'refs/heads/main'"
HEAD = "inputs.qualify_head == '' || inputs.qualify_head == github.sha"


@pytest.mark.parametrize("job", COMMIT_SCOPED_JOBS)
def test_a_main_push_leaves_the_commit_scoped_jobs_to_the_dev_run(
    github: dict[str, Any], job: str
) -> None:
    assert github["jobs"][job]["if"] == f"${{{{ {REGULAR} && !({MAIN_PUSH}) && ({HEAD}) }}}}"


def test_every_push_and_pull_request_admits_its_own_range_once(github: dict[str, Any]) -> None:
    assert "main" in github["on"]["push"]["branches"]
    job = github["jobs"]["commit-policy"]
    assert job["if"] == "${{ github.event_name == 'push' || github.event_name == 'pull_request' }}"
    events = [step["if"] for step in job["steps"] if "hook commit-range" in step.get("run", "")]
    assert events == ["github.event_name == 'push'", "github.event_name == 'pull_request'"]
    others = {name: other for name, other in github["jobs"].items() if name != "commit-policy"}
    assert "hook commit-range" not in str(others)
