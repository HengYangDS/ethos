"""Hosted artifacts expire after one retention; GitLab archives evidence, never build output."""

from __future__ import annotations

from typing import Any


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


def test_every_hosted_artifact_expires_after_the_one_declared_retention(
    github: dict[str, Any], gitlab: dict[str, Any]
) -> None:
    """Every upload step and every archive carries the same retention, on both Forges."""
    uploads = [
        step["with"]
        for job in github["jobs"].values()
        for step in job["steps"]
        if step.get("uses", "").startswith("actions/upload-artifact@")
    ]
    archives = [job["artifacts"] for job in gitlab.values() if "artifacts" in job]
    assert {upload.get("retention-days") for upload in uploads} == {14}
    assert {archive.get("expire_in") for archive in archives} == {"14 days"}
