from __future__ import annotations

import shutil
import subprocess
from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:
    from pathlib import Path


def _git(root: Path, *args: str, input_bytes: bytes | None = None) -> bytes:
    result = subprocess.run(
        ["git", *args], cwd=root, input=input_bytes, capture_output=True, check=False
    )
    if result.returncode == 0:
        return result.stdout
    detail = result.stderr.decode(errors="replace").strip()
    message = f"Local emulator source materialization failed: git {' '.join(args)}: {detail}"
    raise RuntimeError(message)


def _remove_path(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    elif path.exists() or path.is_symlink():
        path.unlink()


def materialize_emulator_source(
    *, source_root: Path, state_dir: Path, expected_head: str, expected_branch: str
) -> dict[str, Any]:
    """Create a standalone Git snapshot so Docker never sees a linked `.git` file."""
    state_dir.mkdir(parents=True, exist_ok=True)
    source_dir = state_dir / "source"
    staging_dir = state_dir / "source.staging"
    bundle_path = state_dir / "source.bundle"
    _remove_path(staging_dir)
    _remove_path(bundle_path)
    tracked_diff = b""
    source_head = _git(source_root, "rev-parse", "HEAD").decode().strip()
    source_branch = _git(source_root, "rev-parse", "--abbrev-ref", "HEAD").decode().strip()
    if source_head != expected_head:
        message = (
            "Local emulator source materialization failed: "
            f"expected HEAD {expected_head}, observed {source_head}"
        )
        raise RuntimeError(message)
    if source_branch != expected_branch or source_branch == "HEAD":
        message = (
            "Local emulator source materialization failed: "
            f"expected branch {expected_branch}, observed {source_branch or '<missing>'}"
        )
        raise RuntimeError(message)
    try:
        _git(source_root, "bundle", "create", str(bundle_path), "HEAD")
        _git(state_dir, "init", "--quiet", str(staging_dir))
        _git(staging_dir, "fetch", "--quiet", "--no-tags", str(bundle_path), "HEAD")
        _git(staging_dir, "checkout", "--quiet", "-b", expected_branch, "FETCH_HEAD")
        tracked_diff = _git(source_root, "diff", "--binary", expected_head)
        if tracked_diff:
            _git(
                staging_dir,
                "apply",
                "--index",
                "--binary",
                "--whitespace=error-all",
                "-",
                input_bytes=tracked_diff,
            )
        _remove_path(source_dir)
        staging_dir.replace(source_dir)
    except Exception:
        _remove_path(staging_dir)
        raise
    finally:
        _remove_path(bundle_path)

    source_head = _git(source_dir, "rev-parse", "HEAD").decode().strip()
    source_branch = _git(source_dir, "rev-parse", "--abbrev-ref", "HEAD").decode().strip()
    return {
        "kind": "independent_git_checkout",
        "source_dir": str(source_dir),
        "source_head": source_head,
        "source_head_matches_expected": source_head == expected_head,
        "source_branch": source_branch,
        "source_branch_matches_expected": source_branch == expected_branch,
        "git_directory_is_real": (source_dir / ".git").is_dir(),
        "uses_external_object_alternates": (source_dir / ".git/objects/info/alternates").is_file(),
        "tracked_diff_bytes": len(tracked_diff),
    }
