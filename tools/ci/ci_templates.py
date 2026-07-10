from __future__ import annotations

import hashlib
import json
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
CONFIG_PATH = ROOT / ".config/checks/ci/templates.toml"


UNTRACKED_PREVIEW_LIMIT = 12


def _git_output(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def _git_lines(*args: str) -> list[str]:
    output = _git_output(*args)
    return [line for line in output.splitlines() if line]


def _git_head() -> str:
    return _git_output("rev-parse", "HEAD")


def _git_dirty() -> bool:
    return bool(_git_output("status", "--short"))


def _git_summary() -> dict[str, Any]:
    untracked = _git_lines("ls-files", "--others", "--exclude-standard")
    unstaged = _git_lines("diff", "--name-only", "--diff-filter=ACMRT")
    staged = _git_lines("diff", "--cached", "--name-only", "--diff-filter=ACMRT")
    tracked_changed = sorted({*unstaged, *staged})
    return {
        "branch": _git_output("rev-parse", "--abbrev-ref", "HEAD"),
        "head": _git_head(),
        "dirty": _git_dirty(),
        "status_short": _git_output("status", "--short"),
        "changed_scope": {
            "staged_paths": staged,
            "unstaged_paths": unstaged,
            "tracked_changed_paths": tracked_changed,
            "untracked_count": len(untracked),
            "untracked_preview": untracked[:UNTRACKED_PREVIEW_LIMIT],
            "untracked_preview_limit": UNTRACKED_PREVIEW_LIMIT,
        },
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_config() -> dict[str, Any]:
    return tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _projection_entries() -> list[dict[str, Any]]:
    entries = _load_config().get("projection", [])
    if not isinstance(entries, list):
        message = ".config/checks/ci/templates.toml projection must be a list"
        raise SystemExit(message)
    return entries


def check_templates(*, json_output: bool) -> int:
    failures: list[dict[str, str]] = []
    projections: list[dict[str, Any]] = []
    for entry in _projection_entries():
        provider = str(entry["provider"])
        template = ROOT / str(entry["template"])
        projection = ROOT / str(entry["projection"])
        emulator = ROOT / str(entry["local_emulator"])
        missing = [
            rel
            for rel, path in [
                (str(entry["template"]), template),
                (str(entry["projection"]), projection),
                (str(entry["local_emulator"]), emulator),
            ]
            if not path.is_file()
        ]
        owner_missing = [
            script
            for script in entry.get("required_owner_scripts", [])
            if not (ROOT / str(script)).is_file()
        ]
        if missing:
            failures.append(
                {
                    "provider": provider,
                    "reason": f"missing files: {', '.join(missing)}",
                }
            )
            continue
        if owner_missing:
            failures.append(
                {
                    "provider": provider,
                    "reason": f"missing owner scripts: {', '.join(owner_missing)}",
                }
            )
        template_bytes = template.read_bytes()
        projection_bytes = projection.read_bytes()
        match = template_bytes == projection_bytes
        if not match:
            failures.append(
                {
                    "provider": provider,
                    "reason": "projection drift: "
                    f"{projection.relative_to(ROOT)} != {template.relative_to(ROOT)}",
                }
            )
        projections.append(
            {
                "provider": provider,
                "template": str(template.relative_to(ROOT)),
                "projection": str(projection.relative_to(ROOT)),
                "local_emulator": str(emulator.relative_to(ROOT)),
                "template_sha256": _sha256(template),
                "projection_sha256": _sha256(projection),
                "projection_matches_template": match,
                "required_owner_scripts": list(entry.get("required_owner_scripts", [])),
            }
        )
    evidence = {
        "schema_version": 1,
        "kind": "ethos_ci_template_consistency",
        "ok": not failures,
        "head": _git_head(),
        "dirty": _git_dirty(),
        "config": str(CONFIG_PATH.relative_to(ROOT)),
        "generated_at": datetime.now(UTC).isoformat(),
        "projections": projections,
        "failures": failures,
    }
    if json_output:
        sys.stdout.write(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    elif failures:
        for failure in failures:
            sys.stderr.write(f"{failure['provider']}: {failure['reason']}\n")
    return 0 if evidence["ok"] else 1


def _write_evidence(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _run_command(
    command: list[str],
    *,
    dry_run: bool,
    tool_required: bool = True,
) -> dict[str, Any]:
    if dry_run:
        return {"returncode": None, "ok": True, "stdout": "", "stderr": ""}
    if not command:
        return {"returncode": None, "ok": True, "stdout": "", "stderr": ""}
    if shutil.which(command[0]) is None:
        return {
            "returncode": 127,
            "ok": not tool_required,
            "stdout": "",
            "stderr": "tool not found",
        }
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    return {
        "returncode": result.returncode,
        "ok": result.returncode == 0,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def _provider_paths(provider: str) -> dict[str, str]:
    if provider == "github":
        return {
            "config": ".config/ci/emulators/act.yml",
            "projected_file": ".github/workflows/ci.yml",
            "template_file": ".config/ci/templates/hosted/github-actions.yml",
        }
    return {
        "config": ".config/ci/emulators/gitlab.yml",
        "projected_file": ".gitlab-ci.yml",
        "template_file": ".config/ci/templates/hosted/gitlab-ci.yml",
    }


def _file_facts(paths: dict[str, str]) -> dict[str, dict[str, Any]]:
    facts: dict[str, dict[str, Any]] = {}
    for role, relative in paths.items():
        path = ROOT / relative
        facts[role] = {
            "path": relative,
            "exists": path.is_file(),
            "sha256": _sha256(path) if path.is_file() else "",
        }
    return facts


def _mode_allows_untracked(mode: str, *, dry_run: bool) -> bool:
    return _mode_is_observation(mode, dry_run=dry_run)


def _mode_is_observation(mode: str, *, dry_run: bool) -> bool:
    return dry_run or mode in {"doctor", "list", "dry-run"}


def _emulator_tool_required(mode: str, *, dry_run: bool) -> bool:
    return not _mode_is_observation(mode, dry_run=dry_run)


def _materialization_issue(mode: str, *, dry_run: bool, allow_untracked: bool) -> str:
    if allow_untracked or _mode_allows_untracked(mode, dry_run=dry_run):
        return ""
    untracked = _git_lines("ls-files", "--others", "--exclude-standard")
    if not untracked:
        return ""
    preview = ", ".join(untracked[:UNTRACKED_PREVIEW_LIMIT])
    suffix = ""
    if len(untracked) > UNTRACKED_PREVIEW_LIMIT:
        suffix = f", ... (+{len(untracked) - UNTRACKED_PREVIEW_LIMIT} more)"
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
    if provider == "github":
        tool = "act"
        paths = _provider_paths(provider)
        command = ["act", "-W", paths["config"], "workflow_dispatch", "--list"]
        output_dir = ROOT / "build/evidence/local-ci/github"
        hosted_flags = {
            "hosted_github_status_claimed": False,
            "hosted_gitlab_status_claimed": False,
        }
        evidence_class = "local_github_emulator"
    elif provider == "gitlab":
        tool = "gitlab-ci-local"
        paths = _provider_paths(provider)
        command = [
            "gitlab-ci-local",
            "--file",
            paths["config"],
            "--state-dir",
            "build/runtime/work/gitlab-ci-local",
            "--list",
        ]
        output_dir = ROOT / "build/evidence/local-ci/gitlab"
        hosted_flags = {
            "hosted_github_status_claimed": False,
            "hosted_gitlab_status_claimed": False,
        }
        evidence_class = "local_gitlab_emulator"
    else:
        message = f"unknown provider: {provider}"
        raise SystemExit(message)

    output_path = output or output_dir / f"{mode}.json"
    started_at = datetime.now(UTC)
    git_start = _git_summary()
    issue = _materialization_issue(mode, dry_run=dry_run, allow_untracked=allow_untracked)
    run = (
        {"returncode": 1, "ok": False, "stdout": "", "stderr": issue}
        if issue
        else _run_command(
            command,
            dry_run=dry_run,
            tool_required=_emulator_tool_required(mode, dry_run=dry_run),
        )
    )
    finished_at = datetime.now(UTC)
    git_end = _git_summary()
    executable = shutil.which(tool)
    head_stable = git_start["head"] == git_end["head"]
    payload: dict[str, Any] = {
        "schema_version": 1,
        "kind": evidence_class,
        "provider": provider,
        "mode": mode,
        "ok": bool(run["ok"]) and head_stable,
        "dry_run": dry_run,
        "head": git_end["head"],
        "head_start": git_start["head"],
        "head_end": git_end["head"],
        "head_stable": head_stable,
        "dirty": git_end["dirty"],
        "git_start": git_start,
        "git_end": git_end,
        "generated_at": finished_at.isoformat(),
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "tool": tool,
        "tool_available": executable is not None,
        "tool_path": executable or "",
        **paths,
        "files": _file_facts(paths),
        "command": command,
        "returncode": run["returncode"],
        "stdout": str(run["stdout"])[-4000:],
        "stderr": str(run["stderr"])[-4000:],
        "materialization": {
            "mode_allows_untracked": _mode_allows_untracked(mode, dry_run=dry_run),
            "normal_run_refuses_untracked_by_default": True,
            "untracked_allowed": allow_untracked,
            "untracked_policy": "refuse_before_emulator_run",
            "issue": issue,
        },
        "claim_boundary": "local provider emulator evidence only; not hosted provider status",
        **hosted_flags,
    }
    _write_evidence(output_path, payload)
    sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0 if payload["ok"] else int(run["returncode"] or 1)


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
    mode: str = "list",
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
