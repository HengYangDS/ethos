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
CONFIG_PATH = ROOT / ".config/checks/runbook/registry.toml"


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
    registry = ROOT / str(config["registry"])
    text = registry.read_text(encoding="utf-8") if registry.is_file() else ""
    failures: list[dict[str, str]] = []
    entries = config.get("entry", [])
    if not registry.is_file():
        failures.append({"id": "registry", "reason": f"missing {config['registry']}"})
    for entry in entries:
        command = str(entry["command"])
        executable = command.split(maxsplit=1)[0]
        if executable.startswith("ETHOS_LOCAL_EMULATOR_DRY_RUN=1"):
            executable = command.split()[1]
        if executable.startswith("tools/") and not (ROOT / executable).is_file():
            failures.append({"id": str(entry["id"]), "reason": f"missing command {executable}"})
        expected_needles = [
            str(entry["id"]),
            command,
            str(entry["category"]),
            str(entry["evidence"]),
        ]
        missing_needles = [needle for needle in expected_needles if needle not in text]
        failures.extend(
            {"id": str(entry["id"]), "reason": f"registry missing {needle}"}
            for needle in missing_needles
        )
    payload = {
        "schema_version": 1,
        "kind": "ethos_runbook_registry_check",
        "ok": not failures,
        "head": _git_head(),
        "config": str(CONFIG_PATH.relative_to(ROOT)),
        "registry": str(registry.relative_to(ROOT)),
        "generated_at": datetime.now(UTC).isoformat(),
        "entry_count": len(entries),
        "failures": failures,
    }
    sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
