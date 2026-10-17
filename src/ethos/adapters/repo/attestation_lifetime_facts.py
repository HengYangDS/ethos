"""Observe the repository facts that can end Attestation lifetimes, or report them unobservable."""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING
from typing import Final

from ethos.adapters.repo.attestation_lifetime import LifetimeFacts
from ethos.adapters.repo.attestation_lifetime import latest_publications
from ethos.adapters.repo.attestation_lifetime import lifetime
from ethos.adapters.repo.git import run_git

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.semantic import Attestation

REFS_UNAVAILABLE: Final = "attestation_lifetime_refs_unavailable"
REACHABILITY_UNAVAILABLE: Final = "attestation_lifetime_reachability_unavailable"
UNOBSERVABLE_FACTS: Final = frozenset({REFS_UNAVAILABLE, REACHABILITY_UNAVAILABLE})


def observe_lifetime_facts(repo: Path, members: tuple[Attestation, ...]) -> LifetimeFacts:
    """Observe the refs, pinned commits and pre-repair objects that can end lifetimes."""
    shown = run_git(repo, "show-ref", "--dereference", check=False, observation=True)
    if shown.returncode not in {0, 1} or shown.stderr:
        raise ValueError(REFS_UNAVAILABLE)
    refs: dict[str, str] = {}
    pinned: set[str] = set()
    for row in shown.stdout.splitlines():
        object_id, name = row.split(" ", maxsplit=1)
        if name.endswith("^{}"):
            pinned.add(object_id)
        else:
            refs[name] = object_id
    worktrees = run_git(repo, "worktree", "list", "--porcelain", observation=True).stdout
    pinned.update(
        line.removeprefix("HEAD ") for line in worktrees.splitlines() if line.startswith("HEAD ")
    )
    olds = sorted(
        {
            old
            for kind, key in (lifetime(member) for member in members)
            if kind == "lineage" and key.startswith("repair:")
            for old in key.removeprefix("repair:").split()
        }
    )
    checked = (
        run_git(
            repo,
            "cat-file",
            "--batch-check",
            stdin="".join(f"{old}\n" for old in olds),
            observation=True,
        ).stdout.splitlines()
        if olds
        else []
    )
    absent = frozenset(line.split()[0] for line in checked if line.endswith(" missing"))
    tips = {*refs.values(), *pinned, *latest_publications(members), *(set(olds) - absent)}
    return LifetimeFacts(
        refs=refs,
        pinned=frozenset(pinned),
        absent_objects=absent,
        now=datetime.now(UTC),
        reachable=_reachable_commits(repo, tips),
    )


def _reachable_commits(repo: Path, tips: set[str]) -> frozenset[str]:
    """Walk every commit the selected tips reach; a missing tip would hide ancestry."""
    kinds = run_git(
        repo,
        "cat-file",
        "--batch-check=%(objectname) %(objecttype)",
        stdin="".join(f"{tip}\n" for tip in sorted(tips)),
        observation=True,
    ).stdout.splitlines()
    if any(line.endswith(" missing") for line in kinds) or len(kinds) != len(tips):
        raise ValueError(REACHABILITY_UNAVAILABLE)
    commits = [line.split()[0] for line in kinds if line.split()[1] in {"commit", "tag"}]
    if not commits:
        return frozenset()
    walked = run_git(
        repo,
        "rev-list",
        "--stdin",
        stdin="".join(f"{commit}\n" for commit in commits),
        check=False,
        observation=True,
    )
    if walked.returncode or walked.stderr:
        raise ValueError(REACHABILITY_UNAVAILABLE)
    return frozenset(walked.stdout.split())
