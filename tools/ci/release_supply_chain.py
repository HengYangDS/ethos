from __future__ import annotations

import json
import shlex
import subprocess
import sys
import tomllib
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / ".config/release/supply-chain.toml"


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


def _run_json(command: str) -> dict[str, Any]:
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
    config = _load_config()
    command_results = [_run_json(str(command)) for command in config.get("commands", [])]
    failures = [
        {"command": item["command"], "reason": item["stderr"] or "command failed"}
        for item in command_results
        if not item["ok"]
    ]
    payload = {
        "schema_version": 1,
        "kind": "ethos_release_supply_chain_envelope",
        "ok": not failures,
        "head": _git_head(),
        "config": str(CONFIG_PATH.relative_to(ROOT)),
        "generated_at": datetime.now(UTC).isoformat(),
        "claim_boundary": config.get("boundary", {}).get("claim", ""),
        "not_claimed": config.get("boundary", {}).get("not_claimed", []),
        "commands": command_results,
        "failures": failures,
    }
    output = ROOT / str(config["output"])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
