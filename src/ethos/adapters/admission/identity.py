"""Configured Git identity admission for newly pushed commits."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from ethos.adapters.repo.git import run_git

_ZERO = "0" * 40
_IDENTITY_FIELDS = ("author_name", "author_email", "committer_name", "committer_email")


@dataclass(frozen=True, slots=True)
class ReconciliationObservation:
    """Observed heads and exact receipt for one reconciliation attempt."""

    proposal_branch: str = ""
    receipt_path: str = ""
    peer_heads: tuple[tuple[str, str, str], ...] = ()


_NO_RECONCILIATION = ReconciliationObservation()


def _git(root: Path, *args: str):
    return run_git(root, *args, check=False)


def commit_contained_in(root: Path, commit: str, branch: str) -> bool:
    """Return whether Git proves commit is contained in branch."""
    return _git(root, "merge-base", "--is-ancestor", commit, branch).returncode == 0


def _exists(root: Path, revision: str) -> bool:
    return (
        bool(revision and revision != _ZERO)
        and _git(root, "cat-file", "-e", f"{revision}^{{commit}}").returncode == 0
    )


def _pushed_commit_range(
    root: Path, *, pushed_head: str, remote_head: str
) -> tuple[list[str], bool]:
    if not _exists(root, pushed_head):
        return [], False
    revision = f"{remote_head}..{pushed_head}" if _exists(root, remote_head) else pushed_head
    result = _git(root, "rev-list", revision)
    return (result.stdout.splitlines(), True) if result.returncode == 0 else ([], False)


def _pushed_commit_range_excluding(
    root: Path, *, pushed_head: str, trusted_baselines: tuple[str, ...]
) -> tuple[list[str], bool]:
    if not _exists(root, pushed_head):
        return [], False
    result = _git(root, "rev-list", pushed_head, "--not", *trusted_baselines)
    return (result.stdout.splitlines(), True) if result.returncode == 0 else ([], False)


def _commit_identity(root: Path, revision: str) -> dict[str, str]:
    result = _git(root, "show", "-s", "--format=%an%x00%ae%x00%cn%x00%ce", revision)
    parts = result.stdout.rstrip("\n").split("\x00")
    return (
        dict(zip(_IDENTITY_FIELDS, parts, strict=True))
        if result.returncode == 0 and len(parts) == len(_IDENTITY_FIELDS)
        else dict.fromkeys(_IDENTITY_FIELDS, "")
    )


def _range_base(root: Path, pushed: str, remote: str, trusted: str) -> tuple[str, list[str]]:
    if remote != _ZERO or not trusted:
        return remote, []
    if not _exists(root, trusted):
        return "", [f"push_identity_proposal_baseline_missing:{trusted}"]
    if not _exists(root, pushed) or commit_contained_in(root, trusted, pushed):
        return trusted, []
    return "", [f"push_identity_proposal_baseline_not_ancestor:{trusted}"]


def reconciliation_receipt_payload(
    *,
    proposal_branch: str,
    source_head: str,
    peer_heads: tuple[tuple[str, str, str], ...],
) -> dict[str, object]:
    """Build the deterministic non-authorizing reconciliation observation."""
    payload: dict[str, object] = {
        "schema_version": 1,
        "kind": "proposal-reconciliation",
        "proposal_branch": proposal_branch,
        "source_head": source_head,
        "peer_heads": [
            {
                "id": peer_id,
                "accepted_head": accepted_head,
                "release_head": release_head,
            }
            for peer_id, accepted_head, release_head in peer_heads
        ],
        "mints_authority": False,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return {**payload, "payload_digest": hashlib.sha256(encoded).hexdigest()}


def _read_reconciliation_receipt(path: str) -> dict[str, object] | None:
    if not path:
        return None
    try:
        payload = json.loads(Path(path).expanduser().resolve().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _reconciliation_baselines(
    root: Path,
    *,
    pushed_head: str,
    primary_baseline: str,
    observation: ReconciliationObservation,
) -> tuple[tuple[str, ...], list[str]]:
    if (not observation.proposal_branch and not observation.receipt_path) or not _exists(
        root, pushed_head
    ):
        return (), []
    primary_suffices = _exists(root, primary_baseline) and commit_contained_in(
        root, primary_baseline, pushed_head
    )
    if not observation.receipt_path:
        return (
            ((), [])
            if primary_suffices
            else ((), ["push_identity_reconciliation_receipt_required"])
        )
    receipt = _read_reconciliation_receipt(observation.receipt_path)
    if receipt is None:
        return (), ["push_identity_reconciliation_receipt_invalid"]
    expected = reconciliation_receipt_payload(
        proposal_branch=observation.proposal_branch or str(receipt.get("proposal_branch") or ""),
        source_head=pushed_head,
        peer_heads=_receipt_peer_heads(receipt),
    )
    gaps = [
        f"push_identity_reconciliation_receipt_{field}_mismatch"
        for field, value in expected.items()
        if receipt.get(field) != value
    ]
    receipt_heads = _receipt_peer_heads(receipt)
    if observation.peer_heads != receipt_heads:
        gaps.append("push_identity_reconciliation_peer_heads_stale")
    baselines = tuple(
        head
        for _peer_id, accepted_head, release_head in receipt_heads
        for head in (accepted_head, release_head)
        if head
    )
    gaps.extend(
        f"push_identity_reconciliation_baseline_missing:{head}"
        for head in baselines
        if not _exists(root, head)
    )
    return (baselines, []) if not gaps else ((), gaps)


def _receipt_peer_heads(receipt: dict[str, object]) -> tuple[tuple[str, str, str], ...]:
    rows = receipt.get("peer_heads")
    if not isinstance(rows, list):
        return ()
    return tuple(
        (
            str(row.get("id") or ""),
            str(row.get("accepted_head") or ""),
            str(row.get("release_head") or ""),
        )
        for row in rows
        if isinstance(row, dict)
    )


def push_identity_policy_report(
    root: Path,
    pushed_head: str,
    remote_head: str = "",
    trusted_baseline: str = "",
    reconciliation: ReconciliationObservation = _NO_RECONCILIATION,
) -> dict[str, object]:
    """Require configured author and committer identity for newly pushed commits."""
    mode = _git(root, "config", "--get", "ethos.pushIdentityPolicy").stdout.strip()
    if mode != "configured-user":
        return {
            "verdict": "pass",
            "mode": mode or "disabled",
            "expected_identity": "",
            "checked_commit_count": 0,
            "violations": [],
            "required_gaps": [],
        }
    name = _git(root, "config", "--get", "user.name").stdout.strip()
    email = _git(root, "config", "--get", "user.email").stdout.strip()
    gaps = [
        gap
        for value, gap in (
            (name, "push_identity_user_name_missing"),
            (email, "push_identity_user_email_missing"),
        )
        if not value
    ]
    head_exists = _exists(root, pushed_head)
    baselines, reconciliation_gaps = _reconciliation_baselines(
        root,
        pushed_head=pushed_head,
        primary_baseline=trusted_baseline,
        observation=reconciliation,
    )
    range_base, baseline_gaps = _range_base(root, pushed_head, remote_head, trusted_baseline)
    gaps.extend(reconciliation_gaps)
    if not baselines:
        gaps.extend(baseline_gaps)
    commits, range_readable = (
        _pushed_commit_range_excluding(root, pushed_head=pushed_head, trusted_baselines=baselines)
        if baselines
        else _pushed_commit_range(root, pushed_head=pushed_head, remote_head=range_base)
        if head_exists and not baseline_gaps
        else ([], True)
    )
    if pushed_head and (not head_exists or not range_readable):
        gaps.append("push_identity_commit_range_unreadable")
    violations = []
    for commit in commits:
        identity = _commit_identity(root, commit)
        author_ok = (identity["author_name"], identity["author_email"]) == (name, email)
        committer_ok = (identity["committer_name"], identity["committer_email"]) == (name, email)
        if author_ok and committer_ok:
            continue
        violations.append(
            {
                "commit": commit,
                "author": f"{identity['author_name']} <{identity['author_email']}>",
                "committer": f"{identity['committer_name']} <{identity['committer_email']}>",
            }
        )
        if not author_ok:
            gaps.append(f"pushed_commit_author_not_configured_identity:{commit}")
        if not committer_ok:
            gaps.append(f"pushed_commit_committer_not_configured_identity:{commit}")
    return {
        "verdict": "block" if gaps else "pass",
        "mode": mode,
        "expected_identity": f"{name} <{email}>" if name or email else "",
        "checked_commit_count": len(commits),
        "violations": violations,
        "required_gaps": gaps,
    }
