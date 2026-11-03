"""A newer proposal push supersedes its earlier run; no other run is cancelled or queued."""

from __future__ import annotations

from typing import Any

import yaml

import tools.ci.ci_projection as owner

ROOT = owner.ROOT
PROPOSAL_PUSH = "github.event_name == 'push' && startsWith(github.ref, 'refs/heads/proposal/')"


def _projection(relative: str) -> dict[str, Any]:
    return yaml.safe_load((ROOT / relative).read_text(encoding="utf-8"))


def test_github_groups_only_a_proposal_push_with_its_ref() -> None:
    by_ref = "format('{0}-{1}', github.workflow, github.ref)"
    by_run = "format('{0}-run-{1}', github.workflow, github.run_id)"
    assert _projection(".github/workflows/ci.yml").get("concurrency") == {
        "group": f"${{{{ {PROPOSAL_PUSH} && {by_ref} || {by_run} }}}}",
        "cancel-in-progress": True,
    }


def test_gitlab_cancels_only_a_superseded_proposal_pipeline() -> None:
    gitlab = _projection(".gitlab-ci.yml")
    assert gitlab["default"].get("interruptible") is True
    jobs = {name: job for name, job in gitlab.items() if name.startswith("ethos:")}
    assert jobs
    assert all("interruptible" not in job for job in jobs.values())
    rules = [
        (rule.get("if"), rule.get("when"), rule.get("auto_cancel"))
        for rule in gitlab["workflow"]["rules"]
    ]
    assert rules == [
        ('$CI_PIPELINE_SOURCE == "merge_request_event"', None, {"on_new_commit": "none"}),
        (
            '$CI_COMMIT_BRANCH == "dev" || $CI_COMMIT_BRANCH == "main"',
            None,
            {"on_new_commit": "none"},
        ),
        ("$CI_COMMIT_BRANCH =~ /^proposal\\/.+$/", None, {"on_new_commit": "interruptible"}),
        (None, "never", None),
    ]
