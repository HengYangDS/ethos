from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_CONFIG = ROOT / ".config/checks/ci/templates.toml"


def _template_config() -> dict[str, object]:
    return tomllib.loads(TEMPLATE_CONFIG.read_text(encoding="utf-8"))


def _projection_entries() -> list[dict[str, object]]:
    entries = _template_config()["projection"]
    assert isinstance(entries, list)
    return entries


def _tool_block(concern: str) -> str:
    text = (ROOT / "system/tools.toml").read_text(encoding="utf-8")
    marker = f'concern = "{concern}"'
    assert marker in text
    before, after = text.split(marker, 1)
    block_start = before.rfind("[[tool]]")
    next_block = after.find("[[tool]]")
    body = marker + (after if next_block == -1 else after[:next_block])
    return before[block_start:] + body


def test_hosted_provider_templates_are_projection_sources() -> None:
    providers = {str(entry["provider"]): entry for entry in _projection_entries()}

    assert set(providers) == {"github", "gitlab"}
    assert providers["github"]["template"] == ".config/ci/templates/hosted/github-actions.yml"
    assert providers["github"]["projection"] == ".github/workflows/ci.yml"
    assert providers["gitlab"]["template"] == ".config/ci/templates/hosted/gitlab-ci.yml"
    assert providers["gitlab"]["projection"] == ".gitlab-ci.yml"

    for entry in providers.values():
        template = ROOT / str(entry["template"])
        projection = ROOT / str(entry["projection"])
        emulator = ROOT / str(entry["local_emulator"])
        assert template.is_file()
        assert projection.is_file()
        assert emulator.is_file()
        assert template.read_bytes() == projection.read_bytes()


def test_provider_yaml_invokes_owner_scripts_not_inline_policy() -> None:
    required_scripts = {
        "tools/ci/scripts/bootstrap-python.sh",
        "tools/ci/scripts/run-python-lint.sh",
        "tools/ci/scripts/run-config-lint.sh",
        "tools/ci/scripts/run-shell-lint.sh",
        "tools/ci/scripts/run-markdown-lint.sh",
        "tools/ci/scripts/run-prose-check.sh",
        "tools/ci/scripts/run-import-linter.sh",
        "tools/ci/scripts/run-dependency-hygiene.sh",
        "tools/ci/scripts/run-docstring-coverage.sh",
        "tools/ci/scripts/run-module-layout.sh",
        "tools/ci/scripts/run-bandit.sh",
        "tools/ci/scripts/run-python-vulnerability-audit.sh",
        "tools/ci/scripts/run-repository-hygiene.sh",
        "tools/ci/scripts/run-product-boundary.sh",
        "tools/ci/scripts/run-secrets-scan.sh",
        "tools/ci/scripts/run-python-tests.sh",
        "tools/ci/scripts/run-ci-template-check.sh",
        "tools/ci/scripts/run-json-schema-check.sh",
        "tools/ci/scripts/run-hosted-provider-observation.sh",
    }
    github = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    gitlab = (ROOT / ".gitlab-ci.yml").read_text(encoding="utf-8")
    combined = github + "\n" + gitlab

    for script in required_scripts:
        assert script in combined
        mode = (ROOT / script).stat().st_mode
        assert mode & stat.S_IXUSR

    assert "tools/ci/scripts/run-actionlint.sh" in github
    assert "tools/ci/scripts/run-actionlint.sh" in gitlab
    assert "tools/ci/scripts/run-product-boundary.sh" in github
    assert "tools/ci/scripts/run-product-boundary.sh" in gitlab
    assert "uv run --group dev pytest tests/unit tests/architecture -q" not in combined
    assert "uv run --no-project --with import-linter lint-imports" not in combined
    assert "image: node:24" not in combined
    assert "hosted_github_status_claimed=true" not in combined
    assert "hosted_gitlab_status_claimed=true" not in combined


def test_ci_template_check_reports_projection_drift_as_json() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "tools/ci/ci_templates.py",
            "check-templates",
            "--json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)

    assert payload["kind"] == "ethos_ci_template_consistency"
    assert payload["ok"] is True
    assert {item["provider"] for item in payload["projections"]} == {"github", "gitlab"}
    assert all(item["projection_matches_template"] for item in payload["projections"])


def test_local_emulator_wrappers_emit_non_claim_evidence_in_dry_run() -> None:
    env = os.environ.copy()
    env["ETHOS_LOCAL_EMULATOR_DRY_RUN"] = "1"

    for script, provider, output_dir in [
        (
            "tools/ci/scripts/run-github-local-emulator.sh",
            "github",
            "build/evidence/local-ci/github",
        ),
        (
            "tools/ci/scripts/run-gitlab-local-emulator.sh",
            "gitlab",
            "build/evidence/local-ci/gitlab",
        ),
    ]:
        result = subprocess.run(
            [script, "doctor"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        payload = json.loads(result.stdout)
        evidence_path = ROOT / output_dir / "doctor.json"
        persisted = json.loads(evidence_path.read_text(encoding="utf-8"))

        assert payload == persisted
        assert payload["provider"] == provider
        assert payload["dry_run"] is True
        assert payload["hosted_github_status_claimed"] is False
        assert payload["hosted_gitlab_status_claimed"] is False
        assert "local provider emulator evidence only" in payload["claim_boundary"]


def test_tool_catalog_distinguishes_active_provider_gates_from_planned_adapters() -> None:
    active = {
        "ci_template_consistency": "tools/ci/scripts/run-ci-template-check.sh",
        "github_workflow_syntax": "tools/ci/scripts/run-actionlint.sh",
        "github_local_emulator": "tools/ci/scripts/run-github-local-emulator.sh",
        "gitlab_local_emulator": "tools/ci/scripts/run-gitlab-local-emulator.sh",
        "hosted_provider_observation": "tools/ci/scripts/run-hosted-provider-observation.sh",
    }
    for concern, gate in active.items():
        block = _tool_block(concern)
        assert f'gate = "{gate}"' in block
        assert "planned = true" not in block
        assert "adapter_only = true" not in block

    for concern in [
        "nox_runner_adapter",
        "pixi_environment_adapter",
        "pants_graph_adapter",
        "task_ledger_adapter",
        "agent_method_pack_adapter",
    ]:
        block = _tool_block(concern)
        assert "planned = true" in block

    for concern in [
        "nox_runner_adapter",
        "pixi_environment_adapter",
        "pants_graph_adapter",
        "task_ledger_adapter",
        "agent_method_pack_adapter",
    ]:
        block = _tool_block(concern)
        assert "adapter_only = true" in block
