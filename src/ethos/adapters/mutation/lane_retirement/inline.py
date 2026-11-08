"""Continue a lane retirement request written before its reviewed nodes moved to a manifest."""

from __future__ import annotations

import json
from pathlib import Path

from ethos.adapters.mutation.lane_retirement.continuation import fresh_retirement_command
from ethos.adapters.mutation.lane_retirement.continuation import lane_status_command
from ethos.adapters.mutation.lane_retirement.manifest import manifest_reference
from ethos.adapters.mutation.lane_retirement.operation import observe_operation
from ethos.adapters.mutation.lane_retirement.operation import operation_store
from ethos.adapters.mutation.lane_retirement.operation import reduce_progress
from ethos.adapters.mutation.lane_retirement.operation import verified_bytes
from ethos.adapters.repo.git import GitExecutionError
from ethos.contracts.retirement import RetirementOperation


def inline_continuation(root: Path, path: str, sha256: str) -> str:
    """Return the fresh admission for a verified request that still carries its nodes inline.

    Such a request no longer validates, so its coordinates are read into a view whose manifest
    reference exists only in memory; the view is never persisted or executed. Any other request
    has no continuation here, and a carrier that drifted continues through `ethos lane status`.
    """
    try:
        payload = json.loads(verified_bytes(operation_store(root), path, sha256))
        reviewed = payload.get("reviewed_content") if isinstance(payload, dict) else None
        if not isinstance(reviewed, dict) or "entries" not in reviewed:
            return ""
        reference, _ = manifest_reference(reviewed.pop("entries"))
        view = RetirementOperation.model_validate(
            {**payload, "reviewed_content": {**reviewed, "manifest": reference}}
        )
    except (OSError, TypeError, ValueError):
        return ""
    control = Path(view.control_root)
    try:
        progress = reduce_progress(view, observe_operation(control, view))
        return fresh_retirement_command(control, view, progress)
    except (GitExecutionError, OSError, RuntimeError, ValueError):
        return lane_status_command(control)
