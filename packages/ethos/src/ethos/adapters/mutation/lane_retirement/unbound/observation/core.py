"""Fresh repository observations for exceptional unbound Work Lane retirement."""

import hashlib
import json
import os
import stat
import subprocess
import tomllib
from pathlib import Path
from typing import Any
from typing import cast

from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.repo.status.bindings import ref_head
from ethos.adapters.repo.status.core import workspace_status
from ethos_core.contracts.branch.roles import load_branch_role_policy

HAS_ACTIVE_LEASE = "has_active_lease"
HAS_LOCAL_CHRONICLE = "has_local_chronicle"
HAS_ACCEPTED_CHRONICLE = "has_accepted_chronicle"
HAS_LOCAL_CLAIM = "has_local_claim"
HAS_ACCEPTED_CLAIM = "has_accepted_claim"


def _keys(value: str) -> tuple[str, ...]:
    return tuple(value.split())


def _data(**values: Any) -> dict[str, Any]:
    return values


_CHRONICLE_TEXT = _keys(
    "sha256 accepted_sha256 event target_branch target_head target_claim "
    "claim_sha256 claim_accepted_sha256 lease_recovery source_lease_id "
    "source_lease_holder source_lease_epoch source_lease_expected_head "
    "source_worktree_path_sha256 source_worktree_absent"
)
_CHRONICLE_FLAGS = (
    HAS_LOCAL_CHRONICLE,
    HAS_ACCEPTED_CHRONICLE,
    "byte_identical_to_accepted",
    HAS_LOCAL_CLAIM,
    HAS_ACCEPTED_CLAIM,
    "claim_byte_identical_to_accepted",
    "claim_id_matches_target",
    "claim_active",
)
_PUBLIC_KEYS = _keys(
    "branch head accepted_head protected_refs status_unbound worktree_binding "
    "relation_to_accepted claim_id claim_binding has_active_lease "
    "chronicle observation_sha256"
)
_BINDING_KEYS = _keys(
    "head accepted_head protected_refs status_unbound worktree_binding "
    "relation_to_accepted claim_id claim_binding active_lease has_active_lease chronicle"
)
_RETIREMENT_KEYS = tuple(
    key for key in _BINDING_KEYS if key not in {"active_lease", HAS_ACTIVE_LEASE}
)
_CHRONICLE_BINDING_KEYS = _keys(
    "ref sha256 accepted_sha256 event target_branch target_head target_claim "
    "claim_sha256 claim_accepted_sha256 byte_identical_to_accepted "
    "claim_byte_identical_to_accepted has_accepted_chronicle has_accepted_claim "
    "lease_recovery source_lease_id source_lease_holder source_lease_epoch "
    "source_lease_expected_head source_worktree_path_sha256 source_worktree_absent"
)


def observe(repo: Path, *, branch: str, chronicle_ref: str) -> dict[str, object]:
    """Observe the exact target, policy, lease, and protected-ref state."""
    status, branch_policy = workspace_status(repo), load_branch_role_policy(repo)
    current, binding = unbound_work_lane_ref(status, branch), branch_binding(status, branch)
    worktrees = status.get("worktrees")
    typed = cast("list[dict[str, str]]", worktrees) if isinstance(worktrees, list) else []
    active_lease = leases_by_branch(typed, current_path=repo).get(branch, {})
    refs = protected_refs(
        branch_policy.release_branch, branch_policy.accepted_branch, branch_policy.candidate_branch
    )
    payload = _data(branch=branch, head=ref_head(repo, branch))
    payload |= _data(accepted_head=ref_head(repo, branch_policy.accepted_branch))
    payload |= _data(protected_refs={ref: ref_head(repo, ref) for ref in refs})
    payload |= _data(status_unbound=current is not None)
    payload |= _data(worktree_binding=str((binding or {}).get("worktree_binding") or ""))
    payload |= _data(relation_to_accepted=str((current or {}).get("relation_to_accepted") or ""))
    payload |= _data(claim_id=str((current or {}).get("claim_id") or ""))
    payload |= _data(claim_binding=str((current or {}).get("claim_binding") or ""))
    payload |= _data(active_lease=public_lease(active_lease), has_active_lease=bool(active_lease))
    payload |= _data(
        chronicle=chronicle_observation(
            repo, accepted_branch=branch_policy.accepted_branch, chronicle_ref=chronicle_ref
        ),
        status=status,
    )
    payload["observation_sha256"] = sha256(public_observation(payload))
    return payload


