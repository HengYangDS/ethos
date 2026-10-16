"""Repository paradigm contract.

The contract is repository-neutral. It names the protocol carriers that every
governed repository shares and the ecosystem modules that apply exactly when
their manifest is tracked, without encoding one repository or its product layout.
"""

import posixpath
import re
import tomllib
from functools import lru_cache
from importlib import resources
from typing import Literal
from typing import Self

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import model_validator

from ethos.contracts.value import FrozenMapping
from ethos.contracts.value import FrozenTuple

_DECLARATION = ConfigDict(frozen=True, strict=True, extra="forbid")


class RootCatalog(BaseModel):
    """Protocol entries a governed repository may track at its root."""

    model_config = _DECLARATION

    entry_documents: FrozenTuple[str]
    required_documents: FrozenTuple[str]
    protocol_files: FrozenTuple[str]
    forge_entries: FrozenTuple[str]
    governance_roots: FrozenTuple[str]

    @model_validator(mode="after")
    def require_admitted_documents(self) -> Self:
        """Keep every required document inside the admitted entry documents."""
        if not set(self.required_documents) <= set(self.entry_documents):
            message = "required paradigm documents must be admitted entry documents"
            raise ValueError(message)
        return self


class BindingFileSet(BaseModel):
    """The ETHOS-defined files a repository binding may track."""

    model_config = _DECLARATION

    root: str
    files: FrozenTuple[str]
    workspace_tables: FrozenTuple[str]


class EditorDefaults(BaseModel):
    """EditorConfig values every governed repository selects for all files."""

    model_config = _DECLARATION

    charset: str
    end_of_line: str
    insert_final_newline: str


class TextNormalization(BaseModel):
    """Declarations that select UTF-8, LF line endings and a final newline."""

    model_config = _DECLARATION

    gitattributes: str
    editorconfig: EditorDefaults


class ConfigurationPlane(BaseModel):
    """The configuration root, its owner groups, toolchain planes and direct files."""

    model_config = _DECLARATION

    root: str
    owner_groups: FrozenTuple[str]
    planes: FrozenTuple[str]
    files: FrozenTuple[str]
    policy: str


class FormatterBinding(BaseModel):
    """The formatter one carrier class uses and the settings its binding declares."""

    model_config = _DECLARATION

    tool: str
    suffixes: FrozenTuple[str]
    settings: FrozenMapping[str | int | bool]


class ReleaseConventions(BaseModel):
    """The version source, tag pattern and changelog grammar of a releasing repository."""

    model_config = _DECLARATION

    version_file: str
    tag_pattern: str
    changelog: str
    changelog_heading: str


class SizeCeilings(BaseModel):
    """Per-file ceilings that every governed repository shares."""

    model_config = _DECLARATION

    python_effective_lines: int = Field(gt=0)
    markdown_nonblank_lines: int = Field(gt=0)


class DocumentConventions(BaseModel):
    """The name grammar of a repository's numbered decision records."""

    model_config = _DECLARATION

    decision_record_name: str


class CommitGrammar(BaseModel):
    """The commit subject grammar and signature every governed repository shares."""

    model_config = _DECLARATION

    types: FrozenTuple[str]
    scope: str
    breaking_marker: str = Field(min_length=1, max_length=1)
    signature: Literal["ssh"]

    @model_validator(mode="after")
    def require_compilable_grammar(self) -> Self:
        """Reject duplicate types and a grammar that does not compile."""
        if not self.types or len(set(self.types)) != len(self.types):
            message = "commit grammar types must be unique and non-empty"
            raise ValueError(message)
        try:
            re.compile(self.subject_pattern())
        except re.error as error:
            message = f"commit grammar does not compile: {error}"
            raise ValueError(message) from error
        return self

    def subject_pattern(self, scopes: tuple[str, ...] = ()) -> str:
        """Compile the subject grammar, restricting scopes to a declared list when present."""
        scope = "|".join(re.escape(name) for name in scopes) if scopes else self.scope
        types = "|".join(self.types)
        return rf"^({types})(\(({scope})\))?{re.escape(self.breaking_marker)}?: .+"


