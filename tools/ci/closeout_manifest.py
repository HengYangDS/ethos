import hashlib
import json
import sys
import tomllib
from datetime import UTC
from datetime import datetime
from pathlib import Path

from ethos.adapters.repo.git import current_tracked_head

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / ".config/checks/evidence/closeout.toml"


def main() -> int:
    config = tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    failures: list[dict[str, str]] = [
        {"path": str(root), "reason": "required evidence root missing"}
        for root in config.get("required_roots", [])
        if not (ROOT / str(root)).is_dir()
    ]
    topics: list[dict[str, object]] = []
    for topic in config.get("topic", []):
        files = []
        for key in ("claim", "chronicle", "openspec"):
            relative = str(topic[key])
            path = ROOT / relative
            if path.is_file():
                files.append(
                    {
                        "role": key,
                        "path": relative,
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        "bytes": path.stat().st_size,
                    }
                )
            else:
                failures.append({"path": relative, "reason": f"missing {key}"})
        topics.append({"id": topic["id"], "files": files})
    payload = {
        "schema_version": 1,
        "kind": "ethos_closeout_evidence_manifest",
        "ok": not failures,
        "head": current_tracked_head(ROOT),
        "config": str(CONFIG_PATH.relative_to(ROOT)),
        "generated_at": datetime.now(UTC).isoformat(),
        "topics": topics,
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
