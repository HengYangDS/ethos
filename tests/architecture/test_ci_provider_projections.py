from __future__ import annotations

import importlib.util
import json
import os
import stat
import subprocess
import sys
import tomllib
from pathlib import Path

import yaml

from tests.support.architecture import tool_block

# fmt: off

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_CONFIG = ROOT / ".config/checks/ci/templates.toml"


def _projection_entries() -> list[dict[str, object]]:
    entries = tomllib.loads(TEMPLATE_CONFIG.read_text(encoding="utf-8"))["projection"]
    assert isinstance(entries, list)
    return entries


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

    expected_emulation = {
        "github": {
            "emulator_tool": "act",
            "emulator_event": "workflow_dispatch",
            "emulator_job": "quality",
            "emulator_image": "catthehacker/ubuntu:act-latest",
        },
        "gitlab": {
            "emulator_tool": "gitlab-ci-local",
            "emulator_event": "pipeline",
            "emulator_job": "ethos:lint",
            "emulator_image": "python:3.12",
        },
    }
    for provider, entry in providers.items():
        template = ROOT / str(entry["template"])
        projection = ROOT / str(entry["projection"])
        assert template.is_file()
        assert projection.is_file()
        assert template.read_bytes() == projection.read_bytes()
        assert "local_emulator" not in entry
        for field, value in expected_emulation[provider].items():
            assert entry[field] == value
        assert entry.get("emulator_state_dir", "") == ""
        assert "PYTHONWARNINGS: error" in projection.read_text(encoding="utf-8")

    assert 'GIT_DEPTH: "0"' in (ROOT / ".gitlab-ci.yml").read_text(encoding="utf-8")


def test_remote_provider_ci_excludes_local_candidate_and_includes_submit() -> None:
    github = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    gitlab = (ROOT / ".gitlab-ci.yml").read_text(encoding="utf-8")

    assert "candidate/dev" not in github
    assert "submit/**" in github
    assert "workflow:" in gitlab
    assert 'CI_COMMIT_BRANCH == "dev"' in gitlab
    assert 'CI_COMMIT_BRANCH == "main"' in gitlab
    assert "submit\\/.+$" in gitlab


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
    assert (
        "uv build --all-packages --out-dir build/artifacts/python --clear --no-create-gitignore"
    ) in combined
    assert "uv run --group dev pytest tests/unit tests/architecture -q" not in combined
    assert "uv run --no-project --with import-linter lint-imports" not in combined
    assert "image: node:24" not in combined
    assert "hosted_github_status_claimed=true" not in combined
    assert "hosted_gitlab_status_claimed=true" not in combined


def test_gitlab_node_compatibility_matrix_projects_the_runtime_policy() -> None:
    providers = {str(entry["provider"]): entry for entry in _projection_entries()}
    runner = "tools/ci/scripts/run-node-compatibility.sh"
    policy = tomllib.loads((ROOT / ".config/checks/node/runtime.toml").read_text(encoding="utf-8"))
    gitlab_text = (ROOT / ".gitlab-ci.yml").read_text(encoding="utf-8")
    gitlab = yaml.safe_load(gitlab_text)
    npm_job = gitlab["ethos:npm"]
    npm_package_job = gitlab["ethos:npm-package"]
    matrix = npm_job["parallel"]["matrix"]

    assert runner in providers["gitlab"]["required_owner_scripts"]
    assert runner not in providers["github"]["required_owner_scripts"]
    assert matrix == [{"NODE_VERSION": policy["compatibility_versions"]}]
    assert npm_job["script"] == ["tools/ci/scripts/install-node.sh", runner]
    assert npm_package_job["script"][0] == "tools/ci/scripts/install-node.sh"
    assert runner not in npm_package_job["script"]
    assert "NODE_VERSION" not in npm_package_job
    assert "npm run test:npm" in npm_package_job["script"]

def test_github_repository_proof_projects_single_worker_stability() -> None:
    github = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))

    assert github["jobs"]["verify"]["env"] == {"ETHOS_TEST_WORKERS": "1"}
    expected_runner = ["self-hosted", "macOS", "ARM64", "${{ vars.ETHOS_GITHUB_RUNNER_LABEL }}"]

    assert github["jobs"]["quality"]["runs-on"] == expected_runner
    assert github["jobs"]["verify"]["runs-on"] == expected_runner
    assert github["jobs"]["package"]["runs-on"] == expected_runner
    gitlab = yaml.safe_load((ROOT / ".gitlab-ci.yml").read_text(encoding="utf-8"))

    assert gitlab["default"]["tags"] == ["${ETHOS_GITLAB_RUNNER_TAG}"]


