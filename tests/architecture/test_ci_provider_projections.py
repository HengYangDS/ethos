from __future__ import annotations

import re
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


def test_hosted_runtime_versions_are_checked_projections_of_native_owners() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    node = tomllib.loads((ROOT / ".config/checks/node/runtime.toml").read_text(encoding="utf-8"))
    github = (ROOT / ".config/ci/templates/hosted/github-actions.yml").read_text(encoding="utf-8")
    gitlab = (ROOT / ".config/ci/templates/hosted/gitlab-ci.yml").read_text(encoding="utf-8")
    uv_requirement = next(
        item for item in project["dependency-groups"]["dev"] if item.startswith("uv>=")
    )
    uv_version = uv_requirement.removeprefix("uv>=")

    assert set(re.findall(r'node-version: "([^"]+)"', github)) == {node["default_version"]}
    assert set(re.findall(r'^\s+- "(\d+\.\d+\.\d+)"$', gitlab, re.MULTILINE)) == set(
        node["compatibility_versions"]
    )
    assert set(re.findall(r'^\s+version: "([^"]+)"$', github, re.MULTILINE)) == {uv_version}
    images = set(re.findall(r"^\s*image:\s+(\S+)$", gitlab, re.MULTILINE))
    assert images == {
        next(
            str(entry["emulator_image"])
            for entry in projection_entries()
            if entry["provider"] == "gitlab"
        )
    }
    assert set(re.findall(r"ghcr\.io/astral-sh/uv:([^-@]+)-", gitlab)) == {uv_version}


def test_github_action_pins_are_unique_full_commit_ids() -> None:
    github = (ROOT / ".config/ci/templates/hosted/github-actions.yml").read_text(encoding="utf-8")
    pins: dict[str, set[str]] = {}
    for action, commit in re.findall(r"uses:\s+([^@\s]+)@([0-9a-f]+)", github):
        pins.setdefault(action, set()).add(commit)
    assert pins
    assert all(len(commits) == 1 for commits in pins.values())
    assert all(
        re.fullmatch(r"[0-9a-f]{40}", commit) for commits in pins.values() for commit in commits
    )
