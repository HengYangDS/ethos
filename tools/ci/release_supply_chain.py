import json
import shlex
import subprocess
import sys
import tomllib
from datetime import UTC
from datetime import datetime
from pathlib import Path

from ethos.adapters.repo.git import current_tracked_head

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / ".config/release/supply-chain.toml"


def _run_json(command: str):
    result = subprocess.run(
        shlex.split(command),
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        payload = {"raw_stdout": result.stdout}
    return {
        "command": command,
        "returncode": result.returncode,
        "ok": result.returncode == 0 and bool(payload.get("ok", True)),
        "payload": payload,
        "stderr": result.stderr.strip(),
    }


def main() -> int:
    config = tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    command_results = [_run_json(str(command)) for command in config.get("commands", [])]
    failures = [
        {"command": item["command"], "reason": item["stderr"] or "command failed"}
        for item in command_results
        if not item["ok"]
    ]
    boundary = config.get("boundary", {})
    payload = {
        "schema_version": 1,
        "kind": "ethos_release_supply_chain_envelope",
        "ok": not failures,
        "head": current_tracked_head(ROOT),
        "config": str(CONFIG_PATH.relative_to(ROOT)),
        "generated_at": datetime.now(UTC).isoformat(),
        "claim_boundary": boundary.get("claim", ""),
        "not_claimed": boundary.get("not_claimed", []),
        "commands": command_results,
        "failures": failures,
    }
    output = ROOT / str(config["output"])
    output.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    output.write_text(rendered, encoding="utf-8")
    sys.stdout.write(rendered)
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