def test_provider_python_producers_are_runtime_bound() -> None:
    runtime = "tools/ci/scripts/with-python-runtime.sh -- uv"
    provider_paths = [
        ".github/workflows/ci.yml",
        ".gitlab-ci.yml",
        "tools/ci/scripts/run-github-local-emulator.sh",
        "tools/ci/scripts/run-gitlab-local-emulator.sh",
    ]

    for relative_path in provider_paths:
        lines = (ROOT / relative_path).read_text(encoding="utf-8").splitlines()
        uv_producers = [line.strip() for line in lines if "uv run" in line or "uv build" in line]

        assert uv_producers, relative_path
        assert all(runtime in line for line in uv_producers), relative_path


def test_hosted_proof_receipt_is_owner_scripted_and_retained() -> None:
    runner = "tools/ci/scripts/run-head-bound-proof.sh"
    github = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    gitlab = yaml.safe_load((ROOT / ".gitlab-ci.yml").read_text(encoding="utf-8"))
    script = (ROOT / runner).read_text(encoding="utf-8")

    assert runner in github
    assert runner in gitlab["ethos:verify"]["script"]
    assert "ethos prove --execute --expect-head" not in github
    assert "ethos prove --execute --expect-head" not in "\n".join(gitlab["ethos:verify"]["script"])
    assert gitlab["ethos:verify"]["artifacts"] == {
        "when": "always",
        "paths": [
            "build/evidence/quality/proof/",
            "build/evidence/quality/readiness/",
        ],
    }
    assert "ethos audit --json" in script
    assert "ethos report --json" in script
    assert "ethos prove --execute --expect-head" in script
    assert "executed-proof.json" in script
    assert "ethos_hosted_readiness_receipt" in script
    assert (ROOT / runner).stat().st_mode & stat.S_IXUSR
    assert "proof_evidence_digest" in script


def test_local_ci_fails_on_python_warnings() -> None:
    assert "export PYTHONWARNINGS=error" in (
        ROOT / "tools/ci/scripts/run-local-ci.sh"
    ).read_text(encoding="utf-8")


def test_openspec_ci_supply_is_pinned_to_the_supported_release() -> None:
    bootstrap = (ROOT / "tools/ci/scripts/bootstrap-python.sh").read_text(encoding="utf-8")
    gitlab_projection = (ROOT / ".gitlab-ci.yml").read_text(encoding="utf-8")

    assert 'npx --yes @fission-ai/openspec@1.6.0 "$@"' in bootstrap
    assert "openspec --version" in gitlab_projection


def test_hosted_python_bootstrap_avoids_ambient_root_pip() -> None:
    bootstrap = (ROOT / "tools/ci/scripts/bootstrap-python.sh").read_text(encoding="utf-8")

    assert "python -m venv" in bootstrap
    assert "python -m pip install" not in bootstrap
    assert "pip install uv" not in bootstrap


def test_github_ci_uses_current_action_majors() -> None:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "actions/checkout@v7" in workflow
    assert "actions/setup-python@v6" in workflow
    assert "actions/upload-artifact@v7" in workflow


def test_hosted_python_bootstrap_materializes_the_source_bound_runtime() -> None:
    bootstrap = (ROOT / "tools/ci/scripts/bootstrap-python.sh").read_text(encoding="utf-8")

    tool_runtime = 'bootstrap_venv="${repo_root}/build/runtime/tool-cache/uv-bootstrap"'
    environment = 'export UV_PROJECT_ENVIRONMENT="${repo_root}/build/runtime/venv"'
    sync = "uv sync --all-packages --group dev"
    assert tool_runtime in bootstrap
    assert "build/runtime/bootstrap" not in bootstrap
    assert environment in bootstrap
    assert sync in bootstrap
    assert bootstrap.index(environment) < bootstrap.index(sync)


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


