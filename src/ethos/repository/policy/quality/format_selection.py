"""Compile declared carrier formatting ownership without granting mutation authority."""

from __future__ import annotations

import fnmatch
import tomllib
from pathlib import Path
from typing import NotRequired
from typing import TypedDict
from typing import TypeGuard
from typing import cast

from ethos.repository.policy.projections import observe_projections

POLICY_PATH = Path(".config/checks/format-selection/policy.toml")


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
    projection_kind: NotRequired[str]


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
        if "projection_kind" in declaration and not _required_text(declaration, "projection_kind"):
            message = f"format ownership projection kind is empty: {owner}"
            raise ValueError(message)
        priority = declaration.get("priority", 0)
        if isinstance(priority, bool) or not isinstance(priority, int):
            message = f"format ownership priority is not an integer: {owner}"
            raise TypeError(message)
    return cast("list[OwnerDeclaration]", value)


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
    immutable = path.startswith("openspec/changes/archive/")
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


def audit(root: Path, *, paths: tuple[str, ...], configuration: Path | None = None) -> CarrierAudit:
    """Compile effective quality ownership for tracked or explicitly selected carriers."""
    config = tomllib.loads((configuration or root / POLICY_PATH).read_text(encoding="utf-8"))
    declarations = _ownership_declarations(config.get("ownership"))
    projection_kinds = (
        {item.output: item.kind for item in observe_projections(root)}
        if any("projection_kind" in item for item in declarations)
        else {}
    )
    tracked = paths
    assignments: list[CarrierAssignment] = []
    failures: list[dict[str, str]] = []
    unowned = multiply_owned = unverified = 0
    for path in tracked:
        matches = [
            item
            for item in declarations
            if _owner_matches(path, item)
            and (
                "projection_kind" not in item
                or projection_kinds.get(path) == item["projection_kind"]
            )
        ]
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
