import json
import os
import shutil
import subprocess
import sys
import tomllib
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any
from typing import cast

from cyclopts import App

from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import git_stdout

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / ".config/checks/ci/hosted-observation.toml"
COMMANDS = {
    "github": ("gh", "run", "list", "--limit", "1", "--json", "status,conclusion,headSha,url"),
    "gitlab": ("glab", "ci", "list", "--per-page", "1", "--output", "json"),
}
FACTS = {
    "github": (
        ("latest_head", "headSha"),
        ("latest_status", "status"),
        ("latest_conclusion", "conclusion"),
        ("latest_url", "url"),
    ),
    "gitlab": (
        ("latest_head", "sha", "commit_sha"),
        ("latest_status", "status"),
        ("latest_conclusion", "status"),
        ("latest_url", "web_url", "url"),
        ("latest_ref", "ref"),
    ),
}
GAPS = {
    "not_configured": "provider_not_configured",
    "tool_unavailable": "provider_tool_unavailable",
    "observation_failed": "provider_observation_failed",
}
FLAGS = (
    "hosted_github_status_claimed",
    "hosted_gitlab_status_claimed",
    "remote_publication_claimed",
)


def provider_command(provider: str, target: str) -> list[str]:
    """Return one provider query bound to an explicit repository target."""
    command = list(COMMANDS[provider])
    if target:
        command[3:3] = ["--repo", target]
    return command


def provider_output_valid(value: object) -> bool:
    """Return whether provider output has the required non-empty list shape."""
    return isinstance(value, list) and bool(value) and isinstance(value[0], dict)


def provider_facts(provider: str, value: object) -> dict[str, str]:
    """Normalize bounded facts without claiming provider success."""
    if not provider_output_valid(value):
        return {}
    item = cast("list[dict[str, Any]]", value)[0]
    return {
        name: str(next((item.get(key) for key in keys if item.get(key)), ""))
        for name, *keys in FACTS[provider]
    }


def observation_summary(
    observations: list[dict[str, Any]], *, execute: bool
) -> tuple[str, str, list[str]]:
    """Derive aggregate state and verdict without minting provider authority."""
    if not execute:
        return "dry_run", "unknown", []
    if not observations:
        return "observation_failed", "unknown", ["provider_configuration_empty"]
    states = [str(item.get("observation_state") or "") for item in observations]
    gaps = []
    for item, state in zip(observations, states, strict=True):
        prefix = (
            "provider_output_invalid"
            if state == "observation_failed" and item.get("returncode") == 0
            else GAPS.get(state)
        )
        if prefix:
            gaps.append(f"{prefix}:{item.get('provider')}")
    observed = states.count("observed")
    state = (
        "observed"
        if observed == len(states)
        else "partial"
        if observed
        else "not_configured"
        if set(states) == {"not_configured"}
        else "observation_failed"
    )
    if state == "observed":
        verdict = "pass"
    elif state == "not_configured":
        verdict = "unknown"
    else:
        verdict = "block"
    return state, verdict, gaps


def _observe(provider: str, config: dict[str, Any], *, execute: bool) -> dict[str, Any]:
    tool = "gh" if provider == "github" else "glab"
    policy = config.get("provider", {}).get(provider, {})
    target_env = str(policy.get("repository_target_env") or "")
    target = os.environ.get(target_env, "").strip()
    tool_path = shutil.which(tool)
    state = (
        "not_configured" if not target else "tool_unavailable" if not tool_path else "not_executed"
    )
    record = {
        "provider": provider,
        "tool": tool,
        "tool_available": bool(tool_path),
        "tool_path": tool_path or "",
        "target_env": target_env,
        "target": target,
        "target_configured": bool(target),
        "command": provider_command(provider, target),
        "executed": False,
        "returncode": None,
        "stdout_json": None,
        "stdout_preview": "",
        "stderr_preview": "",
        "observation_state": state,
        "hosted_status_claimed": False,
        "provider_facts": {},
    }
    if not execute or state != "not_executed":
        return record
    run = subprocess.run(record["command"], cwd=ROOT, capture_output=True, text=True, check=False)
    try:
        stdout_json = json.loads(run.stdout) if run.stdout.strip() else None
    except json.JSONDecodeError:
        stdout_json = None
    record.update(
        executed=True,
        returncode=run.returncode,
        stdout_json=stdout_json,
        stdout_preview=run.stdout[:2000],
        stderr_preview=run.stderr[:2000],
        observation_state=(
            "observed"
            if run.returncode == 0 and provider_output_valid(stdout_json)
            else "observation_failed"
        ),
        provider_facts=provider_facts(provider, stdout_json),
    )
    return record


def capture_observation(*, execute: bool = False, output: Path | None = None) -> int:
    """Capture provider facts without converting them into repository proof."""
    config = tomllib.loads(CONFIG.read_text(encoding="utf-8"))
    providers = list(map(str, config.get("providers", [])))
    observations = [_observe(item, config, execute=execute) for item in providers]
    state, verdict, gaps = observation_summary(observations, execute=execute)
    boundary = config.get("boundary", {})
    payload = {
        "schema_version": 1,
        "kind": "ethos_hosted_provider_observation",
        "verdict": verdict,
        "state": state,
        "head": current_tracked_head(ROOT),
        "remote_url": git_stdout(ROOT, "remote", "get-url", "origin"),
        "config": str(CONFIG.relative_to(ROOT)),
        "generated_at": datetime.now(UTC).isoformat(),
        "execute": execute,
        "evidence_class": boundary.get("evidence_class", "hosted_provider_observation"),
        "claim_boundary": boundary.get("claim", ""),
        "not_claimed": boundary.get("not_claimed", []),
        "observation_gaps": gaps,
        "observation_gap_count": len(gaps),
        "observations": observations,
    } | dict.fromkeys(FLAGS, False)
    path = ROOT / str(output or config["output"])
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    path.write_text(rendered, encoding="utf-8")
    sys.stdout.write(rendered)
    return 0 if verdict == "pass" else 1


app = App(name="ethos-hosted-observation", default_command=capture_observation)


def main(argv: list[str] | None = None) -> int:
    try:
        app(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
