"""Load immutable repository profiles with strict roots and policy boundaries."""

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
from ethos.contracts.gates import GateProofSets
from ethos.contracts.gates import GateRegistryDeclaration
from ethos.contracts.openspec.models import OpenSpecPolicy

DEFAULT_ROOTS = {
    "rules": "rules",
    "docs": "docs",
    "agent_skills": ".agents/skills",
}

PATH_VALUE_ERROR = "repository path must be relative POSIX without dot segments"
INVALID_PROFILE_ERROR = "repository_profile_invalid:.ethos/profile.toml"


def _repository_path(value: str) -> str:
    path = PurePosixPath(value)
    if value in {"", "."} or value.startswith(("/", "./")) or "\\" in value or "\x00" in value:
        raise ValueError(PATH_VALUE_ERROR)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(PATH_VALUE_ERROR)
    return value


NonEmpty = Annotated[str, Field(min_length=1)]
RepositoryPath = Annotated[str, AfterValidator(_repository_path)]
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
    agent_skills: RepositoryPath = DEFAULT_ROOTS["agent_skills"]


SourceMember = Annotated[
    tuple[NonEmpty, RepositoryPath],
    BeforeValidator(lambda value: tuple(value) if isinstance(value, list) else value),
]
SourceMembers = Annotated[
    Mapping[RepositoryPath, SourceMember],
    BeforeValidator(lambda value: dict(value) if isinstance(value, Mapping) else value),
    AfterValidator(lambda value: MappingProxyType(dict(value))),
    PlainSerializer(dict, return_type=dict),
]


class SourceContract(_ProfileModel):
    """Bind artifacts to an existing native producer or locked upstream member.

    This is an obligation declaration, not proof that the output is authentic.
    """

    kind: Literal["generated", "upstream"]
    input_refs: NonEmptyTuple
    members: SourceMembers
    integrity_gate: NonEmpty

    @model_validator(mode="after")
    def require_bounded_native_relations(self) -> SourceContract:
        """Preserve exact repository members and one meaning for each reference."""
        used = {reference for reference, _member in self.members.values()}
        if not self.members or used != set(self.input_refs) or len(used) != len(self.input_refs):
            message = "source contract must use each distinct input reference"
            raise ValueError(message)
        for reference in self.input_refs:
            owner, separator, package = reference.partition("#packages/")
            _repository_path(owner)
            if PurePosixPath(owner).as_posix() != owner:
                message = "source reference must use an exact repository path"
                raise ValueError(message)
            if self.kind == "generated":
                valid = not separator and "#" not in owner
            else:
                valid = (
                    bool(separator)
                    and owner.endswith(".json")
                    and package.startswith("node_modules/")
                )
                if valid:
                    _repository_path(package)
                    valid = PurePosixPath(package).as_posix() == package and "#" not in package
            if not valid:
                message = "source reference has no supported native meaning"
                raise ValueError(message)
        for artifact, (_reference, member) in self.members.items():
            valid = PurePosixPath(artifact).as_posix() == artifact
            valid &= (
                member == artifact if self.kind == "generated" else member.startswith("package/")
            )
            if not valid or PurePosixPath(member).as_posix() != member:
                message = "source member must preserve its exact native identity"
                raise ValueError(message)
        return self


SourceContracts = Annotated[
    tuple[SourceContract, ...],
    BeforeValidator(lambda value: tuple(value) if isinstance(value, list) else value),
]


class ProofPolicy(_ProfileModel):
    gate_registry: RepositoryPath | None = None
    code_correctness_gates: NonEmptyTuple = ()
    gates: GateTuple = ()
    code_correctness_map: CodeCorrectnessMap = Field(default_factory=dict)
    source_contracts: SourceContracts = ()

    @property
    def source_kinds(self) -> dict[str, Literal["generated", "upstream"]]:
        """Compile artifact classification from the one explicit source obligation."""
        return {
            path: contract.kind for contract in self.source_contracts for path in contract.members
        }

    @model_validator(mode="after")
    def require_one_gate_owner(self) -> ProofPolicy:
        """Reject a local registry and profile-native gates as parallel owners."""
        artifacts = [path for contract in self.source_contracts for path in contract.members]
        if len(artifacts) != len(set(artifacts)):
            message = "source artifact has parallel owners"
            raise ValueError(message)
        native = bool(self.code_correctness_gates or self.gates or self.code_correctness_map)
        if self.gate_registry and native:
            msg = "proof policy has parallel gate owners"
            raise ValueError(msg)
        if native:
            declaration = GateRegistryDeclaration(
                id="profile-native",
                proof_sets=GateProofSets(
                    default=self.code_correctness_gates,
                    full=self.code_correctness_gates,
                ),
                gates=self.gates,
            )
            closure = {gate.id for gate in declaration.proof_gates()}
            if not self.code_correctness_gates:
                msg = "profile-native proof policy must declare default roots"
                raise ValueError(msg)
            if self.code_correctness_map and (
                set(self.code_correctness_map) != {"behavior", "static-analysis"}
                or not set(self.code_correctness_map.values()) <= closure
            ):
                msg = "proof code axes must map required gates"
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
