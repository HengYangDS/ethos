#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def run_json(root: Path, *args: str) -> dict[str, Any]:
    completed = subprocess.run(
        ["uv", "run", "--group", "dev", "ethos", *args],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return {
            "ok": False,
            "command": ["ethos", *args],
            "required_gaps": [f"command_failed:{' '.join(args)}"],
            "stderr": completed.stderr,
        }
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        return {
            "ok": False,
            "command": ["ethos", *args],
            "required_gaps": [f"command_json_invalid:{' '.join(args)}"],
            "error": str(exc),
        }


def skill_dirs(root: Path) -> list[Path]:
    skills_root = root / ".agents" / "skills"
    if not skills_root.exists():
        return []
    return sorted(path for path in skills_root.iterdir() if (path / "SKILL.md").exists())


def local_shape_gaps(root: Path) -> list[str]:
    gaps: list[str] = []
    seen_names: dict[str, str] = {}
    for skill_dir in skill_dirs(root):
        gaps.extend(skill_shape_gaps(skill_dir, seen_names))
    return gaps


def skill_shape_gaps(skill_dir: Path, seen_names: dict[str, str]) -> list[str]:
    skill_id = skill_dir.name
    skill_text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    gaps = _skill_file_gaps(skill_id, skill_text, skill_dir / "package.toml")
    name = skill_frontmatter_name(skill_text)
    if name and name != skill_id:
        gaps.append(f"skill_name_folder_mismatch:{skill_id}:{name}")
    if name in seen_names:
        gaps.append(f"skill_name_duplicate:{name}:{seen_names[name]}:{skill_id}")
    elif name:
        seen_names[name] = skill_id
    return gaps


def _skill_file_gaps(skill_id: str, skill_text: str, manifest: Path) -> list[str]:
    gaps: list[str] = []
    lower_text = skill_text.lower()
    if not manifest.exists():
        gaps.append(f"skill_manifest_missing:{skill_id}")
    if "## Trust Boundary" not in skill_text:
        gaps.append(f"skill_trust_boundary_missing:{skill_id}")
    if "repository truth" not in lower_text and "source of truth" not in lower_text:
        gaps.append(f"skill_truth_boundary_weak:{skill_id}")
    return gaps


def skill_frontmatter_name(skill_text: str) -> str:
    if not skill_text.startswith("---"):
        return ""
    header = skill_text.split("---", 2)[1]
    for line in header.splitlines():
        if line.startswith("name:"):
            return line.split(":", 1)[1].strip()
    return ""


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    playbooks = run_json(root, "playbooks", "check", "--mode", "v2-strict", "--json")
    gaps = []
    gaps.extend(str(gap) for gap in playbooks.get("required_gaps", []))
    gaps.extend(local_shape_gaps(root))
    report = {
        "ok": not gaps,
        "kind": "skill_portfolio_audit",
        "root": str(root),
        "skill_count": len(skill_dirs(root)),
        "checks": {
            "playbooks_v2": {"ok": bool(playbooks.get("ok")), "state": playbooks.get("state")},
            "local_shape": {"ok": not local_shape_gaps(root)},
        },
        "required_gaps": sorted(dict.fromkeys(gaps)),
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
