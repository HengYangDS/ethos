from __future__ import annotations

import json
import subprocess
import sys
import tomllib
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

from ethos.adapters.repo.git import current_tracked_head

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / ".config/checks/format/selection.toml"


def _tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def _load_config() -> dict[str, Any]:
    return tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _matches_any(path: str, roots: list[str]) -> bool:
    return any(path == root.rstrip("/") or path.startswith(root) for root in roots)


def _path_allowed_for_extension(path: str, suffix: str, policy: dict[str, Any]) -> bool:
    """Require declared path placement only for extensions with a narrow carrier home."""
    extension_paths = policy.get("extension_paths", {})
    if not isinstance(extension_paths, dict):
        return True
    constraint = extension_paths.get(suffix)
    if not isinstance(constraint, dict):
        return True
    roots = [root for root in constraint.get("roots", []) if isinstance(root, str)]
    files = [file for file in constraint.get("files", []) if isinstance(file, str)]
    return path in files or _matches_any(path, roots)


def main() -> int:
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
    jsonl_roots = list(policy.get("jsonl_allowed_roots", []))
    yaml_roots = list(policy.get("yaml_allowed_roots", []))
    unregistered_extension = policy.get("unregistered_extension", "observe")

    for rel in tracked:
        suffix = Path(rel).suffix
        if suffix in forbidden_exts:
            failures.append({"path": rel, "reason": f"forbidden tracked format: {suffix}"})
        if suffix == ".jsonl" and not _matches_any(rel, jsonl_roots):
            failures.append({"path": rel, "reason": "tracked JSONL outside allowed roots"})
        if suffix in {".yml", ".yaml"} and not _matches_any(rel, yaml_roots):
            failures.append({"path": rel, "reason": "YAML outside ecosystem-native roots"})
        if suffix and not _path_allowed_for_extension(rel, suffix, policy):
            failures.append(
                {"path": rel, "reason": f"format outside declared carrier home: {suffix}"}
            )
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
        "ok": not failures,
        "head": current_tracked_head(ROOT),
        "config": str(CONFIG_PATH.relative_to(ROOT)),
        "generated_at": datetime.now(UTC).isoformat(),
        "format_count": len(formats),
        "failure_count": len(failures),
        "failures": failures,
        "observed_unregistered_extensions": observations[:200],
        "observed_unregistered_extension_count": len(observations),
    }
    sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
