"""Resolve exact post-archive scope authority from local effect evidence."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.openspec.lifecycle.archive_transition import archive_generation_authority
from ethos.normalization.coercion import repository_path_matches
from ethos.normalization.coercion import string_sequence

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.semantic import Commitment
    from ethos.contracts.value import JsonObject


def archive_effect_authority(
    root: Path,
    *,
    head: str,
    repository_id: str,
    commitment: Commitment,
    lease: dict[str, object],
    changed_paths: tuple[str, ...],
) -> JsonObject:
    """Return the sole exact archive effect that authorizes current paths."""
    authority = archive_generation_authority(
        root,
        head=head,
        repository_id=repository_id,
        commitment=commitment,
        lease=lease,
    )
    if not authority:
        return {}
    authority_paths = tuple(string_sequence(authority.get("authorized_paths")))
    outside_commitment = tuple(
        path
        for path in changed_paths
        if not any(repository_path_matches(path, pattern) for pattern in commitment.scope)
    )
    return authority if set(outside_commitment).issubset(authority_paths) else {}
