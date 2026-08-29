from __future__ import annotations

import tomllib
from collections.abc import Mapping
from pathlib import Path
from pathlib import PurePosixPath
from types import MappingProxyType
from typing import Annotated
from typing import Literal

import tomli_w
from pydantic import AfterValidator
from pydantic import BaseModel
from pydantic import BeforeValidator
from pydantic import ConfigDict
from pydantic import Field
from pydantic import PlainSerializer
from pydantic import ValidationError
from pydantic import model_validator

from ethos.contracts.gates import Gate
from ethos.contracts.openspec.models import OpenSpecPolicy

DEFAULT_ROOTS = {
    "rules": "rules",
    "docs": "docs",
    "durable_evidence": "evidence",
    "openspec": "openspec",
    "agent_skills": ".agents/skills",
}

PATH_TYPE_ERROR = "repository path must be a string"
PATH_VALUE_ERROR = "repository path must be relative POSIX without dot segments"
INVALID_PROFILE_ERROR = "repository_profile_invalid:.ethos/profile.toml"


def _repository_path(value: object) -> str:
    if not isinstance(value, str):
        raise TypeError(PATH_TYPE_ERROR)
    path = PurePosixPath(value)
    if value in {"", "."} or value.startswith(("/", "./")) or "\\" in value or "\x00" in value:
        raise ValueError(PATH_VALUE_ERROR)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(PATH_VALUE_ERROR)
    return value


NonEmpty = Annotated[str, Field(min_length=1)]
RepositoryPath = Annotated[str, BeforeValidator(_repository_path)]
NonEmptyTuple = Annotated[
    tuple[NonEmpty, ...],
    BeforeValidator(lambda value: tuple(value) if isinstance(value, list) else value),
]
RepositoryPathTuple = Annotated[
    tuple[RepositoryPath, ...],
    BeforeValidator(lambda value: tuple(value) if isinstance(value, list) else value),
]
CodeCorrectnessMap = Annotated[
    Mapping[str, NonEmpty],
    AfterValidator(lambda value: MappingProxyType(dict(value))),
    PlainSerializer(dict, return_type=dict),
]
GateTuple = Annotated[
    tuple[Gate, ...],
    BeforeValidator(lambda value: tuple(value) if isinstance(value, list) else value),
]


class _ProfileModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, validate_default=True)


class RepositoryRoots(_ProfileModel):
    rules: RepositoryPath = DEFAULT_ROOTS["rules"]
    docs: RepositoryPath = DEFAULT_ROOTS["docs"]
    durable_evidence: RepositoryPath = DEFAULT_ROOTS["durable_evidence"]
    openspec: RepositoryPath = DEFAULT_ROOTS["openspec"]
    agent_skills: RepositoryPath = DEFAULT_ROOTS["agent_skills"]


class EvidenceRoots(_ProfileModel):
    durable_roots: RepositoryPathTuple = ()
    generated_roots: RepositoryPathTuple = ()
    host_local_roots: RepositoryPathTuple = ()


class ProofPolicy(_ProfileModel):
    gate_registry: RepositoryPath | None = None
    code_correctness_gates: NonEmptyTuple = ()
    gates: GateTuple = ()
    code_correctness_map: CodeCorrectnessMap = Field(default_factory=dict)

    @model_validator(mode="after")
    def require_one_gate_owner(self) -> ProofPolicy:
        """Reject a local registry and profile-native gates as parallel owners."""
        native = bool(self.code_correctness_gates or self.gates or self.code_correctness_map)
        if self.gate_registry and native:
            msg = "proof policy has parallel gate owners"
            raise ValueError(msg)
        if any("registries" in gate.model_fields_set for gate in self.gates):
            msg = "profile gates cannot select registries"
            raise ValueError(msg)
        gate_ids = tuple(gate.id for gate in self.gates)
        if len(gate_ids) != len(set(gate_ids)) or set(gate_ids) != set(self.code_correctness_gates):
            msg = "proof gate descriptors must match the proof floor exactly"
            raise ValueError(msg)
        mapped = tuple(self.code_correctness_map.values())
        if self.code_correctness_gates and (
            set(self.code_correctness_map) != {"behavior", "static-analysis"}
            or len(mapped) != len(set(mapped))
            or not set(mapped) <= set(self.code_correctness_gates)
        ):
            msg = "proof code axes must map distinct required gates"
            raise ValueError(msg)
        return self


class VerificationAction(_ProfileModel):
    mode: Literal["disabled", "optional", "required"] = "disabled"


class VerificationActions(_ProfileModel):
    publish: VerificationAction | None = None


