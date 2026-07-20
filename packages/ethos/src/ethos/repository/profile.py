from __future__ import annotations

import subprocess
import tomllib
from collections.abc import Mapping
from contextlib import suppress
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

from ethos_core.contracts.gates import GateDescriptor
from ethos_core.contracts.openspec.models import AdopterOpenSpecPolicy

DEFAULT_ROOTS = {
    "rules": "rules",
    "docs": "docs",
    "durable_evidence": "evidence",
    "openspec": "openspec",
    "claims": "evidence/claims",
    "agent_skills": ".agents/skills",
    "local_state": ".ethos/state",
}

DEFAULT_MATERIAL_PATHS = (
    ".ethos/profile.toml",
    "openspec/**",
    "docs/governance/**",
    "rules/**",
)
PATH_TYPE_ERROR = "repository path must be a string"
PATH_VALUE_ERROR = "repository path must be relative POSIX without dot segments"
INVALID_PROFILE_ERROR = "adopter_profile_invalid:.ethos/profile.toml"


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
StringTupleMap = Annotated[
    Mapping[str, NonEmptyTuple],
    AfterValidator(lambda value: MappingProxyType(dict(value))),
    PlainSerializer(dict, return_type=dict),
]
CodeCorrectnessEntry = NonEmpty | Mapping[str, NonEmpty]
CodeCorrectnessMap = Annotated[
    Mapping[str, CodeCorrectnessEntry],
    AfterValidator(
        lambda value: MappingProxyType(
            {
                key: MappingProxyType(dict(entry)) if isinstance(entry, Mapping) else entry
                for key, entry in value.items()
            }
        )
    ),
    PlainSerializer(
        lambda value: {
            key: dict(entry) if isinstance(entry, Mapping) else entry
            for key, entry in value.items()
        },
        return_type=dict,
    ),
]
GateTuple = Annotated[
    tuple["AdopterGateDescriptor", ...],
    BeforeValidator(lambda value: tuple(value) if isinstance(value, list) else value),
]


class _ProfileModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, validate_default=True)


class RepositoryRoots(_ProfileModel):
    rules: RepositoryPath = DEFAULT_ROOTS["rules"]
    docs: RepositoryPath = DEFAULT_ROOTS["docs"]
    durable_evidence: RepositoryPath = DEFAULT_ROOTS["durable_evidence"]
    openspec: RepositoryPath = DEFAULT_ROOTS["openspec"]
    claims: RepositoryPath = DEFAULT_ROOTS["claims"]
    agent_skills: RepositoryPath = DEFAULT_ROOTS["agent_skills"]
    local_state: RepositoryPath = DEFAULT_ROOTS["local_state"]


class EvidenceRoots(_ProfileModel):
    durable_roots: RepositoryPathTuple = ()
    generated_roots: RepositoryPathTuple = ()
    host_local_roots: RepositoryPathTuple = ()


class AdopterGateDescriptor(GateDescriptor):
    profile: Literal["adopter"] = "adopter"
    toolchain: str = "repository-native"
    execution_mode: str = "subprocess"
    tool_adapter: str = "repository-native"


class ProofPolicy(_ProfileModel):
    code_correctness_gates: NonEmptyTuple = ()
    gates: GateTuple = ()
    code_correctness_axes: StringTupleMap = Field(default_factory=dict)
    code_correctness_map: CodeCorrectnessMap = Field(default_factory=dict)


class VerificationAction(_ProfileModel):
    mode: Literal["disabled", "optional", "required"] = "disabled"


class VerificationActions(_ProfileModel):
    publish: VerificationAction | None = None


class IndependentVerificationPolicy(_ProfileModel):
    mode: Literal["disabled", "optional", "required"] = "disabled"
    actions: VerificationActions = Field(default_factory=VerificationActions)


class ContainerContractPolicy(_ProfileModel):
    schema_version: Literal[1]
    manifest: Literal[".ethos/container-contract.toml"]


class AdoptionBoundaryPolicy(_ProfileModel):
    binding_manifest: RepositoryPath = ".ethos/profile.toml"
    execution_config_root: RepositoryPath = ".config"
    forbidden_external_product_roots: RepositoryPathTuple = ()


class BackendPolicy(_ProfileModel):
    state: NonEmpty
    minimum_version: str = ""
    shadow_required: bool = False
    control: RepositoryPath | Literal[""] = ""
    retirement_policy: RepositoryPath | Literal[""] = ""


class RollbackWindowPolicy(_ProfileModel):
    state: NonEmpty
    evidence_manifest: RepositoryPath | Literal[""] = ""
    completed_scenarios: NonEmptyTuple = ()
    required_scenarios: NonEmptyTuple = ()


