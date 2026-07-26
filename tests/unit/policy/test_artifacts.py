"""Generated artifact entrypoint routing tests."""

from __future__ import annotations

import pytest

from ethos.repository.policy.artifacts import _package_build_route_findings


@pytest.mark.parametrize(
    ("producer_text", "expected_gap_count"),
    [
        (
            'artifact_dir="${repo_root}/build/artifacts/python"\n'
            'uv build --offline --wheel --out-dir "${artifact_dir}" --clear',
            0,
        ),
        ('uv build --offline --wheel --out-dir "${artifact_dir}" --clear', 1),
        (
            'artifact_dir="${repo_root}/build/runtime/python"\n'
            'uv build --offline --wheel --out-dir "${artifact_dir}" --clear',
            1,
        ),
        (
            'other_dir="${repo_root}/build/artifacts/python"\n'
            'uv build --offline --wheel --out-dir "${artifact_dir}" --clear',
            1,
        ),
    ],
)
def test_package_build_route_requires_semantic_out_dir_assignment(
    producer_text: str, expected_gap_count: int
) -> None:
    findings = _package_build_route_findings("tools/ci/scripts/example.sh", producer_text)

    assert len(findings) == expected_gap_count