class IndependentVerificationPolicy(_ProfileModel):
    mode: Literal["disabled", "optional", "required"] = "disabled"
    actions: VerificationActions = Field(default_factory=VerificationActions)


class AdoptionBoundaryPolicy(_ProfileModel):
    binding_manifest: RepositoryPath = ".ethos/profile.toml"
    execution_config_root: RepositoryPath = ".config"
    forbidden_external_product_roots: RepositoryPathTuple = ()


class RepositoryProfileDeclaration(_ProfileModel):
    """The one typed repository binding shared by every profile reader."""

    profile_id: NonEmpty
    openspec: OpenSpecPolicy | None = None
    normative_sources: RepositoryPathTuple = ()
    roots: RepositoryRoots = Field(default_factory=RepositoryRoots)
    evidence: EvidenceRoots = Field(default_factory=EvidenceRoots)
    proof: ProofPolicy = Field(default_factory=ProofPolicy)
    independent_verification: IndependentVerificationPolicy = Field(
        default_factory=IndependentVerificationPolicy
    )
    adoption_boundary: AdoptionBoundaryPolicy = Field(default_factory=AdoptionBoundaryPolicy)

    @classmethod
    def bootstrap(cls, profile_id: str) -> RepositoryProfileDeclaration:
        return cls(profile_id=profile_id)


class RepositoryProfile(_ProfileModel):
    root: Path
    exists: bool
    source: str = ""
    declaration: RepositoryProfileDeclaration | None = None

    @property
    def state(self) -> Literal["missing", "valid", "invalid"]:
        return "valid" if self.declaration else "invalid" if self.exists else "missing"


def render_repository_profile(declaration: RepositoryProfileDeclaration) -> str:
    """Serialize the minimal bootstrap through the canonical TOML writer."""
    return tomli_w.dumps(declaration.model_dump(mode="json", exclude_defaults=True))


def repository_profile_from_text(root: Path, *, exists: bool, text: str) -> RepositoryProfile:
    """Parse one already-observed repository profile material."""
    repo = root.resolve()
    declaration = None
    if exists:
        try:
            declaration = RepositoryProfileDeclaration.model_validate(tomllib.loads(text))
        except (tomllib.TOMLDecodeError, ValidationError):
            declaration = None
    return RepositoryProfile(
        root=repo,
        exists=exists,
        source=".ethos/profile.toml" if exists else "",
        declaration=declaration,
    )


def load_repository_profile(root: Path) -> RepositoryProfile:
    """Load and parse the worktree repository profile."""
    repo = root.resolve()
    path = repo / ".ethos" / "profile.toml"
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(repo)
        exists, text = True, resolved.read_text(encoding="utf-8") if resolved.is_file() else ""
    except FileNotFoundError:
        exists, text = path.is_symlink(), ""
    except (OSError, RuntimeError, UnicodeDecodeError, ValueError):
        exists, text = path.exists() or path.is_symlink(), ""
    return repository_profile_from_text(repo, exists=exists, text=text)


def profile_root(root: Path, key: str) -> Path:
    profile = load_repository_profile(root)
    if profile.state == "invalid":
        raise ValueError(INVALID_PROFILE_ERROR)
    roots = profile.declaration.roots if profile.declaration else RepositoryRoots()
    return profile.root / getattr(roots, key)


def profile_required_gaps(profile: RepositoryProfile) -> tuple[str, ...]:
    return (INVALID_PROFILE_ERROR,) if profile.state == "invalid" else ()


def profile_evidence_roots(root: Path) -> tuple[str, ...]:
    profile = load_repository_profile(root)
    if profile.state == "invalid":
        raise ValueError(INVALID_PROFILE_ERROR)
    declaration = profile.declaration or RepositoryProfileDeclaration.bootstrap(root.name)
    roots = declaration.roots
    candidates = [
        ".ethos/profile.toml",
        *((declaration.proof.gate_registry,) if declaration.proof.gate_registry else ()),
        roots.rules,
        *declaration.normative_sources,
        *((roots.openspec,) if declaration.openspec is not None else ()),
        roots.durable_evidence,
        roots.docs,
    ]
    for values in declaration.evidence.model_dump().values():
        candidates.extend(values)
    return tuple(dict.fromkeys(item for item in candidates if item))


def profile_gate_registry(root: Path) -> str:
    """Return the repository-declared gate registry, if any."""
    profile = load_repository_profile(root)
    if profile.state == "invalid":
        raise ValueError(INVALID_PROFILE_ERROR)
    return profile.declaration.proof.gate_registry or "" if profile.declaration else ""
