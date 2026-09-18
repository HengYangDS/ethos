"""Hosted projections retain native policy and evidence transport boundaries."""

from __future__ import annotations

import os
import re
import shlex
import tomllib
from pathlib import Path

import pytest
import yaml

from ethos.adapters.process import run_command
from tools.ci.ci_projection import check_templates
from tools.ci.ci_projection import projection_entries

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def github():
    """Read the frozen provider source once; parity is checked independently."""
    return yaml.safe_load((ROOT / ".config/ci/templates/hosted/github-actions.yml").read_text())


@pytest.fixture(scope="module")
def gitlab():
    """Read the frozen GitLab projection source once."""
    return yaml.safe_load((ROOT / ".config/ci/templates/hosted/gitlab-ci.yml").read_text())


def _range_coordinates(command: str) -> tuple[str, ...]:
    arguments = shlex.split(command)
    assert arguments[:6] == ["uv", "run", "--frozen", "--offline", "ethos", "hook"]
    assert arguments[6] == "commit-range"
    assert arguments[-3:] == ["--root", ".", "--json"]
    options = arguments[7:-3]
    assert options[::2] == ["--target-ref", "--proposed-head", "--remote-head", "--remote"]
    return tuple(options[1::2])


def test_dual_forge_projections_equal_their_declared_templates(github, gitlab) -> None:
    assert {item["provider"] for item in projection_entries()} == {"github", "gitlab"}
    assert check_templates(json_output=False) == 0
    jobs = {name: github["jobs"][name] for name in ("quality", "verify", "package")}
    steps = [step for job in jobs.values() for step in job["steps"]]
    commands = [step.get("run", "") for step in steps]
    assert commands.count("tools/ci/scripts/bootstrap-python.sh") == 1
    assert commands.count("tools/ci/scripts/run-head-bound-proof.sh") == 1
    assert sum("actions/checkout@" in step.get("uses", "") for step in steps) == 1
    assert not any(
        " -m nox -s build" in command or " -m nox -s supply_chain" in command
        for command in commands
    )
    assert not {
        "ETHOS_TEST_WORKERS",
        "ETHOS_TEST_TIMEOUT_SECONDS",
        "ETHOS_TEST_TIMEOUT_METHOD",
    }.intersection(github["jobs"]["quality"].get("env", {}))
    upload = next(step for step in steps if step.get("name") == "Upload proof receipt")
    junit = "build/evidence/quality/tests/pytest/junit*.xml"
    assert junit in upload["with"]["path"]
    assert upload.get("if") == "always()"
    artifacts = gitlab["ethos:verify"]["artifacts"]
    assert artifacts["when"] == "always"
    assert "build/evidence/quality/tests/pytest/junit*.xml" in artifacts["paths"]
    assert artifacts["reports"]["junit"] == "build/evidence/quality/tests/pytest/junit*.xml"
    assert artifacts["reports"]["coverage_report"] == {
        "coverage_format": "cobertura",
        "path": "build/evidence/quality/tests/coverage/coverage.xml",
    }


@pytest.mark.parametrize("provider", ["github", "gitlab"])
def test_provider_commands_use_shared_owners_without_activating_mutation(provider) -> None:
    entry = next(item for item in projection_entries() if item["provider"] == provider)
    text = (ROOT / entry["template"]).read_text()
    assert "tools/ci/scripts/run-head-bound-proof.sh" in text
    assert "tools/ci/scripts/configure-git-checkout.sh" not in text
    assert "ethos hook install" not in text
    assert "\n    - openspec validate" not in text
    if provider == "gitlab":
        assert "uv run --frozen --offline python -m nox -s format_check" in text
        assert "uv run --frozen --offline python -m nox -s build" in text
        assert "node_modules/.bin/openspec validate --all --strict --json" in text


@pytest.mark.parametrize(
    ("job", "name"), [("verify", "repository proof"), ("package", "package artifacts")]
)
def test_required_github_checks_project_only_successful_execution(github, job, name) -> None:
    projected = github["jobs"][job]
    assert projected["name"] == name
    assert projected["needs"] == "quality"
    assert projected["if"] == "${{ always() }}"
    assert len(projected["steps"]) == 1
    step = projected["steps"][0]
    assert step["env"] == {"QUALITY_RESULT": "${{ needs.quality.result }}"}
    for result in ("success", "failure", "cancelled", "skipped", ""):
        observed = run_command(
            ROOT,
            ("bash", "-c", step["run"]),
            env=os.environ | {"QUALITY_RESULT": result},
            timeout=5,
        )
        assert (observed.returncode == 0) == (result == "success")


