"""Large JSON schema sample builders."""

from __future__ import annotations

from typing import Any

from ethos.repository.policy.schema_sample_shared import _campaign_package_contract_sample
from ethos.repository.policy.schema_sample_shared import _intake_projection_contract_sample
from ethos.repository.policy.schema_sample_shared import _trust_closeout_contract_sample


def _campaign_closeout_contract_sample() -> dict[str, Any]:
    publication = {
        "mode": "local_readiness",
        "remote_push": "not_performed",
        "remote_state": "deferred",
        "submit_branch": "review/example",
        "local_submit_package": {
            "kind": "submit_branch_plan",
            "source_branch": "lane/example",
            "submit_branch": "review/example",
            "remote_push": "not_performed",
            "remote_state": "deferred",
            "blocking": False,
            "required_steps": [
                "land work lane to candidate role",
                "fast-forward accepted root from candidate role",
                "create configured submit branch when remote publication is available",
            ],
        },
        "required_gaps": [],
        "next_actions": ["create configured submit branch when remote publication is available"],
    }
    shadow_provenance = {
        "mode": "tracked_evidence",
        "evidence_path": "evidence/parity/example-shadow.json",
        "freshness": {
            "ok": True,
            "required_gaps": [],
            "product_head": "product-head",
            "current_product_head": "product-head",
            "product_head_current": True,
            "product_head_accepted_by_relevant_tree": False,
            "target_head": "target-head",
            "current_target_head": "target-head",
            "target_head_current": True,
            "target_head_accepted_by_relevant_tree": False,
            "command_sha256": "0" * 64,
        },
    }
    shadow_package = {
        "kind": "shadow_parity_evidence",
        "state": "matched",
        "target": "/repo",
        "evidence_path": "evidence/parity/example-shadow.json",
        "comparison_count": 9,
        "commands": ["ethos status --json"],
        "semantic_dimensions": ["branch role"],
        "blocking": False,
        "required_gaps": [],
        "provenance": shadow_provenance,
        "next_action": "use tracked shadow parity evidence for local closeout",
    }
    return {
        "ok": True,
        "state": "local_ready",
        "workspace": {},
        "evolution": {},
        "campaigns": _campaign_package_contract_sample(),
        "release": {},
        "parity": {},
        "shadow_parity": {},
        "claims": {},
        "intake_projection": _intake_projection_contract_sample(),
        "publication": publication,
        "remote_publication": {
            "remote_push": "not_performed",
            "state": "deferred",
            "reason": "remote publication adapter unavailable",
        },
        "provenance": {
            "shadow_parity": shadow_provenance,
            "closeout": {
                "mode": "local_only",
                "remote_state": "deferred",
            },
        },
        "packages": {
            "local_closeout": {},
            "trust_closeout": _trust_closeout_contract_sample(),
            "campaign": _campaign_package_contract_sample(),
            "intake_projection": _intake_projection_contract_sample(),
            "publication": publication,
            "release": {},
            "parity": {},
            "shadow_parity": shadow_package,
        },
    }


def _workspace_status_contract_sample() -> dict[str, Any]:
    return {
        "root": "/repo",
        "branch": "dev",
        "dirty": False,
        "changed_paths": [],
        "dirty_provenance": {
            "dirty": False,
            "state": "clean",
            "entries": [],
            "summary": {
                "tracked": 0,
                "untracked": 0,
                "deleted": 0,
                "conflicted": 0,
                "unavailable": 0,
            },
        },
        "role": "accepted_root",
        "role_policy": {
            "release_branch": "main",
            "accepted_branch": "dev",
            "candidate_branch": "stage/dev",
            "work_branch_prefix": "lane/",
            "submit_branch_prefix": "review/",
            "semantic_order": [
                {
                    "role": "release_root",
                    "kind": "exact_branch",
                    "config_key": "release_branch",
                    "pattern": "main",
                },
                {
                    "role": "accepted_root",
                    "kind": "exact_branch",
                    "config_key": "accepted_branch",
                    "pattern": "dev",
                },
                {
                    "role": "candidate",
                    "kind": "exact_branch",
                    "config_key": "candidate_branch",
                    "pattern": "stage/dev",
                },
                {
                    "role": "work_lane",
                    "kind": "branch_prefix",
                    "config_key": "work_branch_prefix",
                    "pattern": "lane/*",
                },
                {
                    "role": "submit_lane",
                    "kind": "branch_prefix",
                    "config_key": "submit_branch_prefix",
                    "pattern": "review/*",
                },
            ],
        },
        "runtime_binding": {
            "kind": "workspace_status_runtime_binding",
            "state": "bound_to_audit_root",
            "audit_root": "/repo",
            "runner_module_path": "/repo/packages/ethos/src/ethos/__init__.py",
            "runner_source_root": "/repo",
            "schema_source_root": "/repo",
            "runner_matches_audit_root": True,
            "schema_matches_audit_root": True,
            "advisory_gaps": [],
            "next_action": "runner, schema, and audit root are aligned",
        },
        "candidate": {
            "branch": "stage/dev",
            "exists": True,
            "head": "abc123",
            "worktree_exists": True,
            "worktree_path": "/repo-stage-dev",
            "worktree_binding": "linked",
        },
        "worktrees": [
            {
                "path": "/repo",
                "head": "abc123",
                "branch": "dev",
                "role": "accepted_root",
                "worktree_binding": "current",
            },
            {
                "path": "/repo-stage-dev",
                "head": "abc123",
                "branch": "stage/dev",
                "role": "candidate",
                "worktree_binding": "linked",
            },
        ],
        "branch_bindings": [
            {
                "branch": "main",
                "role": "release_root",
                "head": "abc123",
                "worktree_path": "",
                "worktree_binding": "unbound",
                "claim_id": "",
                "claim_binding": "unbound",
            },
            {
                "branch": "dev",
                "role": "accepted_root",
                "head": "abc123",
                "worktree_path": "/repo",
                "worktree_binding": "current",
                "claim_id": "",
                "claim_binding": "missing",
            },
            {
                "branch": "stage/dev",
                "role": "candidate",
                "head": "abc123",
                "worktree_path": "/repo-stage-dev",
                "worktree_binding": "linked",
                "claim_id": "",
                "claim_binding": "missing",
            },
        ],
        "foreign_work_lanes": [],
        "coordination_gaps": [],
        "coordination": {
            "kind": "work_lane_coordination",
            "blocking": False,
            "required_gaps": [],
            "advisory_gaps": [],
            "foreign_work_lane_count": 0,
            "unbound_work_lane_count": 0,
            "unbound_work_lane_refs": [],
            "missing_lease_count": 0,
            "overlap_count": 0,
            "unknown_scope_count": 0,
            "next_action": ("no Work Lane coordination action required"),
            "migration_recommendations": [],
        },
        "closeout_support": {
            "supported": False,
            "branch": "",
            "target_branch": "stage/dev",
            "target_path": "/repo-stage-dev",
            "operation": "",
            "owner": "",
            "claim_id": "",
            "claim_binding": "unbound",
            "required_gaps": ["protected_root_mutation"],
        },
        "stage_gates": {
            "authoring_allowed": False,
            "integration_allowed": False,
            "accepted_closeout_allowed": False,
            "blocked_stage": "authoring",
            "blocker_owner": "",
            "recommended_next_command": "ethos lane start <name>",
            "next_commands": ["ethos lane start <name>"],
        },
        "required_gaps": [],
    }