def protected_refs(release: str, accepted: str, candidate: str) -> tuple[str, ...]:
    """Return distinct protected refs required to remain stable."""
    return tuple(dict.fromkeys((release, accepted, candidate)))


def _chronicle(ref: str, *, valid: bool) -> dict[str, Any]:
    return (
        _data(ref=ref, path_valid=valid)
        | dict.fromkeys(_CHRONICLE_FLAGS, False)
        | dict.fromkeys(_CHRONICLE_TEXT, "")
    )


def _regular_bytes(path: Path) -> bytes | None:
    try:
        return path.read_bytes() if stat.S_ISREG(os.lstat(path).st_mode) else None
    except OSError:
        return None


def chronicle_observation(
    repo: Path, *, accepted_branch: str, chronicle_ref: str
) -> dict[str, object]:
    """Read a local Chronicle and compare it with accepted policy bytes."""
    path = chronicle_path(repo, chronicle_ref)
    result = _chronicle(chronicle_ref, valid=path is not None)
    local = _regular_bytes(path) if path else None
    if local is None:
        return result
    result.update(_data(has_local_chronicle=True, sha256=hashlib.sha256(local).hexdigest()))
    result.update(chronicle_fields(local))
    accepted = git_show_bytes(repo, f"{accepted_branch}:{chronicle_ref}")
    if accepted is None:
        return result
    result.update(
        _data(
            has_accepted_chronicle=True,
            accepted_sha256=hashlib.sha256(accepted).hexdigest(),
            byte_identical_to_accepted=accepted == local,
        )
    )
    result.update(
        claim_observation(
            repo, accepted_branch=accepted_branch, claim_id=str(result["target_claim"])
        )
    )
    return result


def chronicle_path(repo: Path, chronicle_ref: str) -> Path | None:
    """Accept only a regular Chronicle path under the local evidence root."""
    candidate = Path(chronicle_ref)
    if (
        not chronicle_ref
        or candidate.is_absolute()
        or not chronicle_ref.startswith("evidence/chronicle/")
    ):
        return None
    if any(part in {"", ".", ".."} for part in candidate.parts):
        return None
    try:
        path = repo / candidate
        return path if path.resolve().is_relative_to(repo.resolve()) else None
    except OSError:
        return None


def chronicle_fields(payload: bytes) -> dict[str, str]:
    """Extract the narrow target binding fields from a Chronicle."""
    try:
        lines = payload.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        return {}
    fields = (line.partition(":") for line in lines)
    return {
        key: value.strip()
        for key, separator, value in fields
        if separator
        and key
        in {
            "event",
            "target_branch",
            "target_head",
            "target_claim",
            "lease_recovery",
            "source_lease_id",
            "source_lease_holder",
            "source_lease_epoch",
            "source_lease_expected_head",
            "source_worktree_path_sha256",
            "source_worktree_absent",
        }
    }


def _claim() -> dict[str, object]:
    flags = _keys(
        "has_local_claim has_accepted_claim claim_byte_identical_to_accepted "
        "claim_id_matches_target claim_active"
    )
    return cast(
        "dict[str, object]",
        dict.fromkeys(flags, False)
        | dict.fromkeys(_keys("claim_sha256 claim_accepted_sha256"), ""),
    )


def claim_observation(repo: Path, *, accepted_branch: str, claim_id: str) -> dict[str, object]:
    """Compare the named active Claim with its accepted branch bytes."""
    result, relative = _claim(), claim_ref(claim_id)
    local = _regular_bytes(repo / relative) if relative else None
    if local is None:
        return result
    try:
        payload = tomllib.loads(local.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError):
        return result
    if not isinstance(payload, dict):
        return result
    claim = payload.get("claim")
    result.update(
        _data(
            has_local_claim=True,
            claim_sha256=hashlib.sha256(local).hexdigest(),
            claim_id_matches_target=isinstance(claim, dict)
            and str(claim.get("id") or "") == claim_id,
            claim_active=isinstance(claim, dict) and claim.get("state") == "active",
        )
    )
    accepted = git_show_bytes(repo, f"{accepted_branch}:{relative}")
    if accepted is not None:
        result.update(
            _data(
                has_accepted_claim=True,
                claim_accepted_sha256=hashlib.sha256(accepted).hexdigest(),
                claim_byte_identical_to_accepted=accepted == local,
            )
        )
    return result


