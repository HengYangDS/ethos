"""Observe accepted contribution conservation before retiring a review projection."""

from __future__ import annotations

import json
import shlex
import subprocess
from typing import TYPE_CHECKING
from typing import cast
from urllib.parse import urlsplit

import ethos.adapters.process as process
from ethos.adapters.mutation.publication.observation import observe_remote_ref
from ethos.adapters.repo.commit.rewrite import refreshed_object_provenance
from ethos.adapters.repo.commit.signature import repaired_object_provenance
from ethos.adapters.repo.git import committed_file_text
from ethos.adapters.repo.git import current_head
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git import is_ancestor
from ethos.adapters.repo.git import ref_head
from ethos.adapters.repo.git_object import zero_oid
from ethos.contracts.branch.roles import branch_role_policy_from_text
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.verdict import report_verdict
from ethos.repository.release.configuration import release_config_from_text
from ethos.repository.release.publication import publication_ref_role
from ethos.repository.release.publication import publication_topology

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path


def _accepted_contribution(root: Path, old: str, accepted: str) -> dict[str, object]:
    """Require ancestry or conserved native rewrite provenance, never patch-id."""
    if is_ancestor(root, old, accepted):
        return {"state": "ancestor", "old": old, "replacement": old}
    repair = repaired_object_provenance(root, old=old, new=accepted)
    if repair is not None:
        mapping = cast("Mapping[str, str]", repair["mapping"])
        return {
            "state": "repaired",
            "old": old,
            "replacement": mapping[old],
            "attestation_id": repair["attestation_id"],
        }
    return refreshed_object_provenance(root, old=old, new=accepted) or {
        "state": "not_absorbed",
        "old": old,
    }


def observe_proposal_review(
    root: Path, remote: str, provider: str, branch: str, *, repository: str = ""
) -> dict[str, object]:
    """Ask the declared provider for open reviews of one exact source branch."""
    if provider == "git":
        return {"verdict": "pass", "state": "not_applicable", "provider": provider}
    url = (
        repository
        or git_stdout(root, "config", "--local", "--get", f"remote.{remote}.forgeRepository")
        or git_stdout(root, "remote", "get-url", remote)
    )
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return {
            "verdict": "unknown",
            "state": "unavailable",
            "provider": provider,
            "remote": remote,
            "source_branch": branch,
            "reason": "forge_repository_required",
            "next_action": "Declare this peer's forge_repository in .ethos/release.toml",
        }
    commands = {
        "github": (
            "gh",
            "pr",
            "list",
            "--repo",
            url,
            "--state",
            "open",
            "--head",
            branch,
            "--limit",
            "1",
            "--json",
            "number,state,headRefName,url",
        ),
        "gitlab": (
            "glab",
            "mr",
            "list",
            "--repo",
            url,
            "--source-branch",
            branch,
            "--per-page",
            "1",
            "--output",
            "json",
        ),
    }
    command = commands.get(provider, ())
    result: dict[str, object] = {
        "verdict": "unknown",
        "state": "unavailable",
        "provider": provider,
        "remote": remote,
        "source_branch": branch,
        "command": list(command),
        "next_action": shlex.join(command) if command else "ethos status --json",
    }
    if not command or not url:
        return result
    environment = {"GH_PROMPT_DISABLED": "1", "GLAB_NO_PROMPT": "1"}
    if provider == "gitlab":
        environment["GITLAB_HOST"] = f"{parsed.scheme}://{parsed.netloc}"
    try:
        run = process.run_command(
            root,
            command,
            stdin="",
            timeout=30,
            env=environment,
        )
        result["exit_code"] = run.returncode
        if run.returncode:
            result.update(reason="provider_query_failed", stderr=run.stderr[-2000:])
            return result
        rows = json.loads(run.stdout)
        state_key, branch_key = (
            "state",
            "headRefName" if provider == "github" else "source_branch",
        )
        if not isinstance(rows, list) or any(
            not isinstance(item, dict)
            or item.get(branch_key) != branch
            or str(item.get(state_key)).lower() not in {"open", "opened"}
            for item in rows
        ):
            return result
        result.update(
            verdict="block" if rows else "pass", state="open" if rows else "closed", reviews=rows
        )
    except (ValueError, OSError, subprocess.TimeoutExpired):
        pass
    return result


