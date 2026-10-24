"""Documentation registry metadata and taxonomy vocabulary."""

from __future__ import annotations

import re
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import PurePosixPath
from types import MappingProxyType
from typing import TYPE_CHECKING
from typing import Annotated
from typing import Any
from typing import Literal
from typing import override

import yaml
from pydantic import AfterValidator
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import PlainSerializer
from pydantic import TypeAdapter
from pydantic import ValidationError
from pydantic import model_validator
from yaml.constructor import ConstructorError

from ethos.repository.openspec.identifiers import parse_archived_change_root
from ethos.repository.policy.projections import observe_projections
from ethos.repository.profile import NonEmpty
from ethos.repository.profile import RepositoryPath
from ethos.repository.profile import profile_root

if TYPE_CHECKING:
    from collections.abc import Collection
    from pathlib import Path

DEFAULT_STATE_VALUES = (
    "canonical",
    "active",
    "planned",
    "experimental",
    "superseded",
    "archived",
)
DEFAULT_ROLE_VALUES = (
    "index",
    "explanation",
    "reference",
    "decision",
    "policy",
    "evidence",
    "history",
    "template",
    "plan",
    "research",
    "findings",
    "progress",
    "how-to",
)

REQUIRED_FIELDS = ("subject", "role", "state", "relations")
DEFAULT_ALLOWED_STATES = frozenset(DEFAULT_STATE_VALUES)
DEFAULT_ALLOWED_ROLES = frozenset(DEFAULT_ROLE_VALUES)
RESERVED_STATE_VALUES = frozenset({"current", "future"})
TAXONOMY_INVALID = "docs_taxonomy_invalid"


@dataclass(frozen=True, slots=True)
class DocumentOrigins:
    """Native original observations or their exact refusal, never inferred approval."""

    entries: Mapping[str, RetainedDocument]
    required_gaps: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Detach the observation container from the producer's mutable map."""
        object.__setattr__(self, "entries", MappingProxyType(dict(self.entries)))


def docs_root(root: Path) -> Path:
    """Resolve the one adopter-declared documentation root."""
    return profile_root(root, "docs")


class _UniqueSafeLoader(yaml.SafeLoader):
    """Use native safe YAML while rejecting duplicate explicit mapping keys."""

    @override
    def construct_mapping(self, node: yaml.MappingNode, deep: bool = False) -> dict:
        keys = [
            self.construct_object(key, deep=deep)
            for key, _value in node.value
            if key.tag != "tag:yaml.org,2002:merge"
        ]
        if any(key in keys[:index] for index, key in enumerate(keys)):
            message = "duplicate mapping key"
            raise ConstructorError(None, None, message, node.start_mark)
        return super().construct_mapping(node, deep=deep)


