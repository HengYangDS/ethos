"""The hosted reader states what a peer's forge answered for one exact commit, and no more."""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.process as process
from ethos.adapters.mutation.publication.hosted_runs import observe_hosted_runs
from tests.support.governed_repository import git

if TYPE_CHECKING:
    from pathlib import Path

HEAD = "a" * 40
URLS = {"github": "https://hub.test/team/repo", "gitlab": "https://lab.test/team/repo"}
_TOOLS = {"gh": "github", "glab": "gitlab"}
# Each provider's own word for a state, as its CLI prints it; any other word is used as given.
_WORDS = {
    "github": {"passed": "success", "failed": "failure", "running": "in_progress"},
    "gitlab": {"passed": "success", "failed": "failed", "running": "running"},
}


def row(provider: str, state: str, **fields: object) -> dict[str, object]:
    """Return one run or job row in a state, shaped as the provider's CLI prints it."""
    word = _WORDS[provider].get(state, state)
    if provider == "gitlab":
        return {"status": word, **fields}
    done = state != "running"
    return {"status": "completed" if done else word, "conclusion": word if done else "", **fields}


def run_row(provider: str, state: str, head: str = HEAD, run: int = 7) -> dict[str, object]:
    """Return one run row of a commit under the provider's own identity and head keys."""
    keys = ("databaseId", "headSha") if provider == "github" else ("id", "sha")
    return row(provider, state, **dict(zip(keys, (run, head), strict=True)))


def job_row(provider: str, state: str) -> dict[str, object]:
    """Return one job row; `allowed` is a failed job that the pipeline lets fail."""
    if state != "allowed":
        return row(provider, state, name="unit")
    # Only one provider marks the job itself; the other says it through the run's conclusion.
    mark = {"allow_failure": True} if provider == "gitlab" else {}
    return row(provider, "failed", name="links", **mark)


def recorded_forge(
    monkeypatch: pytest.MonkeyPatch, answers: dict[str, object]
) -> list[tuple[str, ...]]:
    """Answer `gh` and `glab` from recorded rows; return the provider commands that ran.

    A provider's answer is its run rows with every run's job rows, a process result to return as
    it is, or an error to raise.
    """
    native, commands = process.run_command, []

    def provider_process(root, command, **kwargs):
        if command[0] not in _TOOLS:
            return native(root, command, **kwargs)
        # These preconditions establish that the recorded answer meets a bounded, promptless query.
        assert (kwargs["stdin"], kwargs["timeout"]) == ("", 60)
        assert kwargs["env"]["GH_PROMPT_DISABLED"] == kwargs["env"]["GLAB_NO_PROMPT"] == "1"
        assert URLS[_TOOLS[command[0]]] in command
        commands.append(command)
        answer = answers[_TOOLS[command[0]]]
        if isinstance(answer, Exception):
            raise answer
        if isinstance(answer, subprocess.CompletedProcess):
            return answer
        runs, jobs = answer
        body = runs if "list" in command else {"jobs": jobs}
        return subprocess.CompletedProcess(command, 0, json.dumps(body), "")

    monkeypatch.setattr(process, "run_command", provider_process)
    return commands


def _peer(tmp_path: Path, provider: str, url: str = "") -> Path:
    """Create one repository whose remote `forge` is the provider's web repository."""
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "dev")
    git(repo, "remote", "add", "forge", url or f"{URLS[provider]}.git")
    return repo


@pytest.mark.parametrize("provider", ["github", "gitlab"])
@pytest.mark.parametrize(
    ("runs", "jobs", "wanted", "job_states"),
    [
        ([], [], "no_run", []),
        (["running"], ["running", "passed"], "running", ["running"]),
        (["passed"], ["passed"], "passed", []),
        (["failed"], ["passed", "failed", "skipped", "running"], "failed", ["failed", "running"]),
        (["passed"], ["passed", "allowed"], "passed", []),
        (["skipped"], ["skipped"], "no_run", []),
        (["passed", "running"], ["passed"], "running", []),
        (["running", "failed"], ["failed"], "failed", ["failed", "failed"]),
    ],
)
def test_a_peers_runs_of_one_commit_are_read_with_the_jobs_that_did_not_pass(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    provider: str,
    runs: list[str],
    jobs: list[str],
    wanted: str,
    job_states: list[str],
) -> None:
    """The run's own conclusion decides it; a run that passed is one row and one call.

    Jobs are read only for a run that failed or still runs, and only those that did not pass stay.
    """
    answer = (
        [run_row(provider, state, run=index) for index, state in enumerate(runs, 1)],
        [job_row(provider, state) for state in jobs],
    )
    commands = recorded_forge(monkeypatch, {provider: answer})
    observed = observe_hosted_runs(_peer(tmp_path, provider), "forge", provider, HEAD)
    assert (observed["state"], observed["head"], observed.get("reason")) == (wanted, HEAD, None)
    assert [run["state"] for run in observed["runs"]] == runs
    assert [job["state"] for run in observed["runs"] for job in run["jobs"]] == job_states
    # One listing names the exact commit; one read follows for each run that did not conclude well.
    assert HEAD in commands[0]
    assert len(commands) == 1 + sum(state in {"failed", "running"} for state in runs)


