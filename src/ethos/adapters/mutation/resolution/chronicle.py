"""Chronicle bindings for exceptional lane-resolution effects."""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

import ethos.adapters.mutation.resolution.records.io.posix as record_posix
from ethos.adapters.mutation.resolution.observation import OwnerlessGitObservationError
from ethos.adapters.mutation.resolution.observation import git_object_bytes
from ethos.adapters.mutation.resolution.observation import read_root_bound_regular_file

if TYPE_CHECKING:
    from collections.abc import Mapping

_MAX_CHRONICLE_BYTES = 1024 * 1024
_MIN_CHRONICLE_REF_PARTS = 3
_TARGET_HEAD_PATTERN = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?")


def read_accepted_preserve_retire_chronicle(
    root: Path,
    *,
    chronicle_ref: str,
    target_branch: str,
    target_head: str,
) -> tuple[bytes | None, str]:
    """Return one exact accepted Chronicle bound to one preserve-retire target."""
    relative, gap = _preserve_retire_chronicle_reference(chronicle_ref)
    if gap:
        return None, gap
    try:
        working = read_root_bound_regular_file(root, relative, maximum_bytes=_MAX_CHRONICLE_BYTES)
    except OwnerlessGitObservationError as error:
        return (
            None,
            "lane_resolution_chronicle_missing"
            if error.detail == "file_missing"
            else "lane_resolution_chronicle_invalid",
        )
    accepted = _accepted_chronicle_bytes(root, relative)
    if accepted is None or accepted != working.raw:
        return None, "lane_resolution_chronicle_invalid"
    try:
        text = working.raw.decode("utf-8")
    except UnicodeDecodeError:
        return None, "lane_resolution_chronicle_invalid"
    if not _preserve_retire_chronicle_target_matches(text, target_branch, target_head):
        return None, (
            "lane_resolution_chronicle_disposition_mismatch"
            if "lane_resolution/preserve-retire" not in text
            else "lane_resolution_chronicle_invalid"
        )
    return working.raw, ""


def _accepted_chronicle_bytes(root: Path, relative: str) -> bytes | None:
    try:
        return git_object_bytes(root, f"HEAD:{relative}")
    except OwnerlessGitObservationError:
        return None


def _preserve_retire_chronicle_reference(chronicle_ref: str) -> tuple[str, str]:
    relative_path = PurePosixPath(chronicle_ref)
    if (
        not chronicle_ref.strip()
        or relative_path.is_absolute()
        or ".." in relative_path.parts
        or relative_path.as_posix() != chronicle_ref
    ):
        return "", "lane_resolution_chronicle_outside_repository"
    relative = relative_path.as_posix()
    return (
        (relative, "")
        if relative.startswith("evidence/chronicle/")
        else (relative, "lane_resolution_chronicle_missing")
    )


def _preserve_retire_chronicle_target_matches(
    text: str, target_branch: str, target_head: str
) -> bool:
    fields = _front_matter_fields(text)
    if fields is None or not _TARGET_HEAD_PATTERN.fullmatch(target_head):
        return False
    event = fields.get("event", [])
    target_heads = fields.get("target_head", [])
    branches = fields.get("target_branch", [])
    branch_digests = fields.get("target_branch_sha256", [])
    if event != ["lane_resolution/preserve-retire"] or target_heads != [target_head]:
        return False
    if (len(branches), len(branch_digests)) == (1, 0):
        return branches[0] == target_branch
    if (len(branches), len(branch_digests)) == (0, 1):
        return branch_digests[0] == hashlib.sha256(target_branch.encode("utf-8")).hexdigest()
    return False


def _front_matter_fields(text: str) -> dict[str, list[str]] | None:
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        return None
    fields: dict[str, list[str]] = {}
    for line in lines[1:]:
        if line == "---":
            return fields
        key, separator, value = line.partition(": ")
        if not separator or not key or not value:
            return None
        fields.setdefault(key, []).append(value)
    return None


def current_resolution_chronicle_matches(root: Path, decision: Mapping[str, object]) -> bool:
    """Match current Chronicle bytes using the admitted lane-resolution semantics."""
    reference = Path(str(decision.get("chronicle_ref") or ""))
    if reference.is_absolute() or ".." in reference.parts:
        return False
    candidate = (root / reference).absolute()
    try:
        relative = candidate.relative_to(root.absolute())
        if (
            relative.parts[:2] != ("evidence", "chronicle")
            or len(relative.parts) < _MIN_CHRONICLE_REF_PARTS
        ):
            return False
        parent = record_posix.open_directory_path(candidate.parent, create=False)
    except (OSError, ValueError):
        return False
    try:
        parent_identity = record_posix.directory_identity(os.fstat(parent))
        identity = record_posix.entry_file_identity(parent, candidate.name)
        content = (
            None
            if identity is None
            else record_posix.read_bound_file(
                parent,
                candidate.name,
                identity,
                max_bytes=_MAX_CHRONICLE_BYTES,
            )
        )
        if content is None or not record_posix.directory_descriptor_is_live(
            candidate.parent, parent, parent_identity
        ):
            return False
        text = content.decode()
    except (OSError, UnicodeDecodeError, ValueError):
        return False
    finally:
        os.close(parent)
    return f"lane_resolution/{decision.get('disposition')}" in text and hashlib.sha256(
        content
    ).hexdigest() == decision.get("chronicle_digest")
