"""GitLab admits every pushed ref and keeps its full set for what GitHub does not verify."""

from __future__ import annotations

MAIN = '$CI_COMMIT_BRANCH == "main"'
SCHEDULE = {"if": '$CI_PIPELINE_SOURCE == "schedule"'}
MAIN_DIFFERS = {"if": MAIN, "changes": {"paths": ["**/*"], "compare_to": "refs/heads/dev"}}
BATCH_HEAD = {
    "if": '($CI_PIPELINE_SOURCE == "web" || $CI_PIPELINE_SOURCE == "api")'
    " && $CI_COMMIT_BRANCH =~ /^proposal\\/.+$/"
}
# A ref published to both Forges: a main push at dev's commit reuses the dev pipeline.
CONFORMANCE = [SCHEDULE, MAIN_DIFFERS, {"if": MAIN, "when": "never"}, {"when": "on_success"}]
# What GitHub does not verify: a merge request, a batch head and a main that differs from dev.
MERGE_REQUEST = {"if": '$CI_PIPELINE_SOURCE == "merge_request_event"'}
FULL_SET = [SCHEDULE, MERGE_REQUEST, BATCH_HEAD, MAIN_DIFFERS, {"when": "never"}]
ROLES = {
    "ethos:host-conformance": CONFORMANCE,
    "ethos:npm": CONFORMANCE,
    "ethos:verify": FULL_SET,
    "ethos:external-links": FULL_SET,
}


def test_each_commit_scoped_job_runs_in_its_role_by_event(gitlab) -> None:
    assert {job: gitlab[job]["rules"] for job in ROLES} == ROLES


def test_every_pushed_ref_keeps_its_commit_admission(gitlab) -> None:
    jobs = {name for name in gitlab if name.startswith("ethos:")}
    assert jobs == {*ROLES, "ethos:commit-policy"}
    assert all("changes" not in rule for rule in gitlab["ethos:commit-policy"]["rules"])
