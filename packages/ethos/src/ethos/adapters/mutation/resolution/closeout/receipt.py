"""Receipt-sidecar ownership for complete lane-resolution attempts."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.mutation.resolution._shared import transition_gap
from ethos.adapters.mutation.resolution.records.core import claim_resolution_receipt_reservation

if TYPE_CHECKING:
    from contextlib import ExitStack
    from pathlib import Path
    from typing import Literal


def claim_receipt_reservation(
    stack: ExitStack,
    control_root: Path,
    artifact_root: Path,
    decision_id: str,
    *,
    mode: Literal["create", "recover", "recover_completed"],
) -> tuple[bool, int | None, str]:
    """Enter one sidecar claim and map storage failures to stable gaps."""
    try:
        descriptor = stack.enter_context(
            claim_resolution_receipt_reservation(
                root=control_root,
                decision_id=decision_id,
                artifact_root=artifact_root,
                mode=mode,
            )
        )
    except (OSError, ValueError) as error:
        if isinstance(error, ValueError):
            return False, None, transition_gap(error, "lane_resolution_receipt_invalid")
        gap = (
            "lane_resolution_receipt_path_exists"
            if isinstance(error, FileExistsError)
            else "lane_resolution_receipt_path_unsafe"
        )
        return False, None, gap
    return True, descriptor, ""
