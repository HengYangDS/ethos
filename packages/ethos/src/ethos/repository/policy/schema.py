from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError
from jsonschema.exceptions import ValidationError

from ethos.repository.policy.gates import gate_registry
from ethos.repository.policy.schema_samples.core import _campaign_contract_sample
from ethos.repository.policy.schema_samples.core import _capability_profile_contract_sample
from ethos.repository.policy.schema_samples.core import _promotion_target_contract_sample
from ethos.repository.policy.schema_samples.core import _shadow_parity_contract_sample
from ethos.repository.policy.schema_samples.core import _skill_activation_contract_sample
from ethos.repository.policy.schema_samples.core import _skill_package_manifest_contract_sample
from ethos.repository.policy.schema_samples.core import _trust_envelope_contract_sample
from ethos.repository.policy.schema_samples.large import _campaign_closeout_contract_sample
from ethos.repository.policy.schema_samples.large import _workspace_status_contract_sample
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
    ledger_path = root / "evolution" / "ledger.toml"
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


def validate_ethos_result(
    payload: dict[str, Any],
    *,
    root: Path | None = None,
) -> dict[str, object]:
    return validate_schema_instance("result.schema.json", payload, root=root)
