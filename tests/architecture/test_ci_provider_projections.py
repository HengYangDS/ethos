from __future__ import annotations

import importlib.util
import json
import os
import re
import stat
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
import yaml

from tests.support.architecture import tool_block

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_CONFIG = ROOT / ".config/checks/ci/templates.toml"


def _projection_entries() -> list[dict[str, object]]:
    entries = tomllib.loads(TEMPLATE_CONFIG.read_text(encoding="utf-8"))["projection"]
    assert isinstance(entries, list)
    return entries


def _providers() -> dict[str, dict[str, object]]:
    return {str(entry["provider"]): entry for entry in _projection_entries()}


def _yaml(relative: str) -> dict:
    return yaml.safe_load((ROOT / relative).read_text(encoding="utf-8"))


def _load_ci_templates_module():
    spec = importlib.util.spec_from_file_location(
        "ethos_test_ci_templates", ROOT / "tools/ci/ci_templates.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("provider", "template", "projection", "emulator"),
    [
        (
            "github",
            ".config/ci/templates/hosted/github-actions.yml",
            ".github/workflows/ci.yml",
            {
                "emulator_tool": "act",
                "emulator_event": "workflow_dispatch",
                "emulator_job": "quality",
                "emulator_image": "catthehacker/ubuntu:act-latest",
            },
        ),
        (
            "gitlab",
            ".config/ci/templates/hosted/gitlab-ci.yml",
            ".gitlab-ci.yml",
            {
                "emulator_tool": "gitlab-ci-local",
                "emulator_event": "pipeline",
                "emulator_job": "ethos:lint",
                "emulator_image": "ghcr.io/astral-sh/uv:0.12.2-python3.14-trixie-slim@sha256:d6e6a4de8d48bb4e64bcc2e2bd1e2291fb00ee4fd07a5dcfdc4c621afddcfe75",
            },
        ),
    ],
)
def test_hosted_provider_templates_are_projection_sources(
    provider, template, projection, emulator
) -> None:
    entry = _providers()[provider]
    assert entry["template"] == template
    assert entry["projection"] == projection
    assert (ROOT / template).is_file()
    assert (ROOT / projection).is_file()
    assert (ROOT / template).read_bytes() == (ROOT / projection).read_bytes()
    assert "local_emulator" not in entry
    assert entry.get("emulator_state_dir", "") == ""
    assert "PYTHONWARNINGS: error" in (ROOT / projection).read_text(encoding="utf-8")
    for field, value in emulator.items():
        assert entry[field] == value
    assert set(_providers()) == {"github", "gitlab"}
    assert 'GIT_DEPTH: "0"' in (ROOT / ".gitlab-ci.yml").read_text(encoding="utf-8")


def test_forge_collaboration_surfaces_are_semantic_projections() -> None:
    """GitHub and GitLab expose one contract through provider-native files."""
    config = tomllib.loads(TEMPLATE_CONFIG.read_text(encoding="utf-8"))
    surfaces = config["forge_surface"]

    assert {(entry["provider"], entry["kind"]) for entry in surfaces} == {
        ("github", "issue"),
        ("github", "change"),
        ("gitlab", "issue"),
        ("gitlab", "change"),
    }
    for entry in surfaces:
        projection = ROOT / entry["projection"]
        headings = {
            line.removeprefix("## ").strip().lower()
            for line in projection.read_text(encoding="utf-8").splitlines()
            if line.startswith("## ")
        }
        assert headings.issuperset(entry["required_sections"])
        assert "source" not in entry

    github_issue = (ROOT / ".github/ISSUE_TEMPLATE/task.md").read_text(encoding="utf-8")
    gitlab_issue = (ROOT / ".gitlab/issue_templates/task.md").read_text(encoding="utf-8")
    assert github_issue.startswith("---\nname:")
    assert not gitlab_issue.startswith("---\n")


