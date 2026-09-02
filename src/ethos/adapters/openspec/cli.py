"""Repository-locked official OpenSpec command and JSON contracts."""

from __future__ import annotations

import json
import os
import subprocess
from contextlib import suppress
from importlib import resources
from pathlib import Path
from typing import Any

import yaml

from ethos.adapters.process import run_command
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.runtime.materialization.input_resolution import resolve_node_executable
from ethos.adapters.repo.runtime.materialization.node_package_supply import (
    resolve_node_package_supply,
)

OFFICIAL_PACKAGE = "@fission-ai/openspec"
OPENSPEC_COMMAND_TIMEOUT_SECONDS = 60
_SOURCE_COMMAND_LENGTH = 2

_SOURCE_ROOT = Path(__file__).resolve().parents[4]
_SOURCE_DECLARATION = _SOURCE_ROOT / "package.json"
_DISTRIBUTION_DECLARATION = Path(
    str(resources.files("ethos").joinpath("data", "supply-chain", "package.json"))
)
_DISTRIBUTION_LOCK = Path(
    str(resources.files("ethos").joinpath("data", "supply-chain", "package-lock.json"))
)
_DISTRIBUTION_MODULES = Path(
    str(resources.files("ethos").joinpath("data", "openspec-runtime", "node_modules"))
)
_DISTRIBUTION_PACKAGE = _DISTRIBUTION_MODULES / "@fission-ai" / "openspec" / "package.json"
_DISTRIBUTION_ENTRY = _DISTRIBUTION_PACKAGE.parent / "bin" / "openspec.js"
_LOCK = _SOURCE_ROOT / "package-lock.json"


def _json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _declared_version(path: Path) -> str:
    declaration = _json_object(path)
    dependencies = declaration.get("dependencies", {})
    return str(dependencies.get(OFFICIAL_PACKAGE) or "") if isinstance(dependencies, dict) else ""


OFFICIAL_VERSION = _declared_version(
    _SOURCE_DECLARATION if _SOURCE_DECLARATION.is_file() else _DISTRIBUTION_DECLARATION
)
OFFICIAL_PACKAGE_SPEC = f"{OFFICIAL_PACKAGE}@{OFFICIAL_VERSION}"


def _packaged_node() -> str | None:
    """Resolve the platform Node payload installed with the Python distribution."""
    try:
        executable = resolve_node_executable()
    except ValueError:
        return None
    return executable.as_posix()


_SOURCE_NODE = _packaged_node()


def openspec_base_command() -> tuple[str, ...] | None:
    """Return only the source-locked or package-bundled OpenSpec command."""
    source_runtime = _source_runtime()
    source_entry = source_runtime[1] if source_runtime is not None else None
    source = (
        (_SOURCE_NODE, source_entry.as_posix())
        if _SOURCE_NODE and source_entry is not None and source_entry.is_file()
        else None
    )
    if source and _verify_official_cli(source, source_runtime=source_runtime)["verdict"] == "pass":
        return source
    node = _packaged_node()
    bundled = (node, _DISTRIBUTION_ENTRY.as_posix()) if node else None
    if bundled is not None and not _DISTRIBUTION_ENTRY.is_file():
        bundled = None
    return bundled if bundled and verify_official_cli(bundled)["verdict"] == "pass" else None


def verify_official_cli(command: tuple[str, ...]) -> dict[str, object]:
    """Verify package, lock, executable, and reported version as one identity."""
    return _verify_official_cli(command, source_runtime=_source_runtime())


