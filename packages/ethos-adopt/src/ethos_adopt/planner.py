from __future__ import annotations

import json
from pathlib import Path

STATIC_DEFAULT_FILES = {
    ".ethos/workspace.toml": (
        '[[package]]\nname = "root"\npath = "."\ndomains = ["repository"]\n'
    ),
    ".ethos/rules.toml": """[command_plane]\npublic = \"ethos\"\n""",
    ".ethos/assistants.toml": """[projections]\ntruth = \"repository\"\n""",
    ".ethos/state/.gitignore": "*\n!.gitignore\n",
}


def _default_files(root: Path) -> dict[str, str]:
    project_name = json.dumps(root.name)
    return {
        ".ethos/project.toml": (
            f"[meta]\nname = {project_name}\nproduct = \"ETHOS\"\nversion = 1\n"
        ),
        **STATIC_DEFAULT_FILES,
    }


def detect_repo_profile(root: Path) -> str:
    if (root / "pyproject.toml").exists():
        return "python-package"
    if (root / ".gitlab-ci.yml").exists():
        return "gitlab"
    if (root / ".github").exists():
        return "github"
    return "generic"


def adoption_plan(root: Path, *, apply: bool = False) -> dict[str, object]:
    files = _default_files(root)
    planned = sorted(files)
    profile = detect_repo_profile(root)
    if apply:
        for relative, content in files.items():
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
    return {
        "root": str(root),
        "planned_files": planned,
        "applied": apply,
        "profile": profile,
    }