def test_provider_specific_gate_differences_have_explicit_reasons() -> None:
    providers = _providers()
    common = set(providers["github"]["required_owner_scripts"]) & set(
        providers["gitlab"]["required_owner_scripts"]
    )

    assert common
    for provider, peer in (("github", "gitlab"), ("gitlab", "github")):
        unique = set(providers[provider]["required_owner_scripts"]) - set(
            providers[peer]["required_owner_scripts"]
        )
        reasons = providers[provider]["provider_specific_owner_scripts"]
        assert set(reasons) == unique
        assert all(reason.strip() for reason in reasons.values())
    assert providers["github"]["provider_specific_owner_scripts"] == {
        "tools/ci/scripts/run-actionlint.sh": "GitHub workflow syntax is a GitHub-native property."
    }
    assert providers["gitlab"]["provider_specific_owner_scripts"] == {
        "tools/ci/scripts/run-node-compatibility.sh": (
            "GitLab owns the explicit Node compatibility matrix; GitHub package proof "
            "covers the canonical npm artifact once."
        )
    }


@pytest.mark.parametrize(
    "relative", [".config/ci/templates/hosted/gitlab-ci.yml", ".gitlab-ci.yml"]
)
def test_gitlab_verify_reclones_full_history_for_replay(relative: str) -> None:
    payload = _yaml(relative)
    assert payload["variables"]["GIT_DEPTH"] == "0"
    assert payload["ethos:verify"]["variables"]["GIT_STRATEGY"] == "clone"


def test_remote_provider_ci_excludes_local_candidate_and_includes_proposal() -> None:
    github = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    gitlab = (ROOT / ".gitlab-ci.yml").read_text(encoding="utf-8")
    assert "candidate/dev" not in github
    assert "proposal/**" in github
    assert "workflow:" in gitlab
    assert 'CI_COMMIT_BRANCH == "dev"' in gitlab
    assert 'CI_COMMIT_BRANCH == "main"' in gitlab
    assert "proposal\\/.+$" in gitlab


def test_provider_yaml_invokes_owner_scripts_not_inline_policy() -> None:
    required = {
        "bootstrap-python.sh",
        "run-config-lint.sh",
        "run-shell-lint.sh",
        "run-markdown-lint.sh",
        "run-prose-check.sh",
        "run-repository-hygiene.sh",
        "run-secrets-scan.sh",
        "run-hosted-provider-observation.sh",
    }
    combined = "\n".join(
        (ROOT / path).read_text(encoding="utf-8")
        for path in (".github/workflows/ci.yml", ".gitlab-ci.yml")
    )
    for name in required:
        script = f"tools/ci/scripts/{name}"
        assert script in combined
        assert (ROOT / script).stat().st_mode & stat.S_IXUSR
    assert "uv run --frozen --offline python -m nox -s dependencies" in combined
    assert "uv run --frozen --offline python -m nox -s vulnerabilities" in combined
    for session in (
        "ci_templates",
        "format_selection",
        "architecture_projection",
        "runbook_registry",
        "schemas",
        "import_boundaries",
        "docstrings",
        "module_layout",
        "product_boundary",
    ):
        assert f"uv run --frozen --offline python -m nox -s {session}" in combined
    for text in (combined,):
        assert "uv run --frozen --offline python -m nox -s lint" in text
        assert "uv run --frozen --offline python -m nox -s tests" in text
        assert "tools/ci/scripts/run-actionlint.sh" in text
        assert "uv run --frozen --offline python -m nox -s product_boundary" in text
        assert "uv run --frozen --offline python -m nox -s build" in text
        assert "uv run --group dev pytest tests/unit tests/architecture -q" not in text
        assert "uv run --no-project --with import-linter lint-imports" not in text
        assert "image: node:24" not in text
        assert "hosted_github_status_claimed=true" not in text
        assert "hosted_gitlab_status_claimed=true" not in text


def test_hosted_inline_gates_execute_at_the_checked_out_head() -> None:
    github, gitlab = _yaml(".github/workflows/ci.yml"), _yaml(".gitlab-ci.yml")
    github_type = next(
        step["run"]
        for step in github["jobs"]["quality"]["steps"]
        if step.get("name") == "Type policy"
    )
    assert '--execute --gate python-types --expect-head "$(git rev-parse HEAD)"' in github_type
    for job, gate in (("ethos:types", "python-types"), ("ethos:docs-links", "markdown-links")):
        assert f'--execute --gate {gate} --expect-head "$(git rev-parse HEAD)"' in " ".join(
            gitlab[job]["script"]
        )