def _verify_official_cli(
    command: tuple[str, ...],
    *,
    source_runtime: tuple[Path, Path] | None,
) -> dict[str, object]:
    gaps: list[str] = []
    entry = Path(command[1]).resolve() if len(command) == _SOURCE_COMMAND_LENGTH else Path()
    source_package, source_path = source_runtime or (Path(), Path())
    source_entry = source_runtime is not None and entry == source_path.resolve()
    bundled_entry = entry == _DISTRIBUTION_ENTRY
    if source_entry:
        package = _json_object(source_package)
        lock = _json_object(_LOCK)
        packages = lock.get("packages")
        packages = packages if isinstance(packages, dict) else {}
        root = packages.get("", {})
        locked = packages.get("node_modules/@fission-ai/openspec", {})
        checks = (
            (package.get("name") == OFFICIAL_PACKAGE, "openspec_package_identity_mismatch"),
            (package.get("version") == OFFICIAL_VERSION, "openspec_package_version_mismatch"),
            (
                isinstance(root, dict)
                and root.get("dependencies", {}).get(OFFICIAL_PACKAGE) == OFFICIAL_VERSION,
                "openspec_root_pin_mismatch",
            ),
            (
                isinstance(locked, dict) and locked.get("version") == OFFICIAL_VERSION,
                "openspec_lock_version_mismatch",
            ),
        )
    elif bundled_entry:
        declaration = _json_object(_DISTRIBUTION_DECLARATION)
        package = _json_object(_DISTRIBUTION_PACKAGE)
        lock = _json_object(_DISTRIBUTION_LOCK)
        packages = lock.get("packages")
        packages = packages if isinstance(packages, dict) else {}
        root = packages.get("", {})
        locked = packages.get("node_modules/@fission-ai/openspec", {})
        checks = (
            (len(command) == _SOURCE_COMMAND_LENGTH, "openspec_entry_mismatch"),
            (package.get("name") == OFFICIAL_PACKAGE, "openspec_package_identity_mismatch"),
            (package.get("version") == OFFICIAL_VERSION, "openspec_package_version_mismatch"),
            (
                declaration.get("dependencies", {}).get(OFFICIAL_PACKAGE) == OFFICIAL_VERSION,
                "openspec_distribution_pin_mismatch",
            ),
            (
                isinstance(root, dict)
                and root.get("dependencies", {}).get(OFFICIAL_PACKAGE) == OFFICIAL_VERSION,
                "openspec_root_pin_mismatch",
            ),
            (
                isinstance(locked, dict) and locked.get("version") == OFFICIAL_VERSION,
                "openspec_lock_version_mismatch",
            ),
        )
    else:
        checks = ((False, "openspec_entry_mismatch"),)
    gaps.extend(gap for valid, gap in checks if not valid)
    version = ""
    if not gaps:
        completed = run_command(
            _SOURCE_ROOT if source_entry else _DISTRIBUTION_MODULES.parent,
            (*command, "--version"),
            text=True,
            check=False,
            timeout=OPENSPEC_COMMAND_TIMEOUT_SECONDS,
            remove_env_prefixes=("GIT_",),
        )
        version = completed.stdout.strip()
        if completed.returncode or version != OFFICIAL_VERSION:
            gaps.append("openspec_effective_version_mismatch")
    return {
        "verdict": "block" if gaps else "pass",
        "package": OFFICIAL_PACKAGE_SPEC,
        "version": version,
        "base_command": list(command),
        "required_gaps": gaps,
    }


def _source_runtime() -> tuple[Path, Path] | None:
    if not _SOURCE_DECLARATION.is_file():
        return None
    try:
        supply = resolve_node_package_supply(_SOURCE_ROOT)
    except ValueError:
        return None
    package = supply / "@fission-ai" / "openspec" / "package.json"
    return package, package.parent / "bin" / "openspec.js"


def status_contract_gaps(payload: dict[str, Any]) -> list[str]:
    """Validate the official artifact dependency graph projection."""
    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        return ["openspec_status_artifact_graph_missing"]
    valid = all(
        isinstance(item, dict)
        and isinstance(item.get("id"), str)
        and isinstance(item.get("status"), str)
        and isinstance(item.get("requires"), list)
        for item in artifacts
    )
    return [] if valid else ["openspec_status_artifact_graph_invalid"]