class RepositoryProfileDeclaration(_ProfileModel):
    """The one typed adopter binding contract shared by every profile reader."""

    profile_id: NonEmpty
    openspec: AdopterOpenSpecPolicy
    normative_sources: RepositoryPathTuple = ()
    roots: RepositoryRoots = Field(default_factory=RepositoryRoots)
    evidence: EvidenceRoots = Field(default_factory=EvidenceRoots)
    proof: ProofPolicy = Field(default_factory=ProofPolicy)
    independent_verification: IndependentVerificationPolicy = Field(
        default_factory=IndependentVerificationPolicy
    )
    container_contract: ContainerContractPolicy | None = None
    adoption_boundary: AdoptionBoundaryPolicy = Field(default_factory=AdoptionBoundaryPolicy)
    external_backend: BackendPolicy | None = None
    embedded_backend: BackendPolicy | None = None
    rollback_window: RollbackWindowPolicy | None = None

    @classmethod
    def bootstrap(cls, profile_id: str) -> RepositoryProfileDeclaration:
        return cls(
            profile_id=profile_id,
            openspec=AdopterOpenSpecPolicy(material_paths=DEFAULT_MATERIAL_PATHS),
        )


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


def load_repository_profile(root: Path, *, tree_ref: str | None = None) -> RepositoryProfile:
    repo = root.resolve()
    exists, text = _profile_text(repo, tree_ref)
    declaration = None
    if exists:
        with suppress(tomllib.TOMLDecodeError, ValidationError):
            declaration = RepositoryProfileDeclaration.model_validate(
                _normalize_legacy_profile_payload(tomllib.loads(text))
            )
    return RepositoryProfile(
        root=repo,
        exists=exists,
        source=".ethos/profile.toml" if exists else "",
        declaration=declaration,
    )


def _normalize_legacy_profile_payload(payload: object) -> object:
    """Normalize the one explicit former profile declaration before validation.

    The former envelope carried version and repository-identification metadata
    that no longer participates in the typed binding.  Its former root-level
    rules workaround is normalized only with that complete historical shape;
    partial or malformed legacy data remains invalid under the strict validator.
    """
    if not isinstance(payload, dict):
        return payload
    retired = ("schema_version", "profile_version", "ethos_contract_version", "repository")
    if not any(key in payload for key in retired):
        return payload
    repository = payload.get("repository")
    repository_fields = repository if isinstance(repository, dict) else {}
    kind = repository_fields.get("kind")
    root_subject = repository_fields.get("root_subject")
    expected = (
        payload.get("schema_version") == 1
        and payload.get("profile_version") == "1"
        and payload.get("ethos_contract_version") == "1"
        and set(repository_fields) == {"kind", "root_subject"}
        and isinstance(kind, str)
        and bool(kind)
        and isinstance(root_subject, str)
        and bool(root_subject)
    )
    if not expected:
        return payload
    normalized = {key: value for key, value in payload.items() if key not in retired}
    roots = normalized.get("roots")
    if isinstance(roots, dict) and roots.get("rules") == ".":
        normalized["roots"] = {key: value for key, value in roots.items() if key != "rules"}
        if normalized.get("normative_sources") is None:
            normalized["normative_sources"] = ["guidelines.md"]
    return normalized


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, check=False, text=True
    )


def _profile_text(repo: Path, tree_ref: str | None) -> tuple[bool, str]:
    if tree_ref:
        result = _git(repo, "show", f"{tree_ref}:.ethos/profile.toml")
        if result.returncode == 0:
            return True, result.stdout
        if _git(repo, "rev-parse", "--verify", f"{tree_ref}^{{commit}}").returncode == 0:
            return False, ""
    path = repo / ".ethos" / "profile.toml"
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(repo)
        return True, resolved.read_text(encoding="utf-8") if resolved.is_file() else ""
    except FileNotFoundError:
        return path.is_symlink(), ""
    except (OSError, RuntimeError, UnicodeDecodeError, ValueError):
        return path.exists() or path.is_symlink(), ""


def profile_root(root: Path, key: str) -> Path:
    profile = load_repository_profile(root)
    if profile.state == "invalid":
        raise ValueError(INVALID_PROFILE_ERROR)
    roots = profile.declaration.roots if profile.declaration else RepositoryRoots()
    return profile.root / getattr(roots, key)


def profile_required_gaps(profile: RepositoryProfile) -> tuple[str, ...]:
    return ("adopter_profile_invalid:.ethos/profile.toml",) if profile.state == "invalid" else ()


def profile_evidence_roots(root: Path) -> tuple[str, ...]:
    profile = load_repository_profile(root)
    if profile.state == "invalid":
        raise ValueError(INVALID_PROFILE_ERROR)
    declaration = profile.declaration or RepositoryProfileDeclaration.bootstrap(root.name)
    roots = declaration.roots
    candidates = [
        ".ethos/profile.toml",
        roots.rules,
        *declaration.normative_sources,
        roots.claims,
        roots.openspec,
        roots.durable_evidence,
        roots.docs,
    ]
    for values in declaration.evidence.model_dump().values():
        candidates.extend(values)
    return tuple(dict.fromkeys(item for item in candidates if item))
