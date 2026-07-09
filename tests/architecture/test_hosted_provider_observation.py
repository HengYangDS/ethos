from __future__ import annotations

import json
import stat
import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _tool_block(concern: str) -> str:
    text = (ROOT / "system" / "tools.toml").read_text(encoding="utf-8")
    marker = f'concern = "{concern}"'
    assert marker in text
    before, after = text.split(marker, 1)
    block_start = before.rfind("[[tool]]")
    next_block = after.find("[[tool]]")
    body = marker + (after if next_block == -1 else after[:next_block])
    return before[block_start:] + body


def test_hosted_provider_observation_dry_run_is_observation_only() -> None:
    config = tomllib.loads((ROOT / ".config/checks/ci/hosted-observation.toml").read_text())
    assert config["providers"] == ["github", "gitlab"]
    assert "repository proof passed" in config["boundary"]["not_claimed"]

    result = subprocess.run(
        ["tools/ci/scripts/run-hosted-provider-observation.sh"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    persisted = json.loads((ROOT / "build/evidence/hosted-ci/observation.json").read_text())

    assert payload == persisted
    assert payload["kind"] == "ethos_hosted_provider_observation"
    assert payload["state"] == "dry_run"
    assert payload["hosted_github_status_claimed"] is False
    assert payload["hosted_gitlab_status_claimed"] is False
    assert payload["remote_publication_claimed"] is False
    assert {item["provider"] for item in payload["observations"]} == {"github", "gitlab"}
    assert all(item["executed"] is False for item in payload["observations"])


def test_hosted_provider_observation_has_owner_surfaces() -> None:
    gate = "tools/ci/scripts/run-hosted-provider-observation.sh"
    block = _tool_block("hosted_provider_observation")
    combined_ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8") + (
        ROOT / ".gitlab-ci.yml"
    ).read_text(encoding="utf-8")
    template_config = (ROOT / ".config/checks/ci/templates.toml").read_text(encoding="utf-8")
    runbook = (ROOT / "docs/reference/runbook-registry.md").read_text(encoding="utf-8")

    assert f'gate = "{gate}"' in block
    assert "planned = true" not in block
    assert (ROOT / gate).stat().st_mode & stat.S_IXUSR
    assert gate in combined_ci
    assert gate in template_config
    assert gate in runbook
