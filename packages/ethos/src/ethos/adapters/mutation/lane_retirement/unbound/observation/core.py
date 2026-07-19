"""Fresh repository observations for exceptional unbound Work Lane retirement."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
import tomllib
from pathlib import Path
from typing import cast

from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.status.core import workspace_status
from ethos_core.contracts.branch.roles import load_branch_role_policy

HAS_ACTIVE_LEASE = "has_active_lease"
HAS_LOCAL_CHRONICLE = "has_local_chronicle"
HAS_ACCEPTED_CHRONICLE = "has_accepted_chronicle"
HAS_LOCAL_CLAIM = "has_local_claim"
HAS_ACCEPTED_CLAIM = "has_accepted_claim"


def observe(repo: Path, *, branch: str, chronicle_ref: str) -> dict[str, object]:
    """Observe the exact target, policy, lease, and protected-ref state."""
    status = workspace_status(repo)
    policy = load_branch_role_policy(repo)
    current = unbound_work_lane_ref(status, branch)
    binding = branch_binding(status, branch)
    worktrees = status.get("worktrees")
    typed_worktrees = cast("list[dict[str, str]]", worktrees) if isinstance(worktrees, list) else []
    active_lease = leases_by_branch(typed_worktrees, current_path=repo).get(branch, {})
    payload: dict[str, object] = {
        "branch": branch,
        "head": ref_head(repo, branch),
        "accepted_head": ref_head(repo, policy.accepted_branch),
        "protected_refs": {
            ref: ref_head(repo, ref)
            for ref in protected_refs(
                policy.release_branch, policy.accepted_branch, policy.candidate_branch
            )
        },
        "status_unbound": current is not None,
        "worktree_binding": str((binding or {}).get("worktree_binding") or ""),
        "relation_to_accepted": str((current or {}).get("relation_to_accepted") or ""),
        "claim_id": str((current or {}).get("claim_id") or ""),
        "claim_binding": str((current or {}).get("claim_binding") or ""),
        "active_lease": public_lease(active_lease),
        HAS_ACTIVE_LEASE: bool(active_lease),
        "chronicle": chronicle_observation(
            repo,
            accepted_branch=policy.accepted_branch,
            chronicle_ref=chronicle_ref,
        ),
        "status": status,
    }
    payload["observation_sha256"] = sha256(public_observation(payload))
    return payload


def protected_refs(release: str, accepted: str, candidate: str) -> tuple[str, ...]:
    """Return the distinct protected refs whose stability the effect requires."""
    return tuple(dict.fromkeys((release, accepted, candidate)))


def chronicle_observation(
    repo: Path,
    *,
    accepted_branch: str,
    chronicle_ref: str,
) -> dict[str, object]:
    """Read a local Chronicle and compare it with the accepted policy bytes."""
    path = chronicle_path(repo, chronicle_ref)
    observation: dict[str, object] = {
        "ref": chronicle_ref,
        "path_valid": path is not None,
        HAS_LOCAL_CHRONICLE: False,
        HAS_ACCEPTED_CHRONICLE: False,
        "byte_identical_to_accepted": False,
        "sha256": "",
        "accepted_sha256": "",
        "event": "",
        "target_branch": "",
        "target_head": "",
        "target_claim": "",
        HAS_LOCAL_CLAIM: False,
        HAS_ACCEPTED_CLAIM: False,
        "claim_byte_identical_to_accepted": False,
        "claim_sha256": "",
        "claim_accepted_sha256": "",
        "claim_id_matches_target": False,
        "claim_active": False,
    }
    if path is None:
        return observation
    try:
        if not stat.S_ISREG(os.lstat(path).st_mode):
            return observation
        local = path.read_bytes()
    except OSError:
        return observation
    observation[HAS_LOCAL_CHRONICLE] = True
    observation["sha256"] = hashlib.sha256(local).hexdigest()
    observation.update(chronicle_fields(local))
    accepted = git_show_bytes(repo, f"{accepted_branch}:{chronicle_ref}")
    if accepted is None:
        return observation
    observation[HAS_ACCEPTED_CHRONICLE] = True
    observation["accepted_sha256"] = hashlib.sha256(accepted).hexdigest()
    observation["byte_identical_to_accepted"] = accepted == local
    observation.update(
        claim_observation(
            repo,
            accepted_branch=accepted_branch,
            claim_id=str(observation["target_claim"]),
        )
    )
    return observation


def chronicle_path(repo: Path, chronicle_ref: str) -> Path | None:
    """Accept only a regular Chronicle path under the local evidence root."""
    if not chronicle_ref:
        return None
    candidate = Path(chronicle_ref)
    if (
        candidate.is_absolute()
        or any(part in {"", ".", ".."} for part in candidate.parts)
        or not chronicle_ref.startswith("evidence/chronicle/")
    ):
        return None
    path = repo / candidate
    try:
        return path if path.resolve().is_relative_to(repo.resolve()) else None
    except OSError:
        return None


def chronicle_fields(payload: bytes) -> dict[str, str]:
    """Extract the narrow target binding fields from a Chronicle."""
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        return {}
    fields: dict[str, str] = {}
    for line in text.splitlines():
        key, separator, value = line.partition(":")
        if separator and key in {
            "event",
            "target_branch",
            "target_head",
            "target_claim",
        }:
            fields[key] = value.strip()
    return fields


def claim_observation(
    repo: Path,
    *,
    accepted_branch: str,
    claim_id: str,
) -> dict[str, object]:
    """Compare the named active Claim with its accepted branch bytes."""
    relative = claim_ref(claim_id)
    observation: dict[str, object] = {
        HAS_LOCAL_CLAIM: False,
        HAS_ACCEPTED_CLAIM: False,
        "claim_byte_identical_to_accepted": False,
        "claim_sha256": "",
        "claim_accepted_sha256": "",
        "claim_id_matches_target": False,
        "claim_active": False,
    }
    if relative is None:
        return observation
    path = repo / relative
    try:
        if not stat.S_ISREG(os.lstat(path).st_mode):
            return observation
        local = path.read_bytes()
        payload = tomllib.loads(local.decode("utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return observation
    claim = payload.get("claim") if isinstance(payload, dict) else {}
    observation[HAS_LOCAL_CLAIM] = True
    observation["claim_sha256"] = hashlib.sha256(local).hexdigest()
    observation["claim_id_matches_target"] = (
        isinstance(claim, dict) and str(claim.get("id") or "") == claim_id
    )
    observation["claim_active"] = isinstance(claim, dict) and claim.get("state") == "active"
    accepted = git_show_bytes(repo, f"{accepted_branch}:{relative}")
    if accepted is None:
        return observation
    observation[HAS_ACCEPTED_CLAIM] = True
    observation["claim_accepted_sha256"] = hashlib.sha256(accepted).hexdigest()
    observation["claim_byte_identical_to_accepted"] = accepted == local
    return observation


def claim_ref(claim_id: str) -> str | None:
    """Return the canonical Claim path for a safe claim identifier."""
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")
    return f"evidence/claims/{claim_id}.toml" if claim_id and set(claim_id) <= allowed else None


def git_show_bytes(repo: Path, ref: str) -> bytes | None:
    """Return exact Git object bytes without turning a read failure into authority."""
    completed = subprocess.run(["git", "show", ref], cwd=repo, check=False, capture_output=True)
    return completed.stdout if completed.returncode == 0 else None


def public_observation(observation: dict[str, object]) -> dict[str, object]:
    """Project only the facts bound into an exceptional operation."""
    return {
        key: observation[key]
        for key in (
            "branch",
            "head",
            "accepted_head",
            "protected_refs",
            "status_unbound",
            "worktree_binding",
            "relation_to_accepted",
            "claim_id",
            "claim_binding",
            HAS_ACTIVE_LEASE,
            "chronicle",
            "observation_sha256",
        )
        if key in observation
    }


def operation_bindings(observation: dict[str, object]) -> dict[str, object]:
    """Return every fact whose drift invalidates the admitted operation."""
    return {
        key: observation[key]
        for key in (
            "head",
            "accepted_head",
            "protected_refs",
            "status_unbound",
            "worktree_binding",
            "relation_to_accepted",
            "claim_id",
            "claim_binding",
            "active_lease",
            HAS_ACTIVE_LEASE,
            "chronicle",
        )
    }


def retirement_bindings(observation: dict[str, object]) -> dict[str, object]:
    """Return bindings that must survive lease relinquishment before ref deletion."""
    return {
        key: observation[key]
        for key in (
            "head",
            "accepted_head",
            "protected_refs",
            "status_unbound",
            "worktree_binding",
            "relation_to_accepted",
            "claim_id",
            "claim_binding",
            "chronicle",
        )
    }


def lease_relinquish_binding(observation: dict[str, object]) -> dict[str, object]:
    """Return the exact active lease generation authorized for native relinquishment."""
    lease = cast("dict[str, object]", observation["active_lease"])
    active = bool(observation[HAS_ACTIVE_LEASE])
    return {
        "active": active,
        "lease_id": str(lease.get("lease_id") or "") if active else "",
        "holder_ref": str(lease.get("holder_ref") or "") if active else "",
        "epoch": int(lease.get("epoch") or 0) if active else 0,
        "expected_head": str(lease.get("expected_head") or "") if active else "",
    }


def chronicle_binding(source: dict[str, object]) -> dict[str, object]:
    """Project accepted Chronicle and Claim facts for operation identity checks."""
    chronicle = source.get("chronicle") if "chronicle" in source else source
    record = cast("dict[str, object]", chronicle) if isinstance(chronicle, dict) else {}
    return {
        key: record.get(key, "")
        for key in (
            "ref",
            "sha256",
            "accepted_sha256",
            "event",
            "target_branch",
            "target_head",
            "target_claim",
            "claim_sha256",
            "claim_accepted_sha256",
            "byte_identical_to_accepted",
            "claim_byte_identical_to_accepted",
            HAS_ACCEPTED_CHRONICLE,
            HAS_ACCEPTED_CLAIM,
        )
    }


def public_lease(lease: dict[str, object]) -> dict[str, object]:
    """Project lease facts without exposing storage implementation details."""
    return {
        key: lease.get(key, "")
        for key in ("lease_id", "holder_ref", "epoch", "expected_head", "expires_at")
    }


def ref_head(repo: Path, ref: str) -> str:
    """Return a ref head or an empty string when it is absent or unreadable."""
    completed = subprocess.run(
        ["git", "rev-parse", "--verify", ref],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip() if completed.returncode == 0 else ""


def unbound_work_lane_ref(status: dict[str, object], branch: str) -> dict[str, object] | None:
    """Find one unbound Work Lane reader entry without trusting malformed status."""
    coordination = status.get("coordination")
    refs = coordination.get("unbound_work_lane_refs") if isinstance(coordination, dict) else None
    if not isinstance(refs, list):
        return None
    for ref in refs:
        if isinstance(ref, dict) and ref.get("branch") == branch:
            return cast("dict[str, object]", ref)
    return None


def branch_binding(status: dict[str, object], branch: str) -> dict[str, object] | None:
    """Find one branch binding without trusting malformed status."""
    bindings = status.get("branch_bindings")
    if not isinstance(bindings, list):
        return None
    for binding in bindings:
        if isinstance(binding, dict) and binding.get("branch") == branch:
            return cast("dict[str, object]", binding)
    return None


def sha256(value: object) -> str:
    """Return a deterministic JSON digest for an operation observation."""
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
