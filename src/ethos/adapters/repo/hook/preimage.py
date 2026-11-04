"""Record the hooks-related Git configuration that ETHOS's first activation replaced.

A repository may have used its own hooks before ETHOS adopted it. Activation replaces the common
`core.hooksPath` and ref-storage configuration and clears worktree overrides, so an exit can only
restore that state exactly if adoption recorded it. The record is written once, when activation
replaces a hooks path that ETHOS does not own, and an absent value is recorded as absent. An
upgrade or a re-install, which replaces only ETHOS's own path, leaves the record unchanged.
"""

from __future__ import annotations

import json
import uuid
from contextlib import suppress
from datetime import UTC
from datetime import datetime
from pathlib import Path

PREIMAGE_NAME = "hooks-preimage.json"
_SCHEMA_VERSION = 1


def hooks_preimage_path(common: Path) -> Path:
    """Where a repository family keeps the configuration its adoption replaced."""
    return common / "ethos" / PREIMAGE_NAME


def ethos_owns_hooks_path(common: Path, values: tuple[str, ...]) -> bool:
    """Whether a hooks path names one of ETHOS's own launcher generations.

    Activation always writes an absolute path, so a relative value is the repository's own.
    """
    owned = (common / "ethos" / "hooks").resolve()
    return any(
        Path(value).is_absolute()
        and (Path(value).resolve() == owned or owned in Path(value).resolve().parents)
        for value in values
    )


def record_hooks_preimage(
    common: Path,
    common_before: dict[str, tuple[str, ...]],
    worktrees_before: dict[Path, dict[str, tuple[str, ...]]],
) -> Path | None:
    """Record the replaced configuration once; return the record this call wrote, if any."""
    target = hooks_preimage_path(common)
    if target.exists() or ethos_owns_hooks_path(common, common_before.get("core.hooksPath", ())):
        return None
    payload = {
        "schema_version": _SCHEMA_VERSION,
        "recorded_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "common": {key: list(values) for key, values in sorted(common_before.items())},
        "worktrees": {
            worktree.as_posix(): {
                key: list(values) for key, values in sorted(values_by_key.items())
            }
            for worktree, values_by_key in sorted(worktrees_before.items())
        },
    }
    staged = target.with_name(f".{PREIMAGE_NAME}-{uuid.uuid4().hex}")
    try:
        staged.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        staged.replace(target)
    finally:
        staged.unlink(missing_ok=True)
    return target


def read_hooks_preimage(common: Path) -> dict[str, dict[str, list[str]]] | None:
    """Read the recorded configuration, or None where adoption recorded nothing readable."""
    with suppress(OSError, ValueError):
        payload = json.loads(hooks_preimage_path(common).read_text(encoding="utf-8"))
        if (
            isinstance(payload, dict)
            and payload.get("schema_version") == _SCHEMA_VERSION
            and isinstance(payload.get("common"), dict)
            and isinstance(payload.get("worktrees"), dict)
        ):
            return {"common": payload["common"], "worktrees": payload["worktrees"]}
    return None