def _retirement_context(root: Path, target_ref: str, remote: str) -> tuple[str, str, str, str]:
    """Read the accepted policy rather than letting unaccepted configuration grant deletion."""
    policy = load_branch_role_policy(root)
    accepted = ref_head(root, policy.accepted_branch)
    gap = "proposal_retirement_accepted_missing"
    if not accepted:
        raise ValueError(gap)
    committed = branch_role_policy_from_text(
        committed_file_text(root, accepted, ".ethos/workspace.toml")
    )
    gap = "proposal_retirement_policy_drift"
    if committed != policy:
        raise ValueError(gap)
    config = release_config_from_text(committed_file_text(root, accepted, ".ethos/release.toml"))
    topology = publication_topology(root, config)
    gap = "proposal_retirement_topology_invalid"
    if topology["required_gaps"]:
        raise ValueError(gap)
    _, role, _ = publication_ref_role(policy, target_ref, ())
    gap = "proposal_retirement_target_not_proposal"
    if role != "proposal_ref":
        raise ValueError(gap)
    peers = [
        peer
        for peer in cast("list[dict[str, object]]", topology["remotes"])
        if peer["git_remote"] == remote
    ]
    gap = "proposal_retirement_peer_unknown"
    if len(peers) != 1:
        raise ValueError(gap)
    return (
        accepted,
        policy.accepted_branch,
        str(peers[0]["provider"]),
        str(peers[0].get("forge_repository", "")),
    )


def _retirement_observations(
    root: Path, *, target_ref: str, old: str, remote: str
) -> dict[str, object]:
    """Keep absorption failures separate from unavailable peer/review observations."""
    accepted, accepted_branch, provider, repository = _retirement_context(root, target_ref, remote)
    zero = zero_oid(root)
    contribution = (
        {"state": "already_absent", "replacement": zero}
        if old == zero
        else _accepted_contribution(root, old, accepted)
    )
    result: dict[str, object] = {"accepted": accepted, "contribution": contribution}
    conservation = contribution.get("conservation")
    if isinstance(conservation, dict) and conservation.get("verdict") == "unknown":
        return {
            **result,
            "verdict": "unknown",
            "required_gaps": ["proposal_retirement_conservation_unknown"],
        }
    if contribution["state"] == "not_absorbed":
        return {**result, "verdict": "block", "required_gaps": ["proposal_retirement_not_accepted"]}
    peer = observe_remote_ref(root, remote, f"refs/heads/{accepted_branch}")
    result["peer_accepted"] = peer
    if peer["state"] == "unavailable":
        return {
            **result,
            "verdict": "unknown",
            "required_gaps": ["proposal_retirement_peer_accepted_unknown"],
        }
    if peer["state"] != "present" or (
        old != zero
        and not is_ancestor(root, str(contribution["replacement"]), str(peer["object_oid"]))
    ):
        return {
            **result,
            "verdict": "block",
            "required_gaps": ["proposal_retirement_peer_not_accepted"],
        }
    review = observe_proposal_review(
        root, remote, provider, target_ref.removeprefix("refs/heads/"), repository=repository
    )
    gaps = (
        []
        if review["verdict"] == "pass"
        else [
            "proposal_retirement_review_open"
            if review["state"] == "open"
            else "proposal_retirement_review_unknown"
        ]
    )
    return {
        **result,
        "verdict": review["verdict"],
        "review": review,
        "required_gaps": gaps,
        "next_action": review.get("next_action", ""),
    }


def proposal_retirement_report(
    root: Path, *, target_ref: str, old: str, remote: str
) -> dict[str, object]:
    """Expose one retirement admission to CLI, hooks and the effect executor."""
    try:
        observed = _retirement_observations(root, target_ref=target_ref, old=old, remote=remote)
    except (OSError, ValueError) as error:
        observed = {"verdict": "block", "required_gaps": [str(error)]}
    verdict = report_verdict(observed)
    return {
        **observed,
        "verdict": verdict,
        "state": "admitted" if verdict == "pass" else verdict,
        "role": "proposal_ref",
        "target_ref": target_ref,
        "target_branch": target_ref.removeprefix("refs/heads/"),
        "remote_name": remote,
        "remote_head": old,
        "mints_authority": False,
        "proof_admission": {"selection": "review_object", "attestation": {}},
        "decision": {
            "action": "allow" if verdict == "pass" else "block",
            "reason": "proposal_retirement",
        },
        "next_action": observed.get("next_action")
        or shlex.join(
            (
                "ethos",
                "publish",
                "--retire",
                "--ref",
                target_ref,
                "--probe-remote",
                "--expect-head",
                current_head(root),
                "--root",
                str(root),
                "--json",
            )
        ),
    }
