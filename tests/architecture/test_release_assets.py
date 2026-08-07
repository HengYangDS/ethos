from __future__ import annotations

import os
import re
import stat
import subprocess
import tomllib
from pathlib import Path

import pytest

import tools.ci.python_test_gate as python_test_gate
from tests.support.architecture import tool_block

ROOT = Path(__file__).resolve().parents[2]


def test_python_test_evidence_cleanup_propagates_removal_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "evidence"
    target.mkdir()

    def denied(_path: Path) -> None:
        message = "cleanup denied"
        raise OSError(message)

    monkeypatch.setattr(python_test_gate.shutil, "rmtree", denied)

    with pytest.raises(OSError, match="cleanup denied"):
        python_test_gate.remove_generated_path(target)


def _write_fake_executable(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _assert_project_configuration(
    pyproject: str,
    ruff: str,
    pytest: str,
    config_readme: str,
) -> None:
    assert "[project]" in pyproject
    assert 'packages = ["src/ethos"]' in pyproject
    assert tomllib.loads(pyproject).get("tool", {}).get("pytest") == {
        "ini_options": {"cache_dir": "build/runtime/tool-cache/pytest"}
    }
    ruff_config = tomllib.loads(ruff)
    assert ruff_config["cache-dir"] == "build/runtime/tool-cache/ruff"
    assert ruff_config["line-length"] == 100
    assert ruff_config["target-version"] == "py312"
    assert set(ruff_config) == {"cache-dir", "line-length", "target-version", "lint", "format"}
    assert "[pytest]" in pytest
    assert "pythonpath" in pytest
    assert "error" in pytest
    assert "Separation of concerns" in config_readme
    assert "system/tools.toml" in config_readme


def _assert_tool_registry(tools: str) -> None:
    assert (
        'config = ".config/checks/pytest/pytest.ini + .config/checks/pytest/policy.toml"' in tools
    )
    assert 'config = "ruff.toml"' in tools
    assert 'config = ".config/checks/import-linter/"' in tools
    assert 'config = ".config/checks/lychee/"' in tools
    assert 'config = ".config/checks/coverage/coverage.ini"' in tools
    assert 'tool = "coverage.py + pytest-cov"' in tools
    assert 'concern = "product_boundary"' in tools
    assert 'gate = "uv run --frozen --offline python -m nox -s product_boundary"' in tools
    assert 'concern = "local_ci_fallback"' in tools
    assert 'gate = "uv run --frozen --offline python -m nox -s local_ci"' in tools
    assert 'config = ".config/checks/docstrings/policy.toml"' in tools
    assert 'tool = "ethos-docstrings-google"' in tools
    assert 'concern = "python_docstrings"' in tools


def _assert_required_ci_scripts() -> None:
    assert (ROOT / "tools/ci/scripts/bootstrap-python.sh").exists()
    assert (ROOT / "tools/ci/scripts/install-lychee.sh").exists()
    noxfile = (ROOT / "noxfile.py").read_text(encoding="utf-8")
    assert "def import_boundaries(" in noxfile
    assert (ROOT / ".config/checks/coverage/coverage.ini").exists()
    assert (ROOT / ".config/checks/coverage/.gitignore").exists()
    assert (ROOT / ".config/checks/docstrings/policy.toml").exists()
    assert "def docstrings(" in noxfile
    assert (ROOT / "tools/ci/local_ci.py").exists()
    assert "def product_boundary(" in noxfile


def test_dual_forge_collaboration_files_exist() -> None:
    required = {
        "CHANGELOG.md",
        "CONTRIBUTING.md",
        "LICENSE",
        ".gitlab-ci.yml",
        ".gitlab/merge_request_templates/default.md",
        ".gitlab/issue_templates/task.md",
        ".github/PULL_REQUEST_TEMPLATE.md",
        ".github/ISSUE_TEMPLATE/task.md",
    }

    files = {path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*") if path.is_file()}

    assert required <= files


def test_change_templates_use_current_ethos_command_plane() -> None:
    templates = [
        (ROOT / ".gitlab/merge_request_templates/default.md").read_text(encoding="utf-8"),
        (ROOT / ".github/PULL_REQUEST_TEMPLATE.md").read_text(encoding="utf-8"),
    ]
    contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")

    for template in templates:
        assert "ethos plan --changed --json" in template
        assert "ethos prove --json" in template
    assert "ethos plan --changed --json" in contributing
    assert "ethos prove --json" in contributing


def test_contributing_declares_commit_and_signature_policy() -> None:
    text = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")

    assert "Conventional Commits" in text
    assert "SSH signing" in text
    assert "allowed_identities" in text
    assert "<your-name-or-team>" in text
    assert "single built-in author" in text


def test_gitlab_ci_uses_ethos_public_command_plane() -> None:
    text = (ROOT / ".gitlab-ci.yml").read_text(encoding="utf-8")

    assert "tools/ci/scripts/run-head-bound-proof.sh" in text
    # The npm jobs run on the layer-cached python:3.12 image and install Node
    # from nodejs.org (install-node.sh), because the node:24 Docker image is
    # unreachable through the runner's registry egress. See install-node.sh.
    assert "image: node:24" not in text
    assert "tools/ci/scripts/install-node.sh" in text
    assert "tools/ci/scripts/run-node-compatibility.sh" in text
    assert "npm config set engine-strict true" in text
    assert "npm ci --ignore-scripts" in text
    assert "npm run test:npm" in text
    assert "uv run --frozen --offline python -m nox -s tests" in text
    assert 'ETHOS_TEST_WORKERS: "1"' in text
    assert "tools/ci/scripts/bootstrap-python.sh" in text
    assert "tools/ci/scripts/install-lychee.sh" in text
    assert "LYCHEE_CACHE_DIR: build/runtime/tool-cache/lychee" in text
    assert "ETHOS_CI_TOOL_CACHE_DIR: build/runtime/tool-cache/ci-tools" in text
    assert "uv run --frozen --offline python -m nox -s import_boundaries" in text
    assert "uv run --frozen --offline python -m nox -s docstrings" in text


def test_ci_tool_cache_is_a_declared_runtime_input() -> None:
    surfaces = tomllib.loads((ROOT / "system/surfaces.toml").read_text(encoding="utf-8"))

    assert "ETHOS_CI_TOOL_CACHE_DIR" in surfaces["runtime"]["inputs"]


def test_configuration_layout_is_separated_by_concern() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    ruff = (ROOT / "ruff.toml").read_text(encoding="utf-8")
    pytest = (ROOT / ".config/checks/pytest/pytest.ini").read_text(encoding="utf-8")
    config_readme = (ROOT / ".config/README.md").read_text(encoding="utf-8")
    tools = (ROOT / "system/tools.toml").read_text(encoding="utf-8")

    _assert_project_configuration(pyproject, ruff, pytest, config_readme)
    _assert_tool_registry(tools)
    _assert_required_ci_scripts()


def test_pyproject_carries_only_package_and_bounded_test_policy() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert tomllib.loads(pyproject).get("tool", {}).get("pytest") == {
        "ini_options": {"cache_dir": "build/runtime/tool-cache/pytest"}
    }
    assert set(tomllib.loads(pyproject).get("tool", {})) == {"hatch", "pytest", "mutmut"}


def test_ci_lychee_installer_is_architecture_aware() -> None:
    installer = (ROOT / "tools/ci/scripts/install-lychee.sh").read_text(encoding="utf-8")

    assert "uname -m" in installer
    assert "aarch64-unknown-linux-gnu" in installer
    assert "x86_64-unknown-linux-gnu" in installer
    assert "find" in installer
    assert 'version="lychee-v0.24.2"' in installer
    assert "releases/latest" not in installer
    assert "LYCHEE_VERSION" not in installer
    assert "checksum_url" in installer
    assert "sha256sum" in installer
    assert "--retry" in installer
    assert "--retry-all-errors" in installer
    assert "--max-time" in installer
    assert "--continue-at -" in installer
    assert "LYCHEE_CACHE_DIR" in installer
    assert "build/runtime/tool-cache/lychee" in installer
    assert "tar tzf" in installer
    assert "command -v lychee" in installer


def test_release_sbom_uses_pinned_syft_over_the_built_wheel() -> None:
    installer = (ROOT / "tools/ci/scripts/install-syft.sh").read_text(encoding="utf-8")
    runner = (ROOT / "tools/ci/release_supply_chain.py").read_text(encoding="utf-8")
    policy = tomllib.loads((ROOT / ".config/release/supply-chain.toml").read_text())

    assert policy["tool"] == "syft"
    assert policy["tool_version"] == "1.50.0"
    assert policy["format"] == "spdx-json"
    assert policy["artifact_glob"] == "build/artifacts/python/ethos-*.whl"
    assert "syft_${version}_linux_${arch}.tar.gz" in installer
    assert "sha256sum -c" in installer
    assert 'f"file:{artifact}"' in runner
    assert '"SPDX-2.3"' in runner
    assert '"not_claimed"' in runner


def test_node_runtime_compatibility_has_one_policy_and_runner_owner() -> None:
    policy_path = ROOT / ".config/checks/node/runtime.toml"
    runner_path = ROOT / "tools/ci/scripts/run-node-compatibility.sh"
    policy = tomllib.loads(policy_path.read_text(encoding="utf-8"))
    runner = runner_path.read_text(encoding="utf-8")
    installer = (ROOT / "tools/ci/scripts/install-node.sh").read_text(encoding="utf-8")
    catalog = tool_block(ROOT, "node_runtime_compatibility")

    assert policy["schema"] == "ethos-node-runtime-compatibility-v1"
    assert policy["owner"] == "ethos-quality-gate-governance"
    assert policy["default_version"] == "26.7.0"
    assert policy["compatibility_versions"] == ["24.19.0", "26.7.0"]
    archive_sha256 = policy["archive_sha256"]
    assert set(archive_sha256) == set(policy["compatibility_versions"])
    for checksums in archive_sha256.values():
        assert set(checksums) == {"linux_arm64", "linux_x64"}
        assert all(re.fullmatch(r"[a-f0-9]{64}", digest) for digest in checksums.values())
    assert runner_path.stat().st_mode & stat.S_IXUSR
    assert ".config/checks/node/runtime.toml" in runner
    assert "with-python-runtime.sh" in runner
    assert "tomllib" in runner
    assert "NODE_VERSION" in runner
    assert "npm_config_engine_strict=true" in runner
    assert "npm ci --ignore-scripts" in runner
    assert "npm run ethos -- --version" in runner
    assert "npm run test:npm" in runner
    installer_default = re.search(r'version="\$\{NODE_VERSION:-([^}]+)\}"', installer)
    assert installer_default is not None
    assert installer_default.group(1) == policy["default_version"]
    assert 'tool = "node + npm"' in catalog
    assert 'config = ".config/checks/node/runtime.toml"' in catalog
    assert 'gate = "tools/ci/scripts/run-node-compatibility.sh"' in catalog


def test_node_runtime_compatibility_runner_executes_exact_acceptance_sequence(
    tmp_path: Path,
) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    npm_log = tmp_path / "npm.log"
    _write_fake_executable(
        fake_bin / "node",
        """#!/bin/sh
printf 'v%s\\n' "${FAKE_NODE_VERSION}"
""",
    )
    _write_fake_executable(
        fake_bin / "npm",
        """#!/bin/sh
printf '%s|engine=%s\\n' "$*" "${npm_config_engine_strict:-}" >> "${FAKE_NPM_LOG}"
""",
    )
    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{fake_bin}{os.pathsep}{env['PATH']}",
            "NODE_VERSION": "24.19.0",
            "FAKE_NODE_VERSION": "24.19.0",
            "FAKE_NPM_LOG": str(npm_log),
        }
    )

    result = subprocess.run(
        ["/bin/bash", "tools/ci/scripts/run-node-compatibility.sh"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    calls = [line for line in npm_log.read_text(encoding="utf-8").splitlines() if line]
    assert calls == [
        "--version|engine=",
        "ci --ignore-scripts|engine=true",
        "run ethos -- --version|engine=true",
        "run test:npm|engine=true",
    ]


def test_node_runtime_compatibility_runner_rejects_version_mismatch_before_npm(
    tmp_path: Path,
) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    npm_log = tmp_path / "npm.log"
    _write_fake_executable(
        fake_bin / "node",
        """#!/bin/sh
printf 'v%s\\n' "${FAKE_NODE_VERSION}"
""",
    )
    _write_fake_executable(
        fake_bin / "npm",
        """#!/bin/sh
printf 'called\\n' >> "${FAKE_NPM_LOG}"
""",
    )
    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{fake_bin}{os.pathsep}{env['PATH']}",
            "NODE_VERSION": "24.19.0",
            "FAKE_NODE_VERSION": "26.7.0",
            "FAKE_NPM_LOG": str(npm_log),
        }
    )

    result = subprocess.run(
        ["/bin/bash", "tools/ci/scripts/run-node-compatibility.sh"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "Node runtime mismatch: requested 24.19.0, active 26.7.0" in result.stderr
    assert not npm_log.exists()


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
    assert "build/runtime/tool-cache/ci-tools" in installer
    assert ".config/checks/node/runtime.toml" in installer
    assert "with-python-runtime.sh" in installer
    assert "archive_sha256" in installer
    assert "sha256sum -c" in installer
    assert "tar tJf" in installer
    assert "command -v node" in installer
    assert "tar xJf" in installer
    assert "--continue-at -" in downloader
    assert "--speed-limit" in downloader
    assert "ETHOS_CI_DOWNLOAD_ATTEMPTS" in downloader
    assert "ETHOS_CI_PERSISTENT_TOOL_CACHE_DIR" in installer
    assert "persistent_archive_path" in installer
    assert "node/${version}/linux-${arch}" in installer
    assert 'verify_archive_checksum "${persistent_archive_path}"' in installer
    assert 'cp "${archive_path}" "${persistent_archive_path}.tmp"' in installer
    assert "ETHOS_CI_NODE_INSTALL_PREFIX" in installer
    assert 'export PATH="${install_bin_dir}:${PATH}"' in installer


def test_secrets_scan_is_bounded_to_git_tracked_source() -> None:
    runner = (ROOT / "tools/ci/scripts/run-secrets-scan.sh").read_text(encoding="utf-8")

    assert '"git", "ls-files", "-z"' in runner
    assert "ethos-gitleaks-tracked" in runner
    assert '--source "${scan_root}"' in runner
    assert "tracked files" in runner


def test_ci_gitleaks_installer_uses_cached_tool_supply_with_checksum() -> None:
    installer = (ROOT / "tools/ci/scripts/install-gitleaks.sh").read_text(encoding="utf-8")
    tools = (ROOT / "system/tools.toml").read_text(encoding="utf-8")

    assert "download-file.sh" in installer
    assert "ETHOS_CI_TOOL_CACHE_DIR" in installer
    assert "build/runtime/tool-cache/ci-tools" in installer
    assert "tar tzf" in installer
    assert "gitleaks_${version}_linux_${arch}.tar.gz" in installer
    assert "sha256sum -c" in installer
    assert "GITLEAKS_LINUX_X64_SHA256" in installer
    assert "GITLEAKS_LINUX_ARM64_SHA256" in installer
    assert "ETHOS_CI_PERSISTENT_TOOL_CACHE_DIR" in installer
    assert "persistent_archive_path" in installer
    assert "gitleaks/${version}/linux-${arch}" in installer
    assert 'verify_archive_checksum "${persistent_archive_path}"' in installer
    assert 'cp "${archive_path}" "${persistent_archive_path}.tmp"' in installer
    assert 'concern = "ci_tool_supply"' in tools
    assert 'config = "tools/ci/scripts/download-file.sh"' in tools
    assert 'artifacts = "build/runtime/tool-cache/ci-tools/"' in tools
    assert 'checksums = "pinned installer SHA-256 values"' in tools


def test_docstring_gate_is_owned_by_separated_policy_and_nox_session() -> None:
    runner = (ROOT / "noxfile.py").read_text(encoding="utf-8")
    policy = tomllib.loads(
        (ROOT / ".config/checks/docstrings/policy.toml").read_text(encoding="utf-8")
    )
    tools = (ROOT / "system/tools.toml").read_text(encoding="utf-8")

    assert "def docstrings(" in runner
    assert '"--gate",\n        "docstrings"' in runner
    assert policy == {
        "paths": ["src/ethos"],
        "fail_under": 100,
        "style": "google",
        "check_structured_signature": True,
    }
    assert 'concern = "python_docstrings"' in tools
    assert 'config = ".config/checks/docstrings/policy.toml"' in tools


def test_module_layout_gate_is_owned_by_policy_and_nox_surfaces() -> None:
    runner = (ROOT / "noxfile.py").read_text(encoding="utf-8")
    local_ci = (ROOT / "tools/ci/local_ci.py").read_text(encoding="utf-8")
    policy = (ROOT / ".config/checks/module-layout/policy.toml").read_text(encoding="utf-8")
    tools = (ROOT / "system/tools.toml").read_text(encoding="utf-8")
    gitlab = (ROOT / ".gitlab-ci.yml").read_text(encoding="utf-8")
    precommit = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")

    assert "def module_layout(" in runner
    assert '"--gate",\n        "module-layout"' in runner
    assert 'semantic_paths = [".agents/skills", "src/ethos", "tests", "tools"]' in policy
    assert 'package_paths = ["src/ethos"]' in policy
    assert 'concern = "python_module_layout"' in tools
    assert 'tool = "ethos-module-layout"' in tools
    assert 'config = ".config/checks/module-layout/policy.toml"' in tools
    assert 'gate = "uv run --frozen --offline python -m nox -s module_layout"' in tools
    assert '"module_layout"' in local_ci
    assert "uv run --frozen --offline python -m nox -s module_layout" in gitlab
    assert "uv run --frozen --offline python -m nox -s module_layout" in precommit
    assert '"product_boundary"' in local_ci
    assert "uv run --frozen --offline python -m nox -s product_boundary" in gitlab
    assert "uv run --frozen --offline python -m nox -s product_boundary" in precommit


def test_python_test_gate_separates_change_execution_from_terminal_coverage() -> None:
    declaration = tomllib.loads((ROOT / "system/gates.toml").read_text(encoding="utf-8"))
    gates = {gate["id"]: gate for gate in declaration["gates"]}
    runner = (ROOT / "tools/ci/python_test_gate.py").read_text(encoding="utf-8")
    coverage = (ROOT / ".config/checks/coverage/coverage.ini").read_text(encoding="utf-8")
    policy = (ROOT / ".config/checks/coverage/policy.toml").read_text(encoding="utf-8")

    assert "unit-architecture" in declaration["proof_sets"]["default"]
    assert "coverage-floor" not in declaration["proof_sets"]["default"]
    assert "coverage-floor" in declaration["proof_sets"]["full"]
    assert gates["coverage-floor"]["depends_on"] == ["unit-architecture"]
    assert gates["coverage-floor"]["command"] == [
        "{python}",
        "-m",
        "nox",
        "-s",
        "coverage_floor",
    ]
    assert "--cov=ethos" in runner
    assert "current_hard_floor" in runner
    assert "def enforce_floor(" in runner
    assert "--cov-fail-under=0" in runner
    assert 'self._coverage("report", f"--fail-under={floor:g}")' in runner
    assert 'f"--fail-under={floor:g}"' in runner
    assert 'self.head_file = self.coverage / "head.txt"' in runner
    assert "current != self.s.head" in runner
    assert '"-W",\n            "error"' in runner
    assert 'self.data = self.coverage / ".coverage"' in runner
    assert 'ROOT / ".coverage"' in runner
    assert 'self.pytest / "junit.xml"' in runner
    assert "--cov-report=term-missing" in runner
    assert "f\"--cov-report=xml:{self.coverage / 'coverage.xml'}\"" in runner
    assert 'f"--cov-config={COVERAGE_CONFIG}"' in runner
    assert "build/evidence/quality/tests" in runner
    assert "ETHOS_TEST_BASETEMP" in runner
    assert "ethos-pytest" in runner
    assert "branch = True" in coverage
    assert "patch = subprocess" in coverage
    assert "current_hard_floor = 95" in policy
    assert "aspirational_floor = 95" in policy
    assert 'source = "uv run --frozen --offline python -m nox -s tests"' in policy


def test_change_proof_does_not_own_terminal_size_debt() -> None:
    declaration = tomllib.loads((ROOT / "system/gates.toml").read_text(encoding="utf-8"))

    assert "python-size" not in declaration["proof_sets"]["default"]
    assert "python-size" in declaration["proof_sets"]["full"]


def test_quality_openspec_uses_current_coverage_floor_language() -> None:
    spec = (ROOT / "openspec/specs/quality/spec.md").read_text(encoding="utf-8")

    assert "configured hard coverage floor" in spec
    assert "current hard floor" in spec
