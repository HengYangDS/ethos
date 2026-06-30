from __future__ import annotations

from pathlib import Path

DEFAULT_FILES = {
    ".ethos/project.toml": (
        '[meta]\nname = "adopted-project"\nproduct = "ETHOS"\nversion = 1\n'
    ),
    ".ethos/workspace.toml": (
        '[[package]]\nname = "root"\npath = "."\ndomains = ["repository"]\n'
    ),
    ".ethos/rules.toml": """[command_plane]\npublic = \"ethos\"\n""",
    ".ethos/assistants.toml": """[projections]\ntruth = \"repository\"\n""",
    ".ethos/state/.gitignore": "*\n!.gitignore\n",
}


def adoption_plan(root: Path, *, apply: bool = False) -> dict[str, object]:
    planned = sorted(DEFAULT_FILES)
    if apply:
        for relative, content in DEFAULT_FILES.items():
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
    return {
        "root": str(root),
        "planned_files": planned,
        "applied": apply,
        "profile": "generic",
    }