def test_a_job_the_pipeline_marks_allowed_stays_apart_in_a_failed_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The provider's own mark tells the job apart even when another job failed the run."""
    jobs = [job_row("gitlab", "allowed"), job_row("gitlab", "failed")]
    recorded_forge(monkeypatch, {"gitlab": ([run_row("gitlab", "failed")], jobs)})
    observed = observe_hosted_runs(_peer(tmp_path, "gitlab"), "forge", "gitlab", HEAD)
    assert observed["state"] == "failed"
    run = observed["runs"][0]
    assert (run["id"], run["conclusion"]) == ("7", "failed")
    assert [(job["name"], job["state"], job["conclusion"]) for job in run["jobs"]] == [
        ("links", "allowed_failure", "failed"),
        ("unit", "failed", "failed"),
    ]


@pytest.mark.parametrize("provider", ["github", "gitlab"])
@pytest.mark.parametrize(
    ("case", "reason", "names"),
    [
        ("denied", "provider_query_failed", "listing"),
        ("timeout", "provider_query_failed", "listing"),
        ("absent", "provider_query_failed", "listing"),
        ("unparsable", "provider_query_failed", "listing"),
        ("jobs_not_listed", "provider_query_failed", "jobs"),
        ("other_commit", "provider_answer_unusable", "hand"),
        ("unnamed_run", "provider_answer_unusable", "hand"),
        ("new_word", "provider_answer_unusable", "hand"),
        ("full_page", "provider_answer_unusable", "hand"),
    ],
)
def test_an_answer_the_reader_cannot_use_is_unknown_and_never_a_pass(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    provider: str,
    case: str,
    reason: str,
    names: str,
) -> None:
    """No credentials, no CLI, a timeout or an answer for another commit states nothing.

    The next action names the query that failed, the listing or the read of a run's jobs;
    an answer that the reader does not use is not asked for again.
    """
    listed = json.dumps([run_row(provider, "failed")])
    answers: dict[str, object] = {
        "denied": subprocess.CompletedProcess((), 1, "", "authentication required"),
        "timeout": subprocess.TimeoutExpired("forge", 60),
        "absent": OSError("no such file"),
        "unparsable": subprocess.CompletedProcess((), 0, "<html>", ""),
        "jobs_not_listed": subprocess.CompletedProcess((), 0, listed, ""),
        "other_commit": ([run_row(provider, "passed", head="b" * 40)], []),
        "unnamed_run": ([row(provider, "passed")], []),
        "new_word": ([run_row(provider, "reviewing")], []),
        "full_page": ([run_row(provider, "passed", run=index) for index in range(1, 101)], []),
    }
    recorded_forge(monkeypatch, {provider: answers[case]})
    observed = observe_hosted_runs(_peer(tmp_path, provider), "forge", provider, HEAD)
    assert (observed["state"], observed["reason"], observed["runs"]) == ("unknown", reason, [])
    assert "authentication" not in json.dumps(observed)
    action = observed["next_action"]
    asked = {"listing": (True, True), "jobs": (True, False), "hand": (False, False)}[names]
    assert (action.split()[0] in {"gh", "glab"}, HEAD in action) == asked


@pytest.mark.parametrize(
    ("provider", "url", "reason", "step"),
    [
        (
            "github",
            "git@example.test:team/repo.git",
            "forge_repository_unresolved:forge",
            "git config --local remote.forge.forgeRepository <web-url>",
        ),
        (
            "git",
            "",
            "provider_unsupported",
            "drop ci_cd and ci_surface from the peer's declaration, or read its runs on its forge",
        ),
    ],
)
def test_a_peer_without_a_readable_forge_runs_no_provider_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    provider: str,
    url: str,
    reason: str,
    step: str,
) -> None:
    """An SSH remote without the local key, or a provider with no reader, is a named unknown.

    Each names what a person can do: the local key, or the two fields of the peer's declaration
    that go together.
    """
    commands = recorded_forge(monkeypatch, {})
    observed = observe_hosted_runs(_peer(tmp_path, "github", url), "forge", provider, HEAD)
    assert (observed["state"], observed["reason"], commands) == ("unknown", reason, [])
    assert observed["next_action"] == step
