from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tomllib
from pathlib import Path

from ethos.repository.evidence.hosted.core import FLAGS
from ethos.repository.evidence.hosted.core import observation_summary
from tests.support.architecture import tool_block

ROOT = Path(__file__).resolve().parents[2]
RUNNER = "tools/ci/scripts/run-hosted-provider-observation.sh"


def _fake(path: Path, payload: list[dict[str, str]], target_env: str) -> None:
    script = (
        "#!/usr/bin/env python3\nimport json, os, sys\n"
        f"assert sys.argv[sys.argv.index('--repo') + 1] == os.environ[{target_env!r}]\n"
        f"print(json.dumps({payload!r}))\n"
    )
    path.write_text(script, encoding="utf-8")
    path.chmod(0o755)


def _fake_raw(path: Path, stdout: str) -> None:
    path.write_text(f"#!/usr/bin/env python3\nprint({stdout!r})\n", encoding="utf-8")
    path.chmod(0o755)


def _execute(
    tmp_path: Path, env: dict[str, str], *, expected_returncode: int = 0
) -> dict[str, object]:
    output = tmp_path / "observation.json"
    command = [
        sys.executable,
        "tools/ci/hosted_observation.py",
        "--execute",
        "--output",
        output.as_posix(),
    ]
    completed = subprocess.run(
        command, cwd=ROOT, env=env, check=False, capture_output=True, text=True
    )
    assert completed.returncode == expected_returncode
    return json.loads(output.read_text(encoding="utf-8"))


def test_hosted_observation_policy_dry_run_and_owner_surfaces() -> None:
    config = tomllib.loads((ROOT / ".config/checks/ci/hosted-observation.toml").read_text())
    assert config["providers"] == ["github", "gitlab"]
    assert [config["provider"][name]["repository_target_env"] for name in config["providers"]] == [
        "ETHOS_HOSTED_GITHUB_REPO",
        "ETHOS_HOSTED_GITLAB_REPO",
    ]
    payload = json.loads(
        subprocess.run([RUNNER], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    )
    assert payload["state"] == "dry_run"
    assert payload["ok"] is True
    assert payload["observation_gaps"] == []
    assert all(payload[key] is False for key in FLAGS)
    assert all(item["executed"] is False for item in payload["observations"])

    block = tool_block(ROOT, "hosted_provider_observation")
    projections = (ROOT / ".github/workflows/ci.yml").read_text() + (
        ROOT / ".gitlab-ci.yml"
    ).read_text()
    assert f'gate = "{RUNNER}"' in block and "planned = true" not in block  # noqa: PT018
    assert (ROOT / RUNNER).stat().st_mode & stat.S_IXUSR
    assert RUNNER in projections
    assert RUNNER in (ROOT / ".config/checks/ci/templates.toml").read_text()
    assert RUNNER in (ROOT / "docs/reference/runbook-registry.md").read_text()


def test_execute_mode_uses_explicit_targets_and_normalizes_facts(
    tmp_path: Path,
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    payloads = {
        "gh": [
            {
                "status": "completed",
                "conclusion": "success",
                "headSha": "abc",
                "url": "gh",
            }
        ],
        "glab": [{"status": "success", "sha": "abc", "ref": "dev", "web_url": "gl"}],
    }
    targets = {
        "ETHOS_HOSTED_GITHUB_REPO": "example/ethos",
        "ETHOS_HOSTED_GITLAB_REPO": "group/ethos",
    }
    _fake(bin_dir / "gh", payloads["gh"], "ETHOS_HOSTED_GITHUB_REPO")
    _fake(bin_dir / "glab", payloads["glab"], "ETHOS_HOSTED_GITLAB_REPO")
    env = os.environ | targets | {"PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}

    payload = _execute(tmp_path, env)
    observations = {item["provider"]: item for item in payload["observations"]}

    assert (  # noqa: PT018
        payload["state"] == "observed" and payload["ok"] and not payload["observation_gaps"]
    )
    assert observations["github"]["command"][3:5] == ["--repo", "example/ethos"]
    assert observations["gitlab"]["command"][3:5] == ["--repo", "group/ethos"]
    assert observations["github"]["provider_facts"]["latest_head"] == "abc"
    assert observations["gitlab"]["provider_facts"]["latest_ref"] == "dev"
    for stdout in ("not-json", '{"status": "success"}'):
        _fake_raw(bin_dir / "gh", stdout)
        failed = _execute(tmp_path, env, expected_returncode=1)
        github = next(item for item in failed["observations"] if item["provider"] == "github")
        assert github["observation_state"] == "observation_failed"
        assert failed["observation_gaps"] == ["provider_output_invalid:github"]


def test_execute_mode_does_not_run_unconfigured_providers(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name in ("gh", "glab"):
        (bin_dir / name).write_text("#!/bin/sh\nexit 97\n", encoding="utf-8")
        (bin_dir / name).chmod(0o755)
    env = os.environ | {"PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}
    env.pop("ETHOS_HOSTED_GITHUB_REPO", None)
    env.pop("ETHOS_HOSTED_GITLAB_REPO", None)

    payload = _execute(tmp_path, env, expected_returncode=1)

    assert (payload["state"], payload["ok"]) == ("not_configured", False)
    assert payload["observation_gaps"] == [
        "provider_not_configured:github",
        "provider_not_configured:gitlab",
    ]
    assert all(item["executed"] is False for item in payload["observations"])


def test_observation_summary_fails_closed() -> None:
    cases = [
        (["observed", "observed"], ("observed", True)),
        (["observed", "not_configured"], ("partial", False)),
        (["observed", "observation_failed"], ("partial", False)),
        (["observation_failed", "observation_failed"], ("observation_failed", False)),
        (["tool_unavailable", "not_configured"], ("observation_failed", False)),
        ([], ("observation_failed", False)),
    ]
    for states, expected in cases:
        observations = [
            {"provider": provider, "observation_state": state}
            for provider, state in zip(("github", "gitlab"), states, strict=False)
        ]
        state, _gaps, ok = observation_summary(observations, execute=True)
        assert (state, ok) == expected
