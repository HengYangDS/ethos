"""GitHub verifies each commit once while every pushed ref keeps its own admission."""

from __future__ import annotations

from typing import Any

import pytest

COMMIT_SCOPED_JOBS = ("host-conformance", "quality", "external-links", "verify", "package")
MAIN_PUSH = "github.event_name == 'push' && github.ref == 'refs/heads/main'"


@pytest.mark.parametrize("job", COMMIT_SCOPED_JOBS)
def test_a_main_push_leaves_the_commit_scoped_jobs_to_the_dev_run(
    github: dict[str, Any], job: str
) -> None:
    condition = github["jobs"][job]["if"]
    assert condition.startswith("${{ ")
    assert condition.endswith(f" && !({MAIN_PUSH}) }}}}")
    assert "||" not in condition


def test_a_main_push_still_admits_its_pushed_range(github: dict[str, Any]) -> None:
    assert "main" in github["on"]["push"]["branches"]
    job = github["jobs"]["commit-policy"]
    assert job["if"] == f"${{{{ {MAIN_PUSH} }}}}"
    pushed = [
        step["run"]
        for step in github["jobs"]["quality"]["steps"]
        if step.get("name") == "Admit pushed commit range"
    ]
    admitted = [step["run"] for step in job["steps"] if "hook commit-range" in step.get("run", "")]
    assert admitted == pushed
