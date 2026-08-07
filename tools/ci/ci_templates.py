from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC
from datetime import datetime
from importlib import import_module
from pathlib import Path
from typing import Annotated
from typing import Any
from typing import Literal

from cyclopts import App
from cyclopts import Parameter

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
_projection = import_module("tools.ci.ci_projection")
_materialization = import_module("tools.ci.provider_materialization")
check_templates = _projection.check_templates
_emulator_declaration = _projection.emulator_declaration
_provider_entry = _projection.provider_entry
materialize_emulator_source = _materialization.materialize_emulator_source
CONFIG_RELATIVE_PATH = ".config/checks/ci/templates.toml"
UNTRACKED_PREVIEW_LIMIT = 12
EVIDENCE_FIELDS = (
    "schema_version",
    "kind",
    "provider",
    "mode",
    "verdict",
    "dry_run",
    "head",
    "head_start",
    "head_end",
    "head_stable",
    "dirty",
    "git_start",
    "git_end",
    "generated_at",
    "started_at",
    "finished_at",
    "tool",
    "tool_available",
    "tool_path",
    "command",
    "returncode",
    "log_warnings",
    "stdout",
    "stderr",
    "materialization",
    "timeout_seconds",
    "timed_out",
    "log_path",
)


def _git_output(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else ""


def _git_lines(*args: str) -> list[str]:
    output = _git_output(*args)
    return [line for line in output.splitlines() if line]


def _git_summary() -> dict[str, Any]:
    untracked = _git_lines("ls-files", "--others", "--exclude-standard")
    unstaged = _git_lines("diff", "--name-only", "--diff-filter=ACMRT")
    staged = _git_lines("diff", "--cached", "--name-only", "--diff-filter=ACMRT")
    status = _git_output("status", "--short")
    return {
        "branch": _git_output("rev-parse", "--abbrev-ref", "HEAD"),
        "head": _git_output("rev-parse", "HEAD"),
        "dirty": bool(status),
        "status_short": status,
        "changed_scope": {
            "staged_paths": staged,
            "unstaged_paths": unstaged,
            "tracked_changed_paths": sorted({*unstaged, *staged}),
            "untracked_count": len(untracked),
            "untracked_preview": untracked[:UNTRACKED_PREVIEW_LIMIT],
            "untracked_preview_limit": UNTRACKED_PREVIEW_LIMIT,
        },
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run_result(
    returncode: int | None,
    *,
    ok: bool,
    stdout: str = "",
    stderr: str = "",
    timed_out: bool = False,
    log_path: str = "",
) -> dict[str, Any]:
    return {
        "returncode": returncode,
        "ok": ok,
        "stdout": stdout,
        "stderr": stderr,
        "timed_out": timed_out,
        "log_path": log_path,
    }


def _log_tail(path: Path, *, limit: int = 4000) -> str:
    if not path.is_file():
        return ""
    with path.open("rb") as stream:
        stream.seek(0, os.SEEK_END)
        size = stream.tell()
        stream.seek(max(0, size - limit))
        return stream.read().decode(errors="replace")


def _run_command(
    command: list[str],
    *,
    dry_run: bool,
    tool_required: bool = True,
    env: dict[str, str] | None = None,
    cwd: Path = ROOT,
    log_path: Path,
    timeout_seconds: int,
) -> dict[str, Any]:
    if dry_run or not command:
        return _run_result(None, ok=True, log_path=str(log_path))
    if shutil.which(command[0]) is None:
        return _run_result(
            127, ok=not tool_required, stderr="tool not found", log_path=str(log_path)
        )
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("wb") as log:
        process = subprocess.Popen(command, cwd=cwd, stdout=log, stderr=subprocess.STDOUT, env=env)
        sys.stderr.write(
            f"local emulator started: pid={process.pid} timeout={timeout_seconds}s log={log_path}\n"
        )
        try:
            returncode = process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            detail = f"emulator timed out after {timeout_seconds} seconds"
            return _run_result(
                124,
                ok=False,
                stdout=_log_tail(log_path),
                stderr=detail,
                timed_out=True,
                log_path=str(log_path),
            )
    return _run_result(
        returncode,
        ok=returncode == 0,
        stdout=_log_tail(log_path),
        log_path=str(log_path),
    )


def _tool_version(tool: str) -> str:
    if shutil.which(tool) is None:
        return ""
    result = subprocess.run(
        [tool, "--version"], cwd=ROOT, capture_output=True, text=True, check=False
    )
    return next((line for line in (result.stdout or result.stderr).splitlines() if line), "")


def _docker_context_endpoint() -> str:
    if shutil.which("docker") is None:
        return ""
    result = subprocess.run(
        ["docker", "context", "inspect"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return ""
    try:
        return str(json.loads(result.stdout)[0]["Endpoints"]["docker"]["Host"])
    except (IndexError, KeyError, TypeError, json.JSONDecodeError):
        return ""


def _emulator_environment() -> dict[str, str] | None:
    if os.environ.get("DOCKER_HOST"):
        return None
    endpoint = _docker_context_endpoint()
    return os.environ | {"DOCKER_HOST": endpoint} if endpoint else None


def _emulator_state_dir(provider: str, emulation: dict[str, Any]) -> str:
    suffix = "act" if provider == "github" else "ci-local"
    return str(emulation["emulator_state_dir"]) or f"build/runtime/work/{provider}-{suffix}"


def _emulator_command(
    provider: str,
    paths: dict[str, str],
    emulation: dict[str, Any],
    mode: str,
    *,
    state_dir: Path | None = None,
) -> list[str]:
    tool = str(emulation["emulator_tool"])
    if provider == "github":
        command = [
            tool,
            str(emulation["emulator_event"]),
            "-W",
            paths["projected_file"],
        ]
        if mode == "run":
            return [
                *command,
                "-j",
                str(emulation["emulator_job"]),
                "--bind",
                "--platform",
                f"self-hosted={emulation['emulator_image']}",
            ]
        return [*command, "--list"]
    command = [tool]
    runtime_state = state_dir or Path(_emulator_state_dir(provider, emulation))
    if mode == "run":
        source_dir = runtime_state / "source"
        relative_state = os.path.relpath(runtime_state / "state", source_dir)
        command.extend(["--cwd", ".", "--file", paths["projected_file"]])
        return [
            *command,
            "--state-dir",
            relative_state,
            str(emulation["emulator_job"]),
        ]
    command.extend(["--file", paths["projected_file"]])
    command.extend(["--state-dir", str(runtime_state)])
    return [*command, "--list"]


def _mode_is_observation(mode: str, *, dry_run: bool) -> bool:
    return dry_run or mode in {"doctor", "list", "dry-run"}


def _execution_observed(provider: str, mode: str, run: dict[str, Any]) -> bool:
    if mode != "run" or not run["ok"]:
        return False
    output = f"{run['stdout']}\n{run['stderr']}"
    if provider == "github":
        return "Job succeeded" in output and "Skipping unsupported platform" not in output
    return bool(output.strip())


def _declared_image_digest(image: str) -> str:
    _, separator, digest = image.partition("@sha256:")
    return digest if separator else ""


def _admit_execution(
    provider: str,
    mode: str,
    *,
    dry_run: bool,
    run: dict[str, Any],
    forbidden_patterns: list[str],
) -> tuple[bool, list[str]]:
    combined_log = f"{run['stdout']}\n{run['stderr']}"
    executed = _execution_observed(provider, mode, run)
    if mode == "run" and not dry_run and not executed:
        run["ok"], run["returncode"] = False, int(run["returncode"] or 1)
    warnings = [
        pattern
        for pattern in forbidden_patterns
        if re.search(str(pattern), combined_log, flags=re.MULTILINE)
    ]
    if warnings:
        run["ok"], run["returncode"] = False, int(run["returncode"] or 1)
    return executed, warnings


def _materialization_issue(mode: str, *, dry_run: bool, allow_untracked: bool) -> str:
    if allow_untracked or _mode_is_observation(mode, dry_run=dry_run):
        return ""
    untracked = _git_lines("ls-files", "--others", "--exclude-standard")
    if not untracked:
        return ""
    preview = ", ".join(untracked[:UNTRACKED_PREVIEW_LIMIT])
    extra = len(untracked) - UNTRACKED_PREVIEW_LIMIT
    suffix = f", ... (+{extra} more)" if extra > 0 else ""
    return (
        "local provider emulator refused to run: provider materialization can omit "
        "untracked files. Stage, commit, ignore, or remove untracked files before "
        f"claiming local emulator evidence. Untracked paths: {preview}{suffix}"
    )


def _prepare_emulator_state(provider: str, state_dir: Path | None) -> None:
    """Create the provider-owned transient state root before execution."""
    if provider == "gitlab" and state_dir is not None:
        (state_dir / "state" / "builds").mkdir(parents=True)


def emulator_evidence(
    provider: str,
    *,
    mode: str,
    dry_run: bool,
    allow_untracked: bool,
    output: Path | None,
) -> int:
    entry = _provider_entry(provider)
    emulation = _emulator_declaration(entry)
    tool = str(emulation["emulator_tool"])
    paths = {
        "config": CONFIG_RELATIVE_PATH,
        "projected_file": str(entry["projection"]),
        "template_file": str(entry["template"]),
    }
    kind = f"local_{provider}_emulator"
    output_path = output or ROOT / "build/evidence/local-ci" / provider / f"{mode}.json"
    run_log_path = output_path.with_suffix(".log")
    timeout_seconds = int(emulation["emulator_timeout_seconds"])
    started_at, git_start = datetime.now(UTC), _git_summary()
    execution_root = ROOT
    issue, executable = (
        _materialization_issue(mode, dry_run=dry_run, allow_untracked=allow_untracked),
        shutil.which(tool),
    )
    materialization: dict[str, Any] = {
        "mode_allows_untracked": _mode_is_observation(mode, dry_run=dry_run),
        "normal_run_refuses_untracked_by_default": True,
        "untracked_allowed": allow_untracked,
        "untracked_policy": "refuse_before_emulator_run",
        "issue": issue,
    }
    materializes = (
        not issue
        and executable is not None
        and provider in {"github", "gitlab"}
        and mode == "run"
        and not dry_run
    )
    workspace = tempfile.TemporaryDirectory(prefix=f"ethos-{provider}-") if materializes else None
    state_dir = Path(workspace.name) if workspace is not None else None
    if workspace is not None:
        materialization_dir = Path(workspace.name)
        try:
            materialization |= materialize_emulator_source(
                source_root=ROOT,
                state_dir=materialization_dir,
                expected_head=str(git_start["head"]),
                expected_branch=str(git_start["branch"]),
            )
            execution_root = Path(str(materialization["source_dir"]))
        except RuntimeError as exc:
            issue = str(exc)
            materialization["issue"] = issue
    command = _emulator_command(provider, paths, emulation, mode, state_dir=state_dir)
    _prepare_emulator_state(provider, state_dir)
    try:
        run = (
            _run_result(1, ok=False, stderr=issue)
            if issue
            else _run_command(
                command,
                dry_run=dry_run,
                tool_required=not _mode_is_observation(mode, dry_run=dry_run),
                env=_emulator_environment(),
                cwd=execution_root,
                log_path=run_log_path,
                timeout_seconds=timeout_seconds,
            )
        )
    finally:
        if workspace is not None:
            workspace.cleanup()
            materialization["source_retained"] = Path(
                str(materialization.get("source_dir", ""))
            ).exists()
    run = {"timed_out": False, "log_path": str(run_log_path), **run}
    execution_observed, log_warnings = _admit_execution(
        provider,
        mode,
        dry_run=dry_run,
        run=run,
        forbidden_patterns=emulation["forbidden_log_patterns"],
    )
    finished_at, git_end = datetime.now(UTC), _git_summary()
    head_start, head_end = map(str, (git_start["head"], git_end["head"]))
    schema_version, head = 1, head_end
    head_stable, dirty = head_start == head_end, git_end["dirty"]
    verdict = "pass" if bool(run["ok"]) and head_stable and not log_warnings else "block"
    generated_at = finished_at = finished_at.isoformat()
    started_at = started_at.isoformat()
    tool_available, tool_path = executable is not None, executable or ""
    returncode = run["returncode"]
    timed_out, log_path = bool(run["timed_out"]), str(run["log_path"])
    stdout, stderr = str(run["stdout"])[-4000:], str(run["stderr"])[-4000:]
    values = locals()
    payload: dict[str, Any] = (
        {name: values[name] for name in EVIDENCE_FIELDS}
        | paths
        | {
            "emulation": emulation,
            "execution": {
                "mode": "selected_job_execution"
                if mode == "run" and not dry_run
                else "observation",
                "formal_workflow": paths["projected_file"],
                "selected_job": str(emulation["emulator_job"]),
                "executed": execution_observed,
            },
            "execution_environment": {
                "declared_image": str(emulation["emulator_image"]),
                "image_digest": _declared_image_digest(str(emulation["emulator_image"])),
                "image_digest_status": "declaration_bound",
                "tool_version": _tool_version(tool),
            },
            "files": {
                role: {
                    "path": relative,
                    "exists": (path := ROOT / relative).is_file(),
                    "sha256": _sha256(path) if path.is_file() else "",
                }
                for role, relative in paths.items()
            },
            "claim_boundary": "local provider emulator evidence only; not hosted provider status",
            "hosted_github_status_claimed": False,
            "hosted_gitlab_status_claimed": False,
        }
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0 if verdict == "pass" else int(returncode or 1)


cli_app = App(name="ethos-ci", help="ETHOS CI projection and local emulator helpers.")


@cli_app.command(name="check-templates")
def check_templates_command(
    *, json_output: Annotated[bool, Parameter(name="--json")] = False
) -> int:
    """Check hosted CI template projections against their generated surfaces."""
    return check_templates(json_output=json_output)


@cli_app.command(name="emulator-evidence")
def emulator_evidence_command(
    provider: Literal["github", "gitlab"],
    *,
    mode: str = "run",
    dry_run: bool = False,
    allow_untracked: bool = False,
    output: Path | None = None,
) -> int:
    """Write local provider-emulator evidence without claiming hosted CI status."""
    return emulator_evidence(
        provider,
        mode=mode,
        dry_run=dry_run,
        allow_untracked=allow_untracked,
        output=output,
    )


def main(argv: list[str] | None = None) -> int:
    """Run the Cyclopts-backed CI helper command surface."""
    try:
        cli_app(argv)
    except SystemExit as exc:
        if isinstance(exc.code, int):
            return exc.code
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
