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
from ethos.repository.openspec.identifiers import archived_change_root_matches
from ethos.repository.openspec.identifiers import logical_change_identifier_issue

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
    return _base_command(execution_probe=True)


def _base_command(*, execution_probe: bool) -> tuple[str, ...] | None:
    """Resolve one locked command; a read batch probes its imported program itself."""
    source_runtime = _source_runtime()
    source_entry = source_runtime[1] if source_runtime is not None else None
    source = (
        (_SOURCE_NODE, source_entry.as_posix())
        if _SOURCE_NODE and source_entry is not None and source_entry.is_file()
        else None
    )
    if (
        source
        and _verify_official_cli(
            source, source_runtime=source_runtime, execution_probe=execution_probe
        )["verdict"]
        == "pass"
    ):
        return source
    node = _packaged_node()
    bundled = (node, _DISTRIBUTION_ENTRY.as_posix()) if node else None
    if bundled is not None and not _DISTRIBUTION_ENTRY.is_file():
        bundled = None
    return (
        bundled
        if bundled
        and _verify_official_cli(
            bundled, source_runtime=source_runtime, execution_probe=execution_probe
        )["verdict"]
        == "pass"
        else None
    )


def verify_official_cli(command: tuple[str, ...]) -> dict[str, object]:
    """Verify package, lock, executable, and reported version as one identity."""
    return _verify_official_cli(command, source_runtime=_source_runtime())


