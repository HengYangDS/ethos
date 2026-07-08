from __future__ import annotations

import json
import subprocess
import sys
import tomllib
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / ".config/checks/local-state/audit.toml"


def _git_head() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def _git_lines(*args: str) -> list[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def _load_config() -> dict[str, Any]:
    return tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _under(path: str, roots: list[str]) -> bool:
    return any(path == root.rstrip("/") or path.startswith(root) for root in roots)


def main() -> int:
    config = _load_config()
    tracked = _git_lines("ls-files")
    untracked = _git_lines("ls-files", "--others", "--exclude-standard")
    forbidden_roots = list(config.get("forbidden_tracked_roots", []))
    allowed_placeholders = set(config.get("allowed_state_placeholders", []))
    ignored_roots = list(config.get("ignored_roots", []))

    failures = [
        {"path": rel, "reason": "generated or host-local state is tracked"}
        for rel in tracked
        if _under(rel, forbidden_roots) and rel not in allowed_placeholders
    ]
    ignored_untracked = [rel for rel in untracked if _under(rel, ignored_roots)]
    payload = {
        "schema_version": 1,
        "kind": "ethos_local_state_audit",
        "ok": not failures,
        "head": _git_head(),
        "config": str(CONFIG_PATH.relative_to(ROOT)),
        "generated_at": datetime.now(UTC).isoformat(),
        "forbidden_tracked_state": failures,
        "ignored_untracked_state_count": len(ignored_untracked),
        "ignored_untracked_state_preview": ignored_untracked[:50],
    }
    output = ROOT / str(config["output"])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
