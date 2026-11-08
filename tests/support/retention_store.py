"""Build fixture Git-common stores for the record retirement preview."""

from __future__ import annotations

import hashlib
import io
import json
import os
import time
from typing import TYPE_CHECKING
from zipfile import ZipFile

from ethos.contracts.semantic import canonical_json_bytes

if TYPE_CHECKING:
    from pathlib import Path

DAY = 86_400


def put(store: Path, directory: str, payload: bytes, suffix: str, *, age_days: float) -> Path:
    """Write one content-addressed record under the store and age its mtime."""
    path = store / directory / f"{hashlib.sha256(payload).hexdigest()}{suffix}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    stamp = time.time() - age_days * DAY
    os.utime(path, (stamp, stamp))
    return path


def proof_check(head: str = "a" * 40) -> bytes:
    """Return a proof-check document of the proof artifact writer's schema."""
    return canonical_json_bytes({"schema_version": 1, "head": head, "checks": []})


def merge_preimage(mention: str = "") -> bytes:
    """Return a merge preimage of the merge recovery writer's schema."""
    document = {"observation": {"note": mention}, "files": {}, "stage_blobs": {}, "metadata": {}}
    return canonical_json_bytes(document)


def archive(members: dict[str, bytes]) -> bytes:
    """Return a zip archive holding the named members."""
    payload = io.BytesIO()
    with ZipFile(payload, "w") as zipped:
        for name, content in members.items():
            zipped.writestr(name, content)
    return payload.getvalue()


def native_attempt(note: bytes = b"") -> bytes:
    """Return a native gate attempt archive of its writer's member layout."""
    return archive({"execution.json": b"{}", "stdout.txt": note, "stderr.txt": b""})


def javascript_attempt() -> bytes:
    """Return a JavaScript gate attempt archive of its writer's member layout."""
    return archive({"observation.json": b"{}"})


def lane_unit(
    store: Path, branch: str, *, age_days: float, request: bool = True, receipt: bool = True
) -> tuple[dict[str, Path], str]:
    """Write one lane retirement request and its terminal receipt; return the paths and digest."""
    body = {"kind": "lane-retirement-operation", "schema_version": 1, "branch": branch}
    payload = canonical_json_bytes(body)
    paths: dict[str, Path] = {}
    if request:
        paths["request"] = put(
            store, "requests/lane-retirement", payload, ".json", age_days=age_days
        )
    if receipt:
        terminal = {
            "kind": "lane-retirement-receipt",
            "schema_version": 1,
            "request": json.loads(payload),
            "progress": {},
        }
        paths["receipt"] = put(
            store,
            "receipts/lane-retirement",
            canonical_json_bytes(terminal),
            ".json",
            age_days=age_days,
        )
    return paths, hashlib.sha256(payload).hexdigest()


def manifest(store: Path, *, age_days: float) -> Path:
    """Write one reviewed manifest that no request binds."""
    body = {"kind": "lane-retirement-manifest", "schema_version": 1, "entries": {}}
    return put(
        store,
        "requests/lane-retirement-manifest",
        canonical_json_bytes(body),
        ".json",
        age_days=age_days,
    )
