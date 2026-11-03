"""Hosted host conformance keeps the stage timings its package acceptance writes."""

from __future__ import annotations

import yaml

import tools.ci.ci_projection as owner

ROOT = owner.ROOT
RECEIPT = (
    "build/evidence/local-install/smoke.json",
    "build/evidence/local-install/smoke.events.jsonl",
)


def test_each_host_conformance_job_uploads_its_timings_with_its_receipt() -> None:
    github, gitlab = (
        yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))
        for path in (".github/workflows/ci.yml", ".gitlab-ci.yml")
    )
    (upload,) = (
        step
        for step in github["jobs"]["host-conformance"]["steps"]
        if str(step.get("uses", "")).startswith("actions/upload-artifact@")
    )
    assert upload["if"] == "always()"
    assert upload["with"]["path"].splitlines() == list(RECEIPT)
    artifacts = gitlab["ethos:host-conformance"]["artifacts"]
    assert artifacts["when"] == "always"
    assert artifacts["paths"] == list(RECEIPT)
