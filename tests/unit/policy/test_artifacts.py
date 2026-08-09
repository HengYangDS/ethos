"""Generated artifact topology and entrypoint routing tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.adapters.gates.generated_artifacts import generated_artifact_gate_report
from ethos.repository.policy.artifact_entrypoints import generated_artifact_entrypoint_audit
from ethos.repository.policy.artifacts import generated_artifact_topology_report
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.literal_cases import literal_case

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    ("script", "expected_gap_count"),
    literal_case(
        "policy.test_artifacts:parametrize:test_entrypoint_audit_requires_semantic_package_build_output:0"
    ),
)
def test_entrypoint_audit_requires_semantic_package_build_output(
    tmp_path: Path, script: str, expected_gap_count: int
) -> None:
    path = tmp_path / "tools/ci/scripts/example.sh"
    path.parent.mkdir(parents=True)
    path.write_text(script, encoding="utf-8")

    report = generated_artifact_entrypoint_audit(tmp_path)

    assert report["verdict"] == ("pass" if expected_gap_count == 0 else "block")
    assert report["summary"]["checked_file_count"] == 1
    assert report["summary"]["blocker_count"] == expected_gap_count


def test_entrypoint_audit_reads_structured_pixi_tasks(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        """
[tool.pixi.tasks]
package = { cmd = ["uv", "build", "--out-dir", "./dist/"] }
""".lstrip(),
        encoding="utf-8",
    )

    report = generated_artifact_entrypoint_audit(tmp_path)

    assert report["verdict"] == "block"
    assert report["required_gaps"] == [
        "generated_artifact_entrypoint_denied_generated_home:pyproject.toml:dist/"
    ]


def test_entrypoint_audit_reads_the_nox_python_test_owner(tmp_path: Path) -> None:
    path = tmp_path / "tools/ci/python_test_gate.py"
    path.parent.mkdir(parents=True)
    path.write_text(
        'PYTEST_CONFIG = ROOT / ".config/checks/pytest/pytest.ini"\npytest\n',
        encoding="utf-8",
    )

    report = generated_artifact_entrypoint_audit(tmp_path)

    assert report["verdict"] == "block"
    assert report["required_gaps"] == [
        ("generated_artifact_entrypoint_coverage_evidence_unrouted:tools/ci/python_test_gate.py"),
        ("generated_artifact_entrypoint_pytest_basetemp_unrouted:tools/ci/python_test_gate.py"),
        (
            "generated_artifact_entrypoint_pytest_config_argument_missing:"
            "tools/ci/python_test_gate.py"
        ),
    ]


def test_entrypoint_audit_allows_the_single_checkout_venv_and_rejects_the_retired_home(
    tmp_path: Path,
) -> None:
    script = tmp_path / "tools/ci/scripts/example.sh"
    script.parent.mkdir(parents=True)
    script.write_text(
        "tools/ci/scripts/with-python-runtime.sh -- .venv/bin/python -m ethos.cli status\n",
        encoding="utf-8",
    )
    assert generated_artifact_entrypoint_audit(tmp_path)["verdict"] == "pass"

    script.write_text(
        "tools/ci/scripts/with-python-runtime.sh -- build/runtime/venv/bin/python "
        "-m ethos.cli status\n",
        encoding="utf-8",
    )
    report = generated_artifact_entrypoint_audit(tmp_path)
    assert report["required_gaps"] == [
        "generated_artifact_entrypoint_retired_venv_runtime:tools/ci/scripts/example.sh"
    ]
    script.unlink()
    script = tmp_path / "tools/ci/scripts/configure-git-checkout.sh"
    script.write_text("python3 -c 'print(1)'\n", encoding="utf-8")
    report = generated_artifact_entrypoint_audit(tmp_path)
    assert report["required_gaps"] == [
        (f"generated_artifact_entrypoint_python_runtime_unbound:{script.relative_to(tmp_path)}")
    ]


def test_topology_report_merges_entrypoint_blockers(tmp_path: Path) -> None:
    path = tmp_path / "tools/ci/scripts/example.sh"
    path.parent.mkdir(parents=True)
    path.write_text(
        "tools/ci/scripts/with-python-runtime.sh -- uv build --out-dir ./dist/\n",
        encoding="utf-8",
    )

    report = generated_artifact_topology_report(
        tmp_path,
        ignored_local_paths=frozenset(),
        tracked_untracked_paths=(),
    )

    assert report["verdict"] == "block"
    assert report["summary"]["entrypoint_blocker_count"] == 2
    assert report["required_gaps"] == [
        "generated_artifact_entrypoint_denied_generated_home:tools/ci/scripts/example.sh:dist/",
        "generated_artifact_entrypoint_package_artifacts_unrouted:tools/ci/scripts/example.sh",
    ]


def test_topology_report_blocks_tracked_untracked_lifecycle_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    foreign = init_git_repo(tmp_path / "foreign")
    path = repo / "build/evidence/proof.json"
    path.parent.mkdir(parents=True)
    path.write_text("{}\n", encoding="utf-8")
    git(repo, "add", "-f", path.relative_to(repo).as_posix())
    monkeypatch.setenv("GIT_DIR", git(foreign, "rev-parse", "--absolute-git-dir"))

    report = generated_artifact_gate_report(repo)

    assert report["verdict"] == "block"
    assert report["required_gaps"] == [
        "generated_artifact_tracked_untracked_home:build/evidence/proof.json"
    ]


def test_topology_report_interprets_supplied_git_classification(tmp_path: Path) -> None:
    """Repository policy consumes facts without observing Git itself."""
    report = generated_artifact_topology_report(
        tmp_path,
        ignored_local_paths=frozenset(),
        tracked_untracked_paths=("build/evidence/proof.json",),
    )

    assert report["required_gaps"] == [
        "generated_artifact_tracked_untracked_home:build/evidence/proof.json"
    ]


def test_topology_report_classifies_every_generated_home_and_prunes_runtime_trees(
    tmp_path: Path,
) -> None:
    cases = (
        "build/evidence/proof.json",
        "evidence/review.json",
        ".config/result.json",
        ".pytest_cache",
        "build/runtime/flat/report.json",
        f"{'adopters'}/sample/report.json",
        "root-report.json",
    )
    for relative in cases:
        path = tmp_path / relative
        if path.suffix:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{}\n", encoding="utf-8")
        else:
            path.mkdir(parents=True)
    ignored = tmp_path / "ignored.json"
    ignored.write_text("{}\n", encoding="utf-8")
    pruned = tmp_path / ".venv/report.json"
    pruned.parent.mkdir()
    pruned.write_text("{}\n", encoding="utf-8")

    report = generated_artifact_topology_report(
        tmp_path,
        ignored_local_paths=frozenset({"ignored.json"}),
        tracked_untracked_paths=(),
    )

    assert "evidence/review.json" in report["review_paths"]
    assert report["ignored_local_paths"] == ["ignored.json"]
    assert report["allowed_paths"] == []
    assert not any(
        path.startswith((".venv", "build/evidence"))
        for paths in (report["review_paths"], report["denied_paths"])
        for path in paths
    )
    assert {".config/result.json", ".pytest_cache", "build/runtime/flat/report.json"} <= set(
        report["denied_paths"]
    )
    assert report["verdict"] == "block"
    assert report["summary"]["path_blocker_count"] >= 4