def _verify_official_cli(
    command: tuple[str, ...],
    *,
    source_runtime: tuple[Path, Path] | None,
    execution_probe: bool = True,
) -> dict[str, object]:
    gaps: list[str] = []
    entry = Path(command[1]).resolve() if len(command) == _SOURCE_COMMAND_LENGTH else Path()
    source_package, source_path = source_runtime or (Path(), Path())
    source_entry = source_runtime is not None and entry == source_path.resolve()
    bundled_entry = entry == _DISTRIBUTION_ENTRY.resolve()
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
    if not gaps and execution_probe:
        completed = _run_official(
            _SOURCE_ROOT if source_entry else _DISTRIBUTION_MODULES.parent,
            (*command, "--version"),
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


def _run_official(
    root: Path,
    command: tuple[str, ...],
    *,
    stdin: str | None = None,
    timeout: float = OPENSPEC_COMMAND_TIMEOUT_SECONDS,
) -> subprocess.CompletedProcess[str]:
    """Own native invocation, environment isolation and the bounded process lifetime."""
    if not 0 < timeout <= OPENSPEC_COMMAND_TIMEOUT_SECONDS:
        message = "openspec_command_timeout_invalid"
        raise ValueError(message)
    return run_command(
        root,
        command,
        stdin=stdin,
        text=True,
        check=False,
        timeout=timeout,
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


def run_json(
    root: Path,
    base_command: tuple[str, ...],
    args: tuple[str, ...],
    *,
    timeout: float = OPENSPEC_COMMAND_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    command = (*base_command, *args)
    try:
        completed = _run_official(root, command, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        stdout, stderr = (
            stream.decode(errors="replace") if isinstance(stream, bytes) else stream or ""
            for stream in (exc.stdout, exc.stderr)
        )
        return {
            "command": list(command),
            "exit_code": 124,
            "stdout": stdout,
            "stderr": stderr or f"openspec command timed out after {timeout:g} seconds",
            "json": {},
            "parse_error": "openspec_command_timeout",
        }
    return _json_result(command, completed.returncode, completed.stdout, completed.stderr)


def _json_result(
    command: tuple[str, ...], exit_code: int, stdout: str, stderr: str, *, error: str = ""
) -> dict[str, Any]:
    """Decode native output once; incomplete transport never supplies a JSON result."""
    payload: dict[str, Any] = {}
    parse_error = error
    if stdout.strip() and not error:
        try:
            parsed = json.loads(stdout)
        except json.JSONDecodeError as exc:
            parse_error = str(exc)
        else:
            if isinstance(parsed, dict):
                payload = parsed
            else:
                parse_error = "openspec_json_not_object"
    return {
        "command": list(command),
        "exit_code": exit_code,
        "stdout": stdout,
        "stderr": stderr,
        "json": payload,
        "parse_error": parse_error,
    }


def _read_only_arguments(args: tuple[str, ...]) -> bool:
    """Admit only the native read shapes consumed by one governance observation."""
    return args in {
        ("config", "list", "--json"),
        ("doctor", "--json"),
        ("list", "--json"),
        ("validate", "--all", "--strict", "--json"),
    } or (
        args[-1:] == ("--json",)
        and (
            (len(args) == 4 and args[:2] == ("status", "--change"))
            or (
                len(args) == 5
                and args[:3]
                in {
                    ("instructions", "apply", "--change"),
                    ("instructions", "archive", "--change"),
                }
            )
            or (len(args) == 5 and args[:1] == ("show",) and args[2:4] == ("--type", "change"))
        )
        and not logical_change_identifier_issue(args[1] if args[0] == "show" else args[-2])
    )


def _batch_rows(output: str, commands: tuple[tuple[str, ...], ...]) -> list[dict[str, Any]]:
    """Bind each native output frame to exactly one ordered input."""
    rows = [json.loads(line) for line in output.splitlines()]
    if len(rows) > len(commands) or any(
        not isinstance(row, dict)
        or set(row) != {"index", "args", "exit_code", "stdout", "stderr"}
        or type(row["index"]) is not int
        or row["index"] != index
        or row["args"] != list(commands[index])
        or type(row["exit_code"]) is not int
        or not isinstance(row["stdout"], str)
        or not isinstance(row["stderr"], str)
        for index, row in enumerate(rows)
    ):
        message = "openspec_batch_invalid"
        raise ValueError(message)
    return rows


def run_json_batch(
    root: Path, base_command: tuple[str, ...] | None, commands: tuple[tuple[str, ...], ...]
) -> tuple[dict[str, Any], ...]:
    """Execute native reads once per batch; preserve exact ordered execution evidence."""
    if not commands:
        return ()
    if not all(_read_only_arguments(args) for args in commands):
        message = "openspec_batch_read_only_required"
        raise ValueError(message)
    base_command = _base_command(execution_probe=False) if base_command is None else base_command
    if base_command is None or len(base_command) != _SOURCE_COMMAND_LENGTH:
        message = (
            "openspec_official_cli_missing"
            if base_command is None
            else "openspec_batch_entry_invalid"
        )
        raise ValueError(message)
    transport = (
        base_command[0],
        str(Path(__file__).with_name("batch.mjs")),
        base_command[1],
        str(OPENSPEC_COMMAND_TIMEOUT_SECONDS),
        OFFICIAL_VERSION,
    )
    gap = ""
    try:
        completed = _run_official(root, transport, stdin=json.dumps(commands))
        output, stderr, code = completed.stdout, completed.stderr, completed.returncode
    except subprocess.TimeoutExpired as error:
        output, stderr = (
            value.decode(errors="replace") if isinstance(value, bytes) else value or ""
            for value in (error.stdout, error.stderr)
        )
        code, gap = 124, "openspec_command_timeout"
    if stderr.strip() == "openspec_effective_version_mismatch":
        raise ValueError(stderr.strip())
    try:
        rows = _batch_rows(output, commands)
    except (ValueError, TypeError):
        rows, gap = [], gap or "openspec_batch_invalid"
    if (
        (code == 0 and len(rows) != len(commands))
        or (code and len(rows) == len(commands) and rows[-1]["exit_code"] != code)
        or stderr
    ):
        rows, gap = [], gap or "openspec_batch_invalid"
    if gap:
        rows = []
    results = []
    for index, args in enumerate(commands):
        result = (
            _json_result(
                (*base_command, *args),
                rows[index]["exit_code"],
                rows[index]["stdout"],
                rows[index]["stderr"],
            )
            if index < len(rows)
            else _json_result(
                (*base_command, *args),
                code or 1,
                "",
                stderr,
                error=gap or "openspec_batch_interrupted",
            )
        )
        results.append(
            result
            | {
                "transport": {
                    "command": list(transport),
                    "input_index": index,
                    **({"stdout": output, "stderr": stderr, "exit_code": code} if gap else {}),
                }
            }
        )
    return tuple(results)


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
    """Validate execution and return only an exactly bound archive cleanup path."""
    payload = result.get("json")
    archive = payload.get("archive") if isinstance(payload, dict) else None
    archive_path = ""
    if isinstance(archive, dict) and archive.get("change") == change:
        with suppress(ValueError, OSError):
            raw = archive.get("path")
            if isinstance(raw, str) and raw:
                target = Path(raw)
                relative = target.relative_to(root.resolve()).as_posix()
                if archived_change_root_matches(relative, change) and target.resolve() == target:
                    archive_path = relative
    valid = result.get("exit_code") == 0 and not result.get("parse_error") and bool(archive_path)
    return ([] if valid else ["openspec_archive_result_invalid"], archive_path)