def front_matter(path: Path) -> dict[str, Any]:
    """Read one leading YAML front matter payload; any other opening carries no metadata."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        return {}
    try:
        end = lines.index("---", 1)
        payload = yaml.load("\n".join(lines[1:end]), Loader=_UniqueSafeLoader)
    except (ValueError, yaml.YAMLError) as exc:
        message = f"docs_metadata_invalid:{path}:syntax"
        raise ValueError(message) from exc
    if not isinstance(payload, dict) or not all(isinstance(key, str) for key in payload):
        message = f"docs_metadata_invalid:{path}:mapping"
        raise ValueError(message)
    return payload


def build_docs_registry(
    root: Path,
    *,
    generated_outputs: frozenset[str] | None = None,
    retained_origins: DocumentOrigins | None = None,
    selected_documents: tuple[str, ...] | None = None,
) -> list[dict[str, Any]]:
    """Validate selected source; only an unbound source-tree reader discovers files."""
    root = root.resolve()
    outputs = generated_outputs
    if outputs is None:
        outputs = frozenset(item.output for item in observe_projections(root))
    retained = _observed_retained_origins(root, retained_origins)
    documentation = docs_root(root)
    sources = (
        documentation.rglob("*.md")
        if selected_documents is None
        else {
            root / relative
            for relative in selected_documents
            if (root / relative).suffix == ".md" and (root / relative).is_relative_to(documentation)
        }
    )
    entries = []
    for path in sorted(sources):
        relative = path.relative_to(root).as_posix()
        if relative in outputs:
            continue
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
            message = f"docs_source_unavailable:{relative}"
            raise ValueError(message)
        try:
            metadata = front_matter(path)
        except ValueError as exc:
            message = f"docs_metadata_invalid:{relative}:syntax"
            raise ValueError(message) from exc
        decision_fields = (
            ("decision_id", "decision_status") if metadata.get("role") == "decision" else ()
        )
        for field in ("subject", "role", "state", *decision_fields):
            if field in metadata and not isinstance(metadata[field], str):
                message = f"docs_metadata_invalid:{relative}:{field}"
                raise ValueError(message)
        relations = metadata.get("relations", {})
        if not isinstance(relations, dict) or any(
            not isinstance(key, str)
            or not key
            or not (
                isinstance(value, str)
                or (isinstance(value, list) and all(isinstance(item, str) for item in value))
            )
            for key, value in relations.items()
        ):
            message = f"docs_metadata_invalid:{relative}:relations"
            raise ValueError(message)
        original = retained.get(relative)
        if original is not None:
            metadata = _retained_metadata(relative, metadata, original.model_dump())
        entries.append(
            {
                "path": relative,
                **{
                    field: metadata[field]
                    for field in (*REQUIRED_FIELDS, *decision_fields)
                    if field in metadata
                },
                **({"origin": original.origin} if original is not None else {}),
            }
        )
    _retained_consumers(root, entries)
    return entries


def _observed_retained_origins(
    root: Path, observation: DocumentOrigins | None
) -> dict[str, RetainedDocument]:
    """Require exact native observations without promoting an unavailable read."""
    if observation is not None and observation.required_gaps:
        raise ValueError(observation.required_gaps[0])
    retained = retained_document_origins(root)
    if retained and (observation is None or dict(observation.entries) != retained):
        declaration = (docs_root(root) / "_meta/taxonomy.toml").relative_to(root).as_posix()
        message = f"docs_metadata_invalid:{declaration}:retained_origin_unobserved"
        raise ValueError(message)
    return retained


def intent_document_owner(
    relative: str,
) -> Literal["openspec", "openspec-history"] | None:
    """Recognize exact official Markdown carriers through the existing archive grammar."""
    parts = PurePosixPath(relative).parts
    if len(parts) == 4 and parts[:2] == ("openspec", "specs") and parts[3] == "spec.md":
        return "openspec"
    if parts[:2] != ("openspec", "changes") or len(parts) < 4:
        return None
    archived = parts[2] == "archive"
    if archived and parse_archived_change_root("/".join(parts[:4])) is None:
        return None
    tail = parts[4:] if archived else parts[3:]
    if (len(tail) == 1 and tail[0] in {"proposal.md", "design.md", "tasks.md"}) or (
        len(tail) == 3 and tail[0] == "specs" and tail[2] == "spec.md"
    ):
        return "openspec-history" if archived else "openspec"
    return None


def authored_document_paths(
    registry: list[dict[str, Any]],
    sources: Collection[str],
    generated_outputs: frozenset[str],
) -> tuple[str, ...]:
    """Derive shared current inputs; names and metadata states grant no exemption."""
    originals = {entry["path"] for entry in registry if entry.get("origin")}
    return tuple(
        sorted(
            path
            for path in set(sources) | {entry["path"] for entry in registry}
            if path.endswith(".md")
            and path not in originals
            and path not in generated_outputs
            and intent_document_owner(path) != "openspec-history"
        )
    )


def taxonomy(root: Path) -> dict[str, object]:
    """Read the optional taxonomy, failing closed when the declaration is invalid."""
    path = docs_root(root) / "_meta" / "taxonomy.toml"
    if not path.exists():
        return {}
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        relative = path.relative_to(root).as_posix()
        gap = f"{TAXONOMY_INVALID}:{relative}"
        raise ValueError(gap) from exc


def taxonomy_allowed(root: Path, section: str) -> set[str]:
    """Return the `allowed` string list under a taxonomy section."""
    payload = taxonomy(root)
    block = payload.get(section)
    if not isinstance(block, dict):
        return set()
    allowed = block.get("allowed")
    if not isinstance(allowed, list):
        return set()
    return {item for item in allowed if isinstance(item, str)}


def allowed_states(root: Path) -> set[str]:
    """Return allowed docs states from taxonomy or the kernel contract default."""
    configured = taxonomy_allowed(root, "states")
    return (configured or set(DEFAULT_ALLOWED_STATES)) - RESERVED_STATE_VALUES


def allowed_roles(root: Path) -> set[str]:
    """Return kernel roles plus taxonomy extension roles."""
    return set(DEFAULT_ALLOWED_ROLES) | taxonomy_allowed(root, "roles")


class RetainedDocument(BaseModel):
    """One exact observational member and its current retrieval consumer."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    path: RepositoryPath
    subject: NonEmpty
    role: Literal["evidence", "history"]
    state: NonEmpty
    relations: Annotated[
        Mapping[NonEmpty, NonEmpty],
        AfterValidator(lambda value: MappingProxyType(dict(value))),
        PlainSerializer(dict, return_type=dict),
    ]
    origin: NonEmpty
    review_date: NonEmpty
    exit_condition: NonEmpty

    @model_validator(mode="after")
    def require_exact_native_origin(self) -> RetainedDocument:
        """Bind an observational member to a full Git commit and current owner."""
        date.fromisoformat(self.review_date)
        revision, separator, member = self.origin.partition(":")
        if (
            not separator
            or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", revision)
            or member != self.path
            or PurePosixPath(self.path).suffix != ".md"
            or PurePosixPath(self.path).as_posix() != self.path
            or "current_owner" not in self.relations
        ):
            message = "retained document requires its exact origin and current owner"
            raise ValueError(message)
        return self


