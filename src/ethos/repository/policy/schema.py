from __future__ import annotations

import json
import tomllib
from importlib import metadata
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import TypedDict

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from ethos.contracts.skill.activation import normalize_skill_activation
from ethos.contracts.skill.activation import skill_registry_digest
from ethos.contracts.verdict import Verdict
from ethos.contracts.verdict import close_verdict
from ethos.contracts.verdict import report_verdict
from ethos.normalization.coercion import string_list
from ethos.quality.gates import product_gate_plan
from ethos.quality.profiles import product_quality_profile
from ethos.repository.policy.gates import resolve_gate_policy
from ethos.repository.registry.docs.health import docs_health_report

if TYPE_CHECKING:
    from collections.abc import Mapping


class SchemaInstanceValidation(TypedDict):
    verdict: Verdict
    required_gaps: list[str]


def _repo_root() -> Path:
    return Path.cwd()


def _schema_dir(root: Path) -> Path:
    return root / "system" / "schemas" / "kernel"


def _product_schema_dir() -> Path:
    return Path(
        str(metadata.distribution("ethos").locate_file("ethos/data/schemas/kernel"))
    ).resolve()


def load_schema(name: str, *, root: Path | None = None) -> dict[str, Any]:
    del root
    return json.loads((_product_schema_dir() / name).read_text(encoding="utf-8"))


def schema_validation_report(root: Path | None = None) -> dict[str, object]:
    repo = root or _repo_root()
    gaps: list[str] = []
    schemas: dict[str, dict[str, object]] = {}
    local_schema_dir = _schema_dir(repo)
    schema_dir = _product_schema_dir()
    retired_schema = local_schema_dir / "capability-profile.schema.json"
    if retired_schema.exists():
        gaps.append("schema_retired:capability-profile.schema.json")
        schemas[retired_schema.name] = {
            "verdict": "block",
            "error": "retired semantic schema",
        }
    for path in sorted(schema_dir.glob("*.schema.json")):
        if path.resolve() == retired_schema.resolve():
            continue
        try:
            schema = json.loads(path.read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(schema)
        except (json.JSONDecodeError, SchemaError) as exc:
            gaps.append(f"{path.name}:{exc.__class__.__name__}")
            schemas[path.name] = {"verdict": "block", "error": str(exc)}
        else:
            schemas[path.name] = {"verdict": "pass", "title": schema.get("title", "")}
    instances = _instance_validation_report(repo)
    for name, instance in instances.items():
        if report_verdict(instance) != "pass":
            gaps.extend(
                f"instance:{name}:{gap}" for gap in string_list(instance.get("required_gaps"))
            )
    return {
        "verdict": close_verdict("pass", required_gaps=tuple(gaps)),
        "mode": "product",
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
) -> SchemaInstanceValidation:
    schema_root = root or _repo_root()
    schema = _bundle_local_refs(load_schema(schema_name, root=schema_root), root=schema_root)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda item: item.json_path)
    if errors:
        return {"verdict": "block", "required_gaps": [error.message for error in errors]}
    return {"verdict": "pass", "required_gaps": []}


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


def _instance_validation_report(root: Path) -> dict[str, Mapping[str, object]]:
    instances: dict[str, Mapping[str, object]] = {}
    docs = docs_health_report(root)
    instances["docs-registry"] = validate_schema_instance(
        "docs-registry.schema.json",
        docs,
        root=root,
    )
    gate_results = [
        validate_schema_instance(
            "gate.schema.json",
            gate.to_dict(),
            root=root,
        )
        for gate in resolve_gate_policy().registry.values()
    ]
    gate_gaps = [
        gap
        for result in gate_results
        if result["verdict"] != "pass"
        for gap in string_list(result.get("required_gaps"))
    ]
    instances["gate-registry"] = {
        "verdict": close_verdict("pass", required_gaps=tuple(gate_gaps)),
        "required_gaps": gate_gaps,
    }
    instances["quality-profile"] = validate_schema_instance(
        "quality-profile.schema.json",
        product_quality_profile(root),
        root=root,
    )
    instances["quality-gate-plan"] = validate_schema_instance(
        "quality-gate-plan.schema.json",
        product_gate_plan(),
        root=root,
    )
    instances.update(_live_skill_contract_instances(root))
    return instances


def _live_skill_contract_instances(root: Path) -> dict[str, Mapping[str, object]]:
    instances: dict[str, Mapping[str, object]] = {}
    activation_path = root / ".agents" / "skills" / "activation.toml"
    if not activation_path.exists():
        return instances
    try:
        activation = tomllib.loads(activation_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        gap = str(exc)
        return {
            "live-skill-activation-contract": {"verdict": "block", "required_gaps": [gap]},
            "live-skill-registry-contract": {"verdict": "block", "required_gaps": [gap]},
            "live-skill-package-manifests": {"verdict": "block", "required_gaps": [gap]},
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
            f"{manifest_path.relative_to(root).as_posix()}:{gap}"
            for gap in string_list(result.get("required_gaps"))
        )
    instances["live-skill-package-manifests"] = {
        "verdict": close_verdict("pass", required_gaps=tuple(package_gaps)),
        "required_gaps": package_gaps,
    }
    return instances


def validate_ethos_result(
    payload: dict[str, Any],
    *,
    root: Path | None = None,
) -> SchemaInstanceValidation:
    return validate_schema_instance("result.schema.json", payload, root=root)
