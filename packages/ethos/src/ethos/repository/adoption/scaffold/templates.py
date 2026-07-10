"""Typed Jinja scaffold template compiler."""

from __future__ import annotations

import json
import tomllib
from functools import lru_cache
from importlib.resources import files
from typing import Annotated
from typing import Literal

from jinja2 import Environment
from jinja2 import PackageLoader
from jinja2 import StrictUndefined
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import model_validator

from ethos_core.contracts.docs.topology import ROLE_VALUES
from ethos_core.contracts.docs.topology import STATE_VALUES

Profile = Literal["generic", "python", "monorepo", "github", "gitlab"]


class TemplateModel(BaseModel):
    """Strict immutable base for declarations and render contexts."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class PackageTemplateContext(TemplateModel):
    """One package projected into the adopted workspace."""

    name: str
    path: str
    domain: str


class RepositoryTemplateContext(TemplateModel):
    """Repository-wide render context."""

    project_name: str
    profile: Profile
    packages: tuple[PackageTemplateContext, ...]
    roles: tuple[str, ...] = ROLE_VALUES
    states: tuple[str, ...] = STATE_VALUES
    registry_digest: str = ""


class ArtifactTemplate(TemplateModel):
    """Output path to packaged-template binding."""

    path: str
    template: str
    required: bool = False
    profiles: tuple[Profile, ...] = ()
    renderer: Literal["repository", "activation", "skill-package"] = "repository"
    subject: str = ""


class FamilyTemplate(TemplateModel):
    """OpenSpec family declaration used by two templates."""

    id: str
    title: str
    scope: str
    profile_family: str
    owner: str


class CapabilityTemplate(TemplateModel):
    """One declared skill capability."""

    id: str
    kind: str
    command: tuple[str, ...]
    guard: str = ""


class SkillTemplate(TemplateModel):
    """One scaffolded skill package declaration."""

    id: str
    capabilities: tuple[CapabilityTemplate, ...]


class FamilyTemplateContext(TemplateModel):
    """Typed OpenSpec family render context."""

    family: FamilyTemplate


class SkillPackageTemplateContext(TemplateModel):
    """Typed skill package render context."""

    skill: SkillTemplate
    package_digest: str


class ScaffoldTemplateDeclaration(TemplateModel):
    """Validated scaffold template manifest."""

    version: Literal[1]
    artifact: tuple[ArtifactTemplate, ...]
    family: tuple[FamilyTemplate, ...]
    skill: tuple[SkillTemplate, ...]

    @model_validator(mode="after")
    def validate_registry(self) -> ScaffoldTemplateDeclaration:
        """Reject ambiguous or unbound scaffold declaration records."""
        _require_unique("artifact path", tuple(item.path for item in self.artifact))
        _require_unique("family id", tuple(item.id for item in self.family))
        _require_unique("skill id", tuple(item.id for item in self.skill))
        activation_count = sum(item.renderer == "activation" for item in self.artifact)
        if activation_count != 1:
            message = "scaffold declaration requires exactly one activation artifact"
            raise ValueError(message)
        skills = {item.id for item in self.skill}
        unknown_subjects = {
            item.subject
            for item in self.artifact
            if item.renderer == "skill-package" and item.subject not in skills
        }
        if unknown_subjects:
            message = "skill-package artifacts must bind declared skills"
            raise ValueError(message)
        return self


def _require_unique(label: str, values: tuple[str, ...]) -> None:
    if len(values) != len(set(values)):
        message = f"duplicate scaffold {label}"
        raise ValueError(message)


TemplateContext = Annotated[
    RepositoryTemplateContext | FamilyTemplateContext | SkillPackageTemplateContext,
    Field(discriminator=None),
]


@lru_cache(maxsize=1)
def declaration() -> ScaffoldTemplateDeclaration:
    """Load and validate the packaged scaffold declaration."""
    resource = files(__package__).joinpath("template_files/manifest.toml")
    return ScaffoldTemplateDeclaration.model_validate(tomllib.loads(resource.read_text()))


@lru_cache(maxsize=1)
def environment() -> Environment:
    """Return the strict packaged-template environment."""
    template_environment = Environment(
        loader=PackageLoader(__package__, "template_files"),
        undefined=StrictUndefined,
        autoescape=False,
        keep_trailing_newline=True,
    )
    template_environment.filters["json"] = json.dumps
    return template_environment


def template_names() -> tuple[str, ...]:
    """List packaged Jinja templates."""
    return tuple(environment().list_templates(extensions=("j2",)))


def render_template(name: str, context: TemplateContext) -> str:
    """Render one packaged template from a strict typed context."""
    payload = context.model_dump(mode="json")
    if isinstance(context, RepositoryTemplateContext):
        payload["host_ci"] = {
            "github": ".github/workflows/ethos.yml",
            "gitlab": ".gitlab-ci.yml",
        }.get(context.profile, "")
    return environment().get_template(name).render(payload)
