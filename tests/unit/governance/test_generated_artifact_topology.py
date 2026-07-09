from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from ethos.repository.policy.artifacts import generated_artifact_entrypoint_audit
from ethos.repository.policy.artifacts import generated_artifact_topology_report
from ethos_core.contracts.artifacts.topology import generated_artifact_contract
from ethos_core.contracts.artifacts.topology import is_denied_root_cache_path
from ethos_core.contracts.artifacts.topology import is_retired_config_script_path
from ethos_core.contracts.artifacts.topology import is_runner_script_path
from ethos_core.contracts.artifacts.topology import path_policy_for

if TYPE_CHECKING:
    from pathlib import Path


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)


def _init_repo(root: Path) -> None:
    root.mkdir()
    _git(root, "init", "-b", "dev")
    _git(root, "config", "user.name", "Test User")
    _git(root, "config", "user.email", "test@example.com")


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


def test_generated_artifact_report_allows_source_owned_json_schemas(tmp_path: Path) -> None:
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


def test_generated_artifact_report_blocks_tracked_generated_home(tmp_path: Path) -> None:
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


def test_generated_artifact_report_tolerates_ignored_root_test_residue(tmp_path: Path) -> None:
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


def test_generated_artifact_report_blocks_tracked_root_test_residue(tmp_path: Path) -> None:
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


def test_entrypoint_audit_ignores_directories_matching_entrypoint_globs(tmp_path: Path) -> None:
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
