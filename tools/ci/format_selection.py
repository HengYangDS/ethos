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
    }
    sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0 if payload["verdict"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
