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
CONFIG_PATH = ROOT / ".config/checks/architecture/projection.toml"
HEADER = "%% Generated from {source}. Do not edit by hand."
MIN_QUOTED_PARTS = 2
DESCRIPTION_QUOTED_PARTS = 4
IDENTIFIER_INDEX = 1
RELATION_SOURCE_INDEX = 1
RELATION_TARGET_INDEX = 2


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


def _parse_model(source: Path) -> tuple[dict[str, str], list[tuple[str, str, str]]]:
    nodes: dict[str, str] = {}
    rels: list[tuple[str, str, str]] = []
    for raw in source.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split('"')
        if line.startswith(("system ", "container ")) and len(parts) >= MIN_QUOTED_PARTS:
            head = parts[0].split()
            ident = head[IDENTIFIER_INDEX]
            label_parts = [parts[1]]
            if len(parts) >= DESCRIPTION_QUOTED_PARTS and parts[3].strip():
                label_parts.append(parts[3])
            nodes[ident] = " ".join(label_parts).strip()
        elif line.startswith("rel ") and len(parts) >= MIN_QUOTED_PARTS:
            left = line.split('"', 1)[0].split()
            rels.append((left[RELATION_SOURCE_INDEX], left[RELATION_TARGET_INDEX], parts[1]))
    return nodes, rels


def render(source_rel: str) -> str:
    source = ROOT / source_rel
    nodes, rels = _parse_model(source)
    lines = [HEADER.format(source=source_rel), "flowchart LR"]
    for ident, label in nodes.items():
        lines.append(f'  {ident}["{label}"]')
    for src, dst, label in rels:
        lines.append(f'  {src} -->|"{label}"| {dst}')
    return "\n".join(lines) + "\n"


def main() -> int:
    config = _load_config()
    failures: list[dict[str, str]] = []
    projections: list[dict[str, Any]] = []
    for entry in config.get("projection", []):
        source = str(entry["source"])
        output = str(entry["output"])
        expected = render(source)
        output_path = ROOT / output
        actual = output_path.read_text(encoding="utf-8") if output_path.is_file() else ""
        matches = actual == expected
        if not matches:
            failures.append({"id": str(entry["id"]), "reason": f"projection drift: {output}"})
        projections.append(
            {
                "id": entry["id"],
                "source": source,
                "output": output,
                "matches": matches,
                "truth_boundary": entry.get("truth_boundary", ""),
            }
        )
    payload = {
        "schema_version": 1,
        "kind": "ethos_architecture_projection_drift",
        "ok": not failures,
        "head": _git_head(),
        "config": str(CONFIG_PATH.relative_to(ROOT)),
        "generated_at": datetime.now(UTC).isoformat(),
        "projections": projections,
        "failures": failures,
    }
    sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
