from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.repository.profile import load_repository_profile
from ethos.repository.profile import profile_root

if TYPE_CHECKING:
    from pathlib import Path


def _has_docs(root: Path) -> bool:
    docs_root = profile_root(root, "docs")
    return (
        (docs_root / "index.md").exists()
        or any((docs_root / "current").glob("*.md"))
        or (root / "README.md").exists()
    )


def inspect_adopter(root: Path) -> dict[str, object]:
    repo = root.resolve()
    profile = load_repository_profile(repo)
    legacy_ethos_config = (repo / ".ethos" / "project.toml").exists()
    legacy_workspace = (repo / ".ethos" / "workspace.toml").exists()
    legacy_rules = (repo / ".ethos" / "rules.toml").exists()
    governance = {
        "ethos_config": profile.exists or legacy_ethos_config,
        "workspace": profile.exists or legacy_workspace,
        "rules": profile_root(repo, "rules").exists() or legacy_rules,
        "openspec": (profile_root(repo, "openspec") / "config.yaml").exists()
        and (profile_root(repo, "openspec") / "specs").exists(),
        "skills": (profile_root(repo, "agent_skills") / "activation.toml").exists(),
        "docs": _has_docs(repo),
        "claims": profile_root(repo, "claims").exists(),
        "evidence": profile_root(repo, "durable_evidence").exists(),
    }
    required_gaps = [
        f"adopter_missing:{name}" for name, present in governance.items() if not present
    ]
    return {
        "ok": not required_gaps,
        "adopter": {
            "root": str(repo),
            "governance": governance,
            "profile_source": profile.source
            or (".ethos/project.toml" if legacy_ethos_config else ""),
            "profile_valid": profile.valid,
            "roots": profile.roots,
        },
        "required_gaps": required_gaps,
    }
