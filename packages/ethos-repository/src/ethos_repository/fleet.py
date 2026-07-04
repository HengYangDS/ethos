from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def _has_docs(root: Path) -> bool:
    return (
        (root / "docs" / "index.md").exists()
        or any((root / "docs" / "current").glob("*.md"))
        or (root / "README.md").exists()
    )


def inspect_adopter(root: Path) -> dict[str, object]:
    repo = root.resolve()
    governance = {
        "ethos_config": (repo / ".ethos" / "project.toml").exists(),
        "workspace": (repo / ".ethos" / "workspace.toml").exists(),
        "rules": (repo / ".ethos" / "rules.toml").exists(),
        "openspec": (repo / "openspec" / "config.yaml").exists()
        and (repo / "openspec" / "specs").exists(),
        "skills": (repo / "skills" / "activation.toml").exists(),
        "docs": _has_docs(repo),
        "claims": (repo / "claims").exists(),
        "evidence": (repo / "docs" / "evidence").exists(),
    }
    required_gaps = [
        f"adopter_missing:{name}" for name, present in governance.items() if not present
    ]
    return {
        "ok": not required_gaps,
        "adopter": {
            "root": str(repo),
            "governance": governance,
            "profile_source": ".ethos/project.toml" if governance["ethos_config"] else "",
        },
        "required_gaps": required_gaps,
    }
