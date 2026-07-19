from __future__ import annotations

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

ROOT = Path(__file__).resolve().parents[2]
CONFIG_RELATIVE_PATH = ".config/checks/ci/templates.toml"
CONFIG_PATH = ROOT / CONFIG_RELATIVE_PATH
UNTRACKED_PREVIEW_LIMIT = 12
EMULATOR_FIELDS = (
    "emulator_tool",
    "emulator_event",
    "emulator_job",
    "emulator_image",
    "emulator_supported_inputs",
    "emulator_hosted_only_reason",
)
_record = dict


def _git_output(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else ""


def _git(root: Path, *args: str, input_bytes: bytes | None = None) -> bytes:
    result = subprocess.run(
        ["git", *args], cwd=root, input=input_bytes, capture_output=True, check=False
    )
    if result.returncode == 0:
        return result.stdout
    detail = result.stderr.decode("utf-8", errors="replace").strip()
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
    state_dir.mkdir(parents=True, exist_ok=True)
    source, staging = state_dir / "source", state_dir / "source.staging"
    _remove_path(staging)
    try:
        _git(source_root, "clone", "--no-local", "--no-checkout", str(source_root), str(staging))
        _git(staging, "checkout", "--detach", expected_head)
        tracked_diff = _git(source_root, "diff", "--binary", expected_head)
        if tracked_diff:
            _git(
                staging,
                "apply",
                "--binary",
                "--whitespace=nowarn",
                "-",
                input_bytes=tracked_diff,
            )
        _remove_path(source)
        staging.replace(source)
    except Exception:
        _remove_path(staging)
        raise
    source_head = _git(source, "rev-parse", "HEAD").decode().strip()
    # fmt: off
    result = _record(kind="independent_git_checkout", source_dir=str(source),
                     source_head=source_head, source_head_matches_expected=source_head == expected_head)  # noqa: E501
    result.update(git_directory_is_real=(source / ".git").is_dir(), tracked_diff_bytes=len(tracked_diff))  # noqa: E501
    result["uses_external_object_alternates"] = (source / ".git/objects/info/alternates").is_file()
    # fmt: on
    return result


def _git_summary() -> dict[str, Any]:
    lines = lambda *args: [line for line in _git_output(*args).splitlines() if line]  # noqa: E731
    untracked = lines("ls-files", "--others", "--exclude-standard")
    unstaged = lines("diff", "--name-only", "--diff-filter=ACMRT")
    staged = lines("diff", "--cached", "--name-only", "--diff-filter=ACMRT")
    status = _git_output("status", "--short")
    # fmt: off
    scope = _record(staged_paths=staged, unstaged_paths=unstaged,
                    tracked_changed_paths=sorted({*unstaged, *staged}), untracked_count=len(untracked),  # noqa: E501
                    untracked_preview=untracked[:UNTRACKED_PREVIEW_LIMIT],
                    untracked_preview_limit=UNTRACKED_PREVIEW_LIMIT)
    summary = _record(branch=_git_output("rev-parse", "--abbrev-ref", "HEAD"),
                      head=_git_output("rev-parse", "HEAD"), dirty=bool(status), status_short=status)  # noqa: E501
    # fmt: on
    summary["changed_scope"] = scope
    return summary


def _projection_entries() -> list[dict[str, Any]]:
    entries = tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8")).get("projection", [])
    if not isinstance(entries, list):
        message = f"{CONFIG_RELATIVE_PATH} projection must be a list"
        raise SystemExit(message)
    return entries


def _provider_entry(provider: str) -> dict[str, Any]:
    entries = [entry for entry in _projection_entries() if entry.get("provider") == provider]
    if len(entries) != 1:
        message = f"expected exactly one CI projection for provider: {provider}"
        raise SystemExit(message)
    return entries[0]


def _emulation(entry: dict[str, Any]) -> dict[str, Any]:
    if missing := [field for field in EMULATOR_FIELDS if field not in entry]:
        raise SystemExit(
            f"CI emulator declaration missing for {entry.get('provider', 'unknown')}: "
            + ", ".join(missing)
        )
    return {field: entry[field] for field in EMULATOR_FIELDS} | {
        "emulator_state_dir": entry.get("emulator_state_dir", "")
    }


def _template_projection(
    entry: dict[str, Any], emulation: dict[str, Any]
) -> tuple[dict[str, Any] | None, list[str]]:
    provider = str(entry["provider"])
    template, projection = (ROOT / str(entry[key]) for key in ("template", "projection"))
    paths = ((str(entry["template"]), template), (str(entry["projection"]), projection))
    if missing := [relative for relative, path in paths if not path.is_file()]:
        return None, [f"missing files: {', '.join(missing)}"]
    owners = list(entry.get("required_owner_scripts", []))
    missing_owners = [script for script in owners if not (ROOT / script).is_file()]
    failures = [f"missing owner scripts: {', '.join(missing_owners)}"] if missing_owners else []
    match = template.read_bytes() == projection.read_bytes()
    if not match:
        failures.append(
            f"projection drift: {projection.relative_to(ROOT)} != {template.relative_to(ROOT)}"
        )
    # fmt: off
    record = _record(provider=provider, template=str(template.relative_to(ROOT)),
                     projection=str(projection.relative_to(ROOT)), emulation=emulation,
                     template_sha256=hashlib.sha256(template.read_bytes()).hexdigest(),
                     projection_sha256=hashlib.sha256(projection.read_bytes()).hexdigest(),
                     projection_matches_template=match, required_owner_scripts=owners)
    # fmt: on
    return record, failures


def check_templates(*, json_output: Annotated[bool, Parameter(name="--json")] = False) -> int:
    failures, projections = [], []
    for entry in _projection_entries():
        provider = str(entry["provider"])
        try:
            projection, reasons = _template_projection(entry, _emulation(entry))
        except SystemExit as exc:
            projection, reasons = None, [str(exc)]
        failures.extend({"provider": provider, "reason": reason} for reason in reasons)
        if projection is not None:
            projections.append(projection)
    # fmt: off
    evidence = _record(schema_version=1, kind="ethos_ci_template_consistency", ok=not failures,
                       head=_git_output("rev-parse", "HEAD"),
                       dirty=bool(_git_output("status", "--short")), config=CONFIG_RELATIVE_PATH,
                       generated_at=datetime.now(UTC).isoformat(), projections=projections,
                       failures=failures)
    # fmt: on
    if json_output:
        sys.stdout.write(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    else:
        sys.stderr.writelines(f"{item['provider']}: {item['reason']}\n" for item in failures)
    return 0 if evidence["ok"] else 1


def _result(returncode: int | None, *, ok: bool, stdout: str = "", stderr: str = "") -> dict:
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
        return _result(None, ok=True)
    if shutil.which(command[0]) is None:
        return _result(127, ok=not tool_required, stderr="tool not found")
    run = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False, env=env)
    return _result(run.returncode, ok=run.returncode == 0, stdout=run.stdout, stderr=run.stderr)


def _tool_version(tool: str) -> str:
    if shutil.which(tool) is None:
        return ""
    run = subprocess.run([tool, "--version"], capture_output=True, text=True, check=False)
    return next((line for line in (run.stdout or run.stderr).splitlines() if line), "")


def _docker_context_endpoint() -> str:
    if shutil.which("docker") is None:
        return ""
    run = subprocess.run(
        ["docker", "context", "inspect"], capture_output=True, text=True, check=False
    )
    try:
        return (
            str(json.loads(run.stdout)[0]["Endpoints"]["docker"]["Host"])
            if run.returncode == 0
            else ""
        )
    except (IndexError, KeyError, TypeError, json.JSONDecodeError):
        return ""


def _state_dir(provider: str, emulation: dict[str, Any]) -> str:
    suffix = "github-act" if provider == "github" else "gitlab-ci-local"
    return str(emulation["emulator_state_dir"]) or f"build/runtime/work/{suffix}"


def _command(
    provider: str, paths: dict[str, str], emulation: dict[str, Any], mode: str
) -> list[str]:
    tool, job = str(emulation["emulator_tool"]), str(emulation["emulator_job"])
    if provider == "github":
        command = [tool, str(emulation["emulator_event"]), "-W", paths["projected_file"]]
        return [*command, "-j", job] if mode == "run" else [*command, "--list"]
    command = [tool, "--file", paths["projected_file"]]
    state = _state_dir(provider, emulation)
    if mode == "run":
        return [tool, "--cwd", f"{state}/source", *command[1:], "--state-dir", "../state", job]
    return [*command, "--state-dir", state, "--list"]


def _materialization_issue(mode: str, *, dry_run: bool, allow_untracked: bool) -> str:
    if allow_untracked or dry_run or mode in {"doctor", "list", "dry-run"}:
        return ""
    paths = [
        line
        for line in _git_output("ls-files", "--others", "--exclude-standard").splitlines()
        if line
    ]
    if not paths:
        return ""
    preview = ", ".join(paths[:UNTRACKED_PREVIEW_LIMIT])
    if len(paths) > UNTRACKED_PREVIEW_LIMIT:
        preview += f", ... (+{len(paths) - UNTRACKED_PREVIEW_LIMIT} more)"
    return (
        "local provider emulator refused to run: provider materialization can omit untracked "
        "files. Stage, commit, ignore, or remove untracked files before claiming local emulator "
        f"evidence. Untracked paths: {preview}"
    )


def emulator_evidence(
    provider: Literal["github", "gitlab"],
    *,
    mode: str = "run",
    dry_run: bool = False,
    allow_untracked: bool = False,
    output: Path | None = None,
) -> int:
    started = datetime.now(UTC)
    entry, git_start = _provider_entry(provider), _git_summary()
    paths = _record(config=CONFIG_RELATIVE_PATH, projected_file=str(entry["projection"]),
                    template_file=str(entry["template"]))  # fmt: skip
    emulation = _emulation(entry)
    tool, observation = (
        str(emulation["emulator_tool"]),
        dry_run or mode in {"doctor", "list", "dry-run"},
    )
    command, issue, executable = (
        _command(provider, paths, emulation, mode),
        _materialization_issue(mode, dry_run=dry_run, allow_untracked=allow_untracked),
        shutil.which(tool),
    )
    # fmt: off
    materialization: dict[str, Any] = _record(mode_allows_untracked=observation,
        normal_run_refuses_untracked_by_default=True, untracked_allowed=allow_untracked,
        untracked_policy="refuse_before_emulator_run", issue=issue)
    # fmt: on
    execution_root = ROOT
    if not issue and executable is not None and mode == "run" and not dry_run:
        try:
            materialization |= materialize_emulator_source(
                source_root=ROOT,
                state_dir=ROOT / _state_dir(provider, emulation),
                expected_head=str(git_start["head"]),
            )
            if provider == "github":
                execution_root = Path(str(materialization["source_dir"]))
        except RuntimeError as exc:
            issue = materialization["issue"] = str(exc)
    environment = None
    if (
        tool == "act"
        and not os.environ.get("DOCKER_HOST")
        and (endpoint := _docker_context_endpoint())
    ):
        environment = os.environ | {"DOCKER_HOST": endpoint}
    run = (
        _result(1, ok=False, stderr=issue)
        if issue
        else _run_command(
            command,
            dry_run=dry_run,
            tool_required=not observation,
            env=environment,
            cwd=execution_root,
        )
    )
    finished, git_end = datetime.now(UTC), _git_summary()
    stable = git_start["head"] == git_end["head"]
    file_facts = {}
    for role, relative in paths.items():
        path = ROOT / relative
        file_facts[role] = _record(path=relative, exists=path.is_file(),
            sha256=hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "")  # fmt: skip  # noqa: E501
    execution_mode = "selected_job_execution" if mode == "run" and not dry_run else "observation"
    execution = _record(mode=execution_mode, formal_workflow=paths["projected_file"])
    execution["selected_job"] = str(emulation["emulator_job"])
    execution_environment = _record(declared_image=str(emulation["emulator_image"]),
        image_digest="", image_digest_status="not_observed", tool_version=_tool_version(tool))  # fmt: skip  # noqa: E501
    payload: dict[str, Any] = _record(schema_version=1, kind=f"local_{provider}_emulator")
    payload.update(provider=provider, mode=mode, ok=bool(run["ok"]) and stable, dry_run=dry_run)
    payload.update(head=git_end["head"], head_start=git_start["head"], head_end=git_end["head"])
    payload.update(head_stable=stable, dirty=git_end["dirty"], git_start=git_start, git_end=git_end)
    payload.update(generated_at=finished.isoformat(), started_at=started.isoformat(),
                   finished_at=finished.isoformat())  # fmt: skip
    payload.update(tool=tool, tool_available=executable is not None, tool_path=executable or "")
    payload.update(paths)
    payload.update(emulation=emulation, execution=execution,
                   execution_environment=execution_environment)  # fmt: skip
    payload.update(files=file_facts, command=command, returncode=run["returncode"])
    payload.update(stdout=str(run["stdout"])[-4000:], stderr=str(run["stderr"])[-4000:])
    # fmt: off
    payload.update(materialization=materialization,
        claim_boundary="local provider emulator evidence only; not hosted provider status",
        hosted_github_status_claimed=False, hosted_gitlab_status_claimed=False)
    # fmt: on
    output_path = output or ROOT / f"build/evidence/local-ci/{provider}/{mode}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    output_path.write_text(rendered, encoding="utf-8")
    sys.stdout.write(rendered)
    return 0 if payload["ok"] else int(run["returncode"] or 1)


def main(argv: list[str] | None = None) -> int:
    cli_app = App(name="ethos-ci", help="ETHOS CI projection and local emulator helpers.")
    cli_app.command(check_templates, name="check-templates")
    cli_app.command(emulator_evidence, name="emulator-evidence")
    try:
        cli_app(argv)
    except SystemExit as exc:
        if isinstance(exc.code, int):
            return exc.code
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
