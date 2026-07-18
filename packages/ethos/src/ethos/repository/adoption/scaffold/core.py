"""Declaration-first adoption scaffold compiler."""

from __future__ import annotations

import hashlib
import tomllib
from typing import TYPE_CHECKING
from typing import cast

from ethos.repository.adoption.scaffold.templates import FamilyTemplateContext
from ethos.repository.adoption.scaffold.templates import PackageTemplateContext
from ethos.repository.adoption.scaffold.templates import Profile
from ethos.repository.adoption.scaffold.templates import RepositoryTemplateContext
from ethos.repository.adoption.scaffold.templates import SkillPackageTemplateContext
from ethos.repository.adoption.scaffold.templates import declaration
from ethos.repository.adoption.scaffold.templates import render_template
from ethos_core.contracts.skill.activation import normalize_skill_activation
from ethos_core.contracts.skill.activation import skill_registry_digest

if TYPE_CHECKING:
    from pathlib import Path

_DECLARATION = declaration()
BASE_ADOPTION_FILES = tuple(item.path for item in _DECLARATION.artifact if item.required)
OPENSPEC_CAPABILITIES = tuple(item.id for item in _DECLARATION.family)


def _packages(root: Path, profile: str) -> tuple[PackageTemplateContext, ...]:
    packages_dir = root / "packages"
    if profile == "monorepo" and packages_dir.exists():
        packages = tuple(
            PackageTemplateContext(
                name=path.name,
                path=f"packages/{path.name}",
                domain="package",
            )
            for path in sorted(item for item in packages_dir.iterdir() if item.is_dir())
        )
        if packages:
            return packages
    return (PackageTemplateContext(name="root", path=".", domain="repository"),)


def _repository_context(
    root: Path, profile: str, *, registry_digest: str = ""
) -> RepositoryTemplateContext:
    return RepositoryTemplateContext(
        project_name=root.name,
        profile=cast("Profile", profile),
        packages=_packages(root, profile),
        registry_digest=registry_digest,
    )


def _package_digest_from_content(files: dict[str, str]) -> str:
    digest = hashlib.sha256()
    for relative, content in sorted(files.items()):
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(content.encode("utf-8"))
        digest.update(b"\0")
    return f"sha256:{digest.hexdigest()}"


def _activation(context: RepositoryTemplateContext) -> str:
    placeholder = "sha256:" + ("0" * 64)
    provisional = render_template(
        "skills/activation.toml.j2",
        context.model_copy(update={"registry_digest": placeholder}),
    )
    registry = normalize_skill_activation(
        tomllib.loads(provisional), source=".agents/skills/activation.toml"
    )
    return render_template(
        "skills/activation.toml.j2",
        context.model_copy(update={"registry_digest": skill_registry_digest(registry)}),
    )


def default_files(root: Path, profile: str) -> dict[str, str]:
    """Compile the complete adopter scaffold from typed declarations and templates."""
    context = _repository_context(root, profile)
    artifacts = tuple(
        artifact
        for artifact in _DECLARATION.artifact
        if not artifact.profiles or profile in artifact.profiles
    )
    activation_template = next(
        artifact for artifact in artifacts if artifact.renderer == "activation"
    )
    package_templates = tuple(
        artifact for artifact in artifacts if artifact.renderer == "skill-package"
    )
    files = {
        artifact.path: render_template(artifact.template, context)
        for artifact in artifacts
        if artifact.renderer == "repository"
    }

    skills = {skill.id: skill for skill in _DECLARATION.skill}
    for artifact in package_templates:
        skill = skills[artifact.subject]
        skill_text = files[f".agents/skills/{skill.id}/SKILL.md"]
        files[artifact.path] = render_template(
            artifact.template,
            SkillPackageTemplateContext(
                skill=skill,
                package_digest=_package_digest_from_content({"SKILL.md": skill_text}),
            ),
        )

    files[activation_template.path] = _activation(context)

    for family in _DECLARATION.family:
        family_context = FamilyTemplateContext(family=family)
        files[f"openspec/specs/{family.id}/spec.md"] = render_template(
            "openspec/spec.md.j2", family_context
        )
        files[f"openspec/specs/{family.id}/capability.toml"] = render_template(
            "openspec/capability.toml.j2", family_context
        )
    return files
