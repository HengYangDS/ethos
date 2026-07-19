import json
import os
import sys
import tomllib
from datetime import UTC
from datetime import datetime
from pathlib import Path

from ethos.adapters.repo.git import current_tracked_head

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / ".config/checks/mcp/smoke.toml"
OUTPUT_PATH = ROOT / "build/evidence/agent/mcp/smoke.json"


def main() -> int:
    config = tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    failures: list[dict[str, str]] = []
    checks: list[dict[str, object]] = []
    for check in config.get("check", []):
        path = ROOT / str(check["path"])
        required_text = str(check["required_text"])
        present = path.is_file() and required_text in path.read_text(encoding="utf-8")
        checks.append({"id": check["id"], "path": check["path"], "present": present})
        if not present:
            failures.append({"id": str(check["id"]), "reason": f"missing {required_text}"})
    generated_at = datetime.now(UTC).isoformat()
    run_id = f"{generated_at.replace(':', '').replace('+', 'Z')}-{os.getpid()}"
    run_output_path = ROOT / "build/evidence/agent/mcp/runs" / f"{run_id}.json"
    boundary = config.get("boundary", {})
    payload = {
        "schema_version": 1,
        "kind": "ethos_mcp_projection_smoke",
        "ok": not failures,
        "head": current_tracked_head(ROOT),
        "config": str(CONFIG_PATH.relative_to(ROOT)),
        "generated_at": generated_at,
        "evidence_path": str(run_output_path.relative_to(ROOT)),
        "latest_projection_path": str(OUTPUT_PATH.relative_to(ROOT)),
        "claim_boundary": boundary.get("claim", ""),
        "not_claimed": boundary.get("not_claimed", []),
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
