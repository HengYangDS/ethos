"""Intake-ledger projection reducer for adopted repositories."""

from __future__ import annotations

import subprocess
import tomllib
from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:
    from pathlib import Path


def intake_projection_report(repo: Path) -> dict[str, Any]:
    """Project the intake-ledger configuration state (a non-truth projection)."""
    config_path = repo / ".ethos" / "intake.toml"
    gaps: list[str] = []
    provider = "unconfigured"
    configured = False
    if config_path.exists():
        try:
            config = tomllib.loads(config_path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError:
            provider = "invalid"
            gaps.append("intake_config_invalid:.ethos/intake.toml")
        else:
            configured_provider = str(config.get("provider") or "").strip()
            if configured_provider:
                provider = configured_provider
                configured = True
            else:
                provider = "invalid"
                gaps.append("intake_provider_missing:.ethos/intake.toml")
    state = "configured" if configured else "invalid" if gaps else "unconfigured"
    return {
        "kind": "intake_projection",
        "state": state,
        "truth_boundary": "projection-evidence",
        "repository_truth": False,
        "provider": provider,
        "configured": configured,
        "expected_config": ".ethos/intake.toml",
        "adapters": ["backlog", "github", "gitlab"],
        "blocking": False,
        "required_gaps": gaps,
    }


def intake_mine_report(repo: Path) -> dict[str, Any]:
    """Mine repository signals into issue candidates without mutating the repository."""
    envelopes: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    head = _git_head(repo)
    claims_dir = repo / "evidence" / "claims"
    if claims_dir.exists():
        for claim_path in sorted(claims_dir.glob("*.toml")):
            _mine_claim_file(
                repo=repo,
                claim_path=claim_path,
                current_head=head,
                envelopes=envelopes,
                candidates=candidates,
            )
    state = "mined" if candidates else "clean"
    return {
        "kind": "intake_mine_report",
        "state": state,
        "truth_boundary": "repository-readmodel",
        "repository_truth": False,
        "writes": [],
        "intake_envelopes": envelopes,
        "issue_candidates": candidates,
        "summary": {
            "signal_count": len(envelopes),
            "candidate_count": len(candidates),
            "auto_raise_allowed": False,
            "auto_dispatch_allowed": False,
        },
        "required_gaps": [],
    }


def _mine_claim_file(
    *,
    repo: Path,
    claim_path: Path,
    current_head: str,
    envelopes: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
) -> None:
    try:
        payload = tomllib.loads(claim_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return
    evidence = payload.get("evidence")
    if not isinstance(evidence, dict):
        return
    evidence_head = str(evidence.get("head") or "").strip()
    if not evidence_head or evidence_head == current_head:
        return
    relative = claim_path.relative_to(repo).as_posix()
    claim_id = str(payload.get("id") or claim_path.stem).strip() or claim_path.stem
    envelope_id = f"claim:{relative}:evidence.head_stale"
    envelopes.append(
        {
            "envelope_id": envelope_id,
            "source_kind": "claim",
            "source_path": relative,
            "signal_kind": "evidence.head_stale",
            "external_provider_truth": False,
        }
    )
    candidates.append(
        {
            "candidate_id": f"claim-{_slug(claim_id)}-head-{_slug(claim_path.stem)}",
            "source_envelope_id": envelope_id,
            "subject": relative,
            "violated_commitment": "evidence must bind claims to current repository head",
            "invalid_state": "evidence.head_stale",
            "scope": "evidence",
            "severity": "medium",
            "dedupe_key": f"evidence.head_stale:{relative}",
            "suggested_disposition": "admit_change_claim",
            "suggested_proof": "refresh claim evidence and run ethos quality claims --json",
            "auto_raise_allowed": False,
            "auto_dispatch_allowed": False,
        }
    )


def _git_head(repo: Path) -> str:
    try:
        completed = subprocess.run(
            ("git", "-C", str(repo), "rev-parse", "HEAD"),
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


def _slug(value: str) -> str:
    return "-".join(part for part in value.lower().replace("_", "-").split("-") if part)
