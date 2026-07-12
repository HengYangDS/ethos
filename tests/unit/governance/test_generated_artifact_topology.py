from __future__ import annotations

import os
import subprocess
from pathlib import Path

from ethos.repository.policy import artifacts as artifacts_mod
from ethos.repository.policy.artifacts import generated_artifact_entrypoint_audit
from ethos.repository.policy.artifacts import generated_artifact_topology_report
from ethos_core.contracts.artifacts.topology import generated_artifact_contract
from ethos_core.contracts.artifacts.topology import is_denied_root_cache_path
from ethos_core.contracts.artifacts.topology import is_retired_config_script_path
from ethos_core.contracts.artifacts.topology import is_runner_script_path
from ethos_core.contracts.artifacts.topology import load_generated_artifact_topology_declaration
from ethos_core.contracts.artifacts.topology import path_policy_for
from ethos_core.contracts.artifacts.topology import path_policy_from_declaration


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)


def _init_repo(root: Path) -> None:
    root.mkdir()
    _git(root, "init", "-b", "dev")
    _git(root, "config", "user.name", "Test User")
    _git(root, "config", "user.email", "test@example.com")


def test_generated_artifact_topology_declaration_drives_contract_and_policy() -> None:
    declaration = load_generated_artifact_topology_declaration(
        Path("system/policies/generated-artifact-topology.toml")
    )
    contract = generated_artifact_contract()

    assert declaration.id == "generated-artifact-topology"
    assert "system/policies/generated-artifact-topology.toml" in contract["source_refs"]
    assert {item["prefix"] for item in contract["allowed_prefixes"]} == {
        item["prefix"] for item in declaration.to_contract()["allowed_prefixes"]
    }

    samples = (
        ".config/ethos/policy.toml",
        ".config/ethos/report.json",
        ".config/ci/scripts/run-python-tests.sh",
        ".cache/tool/state.json",
        ".cache/local-state/worktree/leases.json",
        ".import_linter_cache/cache.sqlite",
        "adopters/acme/report.json",
        "build/ethos/proof/report.json",
        "build/runtime/gitlab-ci-local/state.json",
        "build/runtime/tool-cache/pytest/cache.json",
        "build/runtime/random-cache/state.json",
        "dist/ethos.whl",
        "docs/evidence/2026-07-07-generated-artifacts.md",
        "docs/reference/report.json",
        "package-lock.json",
        "packages/sample/report.json",
        "packages/sample/schemas/contract.schema.json",
        "coverage.xml",
        "tools/ci/scripts/run-python-tests.sh",
    )
    for sample in samples:
        assert path_policy_from_declaration(sample, declaration) == path_policy_for(sample)


def test_contract_is_generic_and_declares_artifact_homes() -> None:
    contract = generated_artifact_contract()

    assert {item["prefix"] for item in contract["declarative_prefixes"]} == {".config/ethos"}
    assert {item["prefix"] for item in contract["allowed_prefixes"]} >= {
        ".cache/local-state",
        ".ethos/state",
        "build/runtime/tool-cache",
        "build/runtime/work",
        "build/ethos",
        "build/evidence",
        "build/artifacts",
    }
    assert {item["prefix"] for item in contract["review_prefixes"]} >= {
        "docs/evidence",
        "evidence/chronicle",
        "evidence/parity",
        "tools/ci/scripts",
    }
    assert {item["prefix"] for item in contract["denied_prefixes"]} >= {
        ".config/ci/scripts",
    }
    assert {item["prefix"] for item in contract["denied_root_cache_prefixes"]} >= {
        ".import_linter_cache",
        ".import-linter-cache",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        ".tox",
        ".nox",
        ".uv-cache",
    }
    assert {item["prefix"] for item in contract["denied_legacy_generated_prefixes"]} >= {
        "build/cache",
        "build/runtime/gitlab-ci-local",
        "dist",
    }
    lifecycle = {item["id"]: item for item in contract["lifecycle_classes"]}
    assert set(lifecycle) == {
        "runtime_cache",
        "machine_evidence",
        "local_artifact",
        "curated_evidence",
    }
    assert ".ethos/state" in lifecycle["runtime_cache"]["homes"]
    assert lifecycle["runtime_cache"]["tracked"] is False
    assert lifecycle["machine_evidence"]["promotion_allowed"] is True
    assert lifecycle["curated_evidence"]["tracked"] is True
    assert contract["adopter_specific_product_dirs_allowed"] is False
    assert "adopters" in contract["product_adopter_root_prefixes"]


