from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.repository.profile import RepositoryRoots
from ethos.repository.profile import load_repository_profile
from ethos.repository.profile import profile_required_gaps

if TYPE_CHECKING:
    from pathlib import Path


def _has_docs(root: Path, docs_root: Path) -> bool:
    return (
        (docs_root / "index.md").exists()
        or any((docs_root / "governance").glob("*.md"))
        or any((docs_root / "reference").glob("*.md"))
        or (root / "README.md").exists()
    )


def inspect_adopter(root: Path) -> dict[str, object]:
    repo = root.resolve()
    profile = load_repository_profile(repo)
    declaration = profile.declaration
    roots = declaration.roots if declaration else RepositoryRoots()
    paths = {key: repo / value for key, value in roots.model_dump().items()}
    capabilities = {
        "rules": paths["rules"].exists(),
        "openspec": (paths["openspec"] / "config.yaml").exists()
        and (paths["openspec"] / "specs").exists(),
        "skills": (paths["agent_skills"] / "activation.toml").exists(),
        "docs": _has_docs(repo, paths["docs"]),
        "claims": paths["claims"].exists(),
        "evidence": paths["durable_evidence"].exists(),
    }
    required_gaps = (
        ["adopter_binding_missing:.ethos/profile.toml"]
        if profile.state == "missing"
        else list(profile_required_gaps(profile))
    )
    return {
        "ok": not required_gaps,
        "adopter": {
            "root": str(repo),
            "binding": {"source": profile.source, "ready": profile.state == "valid"},
            "capabilities": capabilities,
        },
        "required_gaps": required_gaps,
    }
