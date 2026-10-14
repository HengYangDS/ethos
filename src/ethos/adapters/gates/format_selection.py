"""Resolve declared carrier ownership without granting mutation authority."""

import fnmatch
import json
import sys
import tomllib
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import NotRequired
from typing import TypedDict
from typing import TypeGuard
from typing import cast

from ethos.adapters.gates.tool import native_configurations
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import git_files
from ethos.repository.policy.projections import PROJECTION_DECLARATIONS
from ethos.repository.policy.projections import projection_relations
from ethos.repository.policy.quality.measurement import policy_for_root
from ethos.repository.profile import INVALID_PROFILE_ERROR
from ethos.repository.profile import load_repository_profile
from ethos.repository.release.resources import canonical_resource

ROOT = canonical_resource()
CONFIG_PATH = ROOT / ".config/checks/format-selection/policy.toml"


class OwnerDeclaration(TypedDict):
    """One validated native format and quality ownership declaration."""

    id: str
    format_owner: str
    format_command: str
    format_check: str
    validation_owner: str
    validation_command: str
    mutation_policy: str
    paths: NotRequired[list[str]]
    exclude_paths: NotRequired[list[str]]
    extensions: NotRequired[list[str]]
    semantic_companions: NotRequired[list[str]]
    priority: NotRequired[int]


class CarrierAssignment(TypedDict):
    """Validated native quality owner for one tracked carrier."""

    path: str
    format_owner: str
    format_command: str
    format_check: str
    validation_owner: str
    validation_command: str
    semantic_companions: list[str]
    mutation_policy: str


class CarrierAudit(TypedDict):
    """Typed result consumed by carrier-quality checks and the CLI report."""

    schema_version: int
    kind: str
    verdict: str
    tracked_file_count: int
    assignment_count: int
    unowned_file_count: int
    multiply_owned_file_count: int
    unverified_file_count: int
    failures: list[dict[str, str]]
    assignments: list[CarrierAssignment]


def _record(value: object) -> TypeGuard[dict[str, object]]:
    return isinstance(value, dict) and all(isinstance(key, str) for key in value)


def _records(value: object) -> TypeGuard[list[dict[str, object]]]:
    return isinstance(value, list) and all(_record(item) for item in value)


def _strings(value: object) -> TypeGuard[list[str]]:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _required_text(record: dict[str, object], field: str) -> str:
    value = record.get(field)
    if not isinstance(value, str):
        message = f"format ownership field is not text: {field}"
        raise TypeError(message)
    return value


def _ownership_declarations(value: object) -> list[OwnerDeclaration]:
    """Reject malformed native owners before selector precedence can hide one."""
    if not _records(value):
        message = "format ownership declarations must be records"
        raise TypeError(message)
    for declaration in value:
        owner = _required_text(declaration, "id")
        for field in (
            "format_owner",
            "format_command",
            "format_check",
            "validation_owner",
            "validation_command",
            "mutation_policy",
        ):
            _required_text(declaration, field)
        for field in ("paths", "exclude_paths", "extensions", "semantic_companions"):
            if not _strings(declaration.get(field, [])):
                message = f"format ownership selector is not a string list: {owner}:{field}"
                raise TypeError(message)
        priority = declaration.get("priority", 0)
        if isinstance(priority, bool) or not isinstance(priority, int):
            message = f"format ownership priority is not an integer: {owner}"
            raise TypeError(message)
    return cast("list[OwnerDeclaration]", value)


def _tracked_files() -> list[str]:
    return git_files(ROOT, check=True)


def _load_config() -> dict[str, object]:
    return tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _matches_any(path: str, roots: list[str]) -> bool:
    return any(path == root.rstrip("/") or path.startswith(root) for root in roots)


def _matches_glob(path: str, pattern: str) -> bool:
    return fnmatch.fnmatchcase(path, pattern) or Path(path).match(pattern)


def _matches_patterns(path: str, patterns: list[str]) -> bool:
    return any(_matches_glob(path, pattern) for pattern in patterns)


def _owner_matches(path: str, declaration: OwnerDeclaration) -> bool:
    suffix = Path(path).suffix.lower()
    extensions = declaration.get("extensions", [])
    has_selector = bool(declaration.get("paths")) or bool(extensions)
    selected = _matches_patterns(path, declaration.get("paths", [])) or suffix in extensions
    return (
        has_selector
        and selected
        and not _matches_patterns(path, declaration.get("exclude_paths", []))
    )


