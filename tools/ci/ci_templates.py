from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tomllib
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / ".config/checks/ci/templates.toml"


def _git_head() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def _git_dirty() -> bool:
    result = subprocess.run(
        ["git", "status", "--short"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return bool(result.stdout.strip()) if result.returncode == 0 else True


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


def _run_command(command: list[str], *, dry_run: bool) -> tuple[int | None, bool]:
    if dry_run:
        return None, True
    if not command:
        return None, True
    if shutil.which(command[0]) is None:
        return 127, False
    result = subprocess.run(command, cwd=ROOT, check=False)
    return result.returncode, result.returncode == 0


def emulator_evidence(provider: str, *, mode: str, dry_run: bool, output: Path | None) -> int:
    if provider == "github":
        tool = "act"
        config = ".config/ci/emulators/act.yml"
        command = ["act", "-W", config, "workflow_dispatch", "--list"]
        output_dir = ROOT / "build/evidence/local-ci/github"
        hosted_flags = {
            "hosted_github_status_claimed": False,
            "hosted_gitlab_status_claimed": False,
        }
        evidence_class = "local_github_emulator"
    elif provider == "gitlab":
        tool = "gitlab-ci-local"
        config = ".config/ci/emulators/gitlab.yml"
        command = ["gitlab-ci-local", "--file", config, "--list"]
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
    returncode, ok = _run_command(command, dry_run=dry_run)
    executable = shutil.which(tool)
    payload: dict[str, Any] = {
        "schema_version": 1,
        "kind": evidence_class,
        "provider": provider,
        "mode": mode,
        "ok": ok,
        "dry_run": dry_run,
        "head": _git_head(),
        "dirty": _git_dirty(),
        "generated_at": datetime.now(UTC).isoformat(),
        "tool": tool,
        "tool_available": executable is not None,
        "tool_path": executable or "",
        "config": config,
        "projected_file": ".github/workflows/ci.yml" if provider == "github" else ".gitlab-ci.yml",
        "template_file": ".config/ci/templates/hosted/github-actions.yml"
        if provider == "github"
        else ".config/ci/templates/hosted/gitlab-ci.yml",
        "command": command,
        "returncode": returncode,
        "claim_boundary": "local provider emulator evidence only; not hosted provider status",
        **hosted_flags,
    }
    _write_evidence(output_path, payload)
    sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0 if ok else int(returncode or 1)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ETHOS CI projection and local emulator helpers.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    check = subparsers.add_parser("check-templates")
    check.add_argument("--json", action="store_true")

    emulator = subparsers.add_parser("emulator-evidence")
    emulator.add_argument("provider", choices=("github", "gitlab"))
    emulator.add_argument("--mode", default="list")
    emulator.add_argument("--dry-run", action="store_true")
    emulator.add_argument("--output", type=Path)

    args = parser.parse_args(argv)
    if args.command == "check-templates":
        return check_templates(json_output=args.json)
    if args.command == "emulator-evidence":
        return emulator_evidence(
            args.provider,
            mode=args.mode,
            dry_run=args.dry_run,
            output=args.output,
        )
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