class OpenSpecRules(BaseModel):
    """The common rules that begin each artifact's rules in every OpenSpec configuration."""

    model_config = _DECLARATION

    proposal: FrozenTuple[str] = Field(min_length=1)
    specs: FrozenTuple[str] = Field(min_length=1)
    design: FrozenTuple[str] = Field(min_length=1)
    tasks: FrozenTuple[str] = Field(min_length=1)


class OpenSpecConventions(BaseModel):
    """The artifact schema every governed repository selects and its common artifact rules."""

    model_config = _DECLARATION

    artifact_schema: Literal["spec-driven"]
    rules: OpenSpecRules


class EcosystemModule(BaseModel):
    """One ecosystem module, applied exactly when its manifest is tracked at the root."""

    model_config = _DECLARATION

    id: Literal["python", "node", "go"]
    manifest: str
    lock: str
    lock_scope: Literal["manifest", "dependencies"]
    runner_entries: FrozenTuple[str] = ()
    floor: str = ""


class ToolCarrier(BaseModel):
    """One tool's canonical carrier, the names it discovers and where it embeds policy."""

    model_config = _DECLARATION

    id: str
    carrier: str
    root_names: FrozenTuple[str] = ()
    manifest_tables: FrozenTuple[str] = ()
    package_keys: FrozenTuple[str] = ()
    nested: bool = False


class RepositoryParadigm(BaseModel):
    """Executable repository paradigm declaration."""

    model_config = _DECLARATION

    id: Literal["repository-paradigm"]
    source_refs: FrozenTuple[str]
    root: RootCatalog
    binding: BindingFileSet
    normalization: TextNormalization
    configuration: ConfigurationPlane
    immutable_roots: FrozenTuple[str]
    formatter: FrozenTuple[FormatterBinding]
    release: ReleaseConventions
    size: SizeCeilings
    documents: DocumentConventions
    commit: CommitGrammar
    openspec: OpenSpecConventions
    module: FrozenTuple[EcosystemModule]
    tool: FrozenTuple[ToolCarrier]

    @model_validator(mode="after")
    def require_unique_identities(self) -> Self:
        """Reject duplicate module or tool identities and ambiguous root names."""
        groups = (
            [module.id for module in self.module],
            [formatter.tool for formatter in self.formatter],
            [suffix for formatter in self.formatter for suffix in formatter.suffixes],
            [tool.id for tool in self.tool],
            [name for tool in self.tool for name in tool.root_names],
            [table for tool in self.tool for table in tool.manifest_tables],
            [key for tool in self.tool for key in tool.package_keys],
        )
        if any(len(set(group)) != len(group) for group in groups):
            message = "repository paradigm identities must be unique"
            raise ValueError(message)
        return self

    def canonical_carrier(self, root_name: str) -> str:
        """Return the canonical carrier of a root name that a catalogued tool discovers."""
        return next((tool.carrier for tool in self.tool if root_name in tool.root_names), "")

    def native_carrier(self, basename: str) -> str:
        """Return the canonical carrier of a tool-native file name, or an empty string."""
        if basename == self.configuration.policy:
            return ""
        return next(
            (
                tool.carrier
                for tool in self.tool
                if basename in tool.root_names or basename == posixpath.basename(tool.carrier)
            ),
            "",
        )

    def owner_directories(self) -> dict[str, tuple[frozenset[str], bool]]:
        """Map each tool owner directory to its admitted file names and nested-tree support."""
        prefixes = tuple(
            f"{self.configuration.root}/{group}/" for group in self.configuration.owner_groups
        )
        owners: dict[str, tuple[frozenset[str], bool]] = {}
        for tool in self.tool:
            directory, name = posixpath.split(tool.carrier)
            if not directory.startswith(prefixes) or directory.count("/") != 2:
                continue
            names, nested = owners.get(directory, (frozenset(), False))
            owners[directory] = (names | {name}, nested or tool.nested)
        return owners


@lru_cache(maxsize=1)
def load_repository_paradigm() -> RepositoryParadigm:
    """Load the paradigm from the same package as its interpreting code."""
    source = resources.files(__package__).joinpath("paradigm.toml")
    payload = tomllib.loads(source.read_text(encoding="utf-8"))
    return RepositoryParadigm.model_validate(payload)
