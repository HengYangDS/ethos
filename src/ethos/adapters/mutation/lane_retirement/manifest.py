"""Keep a reviewed worktree's nodes in one content-addressed manifest that its request binds.

A reviewed request and its terminal receipt carry only the manifest's digest, size and per-root
totals. Admission and removal read the nodes back by digest, and a terminal operation deletes the
manifest once no request without a terminal receipt binds it.
"""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING
from typing import cast

from ethos.adapters.store.content_addressed import write_content_addressed
from ethos.adapters.store.state.schema import local_state_root
from ethos.contracts.outcome import refuse
from ethos.contracts.retirement import RetirementOperation
from ethos.contracts.retirement import ReviewedManifest
from ethos.contracts.semantic import canonical_json_bytes
from ethos.contracts.semantic import model_digest
from ethos.contracts.value import mutable_json

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

_SNAPSHOT_KEYS = ("root", "index_path", "index")


def manifest_store(root: Path) -> Path:
    """Return the store of reviewed manifests, beside the requests that bind them."""
    return local_state_root(root) / "requests" / "lane-retirement-manifest"


def manifest_reference(entries: Mapping[str, object]) -> tuple[dict[str, object], bytes]:
    """Return the reference a request keeps for these nodes and the manifest bytes it binds."""
    manifest = ReviewedManifest.model_validate({"entries": entries})
    payload = canonical_json_bytes({**manifest.model_dump(mode="json"), "entries": entries})
    digest = hashlib.sha256(payload).hexdigest()
    return {"sha256": digest, "size_bytes": len(payload), "totals": manifest.totals()}, payload


def compacted_content(root: Path, snapshot: Mapping[str, object]) -> dict[str, object]:
    """Write a reviewed snapshot's nodes to their manifest and return the request's form."""
    reference, payload = manifest_reference(cast("Mapping[str, object]", snapshot["entries"]))
    write_content_addressed(
        manifest_store(root) / f"{reference['sha256']}.json",
        payload,
        collision="lane_retirement_manifest_collision",
    )
    return {**{key: snapshot[key] for key in _SNAPSHOT_KEYS}, "manifest": reference}


def expanded_content(root: Path, reviewed: Mapping[str, object]) -> dict[str, object]:
    """Return the full snapshot that verification reads, with the nodes of the bound manifest."""
    reference = cast("Mapping[str, object]", reviewed["manifest"])
    try:
        payload = (manifest_store(root) / f"{reference['sha256']}.json").read_bytes()
    except OSError as error:
        message = "lane_retirement_manifest_missing"
        raise ValueError(message) from error
    try:
        entries = cast("dict[str, object]", json.loads(payload)["entries"])
        # The file must be exactly the canonical bytes of the nodes the reference counts.
        if manifest_reference(entries) != (mutable_json(reference), payload):
            refuse("lane_retirement_manifest_mismatch")
    except (KeyError, TypeError, ValueError) as error:
        message = "lane_retirement_manifest_mismatch"
        raise ValueError(message) from error
    snapshot = {key: mutable_json(reviewed[key]) for key in _SNAPSHOT_KEYS}
    return {**snapshot, "entries": entries}


def release_manifest(root: Path, request: RetirementOperation) -> dict[str, object]:
    """Delete a terminal request's manifest unless an unreceipted request binds it; never raise."""
    if not request.reviewed_content:
        return {}
    digest = str(cast("Mapping[str, object]", request.reviewed_content["manifest"])["sha256"])
    path = manifest_store(root) / f"{digest}.json"
    try:
        if _bound_elsewhere(root, model_digest(request), digest):
            return {"path": path.as_posix(), "state": "kept"}
        path.unlink(missing_ok=True)
    except (OSError, ValueError) as error:
        return {"path": path.as_posix(), "state": "failed", "reason": str(error)}
    return {"path": path.as_posix(), "state": "deleted"}


def _bound_elsewhere(root: Path, request_digest: str, digest: str) -> bool:
    """Return whether another request binds the manifest and has no terminal receipt yet."""
    needle = f'"manifest":{{"sha256":"{digest}"'.encode()
    store = local_state_root(root)
    binding = {
        path.stem
        for path in (store / "requests" / "lane-retirement").glob("*.json")
        if path.stem != request_digest and needle in path.read_bytes()
    }
    if not binding:
        return False
    receipted = {
        model_digest(RetirementOperation.model_validate(json.loads(payload)["request"]))
        for path in (store / "receipts" / "lane-retirement").glob("*.json")
        if needle in (payload := path.read_bytes())
    }
    return bool(binding - receipted)
