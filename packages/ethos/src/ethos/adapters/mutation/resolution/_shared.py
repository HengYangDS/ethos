"""Private shared helpers for lane-resolution adapters."""

from __future__ import annotations

import hashlib
import subprocess
import uuid
from pathlib import Path

from ethos_core.contracts.branch.roles import load_branch_role_policy

LEGACY_ARTIFACT_ROOT = Path("build/artifacts/lane-resolution")
RECORDS_ARTIFACT_ROOT = Path("recovery/lane-resolution")


def accepted_control_root(root: Path) -> Path:
    """Return the registered checkout for the configured accepted branch."""
    primary_root = _primary_control_root(root)
    accepted_ref = f"refs/heads/{load_branch_role_policy(primary_root).accepted_branch}"
    accepted_head = _git_output(primary_root, "rev-parse", "--verify", accepted_ref)
    if not accepted_head:
        raise ValueError("lane_resolution_accepted_control_root_unavailable")  # noqa: EM101, RUF100
    for current in _registered_worktrees(primary_root):
        if current.get("branch") != accepted_ref:
            continue
        candidate = Path(current.get("worktree", "")).resolve()
        if candidate.is_dir() and _git_output(candidate, "rev-parse", "HEAD") == accepted_head:
            return candidate
    raise ValueError("lane_resolution_accepted_control_root_unavailable")  # noqa: EM101, RUF100


def _primary_control_root(root: Path) -> Path:
    common_raw = _git_output(root, "rev-parse", "--git-common-dir")
    if not common_raw:
        raise ValueError("lane_resolution_accepted_control_root_unavailable")  # noqa: EM101, RUF100
    common = Path(common_raw)
    if not common.is_absolute():
        common = root / common
    primary = common.resolve().parent
    if not primary.is_dir():
        raise ValueError("lane_resolution_accepted_control_root_unavailable")  # noqa: EM101, RUF100
    return primary


def _registered_worktrees(root: Path) -> list[dict[str, str]]:
    completed = subprocess.run(
        ["git", "worktree", "list", "--porcelain"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode:
        raise ValueError("lane_resolution_accepted_control_root_unavailable")  # noqa: EM101, RUF100
    records: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in [*completed.stdout.splitlines(), ""]:
        if line:
            key, _, value = line.partition(" ")
            current[key] = value
            continue
        if current:
            records.append(current)
        current = {}
    return records


def _git_output(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=root, check=False, capture_output=True, text=True
    )
    return completed.stdout.strip() if completed.returncode == 0 else ""


def records_artifact_root(root: Path) -> Path:
    """Return the stable sibling owner for new lane-resolution records."""
    control_root = accepted_control_root(root)
    return control_root.parent / f"{control_root.name}-records" / RECORDS_ARTIFACT_ROOT


def artifact_roots(root: Path) -> tuple[Path, ...]:
    """Return canonical then legacy read roots without duplicate paths."""
    control_root = accepted_control_root(root)
    registered = tuple(
        Path(record["worktree"]).absolute() / LEGACY_ARTIFACT_ROOT
        for record in _registered_worktrees(root)
        if record.get("worktree") and Path(record["worktree"]).is_dir()
    )
    candidates = (
        control_root.parent / f"{control_root.name}-records" / RECORDS_ARTIFACT_ROOT,
        control_root / LEGACY_ARTIFACT_ROOT,
        *registered,
        root / LEGACY_ARTIFACT_ROOT,
    )
    return tuple(dict.fromkeys(path.absolute() for path in candidates))


def canonical_record_path(root: Path, path: Path) -> bool:
    """Return whether a new record path belongs to the stable records owner."""
    try:
        return record_destination_safe(records_artifact_root(root), path)
    except ValueError:
        return False


def record_destination_safe(record_root: Path, destination: Path) -> bool:
    """Return whether a record path stays under non-symlinked owner components."""
    lexical_root = record_root.absolute()
    lexical_destination = destination.absolute()
    if not lexical_destination.is_relative_to(lexical_root):
        return False
    try:
        if lexical_root.resolve() != lexical_root:
            return False
    except OSError:
        return False
    current = lexical_root
    for part in lexical_destination.relative_to(lexical_root).parts:
        current /= part
        if current.is_symlink():
            return False
    return True


def valid_decision_id(value: str) -> bool:
    """Return whether the identifier is exactly lane-decision:<canonical UUID>."""
    prefix = "lane-decision:"
    if not value.startswith(prefix):
        return False
    try:
        parsed = uuid.UUID(value.removeprefix(prefix))
    except ValueError:
        return False
    return value == f"{prefix}{parsed}"


def canonical_package_path(artifact_root: Path, decision_id: str) -> Path | None:
    """Resolve a package destination without allowing traversal or symlink escape."""
    if not valid_decision_id(decision_id):
        return None
    candidate = artifact_root / decision_id
    return candidate if record_destination_safe(artifact_root, candidate) else None


def display_path(root: Path, path: Path) -> str:
    """Keep legacy paths relative while representing sibling records absolutely."""
    candidate = path.resolve()
    try:
        return candidate.relative_to(root.resolve()).as_posix()
    except ValueError:
        return candidate.as_posix()


def sha256_digest(path: Path) -> str:
    """Return the hex sha256 digest of a file's bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()
