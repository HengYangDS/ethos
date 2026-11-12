"""Refuse a push that adds a protected peer's identity beyond what that peer already advertises.

A push is read only as far as the commits it adds beyond every tip the peer advertises, so what the
peer already holds counts as disclosed and no history is scanned. The mode comes from the profile
of the commit that push admission already trusts, never from the working tree. An unreadable
advertisement is `unknown`, and a feed the clone cannot know refuses before any advertisement is
read. Gaps carry forms and positions, never a value.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING
from typing import Literal

from ethos.adapters.mutation.publication.observation import observe_remote_namespaces
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.invocation_facts import invocation_fact
from ethos.adapters.repo.peer_feed import local_feed
from ethos.adapters.repo.profile import load_committed_repository_profile
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.repository.paradigm.peer_identity import replacement_spans

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.repository.paradigm.peer_identity import Feed

Advertisement = Literal["network", "tracking"]
_ZERO = frozenset({"0" * 40, "0" * 64})
_HUNK = re.compile(r"^@@+ (?:-\S+ )+\+(\d+)(?:,\d+)? @@")


def peer_identity_push_gaps(
    repo: Path, *, remote: str, pushed: str, trusted: str, advertisement: Advertisement
) -> tuple[list[str], list[str]]:
    """Return one ref update's refusals and advisories; a deletion reads and adds nothing."""
    if pushed in _ZERO:
        return [], []
    mode = mode_at(repo, trusted)
    if mode is None:
        return [], ["peer_identity_mode_unread"]
    if mode != "required":
        return [], []
    known = local_feed(repo)
    if known.gaps:
        return list(known.gaps), []
    tips = _advertised(repo, remote) if advertisement == "network" else _tracking(repo, remote)
    if tips is None:
        return [f"peer_identity_range_unknown:{remote}"], []
    return added_literals(repo, pushed, tips, known.feed), []


def tracking_base(repo: Path, remote: str) -> str:
    """Return the remote-tracking accepted branch, the base a new branch falls back to."""
    branch = load_branch_role_policy(repo).accepted_branch
    found = run_git(
        repo, "rev-parse", "--verify", "--quiet", f"refs/remotes/{remote}/{branch}", check=False
    )
    return found.stdout.strip() if found.returncode == 0 else ""


def mode_at(repo: Path, trusted: str) -> str | None:
    """Read the mode at the trusted commit; a missing or invalid profile there is unread."""
    if not trusted or trusted in _ZERO:
        return None
    try:
        profile = load_committed_repository_profile(repo, trusted)
    except ValueError:
        return None
    if profile.state == "missing":
        return "disabled"
    if profile.declaration is None:
        return None
    return profile.declaration.peer_identity.mode


def _advertised(repo: Path, remote: str) -> tuple[str, ...] | None:
    """Read the peer's advertised tips once per process; an unreadable outcome is kept too."""
    return invocation_fact(("peer-advertisement", remote), lambda: _ls_remote(repo, remote))


def _ls_remote(repo: Path, remote: str) -> tuple[str, ...] | None:
    """Read the whole advertisement through the one bounded peer observer."""
    listed = observe_remote_namespaces(repo, remote, ())
    # A peeled `^{}` row names the commit an annotated tag points at, which is excluded as well.
    return None if listed.failure is not None else tuple(dict.fromkeys(listed.refs.values()))


def _tracking(repo: Path, remote: str) -> tuple[str, ...]:
    listed = run_git(
        repo, "for-each-ref", "--format=%(objectname)", f"refs/remotes/{remote}/", check=False
    )
    return tuple(line for line in listed.stdout.splitlines() if line)


def _present(repo: Path, objects: tuple[str, ...]) -> list[str]:
    """Return the objects held locally; a peer tip this repository lacks is skipped."""
    if not objects:
        return []
    request = "".join(f"{oid}\n" for oid in objects).encode()
    checked = run_git(repo, "cat-file", "--batch-check", stdin=request, text=False, check=False)
    return [
        line.split()[0].decode() for line in checked.stdout.splitlines() if b" missing" not in line
    ]


def added_literals(repo: Path, pushed: str, tips: tuple[str, ...], feed: Feed) -> list[str]:
    """Return a gap for each fed literal in the commits, messages and a tag the push adds."""
    gaps: list[str] = []
    if run_git(repo, "cat-file", "-t", pushed, check=False).stdout.strip() == "tag":
        message = run_git(repo, "cat-file", "-p", pushed).stdout.partition("\n\n")[2]
        gaps += _scan(message.splitlines(), feed, commit=0, file=0)
    request = "".join([f"{pushed}\n", *(f"^{tip}\n" for tip in _present(repo, tips))]).encode()
    listed = run_git(repo, "rev-list", "--stdin", stdin=request, text=False).stdout.decode()
    for number, revision in enumerate(listed.split(), 1):
        message = run_git(repo, "log", "-1", "--format=%B", revision).stdout
        gaps += _scan(message.splitlines(), feed, commit=number, file=0)
        gaps += _added(repo, revision, feed, commit=number)
    return gaps


def _added(repo: Path, revision: str, feed: Feed, *, commit: int) -> list[str]:
    """Scan the lines one revision adds; a merge is read as its combined diff."""
    shown = run_git(
        repo, "show", "--format=", "--unified=0", "--no-color", "--no-ext-diff", "--cc", revision
    )
    gaps: list[str] = []
    file, line = 0, 0
    for row in shown.stdout.splitlines():
        if row.startswith("+++ "):
            file += 1
        elif hunk := _HUNK.match(row):
            line = int(hunk.group(1))
        elif row.startswith("+") and file:
            gaps += [
                f"peer_identity_literal:{span.form}:{commit}:{file}:{line}"
                for span in replacement_spans(row[1:], feed)
            ]
            line += 1
        elif row.startswith(" "):
            line += 1
    return gaps


def _scan(lines: list[str], feed: Feed, *, commit: int, file: int) -> list[str]:
    return [
        f"peer_identity_literal:{span.form}:{commit}:{file}:{number}"
        for number, text in enumerate(lines, 1)
        for span in replacement_spans(text, feed)
    ]
