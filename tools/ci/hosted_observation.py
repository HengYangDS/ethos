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

from cyclopts import App

from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import git_stdout
from ethos.repository.evidence.hosted.core import FLAGS
from ethos.repository.evidence.hosted.core import observation_summary
from ethos.repository.evidence.hosted.core import provider_command
from ethos.repository.evidence.hosted.core import provider_facts
from ethos.repository.evidence.hosted.core import provider_output_valid

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / ".config/checks/ci/hosted-observation.toml"


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
    state, gaps, ok = observation_summary(observations, execute=execute)
    boundary = config.get("boundary", {})
    payload = {
        "schema_version": 1,
        "kind": "ethos_hosted_provider_observation",
        "ok": ok,
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
    return 0 if ok else 1


app = App(name="ethos-hosted-observation", default_command=capture_observation)


def main(argv: list[str] | None = None) -> int:
    try:
        app(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
