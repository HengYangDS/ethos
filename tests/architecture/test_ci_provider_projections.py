from __future__ import annotations

import tomllib
from pathlib import Path

from tools.ci.ci_projection import check_templates
from tools.ci.ci_projection import projection_entries

ROOT = Path(__file__).resolve().parents[2]


def test_dual_forge_projections_equal_their_declared_templates() -> None:
    assert {item["provider"] for item in projection_entries()} == {"github", "gitlab"}
    assert check_templates(json_output=False) == 0


def test_provider_commands_use_locked_offline_registry_sessions() -> None:
    texts = [
        (ROOT / relative).read_text(encoding="utf-8")
        for relative in (".github/workflows/ci.yml", ".gitlab-ci.yml")
    ]
    assert all("uv run --frozen --offline python -m nox -s format_check" in text for text in texts)
    assert all("uv run --frozen --offline python -m nox -s build" in text for text in texts)
    assert "uv run --frozen --offline python -m nox -s tests" in texts[1]


def test_provider_emulators_are_digest_bound_and_fail_closed() -> None:
    config = tomllib.loads((ROOT / ".config/checks/ci/templates.toml").read_text(encoding="utf-8"))
    providers = {item["provider"]: item for item in config["projection"]}
    assert set(providers) == {"github", "gitlab"}
    assert all("@sha256:" in str(item["emulator_image"]) for item in providers.values())
    assert all(int(item["emulator_timeout_seconds"]) > 0 for item in providers.values())
