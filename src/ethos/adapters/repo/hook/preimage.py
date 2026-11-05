"""Decide what ETHOS owns, and keep the records of a faithful exit.

A repository may have used its own hooks before ETHOS adopted it. Activation replaces the common
`core.hooksPath` and ref-storage configuration and clears worktree overrides. A key is ETHOS's
while it holds ETHOS's activation value; in worktree scope, also while it is absent; and
`core.hooksPath` while it names a current or legacy ETHOS hooks directory. Install records, per
key, only a value that ETHOS does not own and replaces, so an exit restores exactly the user's
configuration. An upgrade, which replaces only ETHOS's values, leaves the record unchanged.

An exit writes a durable receipt before its first effect and marks it applied after its last one,
so a re-run resumes it, and status reports it as a fact or as incomplete.
"""

from __future__ import annotations

import json
from contextlib import suppress
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

from ethos.adapters.store.durable import replace_durably

PREIMAGE_NAME = "hooks-preimage.json"
EXIT_RECEIPT_NAME = "exit-receipt.json"
REF_STORAGE_CONFIG = {"gc.packRefs": "false", "maintenance.pack-refs.enabled": "false"}
WORKTREE_ACTIVATION_KEYS = ("core.hooksPath", *REF_STORAGE_CONFIG)
ACTIVATION_KEYS = ("extensions.worktreeConfig", *WORKTREE_ACTIVATION_KEYS)
_ACTIVATION_VALUES = {
    "extensions.worktreeConfig": ("true",),
    **{key: (value,) for key, value in REF_STORAGE_CONFIG.items()},
}
_SCHEMA_VERSION = 1
_DIGITS = frozenset("0123456789abcdef")
Entries = dict[str, list[str]]


def hooks_preimage_path(common: Path) -> Path:
    """Where a repository family keeps the configuration its adoption replaced."""
    return common / "ethos" / PREIMAGE_NAME


def exit_receipt_path(common: Path) -> Path:
    """Where a repository family keeps the receipt of its latest exit."""
    return common / "ethos" / EXIT_RECEIPT_NAME


def write_json_atomically(target: Path, payload: object) -> None:
    """Replace one record with complete, synced JSON, never leaving a partial file behind."""
    replace_durably(target, (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode())


def file_bytes(path: Path) -> bytes | None:
    """The exact bytes of one record, or None while it is absent."""
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None


def restore_file(path: Path, content: bytes | None) -> None:
    """Return one record to exact prior bytes, or to its absence."""
    if content is None:
        path.unlink(missing_ok=True)
    elif file_bytes(path) != content:
        replace_durably(path, content)


def _legacy_hooks_path(common: Path, path: Path) -> bool:
    """A launcher directory of the layouts that 1e3883d67 retired on 2026-08-24."""
    digest = path.name.removeprefix("ethos-hooks-")
    named = path.name == "ethos-hooks" or (
        path.name.startswith("ethos-hooks-") and len(digest) == 64 and not set(digest) - _DIGITS
    )
    return named and (path.parent == common or path.parent.parent == common / "worktrees")


def ethos_owns_hooks_path(common: Path, values: tuple[str, ...]) -> bool:
    """Whether a hooks path names one of ETHOS's current or legacy launcher directories.

    ETHOS always wrote absolute paths, so a relative value is the repository's own.
    """
    root = common.resolve()
    owned = root / "ethos" / "hooks"
    for value in values:
        if not Path(value).is_absolute():
            continue
        path = Path(value).resolve()
        if path == owned or owned in path.parents or _legacy_hooks_path(root, path):
            return True
    return False


def ethos_owns_value(common: Path, key: str, values: tuple[str, ...], *, worktree: bool) -> bool:
    """Whether one key's current values are ETHOS's activation, so an exit may replace them."""
    if worktree and not values:
        return True
    if key == "core.hooksPath":
        return len(values) == 1 and ethos_owns_hooks_path(common, values)
    return values == _ACTIVATION_VALUES.get(key)


def _merged(
    common: Path, previous: Entries, before: dict[str, tuple[str, ...]], *, worktree: bool
) -> Entries:
    """Record what activation replaces now; keep the entry of a key ETHOS already owned."""
    entries: Entries = {}
    for key, values in sorted(before.items()):
        if not ethos_owns_value(common, key, values, worktree=worktree):
            entries[key] = list(values)
        elif key in previous:
            entries[key] = previous[key]
    return entries


def record_hooks_preimage(
    common: Path,
    common_before: dict[str, tuple[str, ...]],
    worktrees_before: dict[Path, dict[str, tuple[str, ...]]],
) -> bool:
    """Merge what this activation replaces into the record; report whether it changed."""
    previous = read_hooks_preimage(common) or {"common": {}, "worktrees": {}}
    worktrees = dict(previous["worktrees"])
    for worktree, values in worktrees_before.items():
        path = worktree.as_posix()
        merged = _merged(common, worktrees.get(path, {}), values, worktree=True)
        if merged:
            worktrees[path] = merged
        else:
            worktrees.pop(path, None)
    record = {
        "common": _merged(common, previous["common"], common_before, worktree=False),
        "worktrees": dict(sorted(worktrees.items())),
    }
    if record == previous:
        return False
    stamp = {"schema_version": _SCHEMA_VERSION, "recorded_at": datetime.now(UTC).isoformat()}
    write_json_atomically(hooks_preimage_path(common), stamp | record)
    return True


def _read(path: Path) -> dict[str, Any] | None:
    with suppress(OSError, ValueError):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and payload.get("schema_version") == _SCHEMA_VERSION:
            return payload
    return None


def read_hooks_preimage(common: Path) -> dict[str, Any] | None:
    """Read the recorded configuration, or None where adoption recorded nothing readable."""
    payload = _read(hooks_preimage_path(common))
    if (
        payload is not None
        and isinstance(payload.get("common"), dict)
        and isinstance(payload.get("worktrees"), dict)
    ):
        return {"common": payload["common"], "worktrees": payload["worktrees"]}
    return None


def read_exit_receipt(common: Path) -> dict[str, Any] | None:
    """Read the latest exit's receipt, or None where no readable receipt exists."""
    return _read(exit_receipt_path(common))


def exit_fact(common: Path) -> dict[str, str] | None:
    """Report an interrupted exit while its receipt remains, and an applied one until adoption."""
    receipt = read_exit_receipt(common)
    if receipt is None:
        return None
    applied = receipt.get("state") == "applied"
    if applied and (common / "ethos" / "runtime" / "CURRENT").exists():
        return None
    return {
        "state": "exited" if applied else "incomplete",
        "receipt": exit_receipt_path(common).as_posix(),
        "plan_digest": str(receipt.get("plan_digest", "")),
        "written_at": str(receipt.get("written_at", "")),
    }
