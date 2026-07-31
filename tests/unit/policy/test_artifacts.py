"""Generated artifact topology and entrypoint routing tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.repository.policy.artifact_entrypoints import generated_artifact_entrypoint_audit
from ethos.repository.policy.artifacts import generated_artifact_topology_report
from tests.support.lane_helpers import git
from tests.support.lane_helpers import init_repo

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    ("script", "expected_gap_count"),
    [
        (
            (
                'artifact_dir="${repo_root}/build/artifacts/python"\n'
                "tools/ci/scripts/with-python-runtime.sh -- uv build "
                '--offline --wheel --out-dir "${artifact_dir}" --clear'
            ),
            0,
        ),
        (
            (
                "tools/ci/scripts/with-python-runtime.sh -- uv build "
                '--offline --wheel --out-dir "${artifact_dir}" --clear'
            ),
            1,
        ),
        (
            (
                'artifact_dir="${repo_root}/build/runtime/python"\n'
                "tools/ci/scripts/with-python-runtime.sh -- uv build "
                '--offline --wheel --out-dir "${artifact_dir}" --clear'
            ),
            1,
        ),
        (
            (
                'other_dir="${repo_root}/build/artifacts/python"\n'
                "tools/ci/scripts/with-python-runtime.sh -- uv build "
                '--offline --wheel --out-dir "${artifact_dir}" --clear'
            ),
            1,
        ),
    ],
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


def test_topology_report_merges_entrypoint_blockers(tmp_path: Path) -> None:
    path = tmp_path / "tools/ci/scripts/example.sh"
    path.parent.mkdir(parents=True)
    path.write_text(
        "tools/ci/scripts/with-python-runtime.sh -- uv build --out-dir ./dist/\n",
        encoding="utf-8",
    )

    report = generated_artifact_topology_report(tmp_path)

    assert report["verdict"] == "block"
    assert report["summary"]["entrypoint_blocker_count"] == 2
    assert report["required_gaps"] == [
        "generated_artifact_entrypoint_denied_generated_home:tools/ci/scripts/example.sh:dist/",
        "generated_artifact_entrypoint_package_artifacts_unrouted:tools/ci/scripts/example.sh",
    ]


def test_topology_report_blocks_tracked_untracked_lifecycle_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_repo(tmp_path / "repo")
    foreign = init_repo(tmp_path / "foreign")
    path = repo / "build/evidence/proof.json"
    path.parent.mkdir(parents=True)
    path.write_text("{}\n", encoding="utf-8")
    git(repo, "add", "-f", path.relative_to(repo).as_posix())
    monkeypatch.setenv("GIT_DIR", git(foreign, "rev-parse", "--absolute-git-dir"))

    report = generated_artifact_topology_report(repo)

    assert report["verdict"] == "block"
    assert report["required_gaps"] == [
        "generated_artifact_tracked_untracked_home:build/evidence/proof.json"
    ]
