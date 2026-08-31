from __future__ import annotations

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

from ethos.adapters.repo.runtime.materialization.input_resolution import resolve_node_runtime
from ethos.adapters.repo.runtime.source import source_build_identity
from ethos.repository.release.identity import BuildIdentity
from ethos.repository.release.identity import build_identity
from ethos.repository.release.identity import load_build_identity_bytes
from ethos.repository.release.identity import product_version
from ethos.repository.release.identity import projected_package_versions
from ethos.repository.release.identity import wheel_build_identity


def test_version_file_is_the_single_product_owner_and_manifests_are_projections() -> None:
    root = Path.cwd()
    product = product_version(root)
    pyproject = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))

    assert product == "0.2.0-alpha.3"
    assert "version" not in pyproject["project"]
    assert "version" in pyproject["project"]["dynamic"]
    assert "version" not in json.loads((root / "package.json").read_text(encoding="utf-8"))
    assert projected_package_versions(root) == {
        "distributions/npm/package.json": product,
        "package-lock.json#packages/distributions/npm": product,
    }
    assert "0.1.0a2" not in (root / "pyproject.toml").read_text(encoding="utf-8")


def test_two_source_commits_produce_distinct_wheel_metadata(tmp_path: Path) -> None:
    root = Path.cwd()
    repo = tmp_path / "repo"
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
    first = _build_wheel(repo, tmp_path / "first")

    readme = repo / "README.md"
    readme.write_text(readme.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "--quiet", "-m", "second source")
    second = _build_wheel(repo, tmp_path / "second")

    assert first.source_commit != second.source_commit
    assert first.source_tree != second.source_tree
    assert first.distribution_version != second.distribution_version
    assert Version(first.distribution_version) < Version("0.2.0a3")
    assert Version(second.distribution_version) < Version("0.2.0a3")


def test_environment_cannot_promote_a_source_build_to_release(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ETHOS_BUILD_CHANNEL", "accepted")

    identity = source_build_identity(Path.cwd())

    assert Version(identity.distribution_version) < Version("0.2.0a3")


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

    assert Version(identity.distribution_version) < Version("0.2.0a3")


@pytest.mark.parametrize("raw", ["1", "1.2", "v1.2.3", "1.2.3a1", "1.2.3-alpha"])
def test_product_version_rejects_noncanonical_semver(tmp_path: Path, raw: str) -> None:
    (tmp_path / "VERSION").write_text(raw + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="product_version_invalid"):
        product_version(tmp_path)


def test_projected_package_version_drift_is_reported(tmp_path: Path) -> None:
    (tmp_path / "VERSION").write_text("1.2.3\n", encoding="utf-8")
    (tmp_path / "package.json").write_text('{"version":"1.2.2"}\n', encoding="utf-8")
    (tmp_path / "package-lock.json").write_text(
        json.dumps(
            {
                "packages": {
                    "": {},
                    "distributions/npm": {"version": "1.2.3"},
                }
            }
        ),
        encoding="utf-8",
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


def _build_wheel(repo: Path, output: Path) -> BuildIdentity:
    node, npm_cli = resolve_node_runtime()
    output.mkdir()
    subprocess.run(
        (
            str(Path(sys.executable).with_name("uv")),
            "build",
            "--offline",
            "--wheel",
            "--out-dir",
            str(output),
            "--no-create-gitignore",
        ),
        cwd=repo,
        env={
            **os.environ,
            "ETHOS_BUILD_NODE": str(node),
            "ETHOS_BUILD_NPM_CLI": str(npm_cli),
        },
        check=True,
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