def test_local_emulator_run_executes_a_selected_formal_provider_job(monkeypatch, tmp_path) -> None:
    ci_templates = _load_ci_templates_module()
    commands: list[list[str]] = []
    execution_roots: list[Path] = []
    monkeypatch.setattr(
        ci_templates.shutil,
        "which",
        lambda tool: "/usr/local/bin/emulator" if tool in {"act", "gitlab-ci-local"} else None,
    )
    monkeypatch.setattr(ci_templates, "_tool_version", lambda tool: f"{tool} 1.0")
    monkeypatch.setattr(
        ci_templates,
        "materialize_emulator_source",
        lambda **kwargs: {"source_dir": str(kwargs["state_dir"] / "source")},
    )
    monkeypatch.setattr(
        ci_templates,
        "_run_command",
        lambda command, **_kwargs: (
            commands.append(command)
            or execution_roots.append(_kwargs["cwd"])
            or {"returncode": 0, "ok": True, "stdout": "executed", "stderr": ""}
        ),
    )

    expected = {
        "github": [
            "act",
            "workflow_dispatch",
            "-W",
            ".github/workflows/ci.yml",
            "-j",
            "quality",
        ],
        "gitlab": [
            "gitlab-ci-local",
            "--cwd",
            "build/runtime/work/gitlab-ci-local/source",
            "--file",
            ".gitlab-ci.yml",
            "--state-dir",
            "../state",
            "ethos:lint",
        ],
    }
    declared_images = {
        "github": "catthehacker/ubuntu:act-latest",
        "gitlab": "python:3.12",
    }
    for provider, command in expected.items():
        output = tmp_path / f"{provider}.json"
        assert (
            ci_templates.emulator_evidence(
                provider,
                mode="run",
                dry_run=False,
                allow_untracked=True,
                output=output,
            )
            == 0
        )
        payload = json.loads(output.read_text())
        assert payload["execution"] == {
            "formal_workflow": ".github/workflows/ci.yml"
            if provider == "github"
            else ".gitlab-ci.yml",
            "mode": "selected_job_execution",
            "selected_job": "quality" if provider == "github" else "ethos:lint",
        }
        assert payload["execution_environment"] == {
            "declared_image": declared_images[provider],
            "image_digest": "",
            "image_digest_status": "not_observed",
            "tool_version": f"{command[0]} 1.0",
        }

    assert commands == [expected["github"], expected["gitlab"]]
    assert execution_roots == [
        ROOT / "build/runtime/work/github-act/source",
        ROOT,
    ]


