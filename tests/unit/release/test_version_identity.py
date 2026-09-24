"""Preserve one product version owner across source and distribution identities."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tomllib
import zipfile
from email.parser import Parser
from pathlib import Path

import pytest
from packaging.version import Version

from ethos.adapters.repo.runtime.materialization.node_package_supply import (
    resolve_node_package_supply,
)
from ethos.adapters.repo.runtime.source import source_build_identity
from ethos.repository.release.identity import BuildIdentity
from ethos.repository.release.identity import build_identity
from ethos.repository.release.identity import load_build_identity_bytes
from ethos.repository.release.identity import product_version
from ethos.repository.release.identity import projected_package_versions
from ethos.repository.release.identity import wheel_build_identity
from tools.ci import sessions
from tools.ci.delivery import pipeline
from tools.ci.toolchain.environment import ProjectRuntime


def test_version_file_is_the_single_product_owner_and_manifests_are_projections() -> None:
    root = Path.cwd()
    product = product_version(root)
    pyproject = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))

    assert product == "0.2.0-alpha.5"
    assert "version" not in pyproject["project"]
    assert "version" in pyproject["project"]["dynamic"]
    assert "version" not in json.loads((root / "package.json").read_text(encoding="utf-8"))
    assert projected_package_versions(root) == {
        "distributions/npm/package.json": product,
        "package-lock.json#packages/distributions/npm": product,
    }
    assert "0.1.0a2" not in (root / "pyproject.toml").read_text(encoding="utf-8")


def test_source_and_release_builds_preserve_exact_metadata(tmp_path: Path, monkeypatch) -> None:
    root = Path.cwd()
    repo = _build_repository(root, tmp_path / "repo")
    first = _build_wheel(repo, tmp_path / "first")
    with zipfile.ZipFile(next((tmp_path / "first").glob("*.whl"))) as archive:
        assert "ethos/data/skills/ethos-repository-work/SKILL.md" in archive.namelist()

    readme = repo / "README.md"
    readme.write_text(readme.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "--quiet", "-m", "second source")
    second = _build_wheel(repo, tmp_path / "second")

    assert first.source_commit != second.source_commit
    assert first.source_tree != second.source_tree
    assert first.distribution_version != second.distribution_version
    assert Version(first.distribution_version) < Version("0.2.0a5")
    assert Version(second.distribution_version) < Version("0.2.0a5")

    source_head = second.source_commit
    monkeypatch.setattr(pipeline, "accepted_release_source", lambda _root, head: {"head": head})
    monkeypatch.setattr(pipeline, "proof_for_repository_transition", lambda *_: (object(), []))
    before = subprocess.check_output(("git", "status", "--porcelain"), cwd=repo)

    class BuildSession:
        posargs = ("--release", "--expect-head", source_head)

        def run(self, *command, env):
            subprocess.run(command, cwd=repo, env={**os.environ, **env}, check=True, timeout=90)

    monkeypatch.setattr(sessions, "RUNTIME", ProjectRuntime.discover(repo))
    monkeypatch.setattr(
        ProjectRuntime, "node_package_supply", lambda _: resolve_node_package_supply(root)
    )
    sessions.build(BuildSession())
    released = wheel_build_identity(next((repo / "build/artifacts/release/python").glob("*.whl")))
    assert released.distribution_version == "0.2.0a5"
    assert released.source_commit == source_head
    assert released.source_tree == second.source_tree
    candidate = pipeline.prepare_release_candidate(repo, source_head)
    assert candidate.build == released
    assert candidate.sha256 == hashlib.sha256(candidate.path.read_bytes()).hexdigest()
    assert not tuple((repo / "build/runtime/work").iterdir())
    assert subprocess.check_output(("git", "status", "--porcelain"), cwd=repo) == before
    for proof, gaps in ((None, []), (object(), ["release_source_not_proven"])):
        with monkeypatch.context() as denied:
            denied.setattr(
                pipeline, "proof_for_repository_transition", lambda *_, value=(proof, gaps): value
            )
            with pytest.raises(ValueError, match="release_source_not_proven"):
                sessions.build(BuildSession())
            with pytest.raises(ValueError, match="release_source_not_proven"):
                pipeline.prepare_release_candidate(repo, source_head)
        assert (
            wheel_build_identity(next((repo / "build/artifacts/release/python").glob("*.whl")))
            == released
        )
        assert not tuple((repo / "build/runtime/work").iterdir())
    with (
        pytest.raises(ValueError, match="release_build_source_stale"),
        pipeline.release_build_source(repo, tmp_path / "stale", head=first.source_commit),
    ):
        pytest.fail("stale source admitted")
    with (
        pytest.raises(ValueError, match="release_build_source_dirty"),
        pipeline.release_build_source(repo, tmp_path / "changed", head=source_head) as prepared,
    ):
        readme.write_text("dirty source\n")
    assert not prepared.exists()
    with (
        pytest.raises(ValueError, match="release_build_source_dirty"),
        pipeline.release_build_source(repo, tmp_path / "dirty", head=source_head),
    ):
        pytest.fail("dirty source admitted")


def test_release_build_requires_explicit_exact_arguments() -> None:
    assert pipeline.release_build_head(("--release", "--expect-head", "a" * 40)) == "a" * 40
    assert pipeline.release_build_head(()) == ""
    for args in (
        ("--release",),
        ("--expect-head", "a" * 40),
        ("--release", "--expect-head", "bad"),
        ("--release", "--expect-head"),
        ("--release", "--expect-head", "a" * 40, "--unknown"),
    ):
        with pytest.raises(ValueError, match="release_build_arguments_invalid"):
            pipeline.release_build_head(args)


def test_sdist_rebuild_reuses_the_identical_node_package_supply(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    _build_wheel(Path.cwd(), artifacts, sdist=True)
    direct_wheel = next(artifacts.glob("*.whl"))
    source_root = tmp_path / "source"
    shutil.unpack_archive(next(artifacts.glob("*.tar.gz")), source_root, filter="data")
    source = next(path for path in source_root.iterdir() if path.is_dir())
    rebuilt = tmp_path / "rebuilt"
    _build_wheel(source, rebuilt, embedded_supply=True)
    rebuilt_wheel = next(rebuilt.glob("*.whl"))

    assert (
        hashlib.sha256(direct_wheel.read_bytes()).digest()
        == hashlib.sha256(rebuilt_wheel.read_bytes()).digest()
    )


def test_environment_cannot_promote_a_source_build_to_release(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ETHOS_BUILD_CHANNEL", "accepted")

    identity = source_build_identity(Path.cwd())

    assert Version(identity.distribution_version) < Version("0.2.0a5")


def test_release_identity_uses_exact_product_projection_only_when_explicit() -> None:
    identity = build_identity(
        product="0.2.0-alpha.2",
        source_commit="a" * 40,
        source_tree="b" * 40,
        release=True,
    )

    assert identity == BuildIdentity(
        product_version="0.2.0-alpha.2",
        distribution_version="0.2.0a2",
        source_commit="a" * 40,
        source_tree="b" * 40,
    )


def test_development_distribution_identity_uses_the_complete_source_coordinates() -> None:
    common = "a" * 12
    first = build_identity(
        product="0.2.0-alpha.2",
        source_commit=common + "1" * 28,
        source_tree=common + "2" * 28,
    )
    second = build_identity(
        product="0.2.0-alpha.2",
        source_commit=common + "3" * 28,
        source_tree=common + "4" * 28,
    )

    assert first.distribution_version != second.distribution_version
    assert first.distribution_version.startswith("0.2.0a2.dev0+")
    assert first.source_commit[:12] in first.distribution_version
    assert first.source_tree[:12] in first.distribution_version


def test_accepted_checkout_remains_a_development_build() -> None:
    identity = source_build_identity(Path.cwd())

    assert Version(identity.distribution_version) < Version("0.2.0a5")


@pytest.mark.parametrize("raw", ["1", "1.2", "v1.2.3", "1.2.3a1", "1.2.3-alpha"])
def test_product_version_rejects_noncanonical_semver(tmp_path: Path, raw: str) -> None:
    (tmp_path / "VERSION").write_text(raw + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="product_version_invalid"):
        product_version(tmp_path)


def test_projected_package_version_drift_is_reported(tmp_path: Path) -> None:
    (tmp_path / "VERSION").write_text("1.2.3\n", encoding="utf-8")
    (tmp_path / "package.json").write_text('{"version":"1.2.2"}\n', encoding="utf-8")
    packages = {"": {}, "distributions/npm": {"version": "1.2.3"}}
    (tmp_path / "package-lock.json").write_text(
        json.dumps({"packages": packages}), encoding="utf-8"
    )
    package = tmp_path / "distributions/npm/package.json"
    package.parent.mkdir(parents=True)
    package.write_text('{"version":"1.2.3"}\n', encoding="utf-8")

    with pytest.raises(ValueError, match=r"package_version_parallel_owner:package\.json"):
        projected_package_versions(tmp_path)


def test_build_identity_loader_rejects_distribution_or_release_drift() -> None:
    identity = build_identity(
        product="0.2.0-alpha.2",
        source_commit="a" * 40,
        source_tree="b" * 40,
    )
    payload = identity.projection()
    payload["distribution_version"] = "0.2.0a2.dev0+wrong"
    with pytest.raises(ValueError, match="package_build_identity_invalid"):
        load_build_identity_bytes(json.dumps(payload).encode())
    base = {
        "product": "1.2.3",
        "source_commit": "a" * 40,
        "source_tree": "b" * 40,
    }
    for change, reason in (
        ({"source_commit": "x"}, "build_source_identity_invalid"),
        ({"release": "invalid"}, "release_build_flag_invalid"),
        ({"product": "1.2.3.post1"}, "product_version_invalid"),
    ):
        with pytest.raises(ValueError, match=reason):
            build_identity(**(base | change))
    for raw in (b"{}", json.dumps(build_identity(**base).projection()).encode(), b"not-json"):
        with pytest.raises(ValueError, match="package_build_identity_invalid"):
            load_build_identity_bytes(raw)


def _build_wheel(
    repo: Path, output: Path, *, sdist: bool = False, embedded_supply: bool = False
) -> BuildIdentity:
    output.mkdir()
    environment = os.environ.copy()
    environment.pop("ETHOS_NODE_PACKAGE_SUPPLY", None)
    if not embedded_supply:
        environment["ETHOS_NODE_PACKAGE_SUPPLY"] = str(resolve_node_package_supply(Path.cwd()))
    subprocess.run(
        (
            str(Path(sys.executable).with_name("uv")),
            "build",
            "--offline",
            "--no-build-isolation",
            "--python",
            sys.executable,
            "--wheel",
            "--out-dir",
            str(output),
            "--no-create-gitignore",
            *(("--sdist",) if sdist else ()),
        ),
        cwd=repo,
        env=environment,
        check=True,
        timeout=90,
    )
    wheel = next(output.glob("ethos-*.whl"))
    identity = wheel_build_identity(wheel)
    with zipfile.ZipFile(wheel) as archive:
        metadata_path = next(
            name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
        )
        metadata = Parser().parsestr(archive.read(metadata_path).decode("utf-8"))
    assert metadata["Version"] == identity.distribution_version
    return identity


def _git(repo: Path, *args: str) -> None:
    subprocess.run(("git", *args), cwd=repo, check=True)


def _build_repository(root: Path, repo: Path) -> Path:
    """Create an independent candidate snapshot without sharing Git or mutable files."""
    repo.mkdir()
    tracked = subprocess.check_output(
        ("git", "ls-files", "-co", "--exclude-standard", "-z"), cwd=root
    ).split(b"\0")
    for raw in tracked:
        if not raw:
            continue
        relative = Path(os.fsdecode(raw))
        source = root / relative
        if not source.exists():
            continue
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target, follow_symlinks=False)
    _git(repo, "init", "--quiet", "--initial-branch=work/build-identity")
    _git(repo, "config", "user.name", "ETHOS Test")
    _git(repo, "config", "user.email", "ethos@example.invalid")
    _git(repo, "add", "-A")
    _git(repo, "commit", "--quiet", "-m", "first source")
    return repo
