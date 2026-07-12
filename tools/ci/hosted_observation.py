from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tomllib
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any

from cyclopts import App

from ethos.adapters.repo.git import current_tracked_head

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / ".config/checks/ci/hosted-observation.toml"


def _git_remote_url() -> str:
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def _load_config() -> dict[str, Any]:
    return tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _provider_tool(provider: str) -> str:
    return {"github": "gh", "gitlab": "glab"}[provider]


def _status_command(provider: str) -> list[str]:
    if provider == "github":
        return ["gh", "run", "list", "--limit", "1", "--json", "status,conclusion,headSha,url"]
    if provider == "gitlab":
        return ["glab", "ci", "list", "--per-page", "1", "--output", "json"]
    raise ValueError(provider)


def _github_facts(stdout_json: Any) -> dict[str, Any]:
    if not isinstance(stdout_json, list) or not stdout_json:
        return {}
    latest = stdout_json[0]
    if not isinstance(latest, dict):
        return {}
    return {
        "latest_head": str(latest.get("headSha") or ""),
        "latest_status": str(latest.get("status") or ""),
        "latest_conclusion": str(latest.get("conclusion") or ""),
        "latest_url": str(latest.get("url") or ""),
    }


def _gitlab_facts(stdout_json: Any) -> dict[str, Any]:
    if not isinstance(stdout_json, list) or not stdout_json:
        return {}
    latest = stdout_json[0]
    if not isinstance(latest, dict):
        return {}
    ref = latest.get("ref")
    sha = latest.get("sha") or latest.get("commit_sha")
    web_url = latest.get("web_url") or latest.get("url")
    status = latest.get("status")
    return {
        "latest_head": str(sha or ""),
        "latest_status": str(status or ""),
        "latest_conclusion": str(status or ""),
        "latest_url": str(web_url or ""),
        "latest_ref": str(ref or ""),
    }


def _provider_facts(provider: str, stdout_json: Any) -> dict[str, Any]:
    if provider == "github":
        return _github_facts(stdout_json)
    if provider == "gitlab":
        return _gitlab_facts(stdout_json)
    raise ValueError(provider)


def _observe(provider: str, *, execute: bool) -> dict[str, Any]:
    tool = _provider_tool(provider)
    available = shutil.which(tool)
    command = _status_command(provider)
    record: dict[str, Any] = {
        "provider": provider,
        "tool": tool,
        "tool_available": available is not None,
        "tool_path": available or "",
        "command": command,
        "executed": False,
        "returncode": None,
        "stdout_json": None,
        "stdout_preview": "",
        "stderr_preview": "",
        "observation_state": "tool_unavailable" if available is None else "not_executed",
        "hosted_status_claimed": False,
        "provider_facts": {},
    }
    if not execute or available is None:
        return record
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    record["executed"] = True
    record["returncode"] = result.returncode
    record["stdout_preview"] = result.stdout[:2000]
    record["stderr_preview"] = result.stderr[:2000]
    try:
        record["stdout_json"] = json.loads(result.stdout) if result.stdout.strip() else None
    except json.JSONDecodeError:
        record["stdout_json"] = None
    record["provider_facts"] = _provider_facts(provider, record["stdout_json"])
    record["observation_state"] = "observed" if result.returncode == 0 else "observation_failed"
    return record


cli_app = App(
    name="ethos-hosted-observation",
    help="Capture hosted provider observation envelopes.",
)


@cli_app.default
def capture_observation(
    *,
    execute: bool = False,
    output: Path | None = None,
) -> int:
    """Capture provider observations without converting them into proof claims."""
    config = _load_config()
    providers = [str(provider) for provider in config.get("providers", [])]
    observations = [_observe(provider, execute=execute) for provider in providers]
    payload: dict[str, Any] = {
        "schema_version": 1,
        "kind": "ethos_hosted_provider_observation",
        "ok": True,
        "state": "observed" if execute else "dry_run",
        "head": current_tracked_head(ROOT),
        "remote_url": _git_remote_url(),
        "config": str(CONFIG_PATH.relative_to(ROOT)),
        "generated_at": datetime.now(UTC).isoformat(),
        "execute": execute,
        "evidence_class": config.get("boundary", {}).get(
            "evidence_class", "hosted_provider_observation"
        ),
        "claim_boundary": config.get("boundary", {}).get("claim", ""),
        "not_claimed": config.get("boundary", {}).get("not_claimed", []),
        "hosted_github_status_claimed": False,
        "hosted_gitlab_status_claimed": False,
        "remote_publication_claimed": False,
        "observations": observations,
    }
    output_path = ROOT / str(output or config["output"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the Cyclopts-backed hosted-observation command surface."""
    try:
        cli_app(argv)
    except SystemExit as exc:
        if isinstance(exc.code, int):
            return exc.code
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
