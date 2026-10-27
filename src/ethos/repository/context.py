"""Derive repository context from the selected explicit adoption profile."""

import hashlib
from pathlib import Path

from ethos.repository.profile import INVALID_PROFILE_ERROR
from ethos.repository.profile import load_repository_profile
from ethos.repository.release.resources import GUIDANCE_RESOURCE
from ethos.repository.release.resources import canonical_resource
from ethos.repository.release.resources import packaged_resource


def repository_context(root: Path) -> dict[str, object]:
    """Project repository context from its explicit profile."""
    profile = load_repository_profile(root)
    if profile.state == "invalid":
        raise ValueError(INVALID_PROFILE_ERROR)
    guidance_path = packaged_resource(GUIDANCE_RESOURCE).resolve(strict=True)
    guidance = guidance_path.read_bytes()
    sources = []
    for relative, role, sections in (
        (
            "docs/governance/product-design-contract.md",
            "product-meaning",
            (
                "Product",
                "Construction And Evolution Discipline",
                "Isomorphic Adopter Governance",
                "Feedback Intent Preservation",
                "Recursive Domain Feedback",
                "Evidence Planes And Completion Claims",
            ),
        ),
        ("rules/README.md", "rules", ("Rule Record", "Upstream Enforcement")),
        ("rules/agents.md", "agent-method", ("Rules", "Feedback Closure")),
        (
            "system/README.md",
            "resources",
            ("Definitions And Boundaries", "Source And Installed Resources"),
        ),
        (
            "docs/governance/docs-registry.md",
            "documentation",
            (
                "Semantic Authority And Carrier Boundaries",
                "Human And Agent Reading Contract",
                "Directory entrypoint rule",
                "Portability Boundary",
            ),
        ),
        (
            "docs/governance/product-design-contract.md",
            "adoption",
            ("Binding Taxonomy", "Configuration Boundaries", "First-Hour UX"),
        ),
        ("rules/release.md", "release", ("Rules",)),
        (
            "docs/governance/product-design-contract.md",
            "recovery",
            ("Runtime And State Authority", "Bounded Maintainer Recovery"),
        ),
        (
            "docs/reference/command-plane.md",
            "commands",
            (
                "Workflow And Transport Roots",
                "Runtime Selection and Recovery",
                "Proof Depth",
                "Assurance And Evidence Boundary",
            ),
        ),
    ):
        path = canonical_resource(relative).resolve(strict=True)
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
