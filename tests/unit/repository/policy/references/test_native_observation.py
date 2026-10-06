"""Qualify native observation applicability independently of static coverage."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from tools.ci import hosted_observation

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize("configured", [False, True])
def test_hosted_observation_reads_only_a_configured_environment_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    *,
    configured: bool,
) -> None:
    """Missing provider configuration never attempts an empty environment lookup."""
    reads: list[str] = []
    getenv = hosted_observation.os.environ.get

    def observed_get(name: str, default: str | None = None) -> str | None:
        reads.append(name)
        return getenv(name, default)

    name = "TEST_HOSTED_REPOSITORY"
    config = tmp_path / "hosted-observation.toml"
    config.write_text(
        'providers = ["github"]\noutput = "observation.json"\n'
        + (f'[provider.github]\nrepository_target_env = "{name}"\n' if configured else ""),
        encoding="utf-8",
    )
    monkeypatch.setattr(hosted_observation, "ROOT", tmp_path)
    monkeypatch.setattr(hosted_observation, "CONFIG", config)
    monkeypatch.setenv(name, "owner/repo")
    monkeypatch.setattr(hosted_observation.os.environ, "get", observed_get)

    assert hosted_observation.capture_observation(execute=False) == 1

    payload = json.loads((tmp_path / "observation.json").read_text(encoding="utf-8"))
    assert json.loads(capsys.readouterr().out) == payload
    assert "" not in reads
    assert reads.count(name) == int(configured)
    assert payload["execute"] is False
    assert all(payload[flag] is False for flag in hosted_observation.FLAGS)
    assert payload["config"] == config.name
    assert len(payload["observations"]) == 1
    observed = payload["observations"][0]
    assert observed["executed"] is False
    assert observed["target_env"] == (name if configured else "")
    assert observed["target"] == ("owner/repo" if configured else "")
    expected = "not_executed" if observed["tool_available"] else "tool_unavailable"
    assert observed["observation_state"] == (expected if configured else "not_configured")