def test_both_hosted_providers_check_external_links_online() -> None:
    """Hosted CI proves external reachability separately from local links."""
    github, gitlab = _yaml(".github/workflows/ci.yml"), _yaml(".gitlab-ci.yml")
    github_external = next(
        step["run"]
        for step in github["jobs"]["quality"]["steps"]
        if step.get("name") == "External links"
    )
    gitlab_external = " ".join(gitlab["ethos:external-links"]["script"])

    for command in (github_external, gitlab_external):
        assert '--execute --gate external-links --expect-head "$(git rev-parse HEAD)"' in command


def test_gitlab_node_compatibility_matrix_projects_the_runtime_policy() -> None:
    providers, gitlab = _providers(), _yaml(".gitlab-ci.yml")
    policy = tomllib.loads((ROOT / ".config/checks/node/runtime.toml").read_text(encoding="utf-8"))
    bootstrap, runner = (
        "source tools/ci/scripts/bootstrap-python.sh",
        "tools/ci/scripts/run-node-compatibility.sh",
    )
    npm, package = gitlab["ethos:npm"], gitlab["ethos:npm-package"]
    assert runner in providers["gitlab"]["required_owner_scripts"]
    assert runner not in providers["github"]["required_owner_scripts"]
    assert gitlab[".python_setup"]["before_script"] == ["tools/ci/scripts/bootstrap-python.sh"]
    assert npm["parallel"]["matrix"] == [{"NODE_VERSION": policy["compatibility_versions"]}]
    assert npm["script"] == [bootstrap, "tools/ci/scripts/install-node.sh", runner]
    assert package["script"][:2] == [bootstrap, "tools/ci/scripts/install-node.sh"]
    assert runner not in package["script"]
    assert "NODE_VERSION" not in package
    assert "npm run test:npm" in package["script"]


def test_github_repository_proof_projects_parallel_worker_stability() -> None:
    github, gitlab = _yaml(".github/workflows/ci.yml"), _yaml(".gitlab-ci.yml")
    runner = ["self-hosted", "macOS", "ARM64", "${{ vars.ETHOS_GITHUB_RUNNER_LABEL }}"]
    assert github["jobs"]["verify"]["env"] == {
        "ETHOS_TEST_WORKERS": "2",
        "ETHOS_TEST_TIMEOUT_SECONDS": "300",
        "ETHOS_TEST_TIMEOUT_METHOD": "signal",
    }
    assert all(github["jobs"][job]["runs-on"] == runner for job in ("quality", "verify", "package"))
    isolation = {
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "core.hooksPath",
        "GIT_CONFIG_VALUE_0": "/dev/null",
    }
    for job in ("quality", "verify", "package"):
        assert (
            github["jobs"][job]["steps"][0]["uses"]
            == "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"
        )
        assert github["jobs"][job]["steps"][0]["env"] == isolation
    assert gitlab["default"]["tags"] == ["${ETHOS_GITLAB_RUNNER_TAG}"]
    assert (
        gitlab["variables"]["ETHOS_CI_PERSISTENT_TOOL_CACHE_DIR"]
        == "/cache/${CI_PROJECT_PATH_SLUG}/ci-tools"
    )


@pytest.mark.parametrize(
    "relative", [".config/ci/templates/hosted/github-actions.yml", ".github/workflows/ci.yml"]
)
def test_github_repository_proof_executes_one_full_test_graph(relative: str) -> None:
    providers = _providers()
    direct = "uv run --frozen --offline python -m nox -s tests"
    proof = "tools/ci/scripts/run-head-bound-proof.sh"
    assert (
        "tools/ci/scripts/run-python-tests.sh" not in providers["github"]["required_owner_scripts"]
    )
    assert (
        "tools/ci/scripts/run-python-tests.sh" not in providers["gitlab"]["required_owner_scripts"]
    )
    assert proof in providers["github"]["required_owner_scripts"]
    payload = _yaml(relative)
    commands = [
        str(step.get("run", ""))
        for step in payload["jobs"]["verify"]["steps"]
        if isinstance(step, dict)
    ]
    assert direct not in commands
    assert commands.count(proof) == 1


