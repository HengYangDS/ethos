"""Derive repository context from the selected explicit adoption profile."""

import hashlib
from importlib.resources import files
from pathlib import Path

from ethos.repository.profile import INVALID_PROFILE_ERROR
from ethos.repository.profile import load_repository_profile


def repository_context(root: Path) -> dict[str, object]:
    """Project repository context from its explicit profile."""
    profile = load_repository_profile(root)
    if profile.state == "invalid":
        raise ValueError(INVALID_PROFILE_ERROR)
    guidance_resource = files("ethos").joinpath("data/skills/ethos-repository-work/SKILL.md")
    guidance_path = Path(str(guidance_resource)).resolve(strict=True)
    guidance = guidance_path.read_bytes()
    package = Path(str(files("ethos"))).resolve(strict=True)
    source = Path(__file__).resolve().parents[3]
    documents = source if package == source / "src/ethos" else package / "data/governance"
    sources = []
    for relative, role, sections in (
        (
            "docs/governance/product-design-contract.md",
            "product-meaning",
            ("Construction And Evolution Discipline", "Evidence Planes And Completion Claims"),
        ),
        ("rules/README.md", "rules", ("Rule Record", "Upstream Enforcement")),
    ):
        path = (documents / relative).resolve(strict=True)
        sources.append(
            {
                "origin": "product",
                "role": role,
                "source": relative,
                "path": path.as_posix(),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "sections": list(sections),
            }
        )
    return {
        "contract": "governed_repository",
        "profile": profile.declaration.profile_id if profile.declaration else "unbound",
        "repository": str(root.resolve()),
        "reader_projection_commands": ["ethos status"],
        "truth_boundary": "repository",
        "profile_boundary": "profile_or_adapter",
        "agent_guidance": {
            "authority": "product_projection",
            "media_type": "text/markdown",
            "sha256": hashlib.sha256(guidance).hexdigest(),
            "path": guidance_path.as_posix(),
            "sources": sources,
        },
    }
