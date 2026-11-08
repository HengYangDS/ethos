"""Write a record retirement plan before any deletion can read it."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from ethos.adapters.store.content_addressed import write_content_addressed
from ethos.contracts.semantic import canonical_json_bytes

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path


def write_plan(store: Path, document: Mapping[str, object]) -> dict[str, object]:
    """Persist one content-addressed plan; an unchanged store's preview writes the same plan."""
    payload = canonical_json_bytes(document)
    digest = hashlib.sha256(payload).hexdigest()
    path = write_content_addressed(
        store / "requests" / "record-retirement" / f"{digest}.json",
        payload,
        collision="record_retirement_plan_collision",
    )
    return {"path": path.as_posix(), "sha256": digest, "size_bytes": len(payload)}
