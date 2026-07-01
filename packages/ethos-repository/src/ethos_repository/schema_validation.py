from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError

from ethos_repository.docs_registry import docs_health_report
from ethos_repository.gates import gate_registry


def _repo_root() -> Path:
    return Path.cwd()


def _schema_dir(root: Path) -> Path:
    return root / "schemas" / "ethos"


def _schema_dir_has_contracts(path: Path) -> bool:
    return path.exists() and any(path.glob("*.schema.json"))


def _schema_dir_has_product_contracts(path: Path) -> bool:
    if not path.exists():
        return False
    return _product_schema_names().issubset(
        {schema.name for schema in path.glob("*.schema.json")}
    )


def _product_schema_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "schemas" / "ethos"
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
    instances = _instance_validation_report(repo)
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
    schema = load_schema(schema_name, root=root)
    validator = Draft202012Validator(schema)
    try:
        validator.validate(payload)
    except ValidationError as exc:
        return {"ok": False, "required_gaps": [exc.message]}
    return {"ok": True, "required_gaps": []}


def _instance_validation_report(root: Path) -> dict[str, dict[str, object]]:
    instances: dict[str, dict[str, object]] = {}
    ledger_path = root / "docs" / "governance" / "self-evolution-ledger.toml"
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
                },
                root=root,
            )
        )
    gate_gaps = [
        gap for result in gate_results for gap in result["required_gaps"] if not result["ok"]
    ]
    instances["gate-registry"] = {"ok": not gate_gaps, "required_gaps": gate_gaps}
    instances["campaign-closeout-contract"] = validate_schema_instance(
        "campaign-closeout.schema.json",
        _campaign_closeout_contract_sample(),
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
        "evidence_path": "docs/evidence/parity/example-shadow.json",
        "freshness": {
            "ok": True,
            "required_gaps": [],
            "product_head": "product-head",
            "target_head": "target-head",
            "current_target_head": "target-head",
            "command_sha256": "0" * 64,
        },
    }
    shadow_package = {
        "kind": "shadow_parity_evidence",
        "state": "matched",
        "target": "/repo",
        "evidence_path": "docs/evidence/parity/example-shadow.json",
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
        "release": {},
        "parity": {},
        "shadow_parity": {},
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
            "publication": publication,
            "release": {},
            "parity": {},
            "shadow_parity": shadow_package,
        },
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
            "kind_counts": {"external_product_self_audit_gap": 1},
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
                    "kind_counts": {"external_product_self_audit_gap": 1},
                },
                "accepted_differences": [
                    {
                        "kind": "external_product_self_audit_gap",
                        "classification": "accepted",
                        "scope": "external_product_self_audit",
                        "commands": ["ethos prove"],
                        "gaps": ["claims_missing"],
                        "reason": (
                            "external product self-audit gap is not an embedded "
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
            },
            {
                "branch": "dev",
                "role": "accepted_root",
                "head": "abc123",
                "worktree_path": "/repo",
                "worktree_binding": "current",
            },
            {
                "branch": "stage/dev",
                "role": "candidate",
                "head": "abc123",
                "worktree_path": "/repo-stage-dev",
                "worktree_binding": "linked",
            },
        ],
        "foreign_work_lanes": [],
        "coordination_gaps": [],
        "closeout_support": {
            "supported": False,
            "branch": "",
            "target_branch": "stage/dev",
            "target_path": "/repo-stage-dev",
            "operation": "",
            "owner": "",
            "required_gaps": ["protected_root_mutation"],
        },
        "required_gaps": [],
    }


def validate_ethos_result(
    payload: dict[str, Any],
    *,
    root: Path | None = None,
) -> dict[str, object]:
    return validate_schema_instance("result.schema.json", payload, root=root)
