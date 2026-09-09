"""Accepted authorization and recovery for exact local Lease takeover."""

from __future__ import annotations

import os
import sqlite3
from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING

from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.attestation_set import record_attestations
from ethos.adapters.repo.dirty.change_provenance import dirty_content_sha256
from ethos.adapters.repo.git import current_head
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import repository_root
from ethos.adapters.repo.native_effect_attestation import NativeEffect
from ethos.adapters.repo.native_effect_attestation import issue_native_effect
from ethos.adapters.repo.profile import repository_identity
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.store.state.lease.lifecycle.transitions import takeover_lease
from ethos.adapters.store.state.lease.projection import integer_value
from ethos.adapters.store.state.schema import state_database

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.coordination import LeaseTakeoverRequest
    from ethos.contracts.semantic import Attestation


def execute_lease_takeover(*, root: Path, request: LeaseTakeoverRequest) -> dict[str, object]:
    """Execute one accepted exact Lease takeover."""
    repo = repository_root(root)
    observed = leases_by_branch(repo).get(request.branch, {})
    expected = _takeover_authorized_state(request)
    gaps = list(_takeover_gaps(repo, request, observed, expected))
    recovered = _takeover_already_applied(request, observed)
    if recovered:
        gaps = list(_takeover_authorization_gaps(repo, request, expected))
    verdict = "unknown" if any("unknown" in gap for gap in gaps) else "block" if gaps else "pass"
    lease: dict[str, object] = observed if recovered else {}
    attestation: Attestation | None = None
    if request.apply and verdict == "pass":
        before = {
            **expected,
            "head": current_head(repo),
            "tree": current_tree(repo),
            "dirty_content_sha256": dirty_content_sha256(repo),
        }
        try:
            lease = observed if recovered else takeover_lease(state_database(repo), request=request)
        except (sqlite3.Error, ValueError) as error:
            verdict, gaps = "block", [str(error)]
        else:
            after = {
                "branch": request.branch,
                "holder_ref": request.target_holder_ref,
                "generation": integer_value(lease.get("generation")),
                "expires_at": str(lease.get("expires_at") or ""),
                "head": current_head(repo),
                "tree": current_tree(repo),
                "dirty_content_sha256": dirty_content_sha256(repo),
            }
            candidate = issue_native_effect(
                repo,
                effect=NativeEffect(
                    predicate="lane-resolution:takeover",
                    operation="takeover",
                    command=("ethos", "lane", "lease", "takeover"),
                    subject={"branch": request.branch},
                    before=before,
                    after=after,
                ),
                state="recognized" if recovered else "applied",
                commitment_digest=request.authorization.commitment_digest,
                repository_id=repository_identity(repo),
                issued_at=datetime.now(UTC),
            )
            record_attestations(repo, (candidate,))
            attestation = candidate
    state = (
        "taken_over"
        if verdict == "pass" and request.apply
        else "planned"
        if verdict == "pass"
        else "blocked"
    )
    return {
        "verdict": verdict,
        "state": state,
        "branch": request.branch,
        "source_state": request.source_state,
        "lease": lease,
        "attestation": attestation.model_dump(mode="json") if attestation else {},
        "required_gaps": gaps,
    }


def _takeover_authorized_state(request: LeaseTakeoverRequest) -> dict[str, object]:
    return {
        "branch": request.branch,
        "holder_ref": request.source_holder_ref,
        "generation": request.generation,
        "expires_at": request.expires_at,
        "target_holder_ref": request.target_holder_ref,
        "source_state": request.source_state,
    }


def _takeover_gaps(
    repo: Path,
    request: LeaseTakeoverRequest,
    observed: dict[str, object],
    expected: dict[str, object],
) -> tuple[str, ...]:
    lease_state = str(observed.get("lease_state") or "missing")
    current = {
        "branch": str(observed.get("lane_ref") or observed.get("subject") or ""),
        "holder_ref": str(observed.get("holder_ref") or ""),
        "generation": integer_value(observed.get("generation")),
        "expires_at": str(observed.get("expires_at") or ""),
        "target_holder_ref": request.target_holder_ref,
        "source_state": request.source_state,
    }
    checks = (
        (lease_state in {"valid", "expired"}, "lease_takeover_lease_unknown"),
        (current == expected, "lease_takeover_generation_drift"),
    )
    return tuple(gap for valid, gap in checks if not valid) + _takeover_authorization_gaps(
        repo, request, expected
    )


def _takeover_authorization_gaps(
    repo: Path,
    request: LeaseTakeoverRequest,
    expected: dict[str, object],
) -> tuple[str, ...]:
    authorization = request.authorization
    try:
        _root, attestations = read_attestation_set(repo)
        accepted = next((item for item in attestations if item.id == authorization.id), None)
    except ValueError:
        accepted = None
    now = datetime.now(UTC)
    checks = (
        (
            os.environ.get("ETHOS_ACTOR", "").strip() == request.target_holder_ref,
            "lease_takeover_actor_mismatch",
        ),
        (accepted == authorization, "lease_takeover_authorization_unaccepted"),
        (
            authorization.predicate == "lane-resolution:takeover",
            "lease_takeover_authorization_kind",
        ),
        (authorization.verdict == "pass", "lease_takeover_authorization_blocked"),
        (
            authorization.subject == f"git:branch:{request.branch}",
            "lease_takeover_authorization_subject_drift",
        ),
        (
            (authorization.valid_from or authorization.issued_at) <= now
            and (authorization.valid_until is None or now <= authorization.valid_until),
            "lease_takeover_authorization_stale",
        ),
        (
            authorization.payload.body.get("authorization") == expected,
            "lease_takeover_authorization_drift",
        ),
    )
    return tuple(gap for valid, gap in checks if not valid)


def _takeover_already_applied(
    request: LeaseTakeoverRequest,
    observed: dict[str, object],
) -> bool:
    return (
        str(observed.get("lane_ref") or observed.get("subject") or "") == request.branch
        and str(observed.get("holder_ref") or "") == request.target_holder_ref
        and integer_value(observed.get("generation")) == request.generation + 1
    )
