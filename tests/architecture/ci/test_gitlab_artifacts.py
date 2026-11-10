"""GitLab archives hold evidence; its instance artifact limit cannot hold the Python wheels."""

from __future__ import annotations

from typing import Any

import tools.ci.ci_projection as owner

ROOT = owner.ROOT


def test_gitlab_jobs_archive_no_build_output(gitlab: dict[str, Any]) -> None:
    """Every archived path is evidence; build outputs under build/artifacts/ stay on GitHub."""
    archived = {
        name: list(job["artifacts"].get("paths", ()))
        for name, job in gitlab.items()
        if isinstance(job, dict) and isinstance(job.get("artifacts"), dict)
    }
    assert archived, "no GitLab job archives anything"
    outputs = {
        name: [path for path in paths if str(path).startswith("build/artifacts/")]
        for name, paths in archived.items()
    }
    assert {name: paths for name, paths in outputs.items() if paths} == {}
