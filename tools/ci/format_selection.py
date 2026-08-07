import fnmatch
import json
import subprocess
import sys
import tomllib
from datetime import UTC
from datetime import datetime
from pathlib import Path

from ethos.adapters.repo.git import current_tracked_head

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / ".config/checks/format/selection.toml"


def _tracked_files() -> list[str]:
    return subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines()


def _load_config() -> dict[str, object]:
    return tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _matches_any(path: str, roots: list[str]) -> bool:
    return any(path == root.rstrip("/") or path.startswith(root) for root in roots)


def _matches_glob(path: str, pattern: str) -> bool:
    return fnmatch.fnmatchcase(path, pattern) or Path(path).match(pattern)


def _matches_patterns(path: str, patterns: object) -> bool:
    return isinstance(patterns, list) and any(
        isinstance(pattern, str) and _matches_glob(path, pattern) for pattern in patterns
    )


def _owner_matches(path: str, declaration: dict[str, object]) -> bool:
    suffix = Path(path).suffix.lower()
    extensions = declaration.get("extensions", [])
    has_selector = bool(declaration.get("paths")) or bool(extensions)
    selected = _matches_patterns(path, declaration.get("paths", [])) or (
        isinstance(extensions, list) and suffix in extensions
    )
    return (
        has_selector
        and selected
        and not _matches_patterns(path, declaration.get("exclude_paths", []))
    )


def _assignment(path: str, declaration: dict[str, object]) -> dict[str, object]:
    immutable = path.startswith(("evidence/", "openspec/changes/archive/"))
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


def audit(root: Path = ROOT) -> dict[str, object]:
    """Compile one effective quality owner for every tracked repository file."""
    config = tomllib.loads((root / CONFIG_PATH.relative_to(ROOT)).read_text(encoding="utf-8"))
    declarations = [item for item in config.get("ownership", []) if isinstance(item, dict)]
    tracked = subprocess.check_output(["git", "ls-files"], cwd=root, text=True).splitlines()
    assignments: list[dict[str, object]] = []
    failures: list[dict[str, str]] = []
    unowned = multiply_owned = unverified = 0
    for path in tracked:
        matches = [item for item in declarations if _owner_matches(path, item)]
        if not matches:
            unowned += 1
            failures.append({"path": path, "reason": "tracked carrier has no quality owner"})
            continue
        priority = max((int(item.get("priority", 0)) for item in matches), default=0)
        primary = [item for item in matches if int(item.get("priority", 0)) == priority]
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
    known_exts = {
        ext for item in formats for ext in item.get("extensions", []) if isinstance(ext, str)
    }
    tracked = _tracked_files()
    failures: list[dict[str, str]] = []
    observations: list[dict[str, str]] = []

    forbidden_exts = set(policy.get("forbid_tracked_extensions", []))
    jsonl_roots = policy.get("jsonl_allowed_roots", [])
    yaml_roots = policy.get("yaml_allowed_roots", [])
    unregistered_extension = policy.get("unregistered_extension", "observe")

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
