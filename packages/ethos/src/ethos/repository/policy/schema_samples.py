"""JSON schema contract sample builders."""

from __future__ import annotations

from typing import Any


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
                    "evidence": ["evidence/chronicle/campaign-orchestration/2026-07-02.md"],
                },
            }
        ],
    }


def _shadow_parity_contract_sample() -> dict[str, Any]:
    return {
        "ok": True,
        "state": "matched",
        "target": "/repo",
        "identity": {
            "target_root": "/repo",
            "target_head": "a" * 40,
            "product_head": "b" * 40,
            "changed_paths": [],
            "commands": ["ethos prove --json"],
            "external_commands": ["python -m ethos.cli prove --root /repo --json"],
            "embedded_commands": ["pixi run ethos prove --json"],
            "evidence_inputs": [
                {"path": ".ethos/profile.toml", "kind": "file", "sha256": "c" * 64}
            ],
        },
        "required_gaps": [],
        "accepted_summary": {
            "total_count": 1,
            "command_count": 1,
            "kind_counts": {"external_product_repository_audit_gap": 1},
        },
        "false_negative_count": 0,
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
                "false_negative_gaps": [],
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
                    "path": "packages/ethos/src/ethos/repository/evidence/claims.py",
                },
                {
                    "kind": "openspec",
                    "path": "openspec/specs/repository-governance/spec.md",
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
