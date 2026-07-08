from __future__ import annotations

import json
import os
import subprocess
import sys
import tomllib
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / ".config/checks/mcp/smoke.toml"
OUTPUT_PATH = ROOT / "build/evidence/agent/mcp/smoke.json"
RUNS_DIR = ROOT / "build/evidence/agent/mcp/runs"


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


def main() -> int:
    config = _load_config()
    failures: list[dict[str, str]] = []
    checks: list[dict[str, Any]] = []
    for check in config.get("check", []):
        path = ROOT / str(check["path"])
        required_text = str(check["required_text"])
        present = path.is_file() and required_text in path.read_text(encoding="utf-8")
        checks.append({"id": check["id"], "path": check["path"], "present": present})
        if not present:
            failures.append({"id": str(check["id"]), "reason": f"missing {required_text}"})
    generated_at = datetime.now(UTC).isoformat()
    head = _git_head()
    run_id = f"{generated_at.replace(':', '').replace('+', 'Z')}-{os.getpid()}"
    run_output_path = RUNS_DIR / f"{run_id}.json"
    payload = {
        "schema_version": 1,
        "kind": "ethos_mcp_projection_smoke",
        "ok": not failures,
        "head": head,
        "config": str(CONFIG_PATH.relative_to(ROOT)),
        "generated_at": generated_at,
        "evidence_path": str(run_output_path.relative_to(ROOT)),
        "latest_projection_path": str(OUTPUT_PATH.relative_to(ROOT)),
        "claim_boundary": config.get("boundary", {}).get("claim", ""),
        "not_claimed": config.get("boundary", {}).get("not_claimed", []),
        "checks": checks,
        "failures": failures,
    }
    serialized = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    run_output_path.parent.mkdir(parents=True, exist_ok=True)
    run_output_path.write_text(serialized, encoding="utf-8")
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_latest = OUTPUT_PATH.with_name(f"{OUTPUT_PATH.name}.{os.getpid()}.tmp")
    tmp_latest.write_text(serialized, encoding="utf-8")
    tmp_latest.replace(OUTPUT_PATH)
    sys.stdout.write(serialized)
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
