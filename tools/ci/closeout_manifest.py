from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tomllib
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / ".config/checks/evidence/closeout.toml"


def _git_head() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def _load_config() -> dict[str, Any]:
    return tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _topic_file(
    topic: dict[str, Any],
    key: str,
    failures: list[dict[str, str]],
) -> dict[str, Any] | None:
    rel = str(topic[key])
    path = ROOT / rel
    if not path.is_file():
        failures.append({"path": rel, "reason": f"missing {key}"})
        return None
    return {
        "role": key,
        "path": rel,
        "sha256": _sha256(path),
        "bytes": path.stat().st_size,
    }


def main() -> int:
    config = _load_config()
    failures: list[dict[str, str]] = [
        {"path": str(root), "reason": "required evidence root missing"}
        for root in config.get("required_roots", [])
        if not (ROOT / str(root)).is_dir()
    ]
    topics: list[dict[str, Any]] = []
    for topic in config.get("topic", []):
        files = [
            file_entry
            for key in ("claim", "chronicle", "openspec")
            if (file_entry := _topic_file(topic, key, failures)) is not None
        ]
        topics.append({"id": topic["id"], "files": files})
    payload = {
        "schema_version": 1,
        "kind": "ethos_closeout_evidence_manifest",
        "ok": not failures,
        "head": _git_head(),
        "config": str(CONFIG_PATH.relative_to(ROOT)),
        "generated_at": datetime.now(UTC).isoformat(),
        "topics": topics,
        "failures": failures,
    }
    output = ROOT / str(config["output"])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