def test_source_bound_uv_runner_uses_semantic_runtime_homes() -> None:
    declaration = load_generated_artifact_topology_declaration(
        Path("system/policies/generated-artifact-topology.toml")
    )
    runner = Path("tools/ci/scripts/run-ethos-lane.sh").read_text(encoding="utf-8")
    bootstrap = Path("tools/ci/scripts/with-python-runtime.sh").read_text(encoding="utf-8")

    assert "build/runtime/venv" in declaration.runtime_allowed_prefixes
    assert (
        path_policy_from_declaration("build/runtime/venv/bin/python", declaration)["decision"]
        == "allow"
    )
    assert (
        'exec "${script_dir}/with-python-runtime.sh" -- uv run --package ethos ethos "$@"' in runner
    )
    assert 'export UV_PROJECT_ENVIRONMENT="${repo_root}/build/runtime/venv"' in bootstrap
    assert 'export UV_CACHE_DIR="${XDG_CACHE_HOME:-${HOME}/.cache}/ethos/uv"' in bootstrap


def test_source_bound_uv_runner_uses_checkout_environment_and_host_cache(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    fake_uv = tmp_path / "bin" / "uv"
    fake_uv.parent.mkdir()
    fake_uv.write_text(
        '#!/usr/bin/env bash\nprintf \'%s\\n%s\\n%s\\n\' "$UV_PROJECT_ENVIRONMENT" "$UV_CACHE_DIR" "$*"\n',
        encoding="utf-8",
    )
    fake_uv.chmod(0o755)
    runner = Path("tools/ci/scripts/run-ethos-lane.sh").resolve()
    environment = dict(os.environ)
    environment["PATH"] = f"{fake_uv.parent}:{environment['PATH']}"
    environment["XDG_CACHE_HOME"] = (tmp_path / "host-cache").as_posix()
    environment.pop("UV_PROJECT_ENVIRONMENT", None)
    environment.pop("UV_CACHE_DIR", None)
    environment.pop("ETHOS_UV_CACHE_DIR", None)
    environment.pop("ETHOS_RUNTIME_ROOT", None)

    completed = subprocess.run(
        [runner.as_posix(), "status", "--json"],
        cwd=repo,
        env=environment,
        check=True,
        text=True,
        capture_output=True,
    )

    assert completed.stdout.splitlines() == [
        f"{repo}/build/runtime/venv",
        f"{tmp_path}/host-cache/ethos/uv",
        "run --package ethos ethos status --json",
    ]
    assert not (repo / "build/runtime/venv").exists()
    assert (tmp_path / "host-cache/ethos/uv").is_dir()


def test_path_policy_keeps_config_declarative_and_build_generated() -> None:
    config = path_policy_for(".config/ethos/policy.toml")
    build = path_policy_for("build/ethos/proof/report.json")
    local_state = path_policy_for(".ethos/state/worktree/leases.json")
    runtime = path_policy_for("build/runtime/tool-cache/pytest/cache.json")
    work = path_policy_for("build/runtime/work/gitlab-ci-local/state.json")
    artifact = path_policy_for("build/artifacts/python/ethos-0.1.0.whl")
    curated = path_policy_for("docs/evidence/2026-07-07-generated-artifacts.md")

    assert config["decision"] == "review"
    assert config["generated"] is False
    assert "declarative" in config["boundary"]
    assert build["decision"] == "allow"
    assert build["generated"] is True
    assert local_state["decision"] == "allow"
    assert local_state["generated"] is True
    assert runtime["decision"] == "allow"
    assert runtime["generated"] is True
    assert "tool runtime caches" in runtime["boundary"]
    assert work["decision"] == "allow"
    assert "working state" in work["boundary"]
    assert artifact["decision"] == "allow"
    assert "build" in artifact["boundary"]
    assert curated["decision"] == "review"


def test_path_policy_treats_package_locks_as_metadata_not_generated_drift() -> None:
    package_lock = path_policy_for("package-lock.json")
    pyproject = path_policy_for("pyproject.toml")

    assert package_lock["decision"] == "ignore"
    assert package_lock["generated"] is False
    assert pyproject["decision"] == "ignore"
    assert pyproject["generated"] is False


def test_generated_artifact_report_allows_source_owned_json_schemas(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    schema = repo / "packages" / "sample" / "schemas" / "contract.schema.json"
    schema.parent.mkdir(parents=True)
    schema.write_text(
        '{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object"}\n',
        encoding="utf-8",
    )
    _git(repo, "add", "packages/sample/schemas/contract.schema.json")
    _git(repo, "commit", "-m", "add source-owned schema contract")

    report = generated_artifact_topology_report(repo)

    assert report["ok"] is True
    assert report["required_gaps"] == []


def test_generated_artifact_report_blocks_root_generated_output(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "coverage.xml").write_text("<coverage />\n", encoding="utf-8")
    _git(repo, "add", "coverage.xml")
    _git(repo, "commit", "-m", "add generated drift")

    report = generated_artifact_topology_report(repo)

    assert report["ok"] is False
    assert "generated_artifact_repo_root_drift:coverage.xml" in report["required_gaps"]


def test_generated_artifact_report_blocks_tracked_generated_home(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    output = repo / "packages" / "sample" / "report.json"
    output.parent.mkdir(parents=True)
    output.write_text("{}\n", encoding="utf-8")
    _git(repo, "add", "packages/sample/report.json")
    _git(repo, "commit", "-m", "track generated output")

    report = generated_artifact_topology_report(repo)

    assert report["ok"] is False
    assert "generated_artifact_source_drift:packages/sample/report.json" in report["required_gaps"]


def test_generated_artifact_report_blocks_ignored_root_cache_with_internal_gitignore(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / ".gitignore").write_text(".import_linter_cache/\n", encoding="utf-8")
    root_cache = repo / ".import_linter_cache"
    root_cache.mkdir()
    (root_cache / ".gitignore").write_text("*\n", encoding="utf-8")
    _git(repo, "add", ".gitignore")
    _git(repo, "commit", "-m", "ignore root tool cache")

    report = generated_artifact_topology_report(repo)

    assert report["ok"] is False
    assert ".import_linter_cache" in report["denied_paths"]
    assert "generated_artifact_root_cache_drift:.import_linter_cache" in report["required_gaps"]


def test_candidate_paths_prune_recursive_allowed_homes_but_scan_adjacent_drift(
    tmp_path: Path,
) -> None:
    declaration = load_generated_artifact_topology_declaration()
    allowed = tmp_path / "build/runtime/tool-cache/pytest/deep/cache.json"
    denied = tmp_path / "build/runtime/random-cache/state.json"
    allowed.parent.mkdir(parents=True)
    denied.parent.mkdir(parents=True)
    allowed.write_text("{}\n", encoding="utf-8")
    denied.write_text("{}\n", encoding="utf-8")

    candidates = {
        path.relative_to(tmp_path).as_posix()
        for path in artifacts_mod._candidate_paths(tmp_path, declaration)
    }

    assert "build/runtime/tool-cache/pytest/deep/cache.json" not in candidates
    assert "build/runtime/random-cache/state.json" in candidates


def test_candidate_paths_retains_an_empty_denied_directory(tmp_path: Path) -> None:
    declaration = load_generated_artifact_topology_declaration()
    (tmp_path / ".cache" / "empty").mkdir(parents=True)

    candidates = {
        path.relative_to(tmp_path).as_posix()
        for path in artifacts_mod._candidate_paths(tmp_path, declaration)
    }

    assert ".cache" in candidates


def test_path_policy_denies_legacy_and_flat_generated_homes() -> None:
    assert path_policy_for(".import_linter_cache/cache.sqlite")["required_gap"] == (
        "generated_artifact_root_cache_drift:.import_linter_cache/cache.sqlite"
    )
    assert path_policy_for("build/cache/lychee/archive.tar.gz")["required_gap"] == (
        "generated_artifact_legacy_generated_home:build/cache/lychee/archive.tar.gz"
    )
    assert path_policy_for("build/runtime/gitlab-ci-local/state.json")["required_gap"] == (
        "generated_artifact_legacy_generated_home:build/runtime/gitlab-ci-local/state.json"
    )
    assert path_policy_for("build/runtime/random-cache/state.json")["required_gap"] == (
        "generated_artifact_runtime_flat_drift:build/runtime/random-cache/state.json"
    )
    assert path_policy_for("dist/ethos.whl")["required_gap"] == (
        "generated_artifact_legacy_generated_home:dist/ethos.whl"
    )
    assert path_policy_for(".cache/tool/state.json")["required_gap"] == (
        "generated_artifact_cache_flat_drift:.cache/tool/state.json"
    )


def test_generated_artifact_report_allows_package_metadata(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "package-lock.json").write_text("{}\n", encoding="utf-8")
    _git(repo, "add", "package-lock.json")
    _git(repo, "commit", "-m", "add package lock")

    report = generated_artifact_topology_report(repo)

    assert report["ok"] is True
    assert report["required_gaps"] == []


def test_generated_artifact_report_tolerates_ignored_root_test_residue(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / ".gitignore").write_text(
        ".coverage\n.coverage.*\ncoverage.xml\njunit.xml\n",
        encoding="utf-8",
    )
    _git(repo, "add", ".gitignore")
    _git(repo, "commit", "-m", "ignore local test residue")
    for name in (".coverage", ".coverage.worker", "coverage.xml", "junit.xml"):
        (repo / name).write_text("local residue\n", encoding="utf-8")

    report = generated_artifact_topology_report(repo)

    assert report["ok"] is True
    assert report["required_gaps"] == []
    assert set(report["ignored_local_paths"]) == {
        ".coverage",
        ".coverage.worker",
        "coverage.xml",
        "junit.xml",
    }


def test_generated_artifact_report_blocks_tracked_root_test_residue(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / ".gitignore").write_text(".coverage.*\n", encoding="utf-8")
    (repo / ".coverage.worker").write_text("tracked residue\n", encoding="utf-8")
    _git(repo, "add", ".gitignore")
    _git(repo, "add", "-f", ".coverage.worker")
    _git(repo, "commit", "-m", "track root coverage residue")

    report = generated_artifact_topology_report(repo)

    assert report["ok"] is False
    assert ".coverage.worker" not in report["ignored_local_paths"]
    assert "generated_artifact_repo_root_drift:.coverage.worker" in report["required_gaps"]


def test_entrypoint_audit_ignores_directories_matching_entrypoint_globs(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    (repo / "tools" / "ci" / "scripts" / "directory-entry").mkdir(parents=True)

    audit = generated_artifact_entrypoint_audit(repo)

    assert audit["ok"] is True
    assert audit["checked_files"] == []
    assert audit["required_gaps"] == []


def test_path_policy_denies_generated_output_under_config() -> None:
    report = path_policy_for(".config/ethos/report.json")

    assert report["decision"] == "deny"
    assert report["required_gap"] == "generated_artifact_config_drift:.config/ethos/report.json"


def test_path_policy_denies_generated_output_under_governed_docs() -> None:
    report = path_policy_for("docs/reference/report.json")

    assert report["decision"] == "deny"
    assert report["required_gap"] == (
        "generated_artifact_governed_docs_drift:docs/reference/report.json"
    )


def test_runner_script_helpers_match_only_active_and_retired_script_homes() -> None:
    assert is_runner_script_path("tools/ci/scripts/run-python-tests.sh") is True
    assert is_runner_script_path("tools/ci") is False

    assert is_retired_config_script_path(".config/ci/scripts/run-python-tests.sh") is True
    assert is_retired_config_script_path(".config/ci") is False

    assert is_denied_root_cache_path(".import_linter_cache/cache.sqlite") is True
    assert is_denied_root_cache_path(".cache/local-state/worktree/leases.json") is False


def test_path_policy_reviews_runner_scripts_and_denies_retired_config_scripts() -> None:
    runner = path_policy_for("tools/ci/scripts/run-python-lint.sh")
    retired = path_policy_for(".config/ci/scripts/run-python-lint.sh")

    assert runner["decision"] == "review"
    assert runner["required_gap"] == ""
    assert "runner" in runner["boundary"]
    assert retired["decision"] == "deny"
    assert retired["required_gap"] == (
        "retired_config_script_home:.config/ci/scripts/run-python-lint.sh"
    )


def test_generated_artifact_entrypoint_audit_blocks_unrouted_tool_producers(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    script = repo / "tools" / "ci" / "scripts" / "run-python-lint.sh"
    script.parent.mkdir(parents=True)
    script.write_text(
        "#!/usr/bin/env bash\nruff check .\nlint-imports --config .config/checks/import-linter/contracts.ini\n",
        encoding="utf-8",
    )
    pytest_ini = repo / ".config" / "checks" / "pytest" / "pytest.ini"
    pytest_ini.parent.mkdir(parents=True)
    pytest_ini.write_text("[pytest]\ncache_dir = .pytest_cache\n", encoding="utf-8")
    (repo / "package.json").write_text("{}\n", encoding="utf-8")
    provider = repo / "tools" / "ci" / "scripts" / "run-gitlab-local-emulator.sh"
    provider.write_text("#!/usr/bin/env bash\ngitlab-ci-local --list\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "add unrouted entrypoints")

    report = generated_artifact_topology_report(repo)

    assert report["ok"] is False
    assert (
        "generated_artifact_entrypoint_ruff_cache_unrouted:tools/ci/scripts/run-python-lint.sh"
        in report["required_gaps"]
    )
    assert (
        "generated_artifact_entrypoint_import_linter_cache_unrouted:"
        "tools/ci/scripts/run-python-lint.sh"
    ) in report["required_gaps"]
    assert (
        "generated_artifact_entrypoint_pytest_cache_unrouted:.config/checks/pytest/pytest.ini"
    ) in report["required_gaps"]


def test_generated_artifact_entrypoint_audit_accepts_semantic_routes(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    script = repo / "tools" / "ci" / "scripts" / "run-python-lint.sh"
    script.parent.mkdir(parents=True)
    script.write_text(
        """#!/usr/bin/env bash
ruff_cache_dir=build/runtime/tool-cache/ruff
ruff check --cache-dir "${ruff_cache_dir}" --config .config/checks/ruff/ruff.toml .
IMPORT_LINTER_CACHE_DIR=build/runtime/tool-cache/import-linter
lint-imports --cache-dir "${IMPORT_LINTER_CACHE_DIR}" --config .config/checks/import-linter/contracts.ini
uv build --all-packages --out-dir build/artifacts/python --clear
gitlab-ci-local --state-dir build/runtime/work/gitlab-ci-local --list
""",
        encoding="utf-8",
    )
    pytest_ini = repo / ".config" / "checks" / "pytest" / "pytest.ini"
    pytest_ini.parent.mkdir(parents=True)
    pytest_ini.write_text(
        "[pytest]\ncache_dir = build/runtime/tool-cache/pytest\n",
        encoding="utf-8",
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "add semantic entrypoint routes")

    audit = generated_artifact_entrypoint_audit(repo)

    assert audit["ok"] is True
    assert audit["required_gaps"] == []


def test_generated_artifact_entrypoint_audit_ignores_cleanup_and_url_literals(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    script = repo / "tools" / "ci" / "scripts" / "cleanup.sh"
    script.parent.mkdir(parents=True)
    script.write_text(
        """#!/usr/bin/env bash
rm -rf .pytest_cache .ruff_cache
url="https://nodejs.org/dist/v1/node.tar.xz"
""",
        encoding="utf-8",
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "add cleanup and url")

    audit = generated_artifact_entrypoint_audit(repo)

    assert audit["ok"] is True
    assert audit["required_gaps"] == []


def test_semantic_runtime_bootstrap_exports_checkout_environment_and_host_cache(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    fake_uv = tmp_path / "bin" / "uv"
    fake_uv.parent.mkdir()
    fake_uv.write_text(
        '#!/usr/bin/env bash\nprintf \'%s\\n%s\\n%s\\n\' "$UV_PROJECT_ENVIRONMENT" "$UV_CACHE_DIR" "$*"\n',
        encoding="utf-8",
    )
    fake_uv.chmod(0o755)
    bootstrap = Path("tools/ci/scripts/with-python-runtime.sh").resolve()
    environment = dict(os.environ)
    environment["PATH"] = f"{fake_uv.parent}:{environment['PATH']}"
    environment["XDG_CACHE_HOME"] = (tmp_path / "host-cache").as_posix()
    environment.pop("UV_PROJECT_ENVIRONMENT", None)
    environment.pop("UV_CACHE_DIR", None)
    environment.pop("ETHOS_UV_CACHE_DIR", None)

    completed = subprocess.run(
        [bootstrap.as_posix(), "--", "uv", "run", "--no-sync", "--version"],
        cwd=repo,
        env=environment,
        check=True,
        text=True,
        capture_output=True,
    )

    assert completed.stdout.splitlines() == [
        f"{repo}/build/runtime/venv",
        f"{tmp_path}/host-cache/ethos/uv",
        "run --no-sync --version",
    ]


def test_semantic_runtime_bootstrap_preserves_explicit_ci_cache(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    fake_uv = tmp_path / "bin" / "uv"
    fake_uv.parent.mkdir()
    fake_uv.write_text(
        '#!/usr/bin/env bash\nprintf \'%s\\n%s\\n\' "$UV_PROJECT_ENVIRONMENT" "$UV_CACHE_DIR"\n',
        encoding="utf-8",
    )
    fake_uv.chmod(0o755)
    bootstrap = Path("tools/ci/scripts/with-python-runtime.sh").resolve()
    environment = dict(os.environ)
    environment["PATH"] = f"{fake_uv.parent}:{environment['PATH']}"
    ci_cache = tmp_path / "ci-cache" / "uv"
    environment["UV_CACHE_DIR"] = ci_cache.as_posix()
    environment.pop("ETHOS_UV_CACHE_DIR", None)

    completed = subprocess.run(
        [bootstrap.as_posix(), "--", "uv", "--version"],
        cwd=repo,
        env=environment,
        check=True,
        text=True,
        capture_output=True,
    )

    assert completed.stdout.splitlines() == [
        f"{repo}/build/runtime/venv",
        ci_cache.as_posix(),
    ]


def test_semantic_runtime_bootstrap_prefers_ethos_cache_override(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    fake_uv = tmp_path / "bin" / "uv"
    fake_uv.parent.mkdir()
    fake_uv.write_text(
        "#!/usr/bin/env bash\nprintf '%s\\n' \"$UV_CACHE_DIR\"\n",
        encoding="utf-8",
    )
    fake_uv.chmod(0o755)
    bootstrap = Path("tools/ci/scripts/with-python-runtime.sh").resolve()
    environment = dict(os.environ)
    environment["PATH"] = f"{fake_uv.parent}:{environment['PATH']}"
    environment["UV_CACHE_DIR"] = (tmp_path / "ci-cache" / "uv").as_posix()
    ethos_cache = tmp_path / "operator-cache" / "uv"
    environment["ETHOS_UV_CACHE_DIR"] = ethos_cache.as_posix()

    completed = subprocess.run(
        [bootstrap.as_posix(), "--", "uv", "--version"],
        cwd=repo,
        env=environment,
        check=True,
        text=True,
        capture_output=True,
    )

    assert completed.stdout == f"{ethos_cache}\n"
    assert ethos_cache.is_dir()


def test_semantic_runtime_bootstrap_materializes_missing_checkout_python(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    fake_uv = tmp_path / "bin" / "uv"
    fake_uv.parent.mkdir()
    fake_uv.write_text(
        '#!/usr/bin/env bash\nprintf \'%s\\n%s\\n%s\\n\' "$UV_PROJECT_ENVIRONMENT" "$UV_CACHE_DIR" "$*"\n',
        encoding="utf-8",
    )
    fake_uv.chmod(0o755)
    bootstrap = Path("tools/ci/scripts/with-python-runtime.sh").resolve()
    environment = dict(os.environ)
    environment["PATH"] = f"{fake_uv.parent}:{environment['PATH']}"
    environment["XDG_CACHE_HOME"] = (tmp_path / "host-cache").as_posix()
    environment.pop("UV_PROJECT_ENVIRONMENT", None)
    environment.pop("UV_CACHE_DIR", None)
    environment.pop("ETHOS_UV_CACHE_DIR", None)
    environment.pop("ETHOS_RUNTIME_ROOT", None)
    resolved_repo = repo.resolve()
    checkout_python = resolved_repo / "build" / "runtime" / "venv" / "bin" / "python"

    completed = subprocess.run(
        [
            bootstrap.as_posix(),
            "--",
            checkout_python.as_posix(),
            "-m",
            "ethos.cli",
            "status",
            "--json",
        ],
        cwd=repo,
        env=environment,
        check=True,
        text=True,
        capture_output=True,
    )

    assert completed.stdout.splitlines() == [
        f"{resolved_repo}/build/runtime/venv",
        f"{tmp_path}/host-cache/ethos/uv",
        "run --group dev python -m ethos.cli status --json",
    ]
    assert not checkout_python.exists()


def test_semantic_runtime_bootstrap_namespaces_nested_cache_under_selected_root(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    fake_uv = tmp_path / "bin" / "uv"
    fake_uv.parent.mkdir()
    fake_uv.write_text(
        '#!/usr/bin/env bash\nprintf \'%s\\n%s\\n%s\\n\' "$UV_PROJECT_ENVIRONMENT" "$UV_CACHE_DIR" "$*"\n',
        encoding="utf-8",
    )
    fake_uv.chmod(0o755)
    bootstrap = Path("tools/ci/scripts/with-python-runtime.sh").resolve()
    environment = dict(os.environ)
    environment["PATH"] = f"{fake_uv.parent}:{environment['PATH']}"
    cache_root = tmp_path / "host-cache" / "ethos" / "uv"
    outer_root = tmp_path / "outer"
    environment["UV_PROJECT_ENVIRONMENT"] = (outer_root / "build" / "runtime" / "venv").as_posix()
    environment["UV_CACHE_DIR"] = cache_root.as_posix()
    environment["ETHOS_RUNTIME_ROOT"] = outer_root.as_posix()
    environment.pop("ETHOS_UV_CACHE_DIR", None)
    checkout_python = repo.resolve() / "build" / "runtime" / "venv" / "bin" / "python"

    completed = subprocess.run(
        [bootstrap.as_posix(), "--", checkout_python.as_posix(), "-m", "ethos.cli"],
        cwd=repo,
        env=environment,
        check=True,
        text=True,
        capture_output=True,
    )

    environment_home, nested_cache, command = completed.stdout.splitlines()
    assert environment_home == f"{repo.resolve()}/build/runtime/venv"
    assert Path(nested_cache).parent == cache_root / "nested-bootstrap"
    assert command == "run --group dev python -m ethos.cli"


def test_semantic_runtime_bootstrap_detaches_owner_script_from_uv_sync_lock(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    fake_uv = tmp_path / "bin" / "uv"
    fake_uv.parent.mkdir()
    fake_uv.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        'printf "%s\\n" "$*" > "$UV_CAPTURE"\n'
        '[[ "$1" == "run" ]]\n'
        "shift\n"
        'while [[ "$1" != "env" ]]; do shift; done\n'
        "shift\n"
        'while [[ "$1" == *=* ]]; do export "$1"; shift; done\n'
        'exec "$@"\n',
        encoding="utf-8",
    )
    fake_uv.chmod(0o755)
    owner_script = repo / "tools" / "ci" / "scripts" / "run-owner.sh"
    owner_script.parent.mkdir(parents=True)
    owner_script.write_text(
        "#!/usr/bin/env bash\n"
        'printf "%s\\n%s\\n" "$ETHOS_RUNTIME_BOOTSTRAPPED" "$UV_PROJECT_ENVIRONMENT"\n',
        encoding="utf-8",
    )
    owner_script.chmod(0o755)
    bootstrap = Path("tools/ci/scripts/with-python-runtime.sh").resolve()
    capture = tmp_path / "uv-command.txt"
    environment = dict(os.environ)
    environment["PATH"] = f"{fake_uv.parent}:{environment['PATH']}"
    environment["UV_CAPTURE"] = capture.as_posix()
    environment.pop("UV_PROJECT_ENVIRONMENT", None)
    environment.pop("UV_CACHE_DIR", None)
    environment.pop("ETHOS_UV_CACHE_DIR", None)
    environment.pop("ETHOS_RUNTIME_ROOT", None)

    completed = subprocess.run(
        [
            bootstrap.as_posix(),
            "--",
            "uv",
            "run",
            "--all-packages",
            "--group",
            "dev",
            "env",
            "OWNER_SCRIPT_MODE=test",
            "ETHOS_RUNTIME_BOOTSTRAPPED=1",
            owner_script.as_posix(),
        ],
        cwd=repo,
        env=environment,
        check=True,
        text=True,
        capture_output=True,
    )

    assert completed.stdout.splitlines() == [
        "1",
        f"{repo.resolve()}/build/runtime/venv",
    ]
    assert capture.read_text(encoding="utf-8") == (
        "run --no-sync --all-packages --group dev env "
        f"OWNER_SCRIPT_MODE=test ETHOS_RUNTIME_BOOTSTRAPPED=1 {owner_script}\n"
    )


def test_generated_artifact_entrypoint_audit_blocks_root_venv_and_bare_uv_run(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    script = repo / "tools" / "ci" / "scripts" / "run-bad.sh"
    script.parent.mkdir(parents=True)
    script.write_text(
        "#!/usr/bin/env bash\n"
        '"$repo_root/.venv/bin/python" -m ethos.cli status --json\n'
        "uv run --package ethos ethos status --json\n",
        encoding="utf-8",
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "add root runtime fallback")

    audit = generated_artifact_entrypoint_audit(repo)

    assert audit["ok"] is False
    assert (
        "generated_artifact_entrypoint_root_venv_runtime:tools/ci/scripts/run-bad.sh"
        in audit["required_gaps"]
    )
    assert (
        "generated_artifact_entrypoint_uv_runtime_unbound:tools/ci/scripts/run-bad.sh"
        in audit["required_gaps"]
    )


def test_generated_artifact_entrypoint_audit_accepts_bootstrap_bound_uv_run(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    script = repo / "tools" / "ci" / "scripts" / "run-good.sh"
    script.parent.mkdir(parents=True)
    script.write_text(
        "#!/usr/bin/env bash\n"
        'script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"\n'
        'exec "${script_dir}/with-python-runtime.sh" -- uv run --package ethos ethos status --json\n',
        encoding="utf-8",
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "add semantic runtime bootstrap")

    audit = generated_artifact_entrypoint_audit(repo)

    assert audit["ok"] is True
    assert audit["required_gaps"] == []


def test_generated_artifact_entrypoint_audit_blocks_unbound_python_execution(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    script = repo / "tools" / "ci" / "scripts" / "run-bad-python.sh"
    script.parent.mkdir(parents=True)
    script.write_text(
        "#!/usr/bin/env bash\npython -m ethos.cli status --json\n",
        encoding="utf-8",
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "add unbound python runtime")

    audit = generated_artifact_entrypoint_audit(repo)

    assert audit["ok"] is False
    assert (
        "generated_artifact_entrypoint_python_runtime_unbound:"
        "tools/ci/scripts/run-bad-python.sh" in audit["required_gaps"]
    )
