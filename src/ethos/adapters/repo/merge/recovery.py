"""Preserve only a native merge's exact destructive preimage and result."""

from __future__ import annotations

import base64
import hashlib
from stat import S_ISLNK
from stat import S_ISREG
from typing import TYPE_CHECKING

from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.merge.observation import MERGE_METADATA
from ethos.adapters.repo.merge.observation import MergeObservation
from ethos.adapters.repo.merge.observation import git_path
from ethos.adapters.repo.merge.observation import metadata_bytes
from ethos.adapters.repo.merge.observation import observe_merge
from ethos.adapters.store.content_addressed import write_content_addressed
from ethos.adapters.store.state.schema import local_state_root
from ethos.contracts.semantic import canonical_json_bytes

if TYPE_CHECKING:
    from pathlib import Path


def _file(root: Path, relative: str) -> dict[str, object]:
    path = root / relative
    if any(
        part.is_symlink() for part in path.parents if part != root and part.is_relative_to(root)
    ):
        message = "merge_recovery_parent_unsafe"
        raise ValueError(message)
    try:
        info = path.lstat()
    except FileNotFoundError:
        return {"kind": "absent"}
    if S_ISLNK(info.st_mode):
        return {"kind": "symlink", "target": str(path.readlink())}
    if not S_ISREG(info.st_mode):
        message = "merge_recovery_content_unsafe"
        raise ValueError(message)
    content = metadata_bytes(path)
    if content is None:
        message = "merge_state_stale"
        raise ValueError(message)
    return {
        "kind": "file",
        "mode": info.st_mode & 0o777,
        "content": base64.b64encode(content).decode(),
    }


def preserve_merge(root: Path, observed: MergeObservation) -> dict[str, object]:
    """Retain affected bytes, conflict blobs and index before destructive projection."""
    changed = run_git(root, "diff", "HEAD", "--name-only", "-z", observation=True).stdout
    staged = run_git(root, "diff", "--cached", "HEAD", "--name-only", "-z", observation=True).stdout
    paths = set(filter(None, (changed + staged).split("\0"))) | set(observed.conflicts)
    files = {path: _file(root, path) for path in sorted(paths)}
    metadata = {name: metadata_bytes(git_path(root, name)) for name in (*MERGE_METADATA, "index")}
    stages = run_git(root, "ls-files", "--stage", "-z", text=False, observation=True).stdout
    objects = {}
    for record in filter(None, stages.split(b"\0")):
        metadata_entry, raw_path = record.split(b"\t", 1)
        if raw_path.decode() not in paths:
            continue
        mode, object_id, _stage = metadata_entry.split()
        if mode == b"160000":
            message = "merge_submodule_recovery_unsupported"
            raise ValueError(message)
        oid = object_id.decode("ascii")
        if oid not in objects:
            blob = run_git(root, "cat-file", "blob", oid, text=False, observation=True).stdout
            objects[oid] = base64.b64encode(blob).decode()
    if observe_merge(root) != observed:
        message = "merge_state_stale"
        raise ValueError(message)
    payload = canonical_json_bytes(
        {
            "observation": observed.projection(),
            "files": files,
            "stage_blobs": objects,
            "metadata": {
                name: base64.b64encode(raw).decode()
                for name, raw in metadata.items()
                if raw is not None
            },
        }
    )
    digest = hashlib.sha256(payload).hexdigest()
    path = write_content_addressed(
        local_state_root(root) / "artifacts" / f"{digest}.json",
        payload,
        collision="merge_recovery_identity_collision",
    )
    return {"path": str(path), "sha256": digest, "size_bytes": len(payload)}
