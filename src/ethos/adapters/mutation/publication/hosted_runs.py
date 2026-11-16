"""Read the hosted runs of one exact commit from a peer's forge, inventing no fact.

The provider's own authenticated CLI answers one listing of the commit's runs; this module reads
no token. A run's own conclusion decides the run, so a run that passed is one row and its jobs are
not read. A run that failed or still runs costs one more read and lists only its jobs that did not
pass, with a failed job told apart as allowed when the provider marks it so. An answer that is
refused, late, malformed or about another commit is `unknown`, never a pass, and carries no
stderr. An unknown peer names what a person can do: the query that failed, so that its own
refusal can be read, or a step by hand where no query of the reader answers. A read returns
states and records nothing.
"""

from __future__ import annotations

import shlex
from typing import TYPE_CHECKING

from ethos.adapters.mutation.publication.forge import forge_web_repository
from ethos.adapters.mutation.publication.forge import provider_rows

if TYPE_CHECKING:
    from pathlib import Path

# Each provider's listing of one commit's runs, its read of one run's jobs, and the row keys that
# hold a run's identity and its commit.
_READERS = {
    "github": (
        (
            "gh run list --repo {url} --commit {head} --limit {page}"
            " --json databaseId,headSha,status,conclusion"
        ),
        "gh run view {run} --repo {url} --json jobs",
        "databaseId",
        "headSha",
    ),
    "gitlab": (
        "glab ci list --repo {url} --sha {head} --per-page {page} --output json",
        "glab ci get --repo {url} --pipeline-id {run} --output json",
        "id",
        "sha",
    ),
}
# The most runs one listing reads; a full page may hide more runs, so it states nothing.
_PAGE = 100
# The provider words that mean each state of a run or a job; any other word states nothing.
_WORDS = {
    "passed": "success",
    "skipped": "skipped neutral",
    "failed": "failure failed cancelled canceled canceling timed_out action_required stale"
    " startup_failure",
    "running": "queued in_progress requested waiting pending created running"
    " waiting_for_resource preparing manual scheduled",
}
_STATES = {word: state for state, words in _WORDS.items() for word in words.split()}
# A peer's state is the first of these that one of its runs holds; a peer whose runs were all
# skipped holds no run that ran.
_ORDER = ("failed", "running", "passed")
# The states of a run whose jobs are read, and the states of a job that a run's row leaves out.
_OPEN = frozenset({"failed", "running"})
_QUIET = frozenset({"passed", "skipped"})
# Why a peer states nothing, with the query that failed; an answer that the reader does not
# use names no query, since asking again repeats it.
type _Unread = tuple[str, tuple[str, ...]]
_UNUSABLE: _Unread = ("provider_answer_unusable", ())
# What a person can do where no query of the reader answers.
_BY_HAND = {
    # A peer declares `ci_cd` and its `ci_surface` together, so both go.
    "provider_unsupported": "drop ci_cd and ci_surface from the peer's declaration, "
    "or read its runs on its forge",
    "provider_answer_unusable": "read the commit's runs on the peer's forge",
}


def observe_hosted_runs(root: Path, remote: str, provider: str, head: str) -> dict[str, object]:
    """Read one peer's runs of one exact commit, and the jobs that kept a run from passing."""
    observed: dict[str, object] = {"provider": provider, "head": head}
    unknown: dict[str, object] = {**observed, "state": "unknown", "runs": []}
    if provider not in _READERS:
        reason = "provider_unsupported"
        return {**unknown, "reason": reason, "next_action": _BY_HAND[reason]}
    resolved = forge_web_repository(root, remote)
    if resolved.gap:
        return {**unknown, "reason": resolved.gap, "next_action": resolved.next_action}
    url, listing = resolved.url, _READERS[provider][0]
    command = tuple(part.format(url=url, head=head, page=_PAGE) for part in listing.split())
    rows = provider_rows(root, provider, command, url)
    failed: _Unread = ("provider_query_failed", command)
    runs = failed if rows is None else _runs(root, provider, url, head, rows)
    if isinstance(runs, tuple):
        reason, query = runs
        action = shlex.join(query) if query else _BY_HAND[reason]
        return {**unknown, "reason": reason, "next_action": action}
    states = {run["state"] for run in runs}
    state = next((item for item in _ORDER if item in states), "no_run")
    return {**observed, "state": state, "runs": runs}


def _runs(
    root: Path, provider: str, url: str, head: str, rows: list[dict[str, object]]
) -> list[dict[str, object]] | _Unread:
    """Project each listed run, or name why the provider's answer states nothing."""
    if len(rows) >= _PAGE:
        return _UNUSABLE
    runs: list[dict[str, object]] = []
    for row in rows:
        run = _run(root, provider, url, head, row)
        if isinstance(run, tuple):
            return run
        runs.append(run)
    return runs


def _run(
    root: Path, provider: str, url: str, head: str, row: dict[str, object]
) -> dict[str, object] | _Unread:
    """Project one run of the commit; its jobs are read only when it failed or still runs."""
    _listing, reading, identity, commit = _READERS[provider]
    run, state = str(row.get(identity) or ""), _state(row)
    if not run or row.get(commit) != head or state == "unknown":
        return _UNUSABLE
    jobs: list[dict[str, object]] | None = []
    command: tuple[str, ...] = ()
    if state in _OPEN:
        command = tuple(part.format(url=url, run=run) for part in reading.split())
        jobs = provider_rows(root, provider, command, url, key="jobs")
    if jobs is None:
        return "provider_query_failed", command
    listed = [job for job in map(_job, jobs) if job["state"] not in _QUIET]
    return {"id": run, "state": state, "conclusion": _word(row), "jobs": listed}


def _word(row: dict[str, object]) -> str:
    """Return the provider's word for a row: its conclusion once it has one, else its status."""
    return str(row.get("conclusion") or row.get("status") or "")


def _state(row: dict[str, object]) -> str:
    """Return what a row's word means, or `unknown` for a word outside the table."""
    return _STATES.get(_word(row), "unknown")


def _job(job: dict[str, object]) -> dict[str, object]:
    """Project one job; a failed job that the provider marks as allowed to fail is told apart."""
    state = _state(job)
    if state == "failed" and job.get("allow_failure") is True:
        state = "allowed_failure"
    return {"name": str(job.get("name") or ""), "state": state, "conclusion": _word(job)}
