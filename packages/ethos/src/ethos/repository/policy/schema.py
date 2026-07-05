from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError
from jsonschema.exceptions import ValidationError

from ethos.repository.policy.gates import gate_registry
from ethos.repository.registry.docs import docs_health_report
from ethos.repository.registry.profiles import governance_profile_report
from ethos_core.contracts.skill_activation import normalize_skill_activation
from ethos_core.contracts.skill_activation import skill_registry_digest
from ethos_core.quality.gates import product_gate_plan
from ethos_core.quality.profiles import product_quality_profile


def _repo_root() -> Path:
    return Path.cwd()


def _schema_dir(root: Path) -> Path:
    return root / "system" / "schemas" / "kernel"


def _schema_dir_has_contracts(path: Path) -> bool:
    return path.exists() and any(path.glob("*.schema.json"))


def _schema_dir_has_product_contracts(path: Path) -> bool:
    if not path.exists():
        return False
    return _product_schema_names().issubset({schema.name for schema in path.glob("*.schema.json")})


def _product_schema_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "system" / "schemas" / "kernel"
        if _schema_dir_has_contracts(candidate):
            return candidate
    return _schema_dir(_repo_root())


def _product_schema_names() -> set[str]:
    product = _product_schema_dir()
    return {schema.name for schema in product.glob("*.schema.json")}


def _effective_schema_dir(root: Path) -> Path:
    local = _schema_dir(root)
    if _schema_dir_has_product_contracts(local):
        return local
    return _product_schema_dir()


def load_schema(name: str, *, root: Path | None = None) -> dict[str, Any]:
    base = _effective_schema_dir(root or _repo_root())
    return json.loads((base / name).read_text(encoding="utf-8"))