def test_local_emulator_run_fails_when_provider_logs_contain_warnings(
    monkeypatch, tmp_path: Path
) -> None:
    ci_templates = _load_ci_templates_module()
    entry = {
        "provider": "github",
        "projection": ".github/workflows/ci.yml",
        "template": ".config/ci/templates/hosted/github-actions.yml",
        "emulator_tool": "act",
        "emulator_event": "workflow_dispatch",
        "emulator_job": "quality",
        "emulator_image": "catthehacker/ubuntu:act-latest",
        "forbidden_log_patterns": ["(?:^|[ >])DeprecationWarning:"],
    }
    monkeypatch.setattr(ci_templates, "_provider_entry", lambda _provider: entry)
    monkeypatch.setattr(ci_templates.shutil, "which", {"act": "/usr/local/bin/act"}.get)
    monkeypatch.setattr(ci_templates, "_tool_version", lambda _tool: "act 1.0")
    monkeypatch.setattr(
        ci_templates,
        "materialize_emulator_source",
        lambda **kwargs: {"source_dir": str(kwargs["state_dir"] / "source")},
    )
    monkeypatch.setattr(
        ci_templates,
        "_run_command",
        lambda _command, **_kwargs: {
            "returncode": 0,
            "ok": True,
            "stdout": "(node:1) DeprecationWarning: stale action runtime",
            "stderr": "",
        },
    )

    output = tmp_path / "github-run.json"
    assert (
        ci_templates.emulator_evidence(
            "github",
            mode="run",
            dry_run=False,
            allow_untracked=True,
            output=output,
        )
        == 1
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["ok"] is False
    assert payload["log_warnings"] == ["(?:^|[ >])DeprecationWarning:"]


def test_local_emulator_run_ignores_declarative_warning_pattern_text(
    monkeypatch, tmp_path: Path
) -> None:
    ci_templates = _load_ci_templates_module()
    entry = {
        "provider": "github",
        "projection": ".github/workflows/ci.yml",
        "template": ".config/ci/templates/hosted/github-actions.yml",
        "emulator_tool": "act",
        "emulator_event": "workflow_dispatch",
        "emulator_job": "quality",
        "emulator_image": "catthehacker/ubuntu:act-latest",
        "forbidden_log_patterns": [
            "(?:^|[ >])DeprecationWarning:",
            "(?:^|[ >])WARNING:",
        ],
    }
    monkeypatch.setattr(ci_templates, "_provider_entry", lambda _provider: entry)
    monkeypatch.setattr(ci_templates.shutil, "which", {"act": "/usr/local/bin/act"}.get)
    monkeypatch.setattr(ci_templates, "_tool_version", lambda _tool: "act 1.0")
    monkeypatch.setattr(
        ci_templates,
        "materialize_emulator_source",
        lambda **kwargs: {"source_dir": str(kwargs["state_dir"] / "source")},
    )
    monkeypatch.setattr(
        ci_templates,
        "_run_command",
        lambda _command, **_kwargs: {
            "returncode": 0,
            "ok": True,
            "stdout": (
                '"forbidden_log_patterns": '
                '["(?:^|[ >])DeprecationWarning:", "(?:^|[ >])WARNING:"]'
            ),
            "stderr": "",
        },
    )

    output = tmp_path / "github-run.json"
    assert (
        ci_templates.emulator_evidence(
            "github",
            mode="run",
            dry_run=False,
            allow_untracked=True,
            output=output,
        )
        == 0
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["ok"] is True
    assert payload["log_warnings"] == []


def test_act_emulator_uses_docker_context_when_no_endpoint_is_explicit(
    monkeypatch, tmp_path: Path
) -> None:
    ci_templates = _load_ci_templates_module()
    environment: dict[str, str] = {}
    monkeypatch.delenv("DOCKER_HOST", raising=False)
    monkeypatch.setattr(ci_templates.shutil, "which", lambda _tool: "/usr/local/bin/tool")
    monkeypatch.setattr(
        ci_templates,
        "_docker_context_endpoint",
        lambda: "unix:///context/docker.sock",
    )
    monkeypatch.setattr(ci_templates, "_tool_version", lambda _tool: "act 1.0")
    monkeypatch.setattr(
        ci_templates,
        "_run_command",
        lambda _command, **kwargs: (
            environment.update(kwargs["env"])
            or {"returncode": 0, "ok": True, "stdout": "", "stderr": ""}
        ),
    )

    assert (
        ci_templates.emulator_evidence(
            "github",
            mode="run",
            dry_run=False,
            allow_untracked=True,
            output=tmp_path / "github-run.json",
        )
        == 0
    )

    assert environment["DOCKER_HOST"] == "unix:///context/docker.sock"


def test_github_emulator_run_materializes_an_independent_git_source(
    monkeypatch, tmp_path: Path
) -> None:
    ci_templates = _load_ci_templates_module()
    source_dir = tmp_path / "build/runtime/work/github-act/source"
    source_dir.mkdir(parents=True)
    entry = {
        "provider": "github",
        "projection": ".github/workflows/ci.yml",
        "template": ".config/ci/templates/hosted/github-actions.yml",
        "emulator_tool": "act",
        "emulator_event": "workflow_dispatch",
        "emulator_job": "quality",
        "emulator_image": "catthehacker/ubuntu:act-latest",
        "emulator_state_dir": "build/runtime/work/github-act",
    }
    summary = {
        "branch": "work/example",
        "head": "expected-head",
        "dirty": False,
        "status_short": "",
        "changed_scope": {
            "staged_paths": [],
            "unstaged_paths": [],
            "tracked_changed_paths": [],
            "untracked_count": 0,
            "untracked_preview": [],
            "untracked_preview_limit": 12,
        },
    }
    recorded: dict[str, object] = {}
    materialization = {
        "kind": "independent_git_checkout",
        "source_dir": str(source_dir),
        "source_head": "expected-head",
        "source_head_matches_expected": True,
        "git_directory_is_real": True,
        "uses_external_object_alternates": False,
        "tracked_diff_bytes": 0,
    }
    monkeypatch.setattr(ci_templates, "ROOT", tmp_path)
    monkeypatch.setattr(ci_templates, "_provider_entry", lambda _provider: entry)
    monkeypatch.setattr(ci_templates.shutil, "which", lambda _tool: "/usr/local/bin/act")
    monkeypatch.setattr(ci_templates, "_docker_context_endpoint", lambda: "")
    monkeypatch.setattr(ci_templates, "_tool_version", lambda _tool: "act 1.0")
    monkeypatch.setattr(ci_templates, "_git_summary", lambda: summary)
    monkeypatch.setattr(
        ci_templates,
        "materialize_emulator_source",
        lambda **kwargs: recorded.update(materialization=kwargs) or materialization,
        raising=False,
    )
    monkeypatch.setattr(
        ci_templates,
        "_run_command",
        lambda command, **kwargs: (
            recorded.update(command=command, run=kwargs)
            or {"returncode": 0, "ok": True, "stdout": "", "stderr": ""}
        ),
    )

    assert (
        ci_templates.emulator_evidence(
            "github",
            mode="run",
            dry_run=False,
            allow_untracked=True,
            output=tmp_path / "github-run.json",
        )
        == 0
    )
    assert recorded["materialization"] == {
        "source_root": tmp_path,
        "state_dir": tmp_path / "build/runtime/work/github-act",
        "expected_head": "expected-head",
    }
    assert recorded["run"]["cwd"] == source_dir


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


def test_gitlab_materialization_creates_an_independent_git_snapshot(
    tmp_path: Path,
) -> None:
    ci_templates = _load_ci_templates_module()
    repository = tmp_path / "repository"
    linked_worktree = tmp_path / "linked-worktree"
    state_dir = tmp_path / "runtime"

    subprocess.run(["git", "init", "--quiet", str(repository)], check=True)
    subprocess.run(
        ["git", "-C", str(repository), "config", "user.email", "test@example.com"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repository), "config", "user.name", "ETHOS test"],
        check=True,
    )
    tracked = repository / "tracked.txt"
    tracked.write_text("base\n", encoding="utf-8")
    deleted = repository / "deleted.txt"
    deleted.write_text("delete me\n", encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(repository), "add", "tracked.txt", "deleted.txt"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repository), "commit", "--quiet", "-m", "base"],
        check=True,
    )
    subprocess.run(
        [
            "git",
            "-C",
            str(repository),
            "worktree",
            "add",
            "--detach",
            str(linked_worktree),
        ],
        check=True,
    )
    (linked_worktree / "tracked.txt").write_text("changed\n", encoding="utf-8")
    (linked_worktree / "deleted.txt").unlink()
    (linked_worktree / "added.txt").write_text("added\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(linked_worktree), "add", "-A"], check=True)
    expected_head = subprocess.run(
        ["git", "-C", str(linked_worktree), "rev-parse", "HEAD"],
        capture_output=True,
        check=True,
        text=True,
    ).stdout.strip()

    materialization = ci_templates.materialize_emulator_source(
        source_root=linked_worktree,
        state_dir=state_dir,
        expected_head=expected_head,
    )

    snapshot = state_dir / "source"
    assert (linked_worktree / ".git").is_file()
    assert (snapshot / ".git").is_dir()
    assert (snapshot / "tracked.txt").read_text(encoding="utf-8") == "changed\n"
    assert not (snapshot / "deleted.txt").exists()
    assert (snapshot / "added.txt").read_text(encoding="utf-8") == "added\n"
    assert (
        subprocess.run(
            ["git", "-C", str(snapshot), "ls-files"],
            capture_output=True,
            check=True,
            text=True,
        ).stdout
        == "added.txt\ntracked.txt\n"
    )
    assert materialization["kind"] == "independent_git_checkout"
    assert materialization["source_head"] == expected_head
    assert materialization["source_head_matches_expected"] is True
    assert materialization["uses_external_object_alternates"] is False
    assert (
        subprocess.run(
            ["git", "-C", str(snapshot), "status", "--short"],
            capture_output=True,
            check=True,
            text=True,
        ).stdout
        == "A  added.txt\nD  deleted.txt\nM  tracked.txt\n"
    )


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
        block = tool_block(ROOT, concern)
        assert f'gate = "{gate}"' in block
        assert "planned = true" not in block
        assert "adapter_only = true" not in block

    for concern in ["github_local_emulator", "gitlab_local_emulator"]:
        assert 'config = ".config/checks/ci/templates.toml"' in tool_block(ROOT, concern)

    tool_catalog = (ROOT / "system/tools.toml").read_text(encoding="utf-8")
    assert ".config/ci/emulators/" not in tool_catalog

    for concern in [
        "nox_runner_adapter",
        "pixi_environment_adapter",
        "pants_graph_adapter",
        "task_ledger_adapter",
        "agent_method_pack_adapter",
    ]:
        block = tool_block(ROOT, concern)
        assert 'adoption = "candidate"' in block
        assert "adapter_only = true" in block

# fmt: on
