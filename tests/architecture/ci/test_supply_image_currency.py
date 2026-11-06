"""A supply image is current while its manifest inputs equal their bytes at its build commit."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tools.ci import supply_image

ROOT = Path(__file__).resolve().parents[3]


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ("git", *args), cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def repository(tmp_path: Path) -> tuple[Path, str]:
    """A repository whose Dockerfile hashes two inputs, committed as the image's source."""
    repo = tmp_path / "repo"
    (repo / ".config/ci/supply").mkdir(parents=True)
    (repo / ".config/ci/supply/Dockerfile").write_text(
        "RUN true \\\n    && sha256sum uv.lock \\\n         package-lock.json \\\n"
        "         > input.sha256 \\\n    && true\n",
        encoding="utf-8",
    )
    (repo / "uv.lock").write_text("locked\n", encoding="utf-8")
    (repo / "package-lock.json").write_text("{}\n", encoding="utf-8")
    _git(repo.parent, "init", "--quiet", "--initial-branch=main", str(repo))
    _git(repo, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "add", "-A")
    _git(repo, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-qm", "s")
    return repo, _git(repo, "rev-parse", "HEAD")


def test_the_manifest_inputs_are_read_from_the_dockerfile(repository) -> None:
    repo, _source = repository
    assert supply_image.manifest_inputs(repo) == (
        ".config/ci/supply/Dockerfile",
        "uv.lock",
        "package-lock.json",
    )


def test_an_unchanged_tree_is_current(repository) -> None:
    repo, source = repository
    assert supply_image.stale_inputs(repo, source) == []


def test_an_input_changed_since_the_build_commit_is_stale(repository) -> None:
    """A lock moved after the image was built makes the bound image stale."""
    repo, source = repository
    (repo / "uv.lock").write_text("moved\n", encoding="utf-8")
    assert supply_image.stale_inputs(repo, source) == ["supply_image_stale:uv.lock"]


def test_an_unknown_source_commit_refuses(repository) -> None:
    repo, _source = repository
    assert supply_image.stale_inputs(repo, "f" * 40) == ["supply_image_source_unavailable"]


def test_the_binding_records_the_commit_that_built_the_bound_image() -> None:
    """The pipeline names the bound digest and the commit it was built from, in one place."""
    digest, source = supply_image.binding(ROOT)
    assert digest.startswith("sha256:")
    assert len(digest) == 71
    assert len(source) == 40
    assert set(source) <= set("0123456789abcdef")
    assert supply_image.stale_inputs(ROOT, source) == []


def test_gitlab_prepares_exactly_the_tools_the_image_carries() -> None:
    """GitLab's offline bootstrap stages the tools the image staged; neither list may drift."""
    dockerfile = (ROOT / ".config/ci/supply/Dockerfile").read_text(encoding="utf-8")
    staged = [
        [tool.strip(')"') for tool in line.split("--mise", 1)[1].split("\\")[0].split()]
        for line in dockerfile.splitlines()
        if "--mise" in line and ("toolchain/native.py" in line or "toolchain.native" in line)
    ]
    gitlab = (ROOT / ".gitlab-ci.yml").read_text(encoding="utf-8")
    bootstrap = [
        line.split("--mise", 1)[1].split()
        for line in gitlab.splitlines()
        if "tools.ci.toolchain.native --root . --mise" in line
    ]
    assert staged
    assert bootstrap
    assert {tuple(sorted(tools)) for tools in staged} == {tuple(sorted(bootstrap[0]))}
    assert {tuple(sorted(tools)) for tools in bootstrap} == {tuple(sorted(bootstrap[0]))}