def _assignment(path: str, declaration: OwnerDeclaration) -> CarrierAssignment:
    immutable = path.startswith(("openspec/changes/archive/", "evidence/", "docs/archive/"))
    mutation_policy = "forbidden" if immutable else declaration["mutation_policy"]
    format_owner = "immutable-carrier" if immutable else declaration["format_owner"]
    format_command = "not-applicable:immutable" if immutable else declaration["format_command"]
    return {
        "path": path,
        "format_owner": format_owner,
        "format_command": format_command,
        "format_check": declaration["format_check"],
        "validation_owner": declaration["validation_owner"],
        "validation_command": declaration["validation_command"],
        "semantic_companions": declaration.get("semantic_companions", []),
        "mutation_policy": mutation_policy,
    }


def _native_ownership(root: Path) -> tuple[list[OwnerDeclaration], tuple[str, ...]]:
    """Compose validated native increments without replacing mandatory owners."""
    policies = native_configurations(
        root, "format-selection", ".config/checks/format-selection/policy.toml"
    )
    parsed = tuple(tomllib.loads(Path(policy).read_text(encoding="utf-8")) for policy in policies)
    owners: dict[str, OwnerDeclaration] = {}
    for policy in parsed:
        for declaration in _ownership_declarations(policy.get("ownership")):
            owner = declaration["id"]
            if owner in owners and owners[owner] != declaration:
                message = f"format ownership conflicts with mandatory baseline: {owner}"
                raise ValueError(message)
            owners[owner] = declaration
    measurement, gaps = policy_for_root(canonical_resource())
    if measurement is None or gaps:
        message = ", ".join(gaps) or "source_budget_policy_invalid"
        raise ValueError(message)
    return list(owners.values()), tuple(
        path
        for carrier in measurement.carriers
        if carrier.category == "dependency_resolution"
        for path in carrier.paths
    )


def _native_sources(root: Path) -> tuple[dict[str, str], dict[str, str]]:
    """Observe explicit byte owners from the native profile and producer declarations."""
    profile = load_repository_profile(root)
    if profile.state == "invalid":
        raise ValueError(INVALID_PROFILE_ERROR)
    native_outputs = {
        path: contract.integrity_gate
        for contract in (profile.declaration.proof.source_contracts if profile.declaration else ())
        for path in contract.members
    }
    projection_sources = {
        relative: (root / relative).read_text(encoding="utf-8")
        for relative in PROJECTION_DECLARATIONS
        if (root / relative).is_file()
    }
    generated = {
        relation.output: "ethos prove --gate generated-artifacts --json"
        for relation in projection_relations(projection_sources)
    }
    return native_outputs, generated


def audit(root: Path = ROOT, *, paths: tuple[str, ...] | None = None) -> CarrierAudit:
    """Compile effective quality ownership for tracked or explicitly selected carriers."""
    declarations, dependency_patterns = _native_ownership(root)
    native_outputs, generated = _native_sources(root)
    tracked = paths if paths is not None else git_files(root, check=True)
    assignments: list[CarrierAssignment] = []
    failures: list[dict[str, str]] = []
    unowned = multiply_owned = unverified = 0
    for path in tracked:
        external = native_outputs.get(path)
        if external:
            verification = f"ethos prove --gate {external} --json"
            assignments.append(
                {
                    "path": path,
                    "format_owner": "native-source-owner",
                    "format_command": verification,
                    "format_check": verification,
                    "validation_owner": external,
                    "validation_command": verification,
                    "semantic_companions": [],
                    "mutation_policy": "forbidden",
                }
            )
            continue
        matches = [item for item in declarations if _owner_matches(path, item)]
        if not matches:
            unowned += 1
            failures.append({"path": path, "reason": "tracked carrier has no quality owner"})
            continue
        priority = max((item.get("priority", 0) for item in matches), default=0)
        primary = [item for item in matches if item.get("priority", 0) == priority]
        if len(primary) != 1:
            multiply_owned += 1
            owners = ",".join(str(item.get("id", "")) for item in primary)
            failures.append({"path": path, "reason": f"multiple primary quality owners: {owners}"})
            continue
        assignment = _assignment(path, primary[0])
        if path in generated and assignment["mutation_policy"] != "generator-only":
            assignment.update(
                format_owner="native-source-owner",
                format_command=generated[path],
                format_check=generated[path],
                validation_owner="native-projection",
                validation_command=generated[path],
                mutation_policy="forbidden",
            )
        if _matches_patterns(path, list(dependency_patterns)):
            assignment["mutation_policy"] = "package-manager-only"
            if assignment["format_owner"] == "python-stdlib-json":
                assignment.update(
                    format_owner="npm",
                    format_command="npm install --package-lock-only --ignore-scripts",
                    format_check="npm ci --ignore-scripts",
                    validation_owner="npm",
                    validation_command="npm ci --ignore-scripts",
                )
        required = (
            "format_owner",
            "format_command",
            "format_check",
            "validation_owner",
            "validation_command",
            "mutation_policy",
        )
        if not all(assignment[field] for field in required):
            unverified += 1
            failures.append({"path": path, "reason": "quality ownership is incomplete"})
            continue
        assignments.append(assignment)
    return {
        "schema_version": 1,
        "kind": "ethos_format_selection_audit",
        "verdict": "block" if failures else "pass",
        "tracked_file_count": len(tracked),
        "assignment_count": len(assignments),
        "unowned_file_count": unowned,
        "multiply_owned_file_count": multiply_owned,
        "unverified_file_count": unverified,
        "failures": failures,
        "assignments": assignments,
    }