def test_integration_events_transport_exact_commit_range_coordinates(github, gitlab) -> None:
    github_steps = {
        step["name"]: step
        for step in github["jobs"]["quality"]["steps"]
        if isinstance(step, dict) and "name" in step
    }

    assert [
        (github_steps[name]["if"], _range_coordinates(github_steps[name]["run"]))
        for name in ("Admit pushed commit range", "Admit pull request commit range")
    ] == [
        (
            "github.event_name == 'push'",
            ("${{ github.ref }}", "${{ github.sha }}", "${{ github.event.before }}", "origin"),
        ),
        (
            "github.event_name == 'pull_request'",
            (
                "refs/heads/${{ github.event.pull_request.base.ref }}",
                "${{ github.event.pull_request.head.sha }}",
                "${{ github.event.pull_request.base.sha }}",
                "origin",
            ),
        ),
    ]

    gitlab_job = gitlab["ethos:commit-policy"]
    assert gitlab_job["variables"] == {"GIT_STRATEGY": "clone"}
    rules = gitlab_job["rules"]
    assert [tuple(rule.get("variables", {}).values()) for rule in rules] == [
        ("refs/heads/${CI_COMMIT_BRANCH}", "${CI_COMMIT_SHA}", "${CI_COMMIT_BEFORE_SHA}"),
        (
            "refs/heads/${CI_MERGE_REQUEST_TARGET_BRANCH_NAME}",
            "${CI_MERGE_REQUEST_SOURCE_BRANCH_SHA}",
            "${CI_MERGE_REQUEST_TARGET_BRANCH_SHA}",
        ),
        (
            "refs/heads/${CI_MERGE_REQUEST_TARGET_BRANCH_NAME}",
            "${CI_COMMIT_SHA}",
            "${CI_MERGE_REQUEST_DIFF_BASE_SHA}",
        ),
        (),
    ]
    assert rules[-1] == {"when": "never"}
    assert _range_coordinates(gitlab_job["script"][0]) == (
        "${ETHOS_COMMIT_TARGET_REF}",
        "${ETHOS_COMMIT_PROPOSED_HEAD}",
        "${ETHOS_COMMIT_REMOTE_HEAD}",
        "origin",
    )

    provider_text = yaml.safe_dump({"github": github, "gitlab": gitlab})
    assert "rev-list" not in provider_text
    assert "subject_pattern" not in provider_text


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


def test_host_conformance_receives_native_python_supply_before_activation(github, gitlab) -> None:
    github_job = github["jobs"]["host-conformance"]
    github_steps = github_job["steps"]
    setup_uv = next(
        step for step in github_steps if str(step.get("uses", "")).startswith("astral-sh/setup-uv@")
    )
    commands = [str(step.get("run", "")) for step in github_steps]

    assert all(
        not str(step.get("uses", "")).startswith("actions/setup-python@") for step in github_steps
    )
    assert github_job["env"]["UV_PYTHON_INSTALL_DIR"] == (
        "${{ github.workspace }}/build/runtime/python"
    )
    assert setup_uv["with"]["python-version"] == "${{ matrix.python }}"
    assert commands.index("uv python install --no-bin ${{ matrix.python }}") < commands.index(
        "uv sync --locked --group dev"
    )
    assert commands.index("uv sync --locked --group dev") < commands.index(
        "uv run --frozen python -m nox -s host_conformance"
    )

    gitlab_job = gitlab["ethos:host-conformance"]
    assert gitlab_job["stage"] == "verify"
    assert gitlab_job["script"] == ["uv run --frozen --offline python -m nox -s host_conformance"]
    assert gitlab_job["image"].startswith("ghcr.io/astral-sh/uv:")
    assert "@sha256:" in gitlab_job["image"]


def test_full_proof_owns_github_workflow_syntax_before_hosted_execution() -> None:
    declaration = tomllib.loads((ROOT / "system/gates.toml").read_text(encoding="utf-8"))
    full = declaration["proof_sets"]["full"]
    gates = {gate["id"]: gate for gate in declaration["gates"]}

    assert full.count("github-workflow-syntax") == 1
    gate = gates["github-workflow-syntax"]
    assert gate["command"] == ["tools/ci/scripts/run-actionlint.sh"]
    assert gate["depends_on"] == ["config-quality"]
    assert gate["writes_files"] is True
    assert gate["network_policy"] == "required"


def test_github_action_pins_are_unique_full_commit_ids() -> None:
    github = (ROOT / ".config/ci/templates/hosted/github-actions.yml").read_text(encoding="utf-8")
    pins: dict[str, set[str]] = {}
    for action, commit in re.findall(r"uses:\s+([^@\s]+)@([0-9a-f]+)", github):
        pins.setdefault(action, set()).add(commit)
    assert pins
    assert all(len(commits) == 1 for commits in pins.values())
    assert all(len(commit) == 40 for commits in pins.values() for commit in commits)
