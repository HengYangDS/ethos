from __future__ import annotations

import importlib.util
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


def _load_ci_templates_module():
    module_path = ROOT / "tools/ci/ci_templates.py"
    spec = importlib.util.spec_from_file_location("ethos_test_ci_templates", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def test_openspec_ci_supply_is_pinned_to_the_supported_release() -> None:
    bootstrap = (ROOT / "tools/ci/scripts/bootstrap-python.sh").read_text(encoding="utf-8")
    adopter_gitlab_template = (
        ROOT
        / "packages/ethos/src/ethos/repository/adoption/scaffold/template_files/ci/gitlab.yml.j2"
    ).read_text(encoding="utf-8")

    assert 'npx --yes @fission-ai/openspec@1.6.0 "$@"' in bootstrap
    assert "npm install -g @fission-ai/openspec@1.6.0" in adopter_gitlab_template


def test_markdown_lint_excludes_uv_cache_projection() -> None:
    config = (ROOT / ".config/checks/markdown/.markdownlint-cli2.yaml").read_text(encoding="utf-8")
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")

    assert '  - "build/runtime/tool-cache/uv/**"' in config
    assert "build/runtime/tool-cache/uv/" in gitignore


def test_actionlint_runner_uses_official_release_fallback_not_npm_package() -> None:
    script = (ROOT / "tools/ci/scripts/run-actionlint.sh").read_text(encoding="utf-8")
    policy = tomllib.loads(
        (ROOT / ".config/checks/github/actionlint.toml").read_text(encoding="utf-8")
    )

    assert policy["tool"]["source"] == "github-release"
    assert policy["tool"]["release_owner"] == "rhysd/actionlint"
    assert "github.com/rhysd/actionlint/releases/download" in script
    assert "npx --yes" not in script
    assert "actionlint@" not in script


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


def test_local_emulator_doctor_degrades_when_optional_tool_is_missing(
    monkeypatch,
) -> None:
    ci_templates = _load_ci_templates_module()
    monkeypatch.setattr(ci_templates.shutil, "which", lambda _: None)

    assert (
        ci_templates.emulator_evidence(
            "gitlab",
            mode="doctor",
            dry_run=False,
            allow_untracked=False,
            output=None,
        )
        == 0
    )
    payload = json.loads((ROOT / "build/evidence/local-ci/gitlab/doctor.json").read_text())

    assert payload["ok"] is True
    assert payload["tool_available"] is False
    assert payload["returncode"] == 127
    assert payload["stderr"] == "tool not found"
    assert payload["hosted_gitlab_status_claimed"] is False


def test_local_emulator_run_requires_optional_tool_when_materializing(
    monkeypatch, tmp_path
) -> None:
    ci_templates = _load_ci_templates_module()
    monkeypatch.setattr(ci_templates.shutil, "which", lambda _: None)

    output = tmp_path / "gitlab-run.json"
    assert (
        ci_templates.emulator_evidence(
            "gitlab",
            mode="run",
            dry_run=False,
            allow_untracked=True,
            output=output,
        )
        == 127
    )
    payload = json.loads(output.read_text())

    assert payload["ok"] is False
    assert payload["tool_available"] is False
    assert payload["returncode"] == 127
    assert payload["stderr"] == "tool not found"
    assert payload["materialization"]["mode_allows_untracked"] is False
    assert payload["materialization"]["untracked_allowed"] is True


def test_local_emulator_wrappers_do_not_require_optional_flag_environment() -> None:
    base_env = os.environ.copy()
    base_env.pop("ETHOS_LOCAL_EMULATOR_DRY_RUN", None)
    base_env.pop("ETHOS_LOCAL_EMULATOR_ALLOW_UNTRACKED", None)

    cases = [
        (
            "tools/ci/scripts/run-github-local-emulator.sh",
            {"ETHOS_LOCAL_EMULATOR_DRY_RUN": "1"},
            True,
        ),
        (
            "tools/ci/scripts/run-gitlab-local-emulator.sh",
            {},
            False,
        ),
    ]
    for script, extra_env, expected_dry_run in cases:
        env = base_env | extra_env
        result = subprocess.run(
            ["/bin/bash", script, "doctor"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        payload = json.loads(result.stdout)

        assert payload["dry_run"] is expected_dry_run
        assert "unbound variable" not in result.stderr
        assert payload["hosted_github_status_claimed"] is False
        assert payload["hosted_gitlab_status_claimed"] is False


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
            ["/bin/bash", script, "doctor"],
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
        assert payload["head_start"] == payload["head_end"] == payload["head"]
        assert payload["head_stable"] is True
        assert payload["git_start"]["changed_scope"]["untracked_count"] >= 0
        assert payload["git_end"]["changed_scope"]["untracked_preview_limit"] == 12
        assert payload["files"]["config"]["exists"] is True
        assert payload["files"]["projected_file"]["exists"] is True
        assert payload["files"]["template_file"]["exists"] is True
        assert payload["materialization"] == {
            "issue": "",
            "mode_allows_untracked": True,
            "normal_run_refuses_untracked_by_default": True,
            "untracked_allowed": False,
            "untracked_policy": "refuse_before_emulator_run",
        }
        assert payload["hosted_github_status_claimed"] is False
        assert payload["hosted_gitlab_status_claimed"] is False
        assert "local provider emulator evidence only" in payload["claim_boundary"]


def test_gitlab_emulator_runtime_state_stays_under_build_runtime() -> None:
    root_state = ROOT / ".gitlab-ci-local"
    if root_state.exists():
        for child in sorted(root_state.rglob("*"), reverse=True):
            if child.is_file() or child.is_symlink():
                child.unlink()
            elif child.is_dir():
                child.rmdir()
        root_state.rmdir()

    env = os.environ.copy()
    env["ETHOS_LOCAL_EMULATOR_DRY_RUN"] = "1"
    result = subprocess.run(
        ["/bin/bash", "tools/ci/scripts/run-gitlab-local-emulator.sh", "doctor"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)

    assert payload["provider"] == "gitlab"
    assert "--state-dir" in payload["command"]
    assert "build/runtime/work/gitlab-ci-local" in payload["command"]
    assert not root_state.exists()


def test_local_emulator_normal_run_refuses_untracked_materialization(
    monkeypatch, tmp_path: Path
) -> None:
    ci_templates = _load_ci_templates_module()
    monkeypatch.setattr(ci_templates, "ROOT", tmp_path)

    subprocess.run(["git", "init", "--quiet"], cwd=tmp_path, check=True)
    output = tmp_path / "github-run.json"
    untracked = tmp_path / "tests/provider-emulator-untracked.txt"
    untracked.parent.mkdir(parents=True, exist_ok=True)
    untracked.write_text("untracked\n", encoding="utf-8")

    result_code = ci_templates.emulator_evidence(
        "github",
        mode="run",
        dry_run=False,
        allow_untracked=False,
        output=output,
    )

    assert result_code == 1
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["ok"] is False
    assert payload["materialization"]["mode_allows_untracked"] is False
    assert payload["materialization"]["untracked_allowed"] is False
    assert (
        "provider materialization can omit untracked files" in payload["materialization"]["issue"]
    )
    assert "tests/provider-emulator-untracked.txt" in payload["materialization"]["issue"]
    assert payload["hosted_github_status_claimed"] is False
    assert payload["hosted_gitlab_status_claimed"] is False


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