def schema_validation_report(root: Path | None = None) -> dict[str, object]:
    repo = root or _repo_root()
    gaps: list[str] = []
    schemas: dict[str, dict[str, object]] = {}
    local_schema_dir = _schema_dir(repo)
    product_schema_dir = _product_schema_dir()
    schema_dir = _effective_schema_dir(repo)
    mode = (
        "product"
        if local_schema_dir.resolve() == product_schema_dir.resolve()
        and schema_dir.resolve() == product_schema_dir.resolve()
        else "adopter"
    )
    for path in sorted(schema_dir.glob("*.schema.json")):
        try:
            schema = json.loads(path.read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(schema)
        except (json.JSONDecodeError, SchemaError) as exc:
            gaps.append(f"{path.name}:{exc.__class__.__name__}")
            schemas[path.name] = {"ok": False, "error": str(exc)}
        else:
            schemas[path.name] = {"ok": True, "title": schema.get("title", "")}
    instances = _instance_validation_report(repo, mode=mode)
    for name, instance in instances.items():
        if not instance["ok"]:
            gaps.extend(f"instance:{name}:{gap}" for gap in instance["required_gaps"])
    return {
        "ok": not gaps,
        "mode": mode,
        "schema_source": schema_dir.as_posix(),
        "schema_count": len(schemas),
        "required_gaps": gaps,
        "schemas": schemas,
        "instances": instances,
    }


def validate_schema_instance(
    schema_name: str,
    payload: dict[str, Any],
    *,
    root: Path | None = None,
) -> dict[str, object]:
    schema_root = root or _repo_root()
    schema = _bundle_local_refs(load_schema(schema_name, root=schema_root), root=schema_root)
    validator = Draft202012Validator(schema)
    try:
        validator.validate(payload)
    except ValidationError as exc:
        return {"ok": False, "required_gaps": [exc.message]}
    return {"ok": True, "required_gaps": []}


def _bundle_local_refs(schema: dict[str, Any], *, root: Path) -> dict[str, Any]:
    return _bundle_node(schema, root=root, seen=frozenset())


def _bundle_node(value: Any, *, root: Path, seen: frozenset[str]) -> Any:
    if isinstance(value, list):
        return [_bundle_node(item, root=root, seen=seen) for item in value]
    if not isinstance(value, dict):
        return value
    ref = value.get("$ref")
    if isinstance(ref, str) and ref.endswith(".schema.json"):
        if ref in seen:
            return value
        referenced = load_schema(ref, root=root)
        return _bundle_node(referenced, root=root, seen=seen | {ref})
    return {key: _bundle_node(item, root=root, seen=seen) for key, item in value.items()}


def _instance_validation_report(root: Path, *, mode: str) -> dict[str, dict[str, object]]:
    from ethos.repository.policy.coupling import coupling_audit_report

    instances: dict[str, dict[str, object]] = {}
    ledger_path = root / "docs" / "governance" / "evolution-ledger.toml"
    if ledger_path.exists():
        try:
            ledger = tomllib.loads(ledger_path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as exc:
            instances["evolution-ledger"] = {"ok": False, "required_gaps": [str(exc)]}
        else:
            instances["evolution-ledger"] = validate_schema_instance(
                "evolution-ledger.schema.json",
                ledger,
                root=root,
            )
    docs = docs_health_report(root)
    instances["docs-registry"] = validate_schema_instance(
        "docs-registry.schema.json",
        docs,
        root=root,
    )
    gate_results = []
    for gate in gate_registry().values():
        gate_results.append(
            validate_schema_instance(
                "gate.schema.json",
                {
                    "id": gate.id,
                    "kind": gate.kind,
                    "command": list(gate.command),
                    "policy": gate.policy,
                    "profile": gate.profile,
                    "toolchain": gate.toolchain,
                    "asset_classes": list(gate.asset_classes),
                    "dimensions": list(gate.dimensions),
                    "execution_mode": gate.execution_mode,
                    "evidence_class": gate.evidence_class,
                    "trust_bearing": gate.trust_bearing,
                    "tool_adapter": gate.tool_adapter,
                    "writes_files": gate.writes_files,
                    "network_policy": gate.network_policy,
                    "version_source": gate.version_source,
                    "depends_on": list(gate.depends_on),
                },
                root=root,
            )
        )
    gate_gaps = [
        gap for result in gate_results for gap in result["required_gaps"] if not result["ok"]
    ]
    instances["gate-registry"] = {"ok": not gate_gaps, "required_gaps": gate_gaps}
    instances["quality-profile"] = validate_schema_instance(
        "quality-profile.schema.json",
        product_quality_profile(),
        root=root,
    )
    instances["quality-gate-plan"] = validate_schema_instance(
        "quality-gate-plan.schema.json",
        product_gate_plan(),
        root=root,
    )
    instances["campaign-closeout-contract"] = validate_schema_instance(
        "campaign-closeout.schema.json",
        _campaign_closeout_contract_sample(),
        root=root,
    )
    instances["campaign-contract"] = validate_schema_instance(
        "campaign.schema.json",
        _campaign_contract_sample(),
        root=root,
    )
    instances["shadow-parity-contract"] = validate_schema_instance(
        "shadow-parity.schema.json",
        _shadow_parity_contract_sample(),
        root=root,
    )
    instances["workspace-status-contract"] = validate_schema_instance(
        "workspace-status.schema.json",
        _workspace_status_contract_sample(),
        root=root,
    )
    instances["trust-envelope-contract"] = validate_schema_instance(
        "trust-envelope.schema.json",
        _trust_envelope_contract_sample(),
        root=root,
    )
    instances["promotion-target-contract"] = validate_schema_instance(
        "promotion-target.schema.json",
        _promotion_target_contract_sample(),
        root=root,
    )
    instances["capability-profile-contract"] = validate_schema_instance(
        "capability-profile.schema.json",
        _capability_profile_contract_sample(),
        root=root,
    )
    instances["governance-profile-contract"] = validate_schema_instance(
        "governance-profile.schema.json",
        governance_profile_report(),
        root=root,
    )
    instances["capability-profiles"] = _capability_profiles_report(root, mode=mode)
    instances["coupling-audit-contract"] = validate_schema_instance(
        "coupling-audit.schema.json",
        coupling_audit_report(root),
        root=root,
    )
    skill_registry = normalize_skill_activation(
        _skill_activation_contract_sample(),
        source=".agents/skills/activation.toml",
    )
    skill_registry["digest"] = skill_registry_digest(skill_registry)
    instances["skill-activation-contract"] = validate_schema_instance(
        "skill-activation.schema.json",
        _skill_activation_contract_sample(),
        root=root,
    )
    instances["skill-registry-contract"] = validate_schema_instance(
        "skill-registry.schema.json",
        skill_registry,
        root=root,
    )
    instances["skill-package-manifest-contract"] = validate_schema_instance(
        "skill-package-manifest.schema.json",
        _skill_package_manifest_contract_sample(),
        root=root,
    )
    instances.update(_live_skill_contract_instances(root))
    return instances


def _live_skill_contract_instances(root: Path) -> dict[str, dict[str, object]]:
    instances: dict[str, dict[str, object]] = {}
    activation_path = root / ".agents" / "skills" / "activation.toml"
    if not activation_path.exists():
        return instances
    try:
        activation = tomllib.loads(activation_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        gap = str(exc)
        return {
            "live-skill-activation-contract": {"ok": False, "required_gaps": [gap]},
            "live-skill-registry-contract": {"ok": False, "required_gaps": [gap]},
            "live-skill-package-manifests": {"ok": False, "required_gaps": [gap]},
        }
    instances["live-skill-activation-contract"] = validate_schema_instance(
        "skill-activation.schema.json",
        activation,
        root=root,
    )
    live_registry = normalize_skill_activation(
        activation,
        source=".agents/skills/activation.toml",
    )
    live_registry["digest"] = skill_registry_digest(live_registry)
    instances["live-skill-registry-contract"] = validate_schema_instance(
        "skill-registry.schema.json",
        live_registry,
        root=root,
    )
    package_gaps: list[str] = []
    for manifest_path in sorted((root / ".agents" / "skills").glob("*/package.toml")):
        try:
            manifest = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as exc:
            package_gaps.append(f"{manifest_path.relative_to(root).as_posix()}:{exc}")
            continue
        result = validate_schema_instance(
            "skill-package-manifest.schema.json",
            manifest,
            root=root,
        )
        package_gaps.extend(
            f"{manifest_path.relative_to(root).as_posix()}:{gap}" for gap in result["required_gaps"]
        )
    instances["live-skill-package-manifests"] = {
        "ok": not package_gaps,
        "required_gaps": package_gaps,
    }
    return instances


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
            "target_head": "target-head",
            "current_target_head": "target-head",
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
            "missing_lease_count": 0,
            "overlap_count": 0,
            "unknown_scope_count": 0,
            "next_action": (
                "resolve overlapping or unknown Work Lane scope before candidate integration"
            ),
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


def _capability_profiles_report(root: Path, *, mode: str) -> dict[str, object]:
    profile_paths = sorted((root / "openspec" / "specs").glob("*/capability.toml"))
    gaps: list[str] = []
    advisory_gaps: list[str] = []
    for path in profile_paths:
        try:
            payload = tomllib.loads(path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as exc:
            gaps.append(f"{path.relative_to(root).as_posix()}:{exc}")
            continue
        validation = validate_schema_instance(
            "capability-profile.schema.json",
            payload,
            root=root,
        )
        if not validation["ok"]:
            gaps.extend(
                f"{path.relative_to(root).as_posix()}:{gap}" for gap in validation["required_gaps"]
            )
    if mode == "adopter":
        advisory_gaps = gaps
        gaps = []
    return {
        "ok": not gaps,
        "profile_count": len(profile_paths),
        "required_gaps": gaps,
        "advisory_gaps": advisory_gaps,
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


def validate_ethos_result(
    payload: dict[str, Any],
    *,
    root: Path | None = None,
) -> dict[str, object]:
    return validate_schema_instance("result.schema.json", payload, root=root)
