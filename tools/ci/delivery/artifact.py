"""Observe one source-bound build output shared by tests and install acceptance."""

from __future__ import annotations

import hashlib
from pathlib import Path

from ethos.adapters.repo.runtime.source import source_build_identity
from ethos.adapters.repo.runtime.transition import PackageArtifact
from ethos.repository.release.identity import build_identity
from ethos.repository.release.identity import is_release_build
from ethos.repository.release.identity import wheel_build_identity


def selected_wheel(repo: Path, *, head: str, artifacts: Path | None = None) -> PackageArtifact:
    """Require exactly one regular wheel for the current complete source identity."""
    directory = artifacts if artifacts is not None else repo / "build/artifacts/python"
    _require_owned_directory(repo, directory)
    wheels = tuple(directory.glob("ethos-*.whl"))
    if directory.is_symlink() or len(wheels) != 1:
        message = "package_build_output_invalid"
        raise ValueError(message)
    selected = _observe(wheels[0])
    expected = source_build_identity(repo)
    if expected.source_commit != head or selected.build != expected:
        message = "package_build_source_stale"
        raise ValueError(message)
    return selected


def require_artifact_current(artifact: PackageArtifact, *, head: str, repo: Path) -> None:
    """Reobserve selected bytes before effects and after an acceptance attempt."""
    _require_owned_directory(repo, artifact.path.parent)
    if (
        artifact.build.source_commit != head
        or artifact.path.is_symlink()
        or not artifact.path.is_file()
        or _observe(artifact.path) != artifact
    ):
        message = "package_acceptance_artifact_changed"
        raise ValueError(message)
    source = source_build_identity(repo)
    expected = build_identity(
        product=source.product_version,
        source_commit=source.source_commit,
        source_tree=source.source_tree,
        release=is_release_build(artifact.build),
    )
    if expected != artifact.build:
        message = "package_acceptance_artifact_changed"
        raise ValueError(message)


def _observe(wheel: Path) -> PackageArtifact:
    if wheel.is_symlink() or not wheel.is_file():
        message = "package_build_output_invalid"
        raise ValueError(message)
    with wheel.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return PackageArtifact(wheel, digest, wheel_build_identity(wheel))


def _require_owned_directory(repo: Path, directory: Path) -> None:
    """Keep build outputs beneath their exact repository without redirected parents."""
    root = repo.resolve()
    candidate = directory.absolute()
    if not candidate.is_relative_to(repo.absolute()) or not candidate.resolve().is_relative_to(
        root
    ):
        message = "package_build_output_invalid"
        raise ValueError(message)
    relative = candidate.relative_to(repo.absolute())
    if any(
        (repo / Path(*relative.parts[:index])).is_symlink()
        for index in range(1, len(relative.parts) + 1)
    ):
        message = "package_build_output_invalid"
        raise ValueError(message)