def test_configure_governed_checkout_does_not_reuse_host_global_signing_key(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(("git", "init", "-b", "main"), cwd=repo, check=True, capture_output=True)
    workspace = repo / ".ethos/workspace.toml"
    workspace.parent.mkdir()
    workspace.write_text(
        "[commit_policy]\n"
        'expected_name = "ETHOS CI"\n'
        'expected_email = "ethos-ci@example.invalid"\n'
        "signing_required = true\n"
        'signing_format = "ssh"\n',
        encoding="utf-8",
    )
    host_key, host_config, runtime_tmp = (
        tmp_path / "host-global-key.pub",
        tmp_path / "host.gitconfig",
        tmp_path / "runtime-tmp",
    )
    host_key.write_text("host-global-key\n", encoding="utf-8")
    host_config.write_text(f"[user]\n\tsigningkey = {host_key}\n", encoding="utf-8")
    runtime_tmp.mkdir()
    env = os.environ | {
        "CI_PROJECT_PATH": "example/ethos",
        "GIT_CONFIG_GLOBAL": str(host_config),
        "GIT_CONFIG_NOSYSTEM": "1",
        "TMPDIR": str(runtime_tmp),
    }
    subprocess.run(
        [str(ROOT / "tools/ci/scripts/configure-git-checkout.sh")],
        cwd=repo,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    key = subprocess.run(
        ("git", "config", "--local", "--get", "user.signingkey"),
        cwd=repo,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert key
    assert key != str(host_key)
    assert Path(key).is_file()


def test_provider_python_producers_use_the_portable_locked_runtime() -> None:
    command = "uv run --frozen --offline python -m nox -s "
    for relative in (
        ".github/workflows/ci.yml",
        ".gitlab-ci.yml",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert command in text, relative
        assert ".venv/bin/" not in text, relative
        assert "uv build" not in text, relative


def test_hosted_proof_receipt_is_owner_scripted_and_retained() -> None:
    runner = "tools/ci/scripts/run-head-bound-proof.sh"
    github, gitlab, script = (
        (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"),
        _yaml(".gitlab-ci.yml"),
        (ROOT / runner).read_text(encoding="utf-8"),
    )
    assert runner in github
    assert runner in gitlab["ethos:verify"]["script"]
    assert "ethos prove --execute --expect-head" not in github
    assert "ethos prove --execute --expect-head" not in "\n".join(gitlab["ethos:verify"]["script"])
    assert gitlab["ethos:verify"]["artifacts"] == {
        "when": "always",
        "paths": ["build/evidence/quality/proof/", "build/evidence/quality/readiness/"],
    }
    for needle in (
        "ethos status --json",
        "ethos prove --execute --expect-head",
        "executed-proof.json",
        "ethos_hosted_readiness_receipt",
        "proof_evidence_digest",
    ):
        assert needle in script
    assert (ROOT / runner).stat().st_mode & stat.S_IXUSR


def test_hosted_proof_receipt_reports_post_execution_readiness(tmp_path: Path) -> None:
    runner, fake_bin = ROOT / "tools/ci/scripts/run-head-bound-proof.sh", tmp_path / "bin"
    fake_bin.mkdir()
    (fake_bin / "uv").write_text(
        """#!/usr/bin/env bash
set -euo pipefail
case "$*" in
  *"ethos prove --execute --expect-head ${ETHOS_FAKE_EXPECTED_HEAD} --json")
    printf '%s\\n' prove >>"${ETHOS_FAKE_CALLS}"
    printf '%s\\n' proven >"${ETHOS_FAKE_STATE}"
    printf '{"verdict":"pass","state":"proven",'
    printf '"data":{"expected_head":{"current":"%s","matches":true}},' "${ETHOS_FAKE_EXPECTED_HEAD}"
    printf '"summary":{"gate_count":1,"evidence_digest":"fake-digest"}}\\n'
    ;;
  *"ethos status --json")
    printf '%s\\n' status >>"${ETHOS_FAKE_CALLS}"
    printf '%s\\n' '{"verdict":"pass","state":"ready"}'
    ;;
  *) printf 'unexpected fake uv command: %s\\n' "$*" >&2; exit 64;;
esac
""",
        encoding="utf-8",
    )
    (fake_bin / "uv").chmod(0o755)
    expected_head, calls = "1" * 40, tmp_path / "calls.log"
    env = os.environ | {
        "ETHOS_FAKE_CALLS": str(calls),
        "ETHOS_FAKE_EXPECTED_HEAD": expected_head,
        "ETHOS_FAKE_STATE": str(tmp_path / "proof-state"),
        "ETHOS_PROOF_EVIDENCE_DIR": str(tmp_path / "proof"),
        "ETHOS_READINESS_EVIDENCE_DIR": str(tmp_path / "readiness"),
        "ETHOS_RUNTIME_BOOTSTRAPPED": "1",
        "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}",
    }
    completed = subprocess.run(
        [str(runner), expected_head], cwd=ROOT, env=env, check=False, capture_output=True, text=True
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert calls.read_text().splitlines() == ["status", "prove", "status"]
    receipt = json.loads(completed.stdout)
    assert {
        receipt["verdict"],
        receipt["status_before_state"],
        receipt["status_after_state"],
        receipt["proof_state"],
    } == {"pass", "ready", "proven"}
    assert receipt["head_matches_expected"] is True
    assert receipt["head"] == expected_head


def test_bootstrapped_semantic_python_bypasses_nested_uv_sync(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(("git", "init", "-q", "-b", "dev"), cwd=repo, check=True)
    (repo / "pyproject.toml").write_text(
        "[project]\nname = 'runtime-test'\nversion = '0.0.0'\n", encoding="utf-8"
    )
    python = repo / ".venv/bin/python"
    python.parent.mkdir(parents=True)
    python.write_text("#!/bin/sh\nprintf 'semantic-runtime\\n'\n", encoding="utf-8")
    python.chmod(0o755)
    (python.parent.parent / "pyvenv.cfg").write_text("home = test\n")
    fake_bin, uv_calls = tmp_path / "bin", tmp_path / "uv-calls"
    fake_bin.mkdir()
    (fake_bin / "uv").write_text(f"#!/bin/sh\ntouch {uv_calls}\nexit 97\n", encoding="utf-8")
    (fake_bin / "uv").chmod(0o755)
    env = os.environ | {
        "ETHOS_RUNTIME_BOOTSTRAPPED": "1",
        "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}",
        "XDG_CACHE_HOME": str(tmp_path / "cache"),
    }
    completed = subprocess.run(
        [str(ROOT / "tools/ci/scripts/with-python-runtime.sh"), "--", str(python)],
        cwd=repo,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    assert completed.stdout.splitlines() == ["semantic-runtime"]
    assert not uv_calls.exists()


@pytest.mark.parametrize(
    ("relative", "needles", "forbidden"),
    [
        ("tools/ci/local_ci.py", ("PYTHONWARNINGS", "ThreadPoolExecutor"), ()),
        (
            "tools/ci/scripts/bootstrap-python.sh",
            (
                "npm ci --ignore-scripts",
                '"${repo_root}/node_modules/.bin/openspec" --version',
                "uv sync --locked --group dev",
                'export UV_PROJECT_ENVIRONMENT="${repo_root}/.venv"',
                'required_uv="0.12.2"',
            ),
            (
                "npx --yes",
                "build/runtime/bootstrap",
                "python -m pip install",
                "pip install uv",
                "uv-bootstrap",
                "build/runtime/venv",
                "uv==0.11.29",
                " -m venv",
                'ln -sf "${repo_root}/node_modules/.bin/openspec"',
            ),
        ),
        (
            ".github/workflows/ci.yml",
            (
                "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
                "actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1",
                "astral-sh/setup-uv@c771a70e6277c0a99b617c7a806ffedaca235ff9",
                "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a",
            ),
            (),
        ),
        (
            ".config/checks/markdown/.markdownlint-cli2.yaml",
            ('  - "build/runtime/tool-cache/uv/**"',),
            (),
        ),
        (
            "tools/ci/scripts/run-actionlint.sh",
            ("github.com/rhysd/actionlint/releases/download",),
            ("npx --yes", "actionlint@"),
        ),
    ],
)
def test_static_ci_policies(
    relative: str, needles: tuple[str, ...], forbidden: tuple[str, ...]
) -> None:
    text = (ROOT / relative).read_text(encoding="utf-8")
    for needle in needles:
        assert needle in text
    for needle in forbidden:
        assert needle not in text


def test_github_actions_use_immutable_commit_identities() -> None:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "actions/checkout@v7" not in workflow
    assert "actions/setup-python@v6" not in workflow
    assert "actions/upload-artifact@v7" not in workflow
    for reference in re.findall(r"uses:\s+[^@\s]+@([^\s]+)", workflow):
        assert re.fullmatch(r"[0-9a-f]{40}", reference)


def test_static_ci_policy_cross_file_invariants() -> None:
    bootstrap = (ROOT / "tools/ci/scripts/bootstrap-python.sh").read_text(encoding="utf-8")
    projection = (ROOT / ".gitlab-ci.yml").read_text(encoding="utf-8")
    assert "node_modules/.bin/openspec --version" in projection
    assert bootstrap.index('export UV_PROJECT_ENVIRONMENT="${repo_root}/.venv"') < bootstrap.index(
        "uv sync --locked --group dev"
    )
    assert "build/runtime/tool-cache/uv/" in (ROOT / ".gitignore").read_text(encoding="utf-8")


def test_gitlab_verify_and_npm_jobs_bootstrap_the_job_local_runtime() -> None:
    gitlab, bootstrap = _yaml(".gitlab-ci.yml"), "source tools/ci/scripts/bootstrap-python.sh"
    for job in ("ethos:verify", "ethos:npm", "ethos:npm-package"):
        assert gitlab[job]["script"][0] == bootstrap


def test_ci_template_check_reports_projection_drift_as_json() -> None:
    result = subprocess.run(
        [sys.executable, "tools/ci/ci_templates.py", "check-templates", "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["kind"] == "ethos_ci_template_consistency"
    assert payload["verdict"] == "pass"
    assert "ok" not in payload
    assert {item["provider"] for item in payload["projections"]} == {"github", "gitlab"}
    assert all(item["projection_matches_template"] for item in payload["projections"])


@pytest.mark.parametrize(
    ("script", "kind"),
    [
        ("tools/ci/runbook_registry.py", "ethos_runbook_registry_check"),
        ("tools/ci/architecture_projection.py", "ethos_architecture_projection_drift"),
        ("tools/ci/format_selection.py", "ethos_format_selection_audit"),
    ],
)
def test_ci_public_check_envelopes_use_verdict(script: str, kind: str) -> None:
    result = subprocess.run(
        [sys.executable, script], cwd=ROOT, capture_output=True, text=True, check=True
    )
    payload = json.loads(result.stdout)
    assert payload["kind"] == kind
    assert payload["verdict"] == "pass"
    assert "ok" not in payload


@pytest.mark.parametrize(
    ("mode", "expected_code", "output"), [("doctor", 0, None), ("run", 127, "gitlab-run.json")]
)
def test_local_emulator_missing_optional_tool(
    monkeypatch, tmp_path: Path, mode: str, expected_code: int, output: str | None
) -> None:
    ci = _load_ci_templates_module()
    monkeypatch.setattr(ci.shutil, "which", lambda _: None)
    destination = None if output is None else tmp_path / output
    assert (
        ci.emulator_evidence(
            "gitlab", mode=mode, dry_run=False, allow_untracked=mode == "run", output=destination
        )
        == expected_code
    )
    payload = json.loads(
        (ROOT / "build/evidence/local-ci/gitlab/doctor.json").read_text()
        if output is None
        else destination.read_text()
    )
    assert payload["tool_available"] is False
    assert payload["returncode"] == 127
    assert payload["stderr"] == "tool not found"
    if mode == "doctor":
        assert payload["verdict"] == "pass"
        assert payload["hosted_gitlab_status_claimed"] is False
    else:
        assert payload["verdict"] == "block"
        assert payload["materialization"] == {
            "issue": "",
            "mode_allows_untracked": False,
            "normal_run_refuses_untracked_by_default": True,
            "untracked_allowed": True,
            "untracked_policy": "refuse_before_emulator_run",
        }


def test_local_emulator_run_executes_a_selected_formal_provider_job(
    monkeypatch, tmp_path: Path
) -> None:
    ci, commands, roots, states = _load_ci_templates_module(), [], [], []
    monkeypatch.setattr(
        ci.shutil,
        "which",
        lambda tool: "/usr/local/bin/emulator" if tool in {"act", "gitlab-ci-local"} else None,
    )
    monkeypatch.setattr(ci, "_tool_version", lambda tool: f"{tool} 1.0")

    def materialize(**kwargs):
        states.append(kwargs["state_dir"])
        return {"source_dir": str(kwargs["state_dir"] / "source")}

    monkeypatch.setattr(ci, "materialize_emulator_source", materialize)
    monkeypatch.setattr(
        ci,
        "_run_command",
        lambda command, **kw: (
            commands.append(command)
            or roots.append(kw["cwd"])
            or {"returncode": 0, "ok": True, "stdout": "executed", "stderr": ""}
        ),
    )
    expected_github = [
        "act",
        "workflow_dispatch",
        "-W",
        ".github/workflows/ci.yml",
        "-j",
        "quality",
    ]
    images = {
        "github": "catthehacker/ubuntu:act-latest",
        "gitlab": "ghcr.io/astral-sh/uv:0.12.2-python3.14-trixie-slim@sha256:d6e6a4de8d48bb4e64bcc2e2bd1e2291fb00ee4fd07a5dcfdc4c621afddcfe75",
    }
    for provider in ("github", "gitlab"):
        output = tmp_path / f"{provider}.json"
        assert (
            ci.emulator_evidence(
                provider, mode="run", dry_run=False, allow_untracked=True, output=output
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
            "declared_image": images[provider],
            "image_digest": "",
            "image_digest_status": "not_observed",
            "tool_version": f"{commands[-1][0]} 1.0",
        }
    assert commands[0] == expected_github
    assert commands[1] == [
        "gitlab-ci-local",
        "--cwd",
        str(states[1] / "source"),
        "--file",
        ".gitlab-ci.yml",
        "--state-dir",
        str(states[1] / "state"),
        "ethos:lint",
    ]
    assert roots == [states[0] / "source", ROOT]
    assert all(not state.is_relative_to(ROOT) for state in states)
    assert all(not state.exists() for state in states)


@pytest.mark.parametrize(
    ("stdout", "expected_code", "warnings"),
    [
        ("(node:1) DeprecationWarning: stale action runtime", 1, ["(?:^|[ >])DeprecationWarning:"]),
        (
            '"forbidden_log_patterns": ["(?:^|[ >])DeprecationWarning:", "(?:^|[ >])WARNING:"]',
            0,
            [],
        ),
    ],
)
def test_local_emulator_log_warning_policy(
    monkeypatch, tmp_path: Path, stdout: str, expected_code: int, warnings: list[str]
) -> None:
    ci = _load_ci_templates_module()
    entry = {
        "provider": "github",
        "projection": ".github/workflows/ci.yml",
        "template": ".config/ci/templates/hosted/github-actions.yml",
        "emulator_tool": "act",
        "emulator_event": "workflow_dispatch",
        "emulator_job": "quality",
        "emulator_image": "catthehacker/ubuntu:act-latest",
        "forbidden_log_patterns": ["(?:^|[ >])DeprecationWarning:", "(?:^|[ >])WARNING:"],
    }
    monkeypatch.setattr(ci, "_provider_entry", lambda _: entry)
    monkeypatch.setattr(ci.shutil, "which", {"act": "/usr/local/bin/act"}.get)
    monkeypatch.setattr(ci, "_tool_version", lambda _: "act 1.0")
    monkeypatch.setattr(
        ci,
        "materialize_emulator_source",
        lambda **kwargs: {"source_dir": str(kwargs["state_dir"] / "source")},
    )
    monkeypatch.setattr(
        ci,
        "_run_command",
        lambda _command, **_: {"returncode": 0, "ok": True, "stdout": stdout, "stderr": ""},
    )
    output = tmp_path / "github-run.json"
    assert (
        ci.emulator_evidence(
            "github", mode="run", dry_run=False, allow_untracked=True, output=output
        )
        == expected_code
    )
    payload = json.loads(output.read_text())
    assert payload["verdict"] == ("pass" if expected_code == 0 else "block")
    assert payload["log_warnings"] == warnings


def test_act_emulator_uses_docker_context_when_no_endpoint_is_explicit(
    monkeypatch, tmp_path: Path
) -> None:
    ci, environment = _load_ci_templates_module(), {}
    monkeypatch.delenv("DOCKER_HOST", raising=False)
    monkeypatch.setattr(ci.shutil, "which", lambda _: "/usr/local/bin/tool")
    monkeypatch.setattr(ci, "_docker_context_endpoint", lambda: "unix:///context/docker.sock")
    monkeypatch.setattr(ci, "_tool_version", lambda _: "act 1.0")
    monkeypatch.setattr(
        ci,
        "_run_command",
        lambda _command, **kwargs: (
            environment.update(kwargs["env"])
            or {"returncode": 0, "ok": True, "stdout": "", "stderr": ""}
        ),
    )
    assert (
        ci.emulator_evidence(
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
    ci = _load_ci_templates_module()
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
    recorded = {}

    def materialize(**kw):
        source_dir = kw["state_dir"] / "source"
        source_dir.mkdir(parents=True)
        materialization = {
            "kind": "independent_git_checkout",
            "source_dir": str(source_dir),
            "source_head": "expected-head",
            "source_head_matches_expected": True,
            "git_directory_is_real": True,
            "uses_external_object_alternates": False,
            "tracked_diff_bytes": 0,
        }
        recorded["materialization"] = kw
        return materialization

    monkeypatch.setattr(ci, "ROOT", tmp_path)
    monkeypatch.setattr(ci, "_provider_entry", lambda _: entry)
    monkeypatch.setattr(ci.shutil, "which", lambda _: "/usr/local/bin/act")
    monkeypatch.setattr(ci, "_docker_context_endpoint", lambda: "")
    monkeypatch.setattr(ci, "_tool_version", lambda _: "act 1.0")
    monkeypatch.setattr(ci, "_git_summary", lambda: summary)
    monkeypatch.setattr(ci, "materialize_emulator_source", materialize, raising=False)
    monkeypatch.setattr(
        ci,
        "_run_command",
        lambda command, **kw: (
            recorded.update(command=command, run=kw)
            or {"returncode": 0, "ok": True, "stdout": "", "stderr": ""}
        ),
    )
    assert (
        ci.emulator_evidence(
            "github",
            mode="run",
            dry_run=False,
            allow_untracked=True,
            output=tmp_path / "github-run.json",
        )
        == 0
    )
    state_dir = recorded["materialization"]["state_dir"]
    assert recorded["materialization"] == {
        "source_root": tmp_path,
        "state_dir": state_dir,
        "expected_head": "expected-head",
    }
    assert not state_dir.is_relative_to(tmp_path)
    assert recorded["run"]["cwd"] == state_dir / "source"
    assert not state_dir.exists()
    payload = json.loads((tmp_path / "github-run.json").read_text())
    assert payload["materialization"]["source_retained"] is False


def test_tool_catalog_contains_only_active_provider_gates() -> None:
    active = {
        "ci_template_consistency": "uv run --frozen --offline python -m nox -s ci_templates",
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
    for concern in ("github_local_emulator", "gitlab_local_emulator"):
        assert 'config = ".config/checks/ci/templates.toml"' in tool_block(ROOT, concern)
    assert ".config/ci/emulators/" not in (ROOT / "system/tools.toml").read_text(encoding="utf-8")
