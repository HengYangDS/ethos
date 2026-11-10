"""GitLab verifies each commit once while every pushed ref keeps its own admission."""

from __future__ import annotations

from typing import Any

import pytest

COMMIT_SCOPED_JOBS = ("ethos:host-conformance", "ethos:verify", "ethos:external-links", "ethos:npm")
REF_SCOPED_JOBS = ("ethos:commit-policy",)
MAIN = '$CI_COMMIT_BRANCH == "main"'


@pytest.mark.parametrize("job", COMMIT_SCOPED_JOBS)
def test_main_push_at_the_dev_commit_reuses_the_dev_pipeline(
    gitlab: dict[str, Any], job: str
) -> None:
    assert gitlab[job]["rules"] == [
        {"if": MAIN, "changes": {"paths": ["**/*"], "compare_to": "refs/heads/dev"}},
        {"if": MAIN, "when": "never"},
        {"when": "on_success"},
    ]


def test_every_pushed_ref_keeps_its_commit_admission(gitlab: dict[str, Any]) -> None:
    jobs = {name for name in gitlab if name.startswith("ethos:")}
    assert jobs == {*COMMIT_SCOPED_JOBS, *REF_SCOPED_JOBS}
    assert all("changes" not in rule for rule in gitlab["ethos:commit-policy"]["rules"])