def instructions_contract_gaps(operation: str, payload: dict[str, Any]) -> list[str]:
    """Validate official apply/archive instruction projections."""
    common = isinstance(payload.get("changeName"), str) and isinstance(payload.get("root"), dict)
    if operation == "archive":
        return [] if common else ["openspec_archive_instructions_invalid"]
    apply = (
        common
        and payload.get("state") in {"blocked", "ready", "all_done"}
        and isinstance(payload.get("progress"), dict)
        and isinstance(payload.get("tasks"), list)
        and isinstance(payload.get("instruction"), str)
    )
    return [] if apply else ["openspec_apply_instructions_invalid"]


def config_contract_gaps(payload: dict[str, Any]) -> list[str]:
    """Reject machine-global root selection that can escape the repository."""
    return ["openspec_default_store_forbidden"] if payload.get("defaultStore") else []


def run_json(
    root: Path,
    base_command: tuple[str, ...],
    args: tuple[str, ...],
) -> dict[str, Any]:
    command = (*base_command, *args)
    try:
        completed = run_command(
            root,
            command,
            text=True,
            check=False,
            timeout=OPENSPEC_COMMAND_TIMEOUT_SECONDS,
            env={
                "PATH": os.environ.get("PATH", os.defpath),
                "PWD": str(root),
                "OLDPWD": str(root),
                "TZ": "UTC",
                "OPENSPEC_TELEMETRY": "0",
                "OPENSPEC_NO_UPDATE_CHECK": "1",
            },
            remove_env_prefixes=("GIT_",),
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        return {
            "command": list(command),
            "exit_code": 124,
            "stdout": stdout,
            "stderr": stderr or "openspec command timed out after 60 seconds",
            "json": {},
            "parse_error": "openspec_command_timeout",
        }
    payload: dict[str, Any] = {}
    parse_error = ""
    if completed.stdout.strip():
        try:
            parsed = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            parse_error = str(exc)
        else:
            if isinstance(parsed, dict):
                payload = parsed
            else:
                parse_error = "openspec_json_not_object"
    return {
        "command": list(command),
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "json": payload,
        "parse_error": parse_error,
    }


def archive_command(
    root: Path,
    change: str,
    *,
    tree_ref: str = "",
    archive_path: str = "",
) -> tuple[str, ...]:
    """Return the stable official archive command declared by one Change."""
    metadata = (
        git_stdout(root, "show", f"{tree_ref}:{archive_path}/.openspec.yaml")
        if tree_ref and archive_path
        else (root / "openspec" / "changes" / change / ".openspec.yaml").read_text(
            encoding="utf-8", errors="replace"
        )
        if (root / "openspec" / "changes" / change / ".openspec.yaml").is_file()
        else ""
    )
    try:
        declaration = yaml.safe_load(metadata) if metadata else None
    except yaml.YAMLError:
        declaration = None
    skip_specs = isinstance(declaration, dict) and declaration.get("skip_specs") is True
    return (
        "openspec",
        "archive",
        change,
        "--yes",
        *(("--skip-specs",) if skip_specs else ()),
        "--json",
    )


def archive_result(
    root: Path,
    change: str,
    result: dict[str, Any],
) -> tuple[list[str], str]:
    """Validate one official archive result and return its repository path."""
    payload = result.get("json")
    archive = payload.get("archive") if isinstance(payload, dict) else None
    archive_path = ""
    if isinstance(archive, dict):
        with suppress(ValueError, OSError):
            archive_path = (
                Path(str(archive.get("path") or "")).resolve().relative_to(root).as_posix()
            )
    valid = (
        result.get("exit_code") == 0
        and not result.get("parse_error")
        and isinstance(archive, dict)
        and archive.get("change") == change
        and archive_path.startswith("openspec/changes/archive/")
        and archive_path.endswith(f"-{change}")
    )
    return ([] if valid else ["openspec_archive_result_invalid"], archive_path)
