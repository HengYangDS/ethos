"""JSON schema contract sample builders."""

from __future__ import annotations

from typing import Any


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


def _campaign_contract_sample() -> dict[str, Any]:
    return {
        "id": "terminal-openspec-productization",
        "state": "active",
        "owner": "ethos-maintainers",
        "objective": "Complete terminal OpenSpec productization through closeout-ready lanes.",
        "claim_id": "ethos-terminal-openspec-productization",
        "steps": [
            {
                "id": "campaign-orchestration",
                "title": "Campaign orchestration",
                "state": "closed",
                "ordinal": 1,
                "depends_on": [],
                "openspec_change": "ethos-campaign-orchestration",
                "work_lane": "work/campaign-orchestration",
                "claim_id": "ethos-campaign-orchestration",
                "closeout": {
                    "state": "retired",
                    "accepted_head": "a" * 40,
                    "candidate_head": "a" * 40,
                    "evidence": ["evidence/campaign-orchestration-2026-07-02.md"],
                },
            }
        ],
    }


def _campaign_package_contract_sample() -> dict[str, Any]:
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


def _shadow_parity_contract_sample() -> dict[str, Any]:
    return {
        "ok": True,
        "state": "matched",
        "target": "/repo",
        "required_gaps": [],
        "accepted_summary": {
            "total_count": 1,
            "command_count": 1,
            "kind_counts": {"external_product_repository_audit_gap": 1},
        },
        "comparisons": [
            {
                "command": "ethos prove",
                "external": {
                    "exit_code": 0,
                    "stdout": "",
                    "stderr": "",
                    "json": {},
                },
                "embedded": {
                    "exit_code": 0,
                    "stdout": "",
                    "stderr": "",
                    "json": {},
                },
                "semantic_diff": {},
                "accepted_summary": {
                    "total_count": 1,
                    "kind_counts": {"external_product_repository_audit_gap": 1},
                },
                "accepted_differences": [
                    {
                        "kind": "external_product_repository_audit_gap",
                        "classification": "accepted",
                        "scope": "external_product_repository_audit",
                        "commands": ["ethos prove"],
                        "gaps": ["claims_missing"],
                        "reason": (
                            "external product repository audit gap is not an embedded "
                            "adopter parity gap"
                        ),
                    }
                ],
            }
        ],
        "execution_packages": [],
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
        "required_gaps": [],
    }


def _intake_projection_contract_sample() -> dict[str, Any]:
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


def _trust_closeout_contract_sample() -> dict[str, Any]:
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


def _promotion_target_contract_sample() -> dict[str, Any]:
    return {
        "kind": "evidence",
        "path": "evidence/sample.md",
        "description": "dated evidence promoted into repository truth",
    }


def _trust_envelope_contract_sample() -> dict[str, Any]:
    return {
        "claim_id": "sample-trust",
        "state": "active",
        "boundary": {
            "owner": "ethos-repository",
            "scope": "repository lifecycle governance",
        },
        "evidence": {
            "dated": "evidence/sample.md",
            "digest_trusted": True,
            "commands": ["ethos prove --execute --json"],
        },
        "carriers": {
            "openspec": "openspec/changes/sample-change",
        },
        "fallback": "stop promotion and keep the previous repository contract",
        "kill_signal": "required lifecycle carrier missing",
        "promotion": {
            "targets": [
                {
                    "kind": "source",
                    "path": "packages/ethos-repository/src/ethos.repository/claims.py",
                },
                {
                    "kind": "openspec",
                    "path": "openspec/specs/ethos-repository/spec.md",
                },
            ],
            "ready": True,
        },
        "required_gaps": [],
    }


def _capability_profile_contract_sample() -> dict[str, Any]:
    return {
        "family": "ethos-repository",
        "owner": {
            "package": "ethos-repository",
            "scope": "repository lifecycle governance",
        },
        "primary_invariant": "repository truth is promoted through claims and evidence",
        "routing_question": "Does this change alter repository trust admission?",
        "decision_axes": ["lifecycle", "surface", "authority"],
        "boundary_rules": [
            "OpenSpec records are specification carriers, not truth owners",
            "adopter-specific terms stay in profiles or evidence",
        ],
        "recommended_facets": {
            "lifecycle": ["authoring", "validation", "archive"],
            "surface": ["docs", "openspec", "schema"],
            "authority": ["docs", "openspec", "claim", "evidence"],
        },
        "proof_profile": {
            "default_command": "ethos prove --json",
            "executed_command": "ethos prove --execute --json",
            "required_gates": ["claims", "schemas"],
        },
    }


def _skill_activation_contract_sample() -> dict[str, Any]:
    return {
        "meta": {"version": 2, "owner": "ethos"},
        "coverage": {"required_roots": ["skills", "docs", "packages"]},
        "retired": {"skill_names": []},
        "skill": [
            {
                "id": "ethos-repository-governance",
                "path": ".agents/skills/ethos-repository-governance/SKILL.md",
                "package_manifest": ".agents/skills/ethos-repository-governance/package.toml",
                "subject": "repository-governance",
                "operation": "govern",
                "authority": "primary",
                "lifecycle": "active",
                "subjects": ["repository-governance", "changed-scope"],
                "path_globs": ["docs/**", "packages/**"],
                "intent_tokens": ["ethos", "governance"],
                "pre_reads": ["AGENTS.md"],
                "during_rules": ["keep repository truth authoritative"],
                "post_checks": ["ethos report --json"],
                "may_coactivate": [],
                "supports": [],
                "excludes": [],
                "commands": ["ethos status --json", "ethos report --json"],
                "boundary": "workflow-package-projection",
            }
        ],
    }


def _skill_package_manifest_contract_sample() -> dict[str, Any]:
    return {
        "schema_version": 2,
        "id": "ethos-repository-governance",
        "entrypoint": "SKILL.md",
        "boundary": "workflow-package-projection",
        "truth": "repository-source-and-contracts",
        "digest_algorithm": "sha256",
        "include": ["SKILL.md"],
        "exclude": [".DS_Store"],
        "expected_digest": "sha256:" + ("0" * 64),
        "required_sections": ["When to Use", "Workflow", "Evidence", "Trust Boundary"],
        "quality": {"official_codex_loadable": True, "placeholder_allowed": False},
        "capability": [
            {
                "id": "ethos.report",
                "kind": "command_readonly",
                "command": ["ethos", "report", "--json"],
            }
        ],
    }
