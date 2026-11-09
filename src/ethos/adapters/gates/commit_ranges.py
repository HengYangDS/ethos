"""Validate, with the checkout's own policy, the commits that its next publications will carry."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.repo.commit.integration import commit_range_admission_report
from ethos.adapters.repo.git import run_git
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.verdict import close_verdict
from ethos.normalization.coercion import string_sequence
from ethos.repository.release.configuration import release_config
from ethos.repository.release.publication import publication_topology
from ethos.repository.release.publication import topology_remotes

if TYPE_CHECKING:
    from pathlib import Path


def commit_ranges_report(root: Path, *, current_head: str) -> dict[str, object]:
    """Judge each configured peer's accepted and release range from its tracking tip.

    The commit policy is chosen per revision, so peers and branches that share a tip share one
    judged range. A checkout that configures no declared peer starts no publication, so nothing
    applies; a configured peer without a tip for one branch is a note, and without any tip it
    refuses. Nothing in the repository is written.
    """
    topology = publication_topology(root, release_config(root))
    # An invalid declaration names itself; it must not read as a checkout that publishes nowhere.
    if declaration := list(string_sequence(topology.get("required_gaps"), drop_empty=True)):
        return {"verdict": "block", "applicable": True, "targets": [], "required_gaps": declaration}
    configured = set(run_git(root, "remote").stdout.split())
    remotes = [name for name in topology_remotes(topology).values() if name in configured]
    if not remotes:
        return {
            "verdict": "pass",
            "applicable": False,
            "targets": [],
            "diagnostics": [_note("commit_ranges_no_peer_remote", "no declared peer remote")],
        }
    policy = load_branch_role_policy(root)
    notes: list[dict[str, str]] = []
    ranges: dict[str, list[tuple[str, str]]] = {}
    for remote in remotes:
        for branch in (policy.accepted_branch, policy.release_branch):
            if tip := _tip(root, f"refs/remotes/{remote}/{branch}"):
                ranges.setdefault(tip, []).append((remote, branch))
            else:
                code = f"commit_ranges_peer_unobserved:{remote}:{branch}"
                notes.append(_note(code, f"git fetch {remote}"))
    targets: list[dict[str, object]] = []
    gaps: list[str] = []
    for tip, holders in ranges.items():
        remote, branch = holders[0]
        report = commit_range_admission_report(
            root,
            target_ref=f"refs/heads/{branch}",
            proposed_head=current_head,
            remote_head=tip,
            remote_name=remote,
        )
        gaps.extend(string_sequence(report.get("required_gaps"), drop_empty=True))
        targets.append(
            {
                "baseline": tip,
                "holders": [f"{name}/{held}" for name, held in holders],
                "checked_commit_count": report.get("checked_commit_count"),
                "verdict": report.get("verdict"),
            }
        )
    if not targets:
        gaps.append("commit_ranges_unobserved")
    unique = list(dict.fromkeys(gaps))
    return {
        "verdict": close_verdict("pass", required_gaps=tuple(unique)),
        "applicable": True,
        "targets": targets,
        "required_gaps": unique,
        "diagnostics": notes,
    }


def _tip(root: Path, ref: str) -> str:
    """Return the commit a tracking ref names, or nothing when the checkout never observed it."""
    completed = run_git(root, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}", check=False)
    return completed.stdout.strip() if completed.returncode == 0 else ""


def _note(code: str, action: str) -> dict[str, str]:
    """Return an advisory, which the gate runner records without promoting it to a gap."""
    return {"severity": "note", "code": code, "message": f"{code}; next: {action}"}