def _path_allowed_for_extension(path: str, suffix: str, policy: dict[str, object]) -> bool:
    """Require declared path placement only for extensions with a narrow carrier home."""
    extension_paths = policy.get("extension_paths", {})
    constraint = extension_paths.get(suffix) if isinstance(extension_paths, dict) else None
    if not isinstance(constraint, dict):
        return True
    roots = [root for root in constraint.get("roots", []) if isinstance(root, str)]
    files = [file for file in constraint.get("files", []) if isinstance(file, str)]
    return path in files or _matches_any(path, roots)


def main() -> int:
    ownership = audit(ROOT)
    config = _load_config()
    formats = config.get("format", [])
    policy = config.get("policy", {})
    if not _records(formats) or not _record(policy):
        message = "format selection has an invalid format or policy record"
        raise ValueError(message)
    known_exts: set[str] = set()
    for item in formats:
        extensions = item.get("extensions", [])
        if not _strings(extensions):
            message = "format selection extensions must be strings"
            raise TypeError(message)
        known_exts.update(extensions)
    tracked = _tracked_files()
    failures: list[dict[str, str]] = []
    observations: list[dict[str, str]] = []

    forbidden = policy.get("forbid_tracked_extensions", [])
    jsonl_roots = policy.get("jsonl_allowed_roots", [])
    yaml_roots = policy.get("yaml_allowed_roots", [])
    unregistered_extension = policy.get("unregistered_extension", "observe")
    if not _strings(forbidden) or not _strings(jsonl_roots) or not _strings(yaml_roots):
        message = "format selection policy lists must contain strings"
        raise TypeError(message)
    if not isinstance(unregistered_extension, str):
        message = "format selection unregistered-extension mode must be a string"
        raise TypeError(message)
    forbidden_exts = set(forbidden)

    for rel in tracked:
        suffix = Path(rel).suffix
        checks = (
            (suffix in forbidden_exts, f"forbidden tracked format: {suffix}"),
            (
                suffix == ".jsonl" and not _matches_any(rel, jsonl_roots),
                "tracked JSONL outside allowed roots",
            ),
            (
                suffix in {".yml", ".yaml"} and not _matches_any(rel, yaml_roots),
                "YAML outside ecosystem-native roots",
            ),
            (
                bool(suffix) and not _path_allowed_for_extension(rel, suffix, policy),
                f"format outside declared carrier home: {suffix}",
            ),
        )
        failures.extend({"path": rel, "reason": reason} for failed, reason in checks if failed)
        if suffix and suffix not in known_exts:
            item = {"path": rel, "extension": suffix}
            if unregistered_extension == "block":
                failures.append(
                    {"path": rel, "reason": f"unregistered tracked extension: {suffix}"}
                )
            else:
                observations.append(item)

    payload = {
        "schema_version": 1,
        "kind": "ethos_format_selection_audit",
        "verdict": "block" if failures else "pass",
        "head": current_tracked_head(ROOT),
        "config": str(CONFIG_PATH.relative_to(ROOT)),
        "generated_at": datetime.now(UTC).isoformat(),
        "format_count": len(formats),
        "failure_count": len(failures),
        "failures": failures,
        "observed_unregistered_extensions": observations[:200],
        "observed_unregistered_extension_count": len(observations),
        "tracked_file_count": ownership["tracked_file_count"],
        "assignment_count": ownership["assignment_count"],
        "unowned_file_count": ownership["unowned_file_count"],
        "multiply_owned_file_count": ownership["multiply_owned_file_count"],
        "unverified_file_count": ownership["unverified_file_count"],
        "assignments": ownership["assignments"],
    }
    payload["failures"] = [*ownership["failures"], *failures]
    payload["failure_count"] = len(payload["failures"])
    payload["verdict"] = "block" if payload["failures"] else "pass"
    sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0 if payload["verdict"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
