"""Hosted CI runs host conformance in tiers and bounds each job's time, credentials and access."""

from __future__ import annotations

import json
import re

import yaml

PUSH = ["linux-x64 3.12", "linux-x64 3.13", "linux-x64 3.14", "macos-arm64 3.12"]
MACOS = ["macos-arm64 3.13", "macos-arm64 3.14"]
WINDOWS = [
    "windows-x64 3.12",
    "windows-x64 3.13",
    "windows-x64 3.14",
    "windows-arm64 cpython-3.14-windows-x86_64-none",
]


def test_a_push_runs_the_push_tier_and_only_a_dispatch_or_schedule_runs_more(github) -> None:
    selection = github["jobs"]["host-conformance"]["strategy"]["matrix"]["include"]
    tiers = [
        ["{platform} {python}".format_map(leg) for leg in json.loads(tier)]
        for tier in re.findall(r"'(\[.*?\])'", selection)
    ]
    assert tiers == [PUSH + MACOS + WINDOWS, PUSH + WINDOWS, PUSH]
    # A batch head or the drift schedule runs every leg; the typed input adds the Windows legs.
    assert re.sub(r"'\[.*?\]'", "TIER", selection) == (
        "${{ fromJSON(((github.event_name == 'workflow_dispatch' && inputs.qualify_head != '')"
        " || github.event_name == 'schedule') && TIER || inputs.windows_legs && TIER || TIER) }}"
    )
    assert github["on"]["schedule"] == [{"cron": "0 19 * * 6"}]
    inputs = github["on"]["workflow_dispatch"]["inputs"]
    assert inputs["qualify_head"]["type"] == "string"
    assert inputs["windows_legs"]["type"] == "boolean"


def test_every_hosted_job_bounds_its_time_credentials_and_permissions(github, gitlab) -> None:
    jobs = github["jobs"]
    assert all(job.get("timeout-minutes") for job in jobs.values())
    assert all(job.get("timeout") for name, job in gitlab.items() if name.startswith("ethos:"))
    workflow = yaml.safe_dump(github)
    assert workflow.count("uses: actions/checkout@") == workflow.count("persist-credentials: false")
    assert "persist-credentials: false" in workflow
    assert github["permissions"] == {"contents": "read"}
    widened = [name for name, job in jobs.items() if "write" in str(job.get("permissions"))]
    assert widened == ["supply-image", "release-publish"]
