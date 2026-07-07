from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from ethos.repository.policy.artifacts import generated_artifact_topology_report
from ethos_core.contracts.generated_artifact_topology import generated_artifact_contract
from ethos_core.contracts.generated_artifact_topology import path_policy_for

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
        "build/ethos",
        "build/evidence",
    }
    assert {item["prefix"] for item in contract["review_prefixes"]} >= {
        "docs/evidence",
        "evidence/chronicle",
        "evidence/parity",
    }
    assert contract["adopter_specific_product_dirs_allowed"] is False
    assert "adopters" in contract["product_adopter_root_prefixes"]


def test_path_policy_keeps_config_declarative_and_build_generated() -> None:
    config = path_policy_for(".config/ethos/policy.toml")
    build = path_policy_for("build/ethos/proof/report.json")
    curated = path_policy_for("docs/evidence/2026-07-07-generated-artifacts.md")

    assert config["decision"] == "review"
    assert config["generated"] is False
    assert "declarative" in config["boundary"]
    assert build["decision"] == "allow"
    assert build["generated"] is True
    assert curated["decision"] == "review"


def test_path_policy_treats_package_locks_as_metadata_not_generated_drift() -> None:
    package_lock = path_policy_for("package-lock.json")
    pyproject = path_policy_for("pyproject.toml")

    assert package_lock["decision"] == "ignore"
    assert package_lock["generated"] is False
    assert pyproject["decision"] == "ignore"
    assert pyproject["generated"] is False


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


def test_generated_artifact_report_allows_package_metadata(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "package-lock.json").write_text("{}\n", encoding="utf-8")
    _git(repo, "add", "package-lock.json")
    _git(repo, "commit", "-m", "add package lock")

    report = generated_artifact_topology_report(repo)

    assert report["ok"] is True
    assert report["required_gaps"] == []


def test_path_policy_denies_generated_output_under_config() -> None:
    report = path_policy_for(".config/ethos/report.json")

    assert report["decision"] == "deny"
    assert report["required_gap"] == "generated_artifact_config_drift:.config/ethos/report.json"
