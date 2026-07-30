from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Annotated
from typing import Any
from typing import Literal

from cyclopts import App
from cyclopts import Parameter


def _words(value: str) -> tuple[str, ...]:
    return tuple(value.split())


ROOT = Path(__file__).resolve().parents[2]
CONFIG_RELATIVE_PATH = ".config/checks/ci/templates.toml"
CONFIG_PATH = ROOT / CONFIG_RELATIVE_PATH


UNTRACKED_PREVIEW_LIMIT = 12
EMULATOR_REQUIRED_FIELDS = _words("emulator_tool emulator_event emulator_job emulator_image")
EVIDENCE_FIELDS = _words(
    "schema_version kind provider mode ok dry_run head head_start head_end head_stable dirty "
    "git_start git_end generated_at started_at finished_at tool tool_available tool_path command "
    "returncode log_warnings stdout stderr materialization"
)


def _git_output(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else ""


def _git_lines(*args: str) -> list[str]:
    output = _git_output(*args)
    return [line for line in output.splitlines() if line]


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
    *, source_root: Path, state_dir: Path, expected_head: str
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
    if source_head != expected_head:
        message = (
            "Local emulator source materialization failed: "
            f"expected HEAD {expected_head}, observed {source_head}"
        )
        raise RuntimeError(message)
    try:
        _git(source_root, "bundle", "create", str(bundle_path), "HEAD")
        _git(state_dir, "init", "--quiet", str(staging_dir))
        _git(staging_dir, "fetch", "--quiet", "--no-tags", str(bundle_path), "HEAD")
        _git(staging_dir, "checkout", "--quiet", "--detach", "FETCH_HEAD")
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
    return {
        "kind": "independent_git_checkout",
        "source_dir": str(source_dir),
        "source_head": source_head,
        "source_head_matches_expected": source_head == expected_head,
        "git_directory_is_real": (source_dir / ".git").is_dir(),
        "uses_external_object_alternates": (source_dir / ".git/objects/info/alternates").is_file(),
        "tracked_diff_bytes": len(tracked_diff),
    }


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


def _projection_entries() -> list[dict[str, Any]]:
    entries = tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8")).get("projection", [])
    if not isinstance(entries, list):
        message = ".config/checks/ci/templates.toml projection must be a list"
        raise SystemExit(message)
    return entries


def _surface_entries() -> list[dict[str, Any]]:
    entries = tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8")).get("forge_surface", [])
    if not isinstance(entries, list):
        message = ".config/checks/ci/templates.toml forge_surface must be a list"
        raise SystemExit(message)
    return entries


def _provider_entry(provider: str) -> dict[str, Any]:
    entries = [entry for entry in _projection_entries() if entry.get("provider") == provider]
    if len(entries) != 1:
        message = f"expected exactly one CI projection for provider: {provider}"
        raise SystemExit(message)
    return entries[0]


def _emulator_declaration(entry: dict[str, Any]) -> dict[str, Any]:
    missing = [field for field in EMULATOR_REQUIRED_FIELDS if field not in entry]
    if missing:
        provider = entry.get("provider", "unknown")
        message = f"CI emulator declaration missing for {provider}: {', '.join(missing)}"
        raise SystemExit(message)
    return {field: entry[field] for field in EMULATOR_REQUIRED_FIELDS} | {
        "emulator_state_dir": entry.get("emulator_state_dir", ""),
        "forbidden_log_patterns": list(entry.get("forbidden_log_patterns", [])),
    }


def _forge_surface_reports() -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    surfaces = []
    failures = []
    for entry in _surface_entries():
        source = ROOT / str(entry["source"])
        projection = ROOT / str(entry["projection"])
        missing = [path.as_posix() for path in (source, projection) if not path.is_file()]
        match = not missing and source.read_bytes() == projection.read_bytes()
        if missing:
            failures.append(
                {
                    "provider": str(entry["provider"]),
                    "reason": f"missing files: {', '.join(missing)}",
                }
            )
        elif not match:
            failures.append(
                {
                    "provider": str(entry["provider"]),
                    "reason": f"projection drift: {entry['projection']} != {entry['source']}",
                }
            )
        surfaces.append(dict(entry) | {"projection_matches_source": match})
    return surfaces, failures


def check_templates(*, json_output: bool) -> int:
    failures: list[dict[str, str]] = []
    projections: list[dict[str, Any]] = []
    for entry in _projection_entries():
        provider = str(entry["provider"])
        template = ROOT / str(entry["template"])
        projection = ROOT / str(entry["projection"])
        try:
            emulation = _emulator_declaration(entry)
        except SystemExit as exc:
            failures.append({"provider": provider, "reason": str(exc)})
            continue
        missing = [
            rel
            for rel, path in [
                (str(entry["template"]), template),
                (str(entry["projection"]), projection),
            ]
            if not path.is_file()
        ]
        owner_missing = [
            script
            for script in entry.get("required_owner_scripts", [])
            if not (ROOT / str(script)).is_file()
        ]
        if missing:
            reason = f"missing files: {', '.join(missing)}"
            failures.append({"provider": provider, "reason": reason})
            continue
        if owner_missing:
            reason = f"missing owner scripts: {', '.join(owner_missing)}"
            failures.append({"provider": provider, "reason": reason})
        match = template.read_bytes() == projection.read_bytes()
        if not match:
            reason = (
                f"projection drift: {projection.relative_to(ROOT)} != {template.relative_to(ROOT)}"
            )
            failures.append({"provider": provider, "reason": reason})
        projections.append(
            {
                "provider": provider,
                "template": str(template.relative_to(ROOT)),
                "projection": str(projection.relative_to(ROOT)),
                "emulation": emulation,
                "template_sha256": _sha256(template),
                "projection_sha256": _sha256(projection),
                "projection_matches_template": match,
                "required_owner_scripts": list(entry.get("required_owner_scripts", [])),
            }
        )
    surfaces, surface_failures = _forge_surface_reports()
    failures.extend(surface_failures)
    evidence = {
        "schema_version": 1,
        "kind": "ethos_ci_template_consistency",
        "ok": not failures,
        "head": _git_output("rev-parse", "HEAD"),
        "dirty": bool(_git_output("status", "--short")),
        "config": str(CONFIG_PATH.relative_to(ROOT)),
        "generated_at": datetime.now(UTC).isoformat(),
        "projections": projections,
        "forge_surfaces": surfaces,
        "failures": failures,
    }
    if json_output:
        sys.stdout.write(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    elif failures:
        for failure in failures:
            sys.stderr.write(f"{failure['provider']}: {failure['reason']}\n")
    return 0 if evidence["ok"] else 1


def _run_result(
    returncode: int | None, *, ok: bool, stdout: str = "", stderr: str = ""
) -> dict[str, Any]:
    return {"returncode": returncode, "ok": ok, "stdout": stdout, "stderr": stderr}


def _run_command(
    command: list[str],
    *,
    dry_run: bool,
    tool_required: bool = True,
    env: dict[str, str] | None = None,
    cwd: Path = ROOT,
) -> dict[str, Any]:
    if dry_run or not command:
        return _run_result(None, ok=True)
    if shutil.which(command[0]) is None:
        return _run_result(127, ok=not tool_required, stderr="tool not found")
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False, env=env)
    return _run_result(
        result.returncode, ok=result.returncode == 0, stdout=result.stdout, stderr=result.stderr
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


def _emulator_environment(tool: str) -> dict[str, str] | None:
    if tool != "act" or os.environ.get("DOCKER_HOST"):
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
            return [*command, "-j", str(emulation["emulator_job"])]
        return [*command, "--list"]
    command = [tool]
    runtime_state = state_dir or Path(_emulator_state_dir(provider, emulation))
    if mode == "run":
        source_dir = str(runtime_state / "source")
        command.extend(["--cwd", source_dir, "--file", paths["projected_file"]])
        return [
            *command,
            "--state-dir",
            str(runtime_state / "state"),
            str(emulation["emulator_job"]),
        ]
    command.extend(["--file", paths["projected_file"]])
    command.extend(["--state-dir", str(runtime_state)])
    return [*command, "--list"]


def _mode_is_observation(mode: str, *, dry_run: bool) -> bool:
    return dry_run or mode in {"doctor", "list", "dry-run"}


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
    if materializes:
        try:
            materialization |= materialize_emulator_source(
                source_root=ROOT,
                state_dir=state_dir,
                expected_head=str(git_start["head"]),
            )
            if provider == "github":
                execution_root = Path(str(materialization["source_dir"]))
        except RuntimeError as exc:
            issue = str(exc)
            materialization["issue"] = issue
    command = _emulator_command(provider, paths, emulation, mode, state_dir=state_dir)
    try:
        run = (
            _run_result(1, ok=False, stderr=issue)
            if issue
            else _run_command(
                command,
                dry_run=dry_run,
                tool_required=not _mode_is_observation(mode, dry_run=dry_run),
                env=_emulator_environment(tool),
                cwd=execution_root,
            )
        )
    finally:
        if workspace is not None:
            workspace.cleanup()
            materialization["source_retained"] = Path(
                str(materialization.get("source_dir", ""))
            ).exists()
    combined_log = f"{run['stdout']}\n{run['stderr']}"
    log_warnings = [
        pattern
        for pattern in emulation["forbidden_log_patterns"]
        if re.search(str(pattern), combined_log, flags=re.MULTILINE)
    ]
    if log_warnings:
        run["ok"], run["returncode"] = False, int(run["returncode"] or 1)
    finished_at = datetime.now(UTC)
    git_end = _git_summary()
    head_start, head_end = map(str, (git_start["head"], git_end["head"]))
    schema_version, head = 1, head_end
    head_stable, dirty = head_start == head_end, git_end["dirty"]
    ok = bool(run["ok"]) and head_stable
    generated_at = finished_at = finished_at.isoformat()
    started_at = started_at.isoformat()
    tool_available, tool_path = executable is not None, executable or ""
    returncode = run["returncode"]
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
            },
            "execution_environment": {
                "declared_image": str(emulation["emulator_image"]),
                "image_digest": "",
                "image_digest_status": "not_observed",
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
    return 0 if ok else int(returncode or 1)


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
