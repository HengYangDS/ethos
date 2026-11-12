"""Version 1 of a history rebuild's record: `rebuild.toml` in its authorizing Change.

The record declares every ref outside the allowlist with its disposition, its old value and each
peer's expected state, and its transform: keyed 64-hex digests of the shared grammar's and the
rebuild's pre-images, each with its discovered count and a witness, and clear public `retain`
prefixes. An original is named by ID only when it is signed, else by the keyed digest of its
`oid` image. The record names its key only by generation and no credential store. Every refusal
names a field or an index, never a value.
"""

from __future__ import annotations

import tomllib
from typing import Annotated
from typing import Literal

from pydantic import AwareDatetime
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import ValidationError

from ethos.contracts.outcome import refuse
from ethos.contracts.value import FrozenMapping
from ethos.contracts.value import FrozenTuple
from ethos.contracts.value import frozen_mapping
from ethos.repository.paradigm.peer_identity import CONTEXTS

_DIGEST = r"^[0-9a-f]{64}$"
Digest = Annotated[str, Field(pattern=_DIGEST)]
ObjectId = Annotated[str, Field(pattern=r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")]
# A digest stands where a value could; any other string there is free text, which no entry holds.
_FREE = frozenset({"extra_forbidden", "string_pattern_mismatch", "string_type", "model_type"})
# Each transform list and the entry kind that the occurrence model attributes its results to.
ENTRY_KINDS = frozen_mapping(
    {
        "trailers": "trailer",
        "paragraphs": "paragraph",
        "spans": "span",
        "hosts": "host",
        "paths": "path",
        "ports": "port",
        "ids": "id",
    }
)


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class Keyed(_Strict):
    """An original named by the keyed digest of its `oid` image, since it carries no signature."""

    digest: Digest


Original = ObjectId | Keyed


class Witness(_Strict):
    """The `n`-th result attributed to an entry in an object's message, or in its blob at `path`."""

    object: Original
    path: str = ""
    n: int = Field(ge=1)


class Entry(_Strict):
    """One declared item: its keyed digest, its discovered count and one result's witness."""

    digest: Digest
    count: int = Field(ge=1)
    witness: Witness


class IdEntry(_Strict):
    """One project ID: the named contexts it is replaced in, one digest per context, in order."""

    contexts: FrozenTuple[str] = ()
    digests: FrozenTuple[Digest] = ()
    count: int = Field(ge=1)
    witness: Witness


class Transform(_Strict):
    """What the rebuild removes or replaces, and the public prefixes it keeps."""

    trailers: FrozenTuple[Entry] = ()
    paragraphs: FrozenTuple[Entry] = ()
    spans: FrozenTuple[Entry] = ()
    hosts: FrozenTuple[Entry] = ()
    paths: FrozenTuple[Entry] = ()
    ports: FrozenTuple[Entry] = ()
    ids: FrozenTuple[IdEntry] = ()
    retain: FrozenTuple[str] = ()


class RefDeclaration(_Strict):
    """One local ref: its disposition, its old value and each peer's expected state."""

    disposition: Literal["rebuild", "retag", "retire", "keep"]
    old: Literal["old"] | Original
    peers: FrozenMapping[Literal["old", "absent"] | Original] = Field(min_length=1)


class KeyName(_Strict):
    generation: str = Field(pattern=r"^[0-9a-f]{16}$")


class RebuildRecord(_Strict):
    """Version 1 of the record, complete: later runtimes read it with exactly these fields."""

    version: Literal[1]
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,62}$")
    owner: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    expires: AwareDatetime
    base: Original
    key: KeyName
    refs: FrozenMapping[RefDeclaration] = Field(min_length=1)
    transform: Transform


def parse_record(text: str) -> RebuildRecord:
    """Parse version 1 of the record; a free string, an invalid field or a bad context refuses."""
    try:
        record = RebuildRecord.model_validate(tomllib.loads(text))
    except tomllib.TOMLDecodeError as error:
        refuse("rebuild_record_unreadable", cause=error)
    except ValidationError as error:
        refuse(*_validation_gaps(error), cause=error)
    gaps = [
        gap for index, entry in enumerate(record.transform.ids) for gap in _id_gaps(index, entry)
    ]
    if gaps:
        refuse(*gaps)
    return record


def _validation_gaps(error: ValidationError) -> list[str]:
    """Name each refusal by its top-level field; a string where no value belongs is free.

    Any other top-level key is the author's text, so it names only the record.
    """
    gaps = (
        "rebuild_record_free_string"
        if item["type"] in _FREE and item["loc"][:1] == ("transform",)
        else f"rebuild_record_invalid:{_field(item['loc'])}"
        for item in error.errors()
    )
    return list(dict.fromkeys(gaps))


def _field(loc: tuple[int | str, ...]) -> str:
    head = str(loc[0]) if loc else ""
    return head if head in RebuildRecord.model_fields else "record"


def _id_gaps(index: int, entry: IdEntry) -> list[str]:
    """An ID names one or more known contexts, each once, with one digest for each."""
    gaps = []
    if not entry.contexts:
        gaps.append(f"rebuild_id_context_missing:{index}")
    if any(name not in CONTEXTS or not name.startswith("id.") for name in entry.contexts):
        gaps.append(f"rebuild_id_context_unknown:{index}")
    if len(set(entry.contexts)) != len(entry.contexts):
        gaps.append(f"rebuild_id_context_repeated:{index}")
    if len(entry.digests) != len(entry.contexts):
        gaps.append(f"rebuild_record_invalid:transform.ids.{index}")
    return gaps
