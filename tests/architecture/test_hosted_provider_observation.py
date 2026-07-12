from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tomllib
from pathlib import Path

from tests.support.architecture import tool_block

ROOT = Path(__file__).resolve().parents[2]


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
    block = tool_block(ROOT, "hosted_provider_observation")
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


def test_hosted_provider_observation_execute_mode_records_provider_facts(
    tmp_path: Path,
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    github_payload = json.dumps(
        [
            {
                "status": "completed",
                "conclusion": "success",
                "headSha": "abc123",
                "url": "https://github.example/run/1",
            }
        ]
    )
    gitlab_payload = json.dumps(
        [
            {
                "status": "success",
                "sha": "abc123",
                "ref": "dev",
                "web_url": "https://gitlab.example/pipelines/1",
            }
        ]
    )
    for name, payload in {"gh": github_payload, "glab": gitlab_payload}.items():
        executable = bin_dir / name
        executable.write_text(f"#!/usr/bin/env python3\nprint({payload!r})\n", encoding="utf-8")
        executable.chmod(0o755)
    output = tmp_path / "observation.json"
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"

    subprocess.run(
        [
            sys.executable,
            "tools/ci/hosted_observation.py",
            "--execute",
            "--output",
            output.as_posix(),
        ],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert payload["state"] == "observed"
    assert payload["execute"] is True
    assert payload["head"]
    assert payload["remote_url"]
    assert payload["hosted_github_status_claimed"] is False
    assert payload["hosted_gitlab_status_claimed"] is False
    observations = {item["provider"]: item for item in payload["observations"]}
    assert observations["github"]["provider_facts"] == {
        "latest_conclusion": "success",
        "latest_head": "abc123",
        "latest_status": "completed",
        "latest_url": "https://github.example/run/1",
    }
    assert observations["gitlab"]["provider_facts"] == {
        "latest_conclusion": "success",
        "latest_head": "abc123",
        "latest_ref": "dev",
        "latest_status": "success",
        "latest_url": "https://gitlab.example/pipelines/1",
    }
