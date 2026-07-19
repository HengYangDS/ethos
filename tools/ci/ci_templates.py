import hashlib
import json
import os
import shutil
import subprocess
import sys
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
EMULATOR_REQUIRED_FIELDS = _words(
    "emulator_tool emulator_event emulator_job emulator_image "
    "emulator_supported_inputs emulator_hosted_only_reason"
)
EVIDENCE_FIELDS = _words(
    "schema_version kind provider mode ok dry_run head head_start head_end head_stable dirty "
    "git_start git_end generated_at started_at finished_at tool tool_available tool_path command "
    "returncode stdout stderr materialization"
)


def _git_output(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else ""


def _git(root: Path, *args: str, input_bytes: bytes | None = None) -> bytes:
    result = subprocess.run(
        ["git", *args], cwd=root, input=input_bytes, capture_output=True, check=False
    )
    if result.returncode:
        detail = result.stderr.decode(errors="replace").strip()
        raise RuntimeError(
            f"Local emulator source materialization failed: git {' '.join(args)}: {detail}"
        )
    return result.stdout


def _remove_path(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink(missing_ok=True)


def materialize_emulator_source(
    *, source_root: Path, state_dir: Path, expected_head: str
) -> dict[str, Any]:
    """Create a standalone Git snapshot for provider emulators."""
    state_dir.mkdir(parents=True, exist_ok=True)
    source_dir, staging_dir = state_dir / "source", state_dir / "source.staging"
    _remove_path(staging_dir)
    try:
        _git(
            source_root,
            "clone",
            "--no-local",
            "--no-checkout",
            str(source_root),
            str(staging_dir),
        )
        _git(staging_dir, "checkout", "--detach", expected_head)
        tracked_diff = _git(source_root, "diff", "--binary", expected_head)
        if tracked_diff:
            _git(
                staging_dir,
                "apply",
                "--binary",
                "--whitespace=nowarn",
                "-",
                input_bytes=tracked_diff,
            )
        _remove_path(source_dir)
        staging_dir.replace(source_dir)
    except Exception:
        _remove_path(staging_dir)
        raise
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
    untracked = _git_output("ls-files", "--others", "--exclude-standard").splitlines()
    unstaged = _git_output("diff", "--name-only", "--diff-filter=ACMRT").splitlines()
    staged = _git_output("diff", "--cached", "--name-only", "--diff-filter=ACMRT").splitlines()
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


def _projection_entries() -> list[dict[str, Any]]:
    entries = tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8")).get("projection", [])
    if not isinstance(entries, list):
        raise SystemExit(f"{CONFIG_RELATIVE_PATH} projection must be a list")
    return entries


def _provider_entry(provider: str) -> dict[str, Any]:
    entries = [item for item in _projection_entries() if item.get("provider") == provider]
    if len(entries) != 1:
        raise SystemExit(f"expected exactly one CI projection for provider: {provider}")
    return entries[0]


def _emulator_declaration(entry: dict[str, Any]) -> dict[str, Any]:
    missing = [field for field in EMULATOR_REQUIRED_FIELDS if field not in entry]
    if missing:
        provider = entry.get("provider", "unknown")
        raise SystemExit(f"CI emulator declaration missing for {provider}: {', '.join(missing)}")
    return {field: entry[field] for field in EMULATOR_REQUIRED_FIELDS} | {
        "emulator_state_dir": entry.get("emulator_state_dir", "")
    }


def check_templates(*, json_output: Annotated[bool, Parameter(name="--json")] = False) -> int:
    failures: list[dict[str, str]] = []
    projections: list[dict[str, Any]] = []
    for entry in _projection_entries():
        provider = str(entry["provider"])
        paths = {key: ROOT / str(entry[key]) for key in ("template", "projection")}
        try:
            emulation = _emulator_declaration(entry)
        except SystemExit as exc:
            failures.append({"provider": provider, "reason": str(exc)})
            continue
        missing = [str(entry[key]) for key, path in paths.items() if not path.is_file()]
        if missing:
            failures.append(
                {"provider": provider, "reason": f"missing files: {', '.join(missing)}"}
            )
            continue
        owner_missing = [
            str(script)
            for script in entry.get("required_owner_scripts", [])
            if not (ROOT / str(script)).is_file()
        ]
        template, projection = paths["template"], paths["projection"]
        match = template.read_bytes() == projection.read_bytes()
        reasons = [f"missing owner scripts: {', '.join(owner_missing)}"] if owner_missing else []
        if not match:
            reasons.append(f"projection drift: {entry['projection']} != {entry['template']}")
        failures.extend({"provider": provider, "reason": reason} for reason in reasons)
        projections.append(
            {
                "provider": provider,
                "template": str(entry["template"]),
                "projection": str(entry["projection"]),
                "emulation": emulation,
                "template_sha256": hashlib.sha256(template.read_bytes()).hexdigest(),
                "projection_sha256": hashlib.sha256(projection.read_bytes()).hexdigest(),
                "projection_matches_template": match,
                "required_owner_scripts": list(entry.get("required_owner_scripts", [])),
            }
        )
    evidence = {
        "schema_version": 1,
        "kind": "ethos_ci_template_consistency",
        "ok": not failures,
        "head": _git_output("rev-parse", "HEAD"),
        "dirty": bool(_git_output("status", "--short")),
        "config": CONFIG_RELATIVE_PATH,
        "generated_at": datetime.now(UTC).isoformat(),
        "projections": projections,
        "failures": failures,
    }
    if json_output:
        sys.stdout.write(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    elif failures:
        sys.stderr.write("".join(f"{item['provider']}: {item['reason']}\n" for item in failures))
    return int(bool(failures))


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
        result.returncode,
        ok=result.returncode == 0,
        stdout=result.stdout,
        stderr=result.stderr,
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
    if result.returncode:
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


def _provider_paths(entry: dict[str, Any]) -> dict[str, str]:
    return {
        "config": CONFIG_RELATIVE_PATH,
        "projected_file": str(entry["projection"]),
        "template_file": str(entry["template"]),
    }


def _emulator_state_dir(provider: str, emulation: dict[str, Any]) -> str:
    suffix = "act" if provider == "github" else "ci-local"
    return str(emulation["emulator_state_dir"]) or f"build/runtime/work/{provider}-{suffix}"


def _emulator_command(
    provider: str, paths: dict[str, str], emulation: dict[str, Any], mode: str
) -> list[str]:
    tool, job = map(str, (emulation["emulator_tool"], emulation["emulator_job"]))
    if provider == "github":
        command = [
            tool,
            str(emulation["emulator_event"]),
            "-W",
            paths["projected_file"],
        ]
        return [*command, "-j", job] if mode == "run" else [*command, "--list"]
    state_dir = _emulator_state_dir(provider, emulation)
    if mode == "run":
        return [
            tool,
            "--cwd",
            f"{state_dir}/source",
            "--file",
            paths["projected_file"],
            "--state-dir",
            "../state",
            job,
        ]
    return [tool, "--file", paths["projected_file"], "--state-dir", state_dir, "--list"]


def _file_fact(relative: str) -> dict[str, Any]:
    path = ROOT / relative
    return {
        "path": relative,
        "exists": path.is_file(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "",
    }


def _file_facts(paths: dict[str, str]) -> dict[str, dict[str, Any]]:
    return {role: _file_fact(relative) for role, relative in paths.items()}


def _materialization_issue(mode: str, *, dry_run: bool, allow_untracked: bool) -> str:
    if allow_untracked or dry_run or mode in {"doctor", "list", "dry-run"}:
        return ""
    untracked = _git_output("ls-files", "--others", "--exclude-standard").splitlines()
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
    provider: Literal["github", "gitlab"],
    *,
    mode: str = "run",
    dry_run: bool = False,
    allow_untracked: bool = False,
    output: Path | None = None,
) -> int:
    entry = _provider_entry(provider)
    paths, emulation = _provider_paths(entry), _emulator_declaration(entry)
    tool = str(emulation["emulator_tool"])
    command = _emulator_command(provider, paths, emulation, mode)
    started_at = datetime.now(UTC).isoformat()
    git_start = _git_summary()
    execution_root = ROOT
    issue = _materialization_issue(mode, dry_run=dry_run, allow_untracked=allow_untracked)
    executable = shutil.which(tool)
    observation = dry_run or mode in {"doctor", "list", "dry-run"}
    materialization: dict[str, Any] = {
        "mode_allows_untracked": observation,
        "normal_run_refuses_untracked_by_default": True,
        "untracked_allowed": allow_untracked,
        "untracked_policy": "refuse_before_emulator_run",
        "issue": issue,
    }
    if not issue and executable and mode == "run" and not dry_run:
        try:
            materialization |= materialize_emulator_source(
                source_root=ROOT,
                state_dir=ROOT / _emulator_state_dir(provider, emulation),
                expected_head=str(git_start["head"]),
            )
            if provider == "github":
                execution_root = Path(str(materialization["source_dir"]))
        except RuntimeError as exc:
            issue = materialization["issue"] = str(exc)
    run = (
        _run_result(1, ok=False, stderr=issue)
        if issue
        else _run_command(
            command,
            dry_run=dry_run,
            tool_required=not observation,
            env=_emulator_environment(tool),
            cwd=execution_root,
        )
    )
    finished_at = datetime.now(UTC).isoformat()
    git_end = _git_summary()
    head_start, head_end = map(str, (git_start["head"], git_end["head"]))
    schema_version, kind, head = 1, f"local_{provider}_emulator", head_end
    head_stable, dirty = head_start == head_end, git_end["dirty"]
    ok = bool(run["ok"]) and head_stable
    tool_available = bool(executable)
    tool_path = executable or ""
    generated_at = finished_at
    returncode = run["returncode"]
    stdout = str(run["stdout"])[-4000:]
    stderr = str(run["stderr"])[-4000:]
    values = locals()
    payload = (
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
            "files": _file_facts(paths),
            "claim_boundary": "local provider emulator evidence only; not hosted provider status",
            "hosted_github_status_claimed": False,
            "hosted_gitlab_status_claimed": False,
        }
    )
    evidence_path = output or ROOT / "build/evidence/local-ci" / provider / f"{mode}.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0 if ok else int(returncode or 1)


cli_app = App(name="ethos-ci", help="ETHOS CI projection and local emulator helpers.")
cli_app.command(check_templates, name="check-templates")
cli_app.command(emulator_evidence, name="emulator-evidence")


def main(argv: list[str] | None = None) -> int:
    """Run the Cyclopts-backed CI helper command surface."""
    try:
        cli_app(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
