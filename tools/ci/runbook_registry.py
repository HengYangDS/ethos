import json
import sys
import tomllib
from datetime import UTC
from datetime import datetime
from pathlib import Path

from ethos.adapters.repo.git import current_tracked_head

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / ".config/checks/runbook/registry.toml"


def main() -> int:
    config = tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    registry = ROOT / str(config["registry"])
    text = registry.read_text(encoding="utf-8") if registry.is_file() else ""
    failures: list[dict[str, str]] = []
    entries = config.get("entry", [])
    if not registry.is_file():
        failures.append({"id": "registry", "reason": f"missing {config['registry']}"})
    for entry in entries:
        command = str(entry["command"])
        executable = command.split(maxsplit=1)[0]
        if executable.startswith("tools/") and not (ROOT / executable).is_file():
            failures.append({"id": str(entry["id"]), "reason": f"missing command {executable}"})
        failures.extend(
            {"id": str(entry["id"]), "reason": f"registry missing {needle}"}
            for needle in (entry["id"], command, entry["category"], entry["evidence"])
            if str(needle) not in text
        )
    payload = {
        "schema_version": 1,
        "kind": "ethos_runbook_registry_check",
        "verdict": "block" if failures else "pass",
        "head": current_tracked_head(ROOT),
        "config": str(CONFIG_PATH.relative_to(ROOT)),
        "registry": str(registry.relative_to(ROOT)),
        "generated_at": datetime.now(UTC).isoformat(),
        "entry_count": len(entries),
        "failures": failures,
    }
    sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0 if payload["verdict"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
