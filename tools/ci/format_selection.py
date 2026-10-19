"""Resolve declared carrier ownership without granting mutation authority."""

import fnmatch
import json
import subprocess
import sys
import tomllib
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import TypeGuard

from ethos.adapters.repo.git import current_tracked_head
from ethos.repository.policy.quality.format_selection import audit

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / ".config/checks/format-selection/policy.toml"


def _record(value: object) -> TypeGuard[dict[str, object]]:
    return isinstance(value, dict) and all(isinstance(key, str) for key in value)


def _records(value: object) -> TypeGuard[list[dict[str, object]]]:
    return isinstance(value, list) and all(_record(item) for item in value)


def _strings(value: object) -> TypeGuard[list[str]]:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _tracked_files() -> list[str]:
    return subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines()


def _load_config() -> dict[str, object]:
    return tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _matches_any(path: str, roots: list[str]) -> bool:
    return any(path == root.rstrip("/") or path.startswith(root) for root in roots)


def _matches_glob(path: str, pattern: str) -> bool:
    return fnmatch.fnmatchcase(path, pattern) or Path(path).match(pattern)


def _matches_patterns(path: str, patterns: list[str]) -> bool:
    return any(_matches_glob(path, pattern) for pattern in patterns)


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
    tracked = _tracked_files()
    ownership = audit(ROOT, paths=tuple(tracked))
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
