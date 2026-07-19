import json
import subprocess
import sys
import tomllib
from datetime import UTC
from datetime import datetime
from pathlib import Path

from ethos.adapters.repo.git import current_tracked_head

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / ".config/checks/local-state/audit.toml"


def _git_lines(*args: str, root: Path = ROOT) -> list[str]:
    return subprocess.check_output(["git", *args], cwd=root, text=True).splitlines()


def _under(path: str, roots: list[str]) -> bool:
    return any(path == root.rstrip("/") or path.startswith(root) for root in roots)


def ignored_untracked_state(
    root: Path,
    ignored_roots: list[str],
    *,
    excluded_roots: list[str] | None = None,
) -> list[str]:
    """Return ignored, untracked local-state paths under governed ignored roots."""
    ignored = _git_lines("ls-files", "--others", "--ignored", "--exclude-standard", root=root)
    excluded = excluded_roots or [".venv/", "node_modules/"]
    return sorted(
        rel
        for rel in ignored
        if not _under(rel, excluded) and matches_state_root(rel, ignored_roots)
    )


def matches_state_root(path: str, roots: list[str]) -> bool:
    """Return whether a path belongs to a configured local-state root."""
    parts = set(path.split("/"))
    return _under(path, roots) or any(root.rstrip("/") in parts for root in roots)


def forbidden_tracked_state(
    tracked: list[str],
    forbidden_roots: list[str],
    *,
    allowed_placeholders: set[str],
) -> list[dict[str, str]]:
    """Return tracked generated or host-local state violations."""
    return [
        {"path": rel, "reason": "generated or host-local state is tracked"}
        for rel in tracked
        if matches_state_root(rel, forbidden_roots) and rel not in allowed_placeholders
    ]


def _existing_root_state(roots: list[str]) -> list[dict[str, str]]:
    paths = ((root.rstrip("/"), ROOT / root.rstrip("/")) for root in roots)
    return [
        {"path": relative, "kind": "dir" if path.is_dir() else "file"}
        for relative, path in paths
        if path.exists()
    ]


def main() -> int:
    config = tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    tracked = _git_lines("ls-files")
    failures = forbidden_tracked_state(
        tracked,
        config.get("forbidden_tracked_roots", []),
        allowed_placeholders=set(config.get("allowed_state_placeholders", [])),
    )
    ignored_untracked = ignored_untracked_state(
        ROOT,
        config.get("ignored_roots", []),
        excluded_roots=config.get("ignored_excluded_roots", []),
    )
    denied_root_cache_state = _existing_root_state(config.get("denied_root_cache_roots", []))
    payload = {
        "schema_version": 1,
        "kind": "ethos_local_state_audit",
        "ok": not failures and not denied_root_cache_state,
        "head": current_tracked_head(ROOT),
        "config": str(CONFIG_PATH.relative_to(ROOT)),
        "generated_at": datetime.now(UTC).isoformat(),
        "semantic_roots": config.get("semantic_roots", []),
        "ignored_excluded_roots": config.get("ignored_excluded_roots", []),
        "forbidden_tracked_state": failures,
        "denied_root_cache_state": denied_root_cache_state,
        "ignored_untracked_state_count": len(ignored_untracked),
        "ignored_untracked_state_preview": ignored_untracked[:50],
    }
    output = ROOT / str(config["output"])
    output.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    output.write_text(rendered, encoding="utf-8")
    sys.stdout.write(rendered)
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