def claim_ref(claim_id: str) -> str | None:
    """Return the canonical Claim path for a safe claim identifier."""
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")
    return f"evidence/claims/{claim_id}.toml" if claim_id and set(claim_id) <= allowed else None


def git_show_bytes(repo: Path, ref: str) -> bytes | None:
    """Return exact Git object bytes without turning read failure into authority."""
    completed = subprocess.run(["git", "show", ref], cwd=repo, check=False, capture_output=True)
    return completed.stdout if completed.returncode == 0 else None


def _project(
    source: dict[str, Any], keys: tuple[str, ...], *, present: bool = False
) -> dict[str, object]:
    return {
        key: source[key] if present else source.get(key, "")
        for key in keys
        if not present or key in source
    }


def public_observation(value: dict[str, object]) -> dict[str, object]:
    """Project only facts bound into an exceptional operation."""
    return _project(value, _PUBLIC_KEYS, present=True)


def operation_bindings(value: dict[str, object]) -> dict[str, object]:
    """Return every fact whose drift invalidates the admitted operation."""
    return _project(value, _BINDING_KEYS, present=True)


def retirement_bindings(value: dict[str, object]) -> dict[str, object]:
    """Return non-lease facts that must survive native relinquishment."""
    return _project(value, _RETIREMENT_KEYS, present=True)


def lease_relinquish_binding(value: dict[str, object]) -> dict[str, object]:
    """Return the exact active lease generation authorized for relinquishment."""
    lease = cast("dict[str, object]", value["active_lease"])
    active, epoch = bool(value[HAS_ACTIVE_LEASE]), lease.get("epoch")
    return _data(
        active=active,
        lease_id=str(lease.get("lease_id") or "") if active else "",
        holder_ref=str(lease.get("holder_ref") or "") if active else "",
        epoch=epoch if active and isinstance(epoch, int) and not isinstance(epoch, bool) else 0,
        expected_head=str(lease.get("expected_head") or "") if active else "",
    )


def chronicle_binding(source: dict[str, object]) -> dict[str, object]:
    """Project accepted Chronicle and Claim facts for identity checks."""
    chronicle = source.get("chronicle") if "chronicle" in source else source
    record = cast("dict[str, Any]", chronicle) if isinstance(chronicle, dict) else {}
    return _project(record, _CHRONICLE_BINDING_KEYS)


def public_lease(lease: dict[str, object]) -> dict[str, object]:
    """Project lease facts without exposing storage details."""
    payload = lease.get("payload")
    recorded_path = str(payload.get("path") or "") if isinstance(payload, dict) else ""
    return _project(lease, _keys("lease_id holder_ref epoch expected_head expires_at")) | {
        "recorded_path": recorded_path
    }


def _entry(items: object, branch: str) -> dict[str, object] | None:
    if not isinstance(items, list):
        return None
    match = next(
        (item for item in items if isinstance(item, dict) and item.get("branch") == branch), None
    )
    return cast("dict[str, object]", match) if match is not None else None


def unbound_work_lane_ref(status: dict[str, object], branch: str) -> dict[str, object] | None:
    """Find one unbound Work Lane reader entry."""
    coordination = status.get("coordination")
    refs = coordination.get("unbound_work_lane_refs") if isinstance(coordination, dict) else None
    return _entry(refs, branch)


def branch_binding(status: dict[str, object], branch: str) -> dict[str, object] | None:
    """Find one branch binding without trusting malformed status."""
    return _entry(status.get("branch_bindings"), branch)


def sha256(value: object) -> str:
    """Return a deterministic JSON digest for an operation observation."""
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
