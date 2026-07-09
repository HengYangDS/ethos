"""Shared JSON schema sample builders."""

from __future__ import annotations

from typing import Any


def campaign_package_contract_sample() -> dict[str, Any]:
    """Return a reusable campaign closeout package sample."""
    return {
        "kind": "campaign_closeout",
        "ok": True,
        "active_count": 1,
        "campaign_count": 1,
        "required_gaps": [],
        "campaigns": [
            {
                "id": "terminal-openspec-productization",
                "state": "active",
                "owner": "ethos-maintainers",
                "objective": "Complete terminal OpenSpec productization.",
                "claim_id": "ethos-terminal-openspec-productization",
                "steps": [],
                "step_summary": {"total": 0, "planned": 0, "active": 0, "closed": 0},
                "required_gaps": [],
            }
        ],
    }


def intake_projection_contract_sample() -> dict[str, Any]:
    """Return a reusable intake projection package sample."""
    return {
        "kind": "intake_projection",
        "state": "unconfigured",
        "truth_boundary": "projection-evidence",
        "repository_truth": False,
        "provider": "unconfigured",
        "configured": False,
        "expected_config": ".ethos/intake.toml",
        "adapters": ["backlog", "github", "gitlab"],
        "blocking": False,
        "required_gaps": [],
    }


def trust_closeout_contract_sample() -> dict[str, Any]:
    """Return a reusable trust closeout package sample."""
    return {
        "kind": "trust_closeout",
        "claim_report_ok": True,
        "trust_claim_count": 1,
        "promotion_ready": True,
        "executed_proof_evidence": True,
        "work_lane": {
            "branch": "work/example",
            "claim_id": "sample-trust",
            "claim_binding": "bound",
        },
        "blocking": False,
        "required_gaps": [],
    }
