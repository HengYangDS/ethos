"""Committed release versions come only from explicit native version fields."""

from pathlib import Path

import pytest

from ethos.adapters.repo.release import committed_release_version
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import init_git_repo


@pytest.mark.parametrize(
    ("path", "content", "gap"),
    [
        ("package.json", '{"version":"1.2.3"}', ""),
        ("pyproject.toml", '[project]\nversion="1.2.3"\n', ""),
        (
            "pyproject.toml",
            '[project]\nversion="1.2.3"\ndynamic=["version"]\n',
            "release_version_source_invalid",
        ),
        ("package.json", '{"version":3}', "release_version_source_invalid"),
        ("package.json", "[]", "release_version_source_invalid"),
    ],
)
def test_native_version_sources_are_explicit(
    tmp_path: Path, path: str, content: str, gap: str
) -> None:
    repo = init_git_repo(tmp_path / "version")
    commit_fixture_file(repo, path, content, "version fixture")
    if gap:
        with pytest.raises(ValueError, match=gap):
            committed_release_version(repo, "HEAD")
    else:
        assert committed_release_version(repo, "HEAD") == {"version": "1.2.3", "source": path}
