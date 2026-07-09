from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_gitlab_visible_project_files_exist() -> None:
    required = {
        "CHANGELOG.md",
        "CONTRIBUTING.md",
        "LICENSE",
        ".gitlab-ci.yml",
        ".gitlab/merge_request_templates/default.md",
        ".gitlab/issue_templates/task.md",
    }

    files = {path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*") if path.is_file()}

    assert required <= files


def test_merge_request_template_uses_current_ethos_command_plane() -> None:
    template = (ROOT / ".gitlab/merge_request_templates/default.md").read_text(encoding="utf-8")
    contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")

    assert "ethos audit --mode shape --json" in template
    assert "ethos audit --mode shape --json" in contributing
    assert "ethos self audit" not in template
    assert "ethos self audit" not in contributing


def test_contributing_declares_commit_and_signature_policy() -> None:
    text = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")

    assert "Conventional Commits" in text
    assert "SSH signing" in text
    assert "allowed_identities" in text
    assert "<your-name-or-team>" in text
    assert "single built-in author" in text


def test_gitlab_ci_uses_ethos_public_command_plane() -> None:
    text = (ROOT / ".gitlab-ci.yml").read_text(encoding="utf-8")

    assert "ethos audit" in text
    assert "ethos report" in text
    # The npm jobs run on the layer-cached python:3.12 image and install Node
    # from nodejs.org (install-node.sh), because the node:24 Docker image is
    # unreachable through the runner's registry egress. See install-node.sh.
    assert "image: node:24" not in text
    assert "tools/ci/scripts/install-node.sh" in text
    assert "npm config set engine-strict true" in text
    assert "npm ci --ignore-scripts" in text
    assert "npm run ethos -- --version" in text
    assert "npm run test:npm" in text
    assert "tools/ci/scripts/run-python-tests.sh" in text
    assert "uv run --group dev pytest tests/unit tests/architecture -q" not in text
    assert "tools/ci/scripts/bootstrap-python.sh" in text
    assert "tools/ci/scripts/install-lychee.sh" in text
    assert "LYCHEE_CACHE_DIR: build/cache/lychee" in text
    assert "ETHOS_CI_TOOL_CACHE_DIR: build/cache/ci-tools" in text
    assert "build/cache/lychee/" in text
    assert "build/cache/ci-tools/" in text
    assert "tools/ci/scripts/run-import-linter.sh" in text
    assert "tools/ci/scripts/run-docstring-coverage.sh" in text
    assert (
        "uv run --group dev lint-imports --config .config/checks/import-linter/contracts.ini"
        not in text
    )
    assert "uv run --no-project --with import-linter lint-imports" not in text
    assert "pip install uv" not in text
    assert "curl -sSL https://github.com/lycheeverse/lychee" not in text
    assert "wt " not in text
    assert "proof " not in text


def test_configuration_layout_is_separated_by_concern() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    ruff = (ROOT / ".config/checks/ruff/ruff.toml").read_text(encoding="utf-8")
    pytest = (ROOT / ".config/checks/pytest/pytest.ini").read_text(encoding="utf-8")
    config_readme = (ROOT / ".config/README.md").read_text(encoding="utf-8")
    tools = (ROOT / "system/tools.toml").read_text(encoding="utf-8")

    assert "[project]" in pyproject
    assert "[tool.uv.workspace]" in pyproject
    assert "[tool.pytest" not in pyproject
    assert "[tool.ruff" not in pyproject
    assert not (ROOT / "ruff.toml").exists()
    assert not (ROOT / "pytest.ini").exists()
    assert "[lint.per-file-ignores]" in ruff
    assert "[pytest]" in pytest
    assert "pythonpath" in pytest
    assert "error::ResourceWarning" in pytest
    assert "Separation of concerns" in config_readme
    assert "system/tools.toml" in config_readme
    assert (
        'config = ".config/checks/pytest/pytest.ini + .config/checks/pytest/policy.toml"' in tools
    )
    assert 'config = ".config/checks/ruff/ruff.toml + .config/checks/ruff/ratchet.toml"' in tools
    assert 'config = ".config/checks/import-linter/"' in tools
    assert 'config = ".config/checks/lychee/"' in tools
    assert 'config = ".config/checks/coverage/coverage.ini"' in tools
    assert 'tool = "coverage.py + pytest-cov"' in tools
    assert "planned = true" not in tools.split('concern = "coverage"', 1)[1].split("[[tool]]", 1)[0]
    assert 'config = ".config/boundaries/"' not in tools
    assert 'config = ".config/docs/lychee.toml"' not in tools
    assert (ROOT / "tools/ci/scripts/bootstrap-python.sh").exists()
    assert (ROOT / "tools/ci/scripts/install-lychee.sh").exists()
    assert (ROOT / "tools/ci/scripts/run-import-linter.sh").exists()
    assert (ROOT / "tools/ci/scripts/run-python-tests.sh").exists()
    assert (ROOT / ".config/checks/coverage/coverage.ini").exists()
    assert (ROOT / ".config/checks/coverage/.gitignore").exists()
    assert (ROOT / ".config/checks/docstrings/policy.toml").exists()
    assert (ROOT / "tools/ci/scripts/run-docstring-coverage.sh").exists()
    assert (ROOT / "tools/ci/scripts/run-local-ci.sh").exists()
    assert (ROOT / "tools/ci/scripts/require-stable-head.sh").exists()
    assert (ROOT / "tools/ci/scripts/run-product-boundary.sh").exists()
    assert (ROOT / "tools/ci/scripts/run-governance-kernel.sh").exists()
    assert 'concern = "product_boundary"' in tools
    assert 'gate = "tools/ci/scripts/run-product-boundary.sh"' in tools
    assert 'concern = "governance_kernel"' in tools
    assert 'gate = "tools/ci/scripts/run-governance-kernel.sh"' in tools
    assert 'concern = "local_ci_fallback"' in tools
    assert "tools/ci/scripts/require-stable-head.sh" in tools
    assert 'gate = "tools/ci/scripts/run-local-ci.sh"' in tools
    assert 'config = ".config/checks/docstrings/policy.toml"' in tools
    assert 'tool = "ethos-docstrings-google"' in tools
    assert 'concern = "python_docstrings"' in tools


def test_ci_lychee_installer_is_architecture_aware() -> None:
    installer = (ROOT / "tools/ci/scripts/install-lychee.sh").read_text(encoding="utf-8")

    assert "uname -m" in installer
    assert "aarch64-unknown-linux-gnu" in installer
    assert "x86_64-unknown-linux-gnu" in installer
    assert "find" in installer
    assert "LYCHEE_VERSION" in installer
    assert "--retry" in installer
    assert "--retry-all-errors" in installer
    assert "--max-time" in installer
    assert "--continue-at -" in installer
    assert "LYCHEE_CACHE_DIR" in installer
    assert "build/cache/lychee" in installer
    assert "tar tzf" in installer
    assert "command -v lychee" in installer
    assert "tar xz -C /usr/local/bin lychee" not in installer


def test_ci_node_installer_is_architecture_aware() -> None:
    installer = (ROOT / "tools/ci/scripts/install-node.sh").read_text(encoding="utf-8")
    downloader = (ROOT / "tools/ci/scripts/download-file.sh").read_text(encoding="utf-8")

    assert "uname -m" in installer
    assert "arm64" in installer
    assert "x64" in installer
    assert "nodejs.org/dist" in installer
    assert "NODE_VERSION" in installer
    assert "download-file.sh" in installer
    assert "ETHOS_CI_TOOL_CACHE_DIR" in installer
    assert "build/cache/ci-tools" in installer
    assert "tar tJf" in installer
    assert "command -v node" in installer
    assert "tar xJf" in installer
    assert "--continue-at -" in downloader
    assert "--speed-limit" in downloader
    assert "ETHOS_CI_DOWNLOAD_ATTEMPTS" in downloader


def test_secrets_scan_is_bounded_to_git_tracked_source() -> None:
    runner = (ROOT / "tools/ci/scripts/run-secrets-scan.sh").read_text(encoding="utf-8")

    assert '"git", "ls-files", "-z"' in runner
    assert "ethos-gitleaks-tracked" in runner
    assert "--source ." not in runner
    assert '--source "${scan_root}"' in runner
    assert "tracked files" in runner


def test_ci_gitleaks_installer_uses_cached_tool_supply_with_checksum() -> None:
    installer = (ROOT / "tools/ci/scripts/install-gitleaks.sh").read_text(encoding="utf-8")
    tools = (ROOT / "system/tools.toml").read_text(encoding="utf-8")

    assert "download-file.sh" in installer
    assert "ETHOS_CI_TOOL_CACHE_DIR" in installer
    assert "build/cache/ci-tools" in installer
    assert "tar tzf" in installer
    assert "gitleaks_${version}_linux_${arch}.tar.gz" in installer
    assert "sha256sum -c" in installer
    assert "GITLEAKS_LINUX_X64_SHA256" in installer
    assert "GITLEAKS_LINUX_ARM64_SHA256" in installer
    assert 'concern = "ci_tool_supply"' in tools
    assert 'config = "tools/ci/scripts/download-file.sh"' in tools
    assert 'artifacts = "build/cache/ci-tools/"' in tools
    assert 'checksums = "pinned installer SHA-256 values"' in tools


def test_secrets_gate_scans_current_tree_and_git_history() -> None:
    runner = (ROOT / "tools/ci/scripts/run-secrets-scan.sh").read_text(encoding="utf-8")
    tools = (ROOT / "system/tools.toml").read_text(encoding="utf-8")

    assert "gitleaks detect" in runner
    assert "--no-git" in runner
    assert "gitleaks git" in runner
    assert '--source "${repo_root}"' not in runner
    assert '"${repo_root}"' in runner
    assert "history-report.json" in runner
    assert "history = true" in tools.split('concern = "secrets"', 1)[1].split("[[tool]]", 1)[0]


def test_docstring_gate_is_owned_by_separated_policy_and_ci_script() -> None:
    runner = (ROOT / "tools/ci/scripts/run-docstring-coverage.sh").read_text(encoding="utf-8")
    policy = (ROOT / ".config/checks/docstrings/policy.toml").read_text(encoding="utf-8")
    tools = (ROOT / "system/tools.toml").read_text(encoding="utf-8")

    assert "ethos quality docstrings" in runner
    assert "--min-coverage" not in runner
    assert "fail_under = 100" in policy
    assert 'paths = ["packages/ethos/src", "packages/ethos-core/src"]' in policy
    assert "skip_private = true" in policy
    assert 'style = "google"' in policy
    assert "check_structured_signature = true" in policy
    assert 'concern = "python_docstrings"' in tools
    assert 'config = ".config/checks/docstrings/policy.toml"' in tools


def test_module_layout_gate_is_owned_by_policy_and_runner_surfaces() -> None:
    runner = (ROOT / "tools/ci/scripts/run-module-layout.sh").read_text(encoding="utf-8")
    local_ci = (ROOT / "tools/ci/scripts/run-local-ci.sh").read_text(encoding="utf-8")
    policy = (ROOT / ".config/checks/module-layout/policy.toml").read_text(encoding="utf-8")
    tools = (ROOT / "system/tools.toml").read_text(encoding="utf-8")
    gitlab = (ROOT / ".gitlab-ci.yml").read_text(encoding="utf-8")
    precommit = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")

    assert "ethos quality module-layout" in runner
    assert "--flat-directory-limit" not in runner
    assert 'paths = ["packages/ethos/src", "packages/ethos-core/src"]' in policy
    assert "flat_directory_limit = 8" in policy
    assert "baseline_gap_limit = 0" in policy
    assert "baseline_suffix_module_limit = 0" in policy
    assert "scaffold_openspec" not in policy
    assert "land_support" not in policy
    assert "baseline_gap_limit" not in runner
    assert 'concern = "python_module_layout"' in tools
    assert 'tool = "ethos-module-layout"' in tools
    assert 'config = ".config/checks/module-layout/policy.toml"' in tools
    assert 'gate = "tools/ci/scripts/run-module-layout.sh"' in tools
    assert "tools/ci/scripts/run-module-layout.sh" in local_ci
    assert "tools/ci/scripts/run-module-layout.sh" in gitlab
    assert "tools/ci/scripts/run-module-layout.sh" in precommit
    assert "tools/ci/scripts/run-product-boundary.sh" in local_ci
    assert "tools/ci/scripts/run-governance-kernel.sh" in local_ci
    assert "tools/ci/scripts/run-product-boundary.sh" in gitlab
    assert "tools/ci/scripts/run-product-boundary.sh" in precommit


def test_python_test_gate_enforces_coverage_floor() -> None:
    runner = (ROOT / "tools/ci/scripts/run-python-tests.sh").read_text(encoding="utf-8")
    coverage = (ROOT / ".config/checks/coverage/coverage.ini").read_text(encoding="utf-8")
    policy = (ROOT / ".config/checks/coverage/policy.toml").read_text(encoding="utf-8")

    assert "--cov=ethos" in runner
    assert "--cov=ethos_core" in runner
    assert "coverage_hard_floor=" in runner
    assert "--cov-fail-under=${coverage_hard_floor}" in runner
    assert "--cov-fail-under=100" not in runner
    assert "-W error::ResourceWarning" not in runner
    assert 'COVERAGE_FILE="${coverage_evidence_dir}/.coverage"' in runner
    assert "rm -f .coverage .coverage.*" in runner
    assert 'rm -f "${COVERAGE_FILE}" "${COVERAGE_FILE}".*' in runner
    assert 'rm -f "${pytest_evidence_dir}/junit.xml"' in runner
    assert "--cov-report=term-missing" in runner
    assert '--cov-report="xml:${coverage_evidence_dir}/coverage.xml"' in runner
    assert '--cov-config="${coverage_config_dir}/coverage.ini"' in runner
    assert "--cov-report=xml:coverage.xml" not in runner
    assert "build/evidence/quality/tests" in runner
    assert "ETHOS_TEST_BASETEMP" in runner
    assert "ethos-pytest" in runner
    assert "fail_under = 100" in coverage
    assert "branch = True" in coverage
    assert "current_hard_floor = 100" in policy
    assert "aspirational_floor = 100" in policy


def test_quality_audit_uses_policy_derived_coverage_floor() -> None:
    audit = (
        ROOT / ".agents/skills/ethos-quality-gate-governance/scripts/quality_audit.py"
    ).read_text(encoding="utf-8")

    assert "coverage_hard_floor=" in audit
    assert "--cov-fail-under=${coverage_hard_floor}" in audit
    assert "--cov-fail-under={hard_floor:g}" not in audit
    assert "quality_python_tests_missing:--cov-fail-under=100" not in audit


def test_quality_audit_requires_config_check_owners_not_root_tool_files() -> None:
    audit = (
        ROOT / ".agents/skills/ethos-quality-gate-governance/scripts/quality_audit.py"
    ).read_text(encoding="utf-8")
    required_files = audit.split("REQUIRED_FILES = (", 1)[1].split(")", 1)[0]

    assert '".config/checks/ruff/ruff.toml"' in required_files
    assert '".config/checks/pytest/pytest.ini"' in required_files
    assert '"ruff.toml"' not in required_files
    assert '"pytest.ini"' not in required_files


def test_quality_audit_detects_owner_script_gate_mismatch() -> None:
    audit_path = ROOT / ".agents/skills/ethos-quality-gate-governance/scripts/quality_audit.py"
    spec = importlib.util.spec_from_file_location("quality_audit_under_test", audit_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module._tool_gate_gaps(
        "tests",
        "tools/ci/scripts/run-python-tests.sh",
        {"gate": "pytest"},
    ) == ["quality_gate_owner_mismatch:tests:pytest"]
    assert (
        module._tool_gate_gaps(
            "tests",
            "tools/ci/scripts/run-python-tests.sh",
            {"gate": "tools/ci/scripts/run-python-tests.sh"},
        )
        == []
    )


def test_quality_openspec_uses_current_coverage_floor_language() -> None:
    spec = (ROOT / "openspec/specs/quality/spec.md").read_text(encoding="utf-8")

    assert "95 percent hard coverage floor" not in spec
    assert "configured hard coverage floor" in spec
    assert "current hard floor" in spec


def test_quality_gate_reference_uses_coverage_policy_ssot() -> None:
    reference = (
        ROOT / ".agents/skills/ethos-quality-gate-governance/references/gate-design.md"
    ).read_text(encoding="utf-8")
    audit = (
        ROOT / ".agents/skills/ethos-quality-gate-governance/scripts/quality_audit.py"
    ).read_text(encoding="utf-8")

    assert "hard floor is 95 percent" not in reference
    assert ".config/checks/coverage/policy.toml" in reference
    assert "quality_reference_stale_coverage_floor:95" in audit