def _retained_metadata(relative: str, metadata: dict, original: dict) -> dict:
    conflicts = any(
        field in metadata and metadata[field] != original[field]
        for field in ("subject", "role", "state")
    ) or any(
        key in original["relations"] and original["relations"][key] != value
        for key, value in metadata.get("relations", {}).items()
    )
    if conflicts:
        message = f"docs_metadata_invalid:{relative}:retained_conflict"
        raise ValueError(message)
    return {
        **original,
        **metadata,
        "relations": {**original["relations"], **metadata.get("relations", {})},
    }


def retained_document_origins(root: Path) -> dict[str, RetainedDocument]:
    """Interpret exact retained metadata; native adapters own byte observation."""
    declaration = (docs_root(root) / "_meta" / "taxonomy.toml").relative_to(root).as_posix()
    invalid = f"docs_metadata_invalid:{declaration}:retained"
    try:
        origins = TypeAdapter(list[RetainedDocument]).validate_python(
            taxonomy(root).get("retained", [])
        )
    except ValidationError as error:
        raise ValueError(invalid) from error
    entries = {entry.path: entry for entry in origins}
    states = allowed_states(root)
    if len(entries) != len(origins) or any(
        entry.state not in states
        or not (root / entry.path).resolve().is_relative_to(docs_root(root).resolve())
        for entry in origins
    ):
        raise ValueError(invalid)
    return entries


def _retained_consumers(root: Path, entries: list[dict[str, Any]]) -> None:
    """Require a live independent reader, not a self-referential archive marker."""
    subjects = {entry.get("subject"): entry for entry in entries if entry.get("subject")}
    paths = {(root / entry["path"]).resolve(): entry for entry in entries}
    for entry in entries:
        if not entry.get("origin"):
            continue
        target = entry["relations"]["current_owner"]
        consumer = subjects.get(target) or paths.get(
            ((root / entry["path"]).parent / target.partition("#")[0]).resolve()
        )
        if (
            consumer is None
            or consumer["path"] == entry["path"]
            or consumer.get("state") not in {"canonical", "active"}
            or consumer.get("role") in {"history", "evidence"}
            or consumer.get("origin")
        ):
            message = f"docs_metadata_invalid:{entry['path']}:retained_consumer"
            raise ValueError(message)
