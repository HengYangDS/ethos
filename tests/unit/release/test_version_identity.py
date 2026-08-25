from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest
from packaging.version import Version

from ethos.repository.release.identity import BuildIdentity
from ethos.repository.release.identity import build_identity
from ethos.repository.release.identity import product_version
from ethos.repository.release.identity import projected_package_versions


def test_version_file_is_the_single_product_owner_and_manifests_are_projections() -> None:
    root = Path.cwd()
    product = product_version(root)
    pyproject = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))

    assert product == "0.1.0-alpha.3"
    assert "version" not in pyproject["project"]
    assert "version" in pyproject["project"]["dynamic"]
    assert projected_package_versions(root) == {
        "package.json": product,
        "package-lock.json": product,
        "distributions/npm/package.json": product,
    }
    assert "0.1.0a2" not in (root / "pyproject.toml").read_text(encoding="utf-8")


def test_unreleased_distribution_identity_is_unique_pep440_and_below_release() -> None:
    first = build_identity(
        product="0.1.0-alpha.3",
        source_commit="a" * 40,
        source_tree="b" * 40,
        channel="development",
        acceptance_state="unaccepted",
    )
    second = build_identity(
        product="0.1.0-alpha.3",
        source_commit="c" * 40,
        source_tree="d" * 40,
        channel="development",
        acceptance_state="unaccepted",
    )

    assert first.distribution_version != second.distribution_version
    assert Version(first.distribution_version) < Version("0.1.0a3")
    assert Version(second.distribution_version) < Version("0.1.0a3")
    assert first.product_version == second.product_version == "0.1.0-alpha.3"


def test_accepted_identity_uses_exact_product_projection() -> None:
    identity = build_identity(
        product="0.1.0-alpha.3",
        source_commit="a" * 40,
        source_tree="b" * 40,
        channel="accepted",
        acceptance_state="accepted",
    )

    assert identity == BuildIdentity(
        product_version="0.1.0-alpha.3",
        distribution_version="0.1.0a3",
        source_commit="a" * 40,
        source_tree="b" * 40,
        channel="accepted",
        acceptance_state="accepted",
    )


@pytest.mark.parametrize("raw", ["1", "1.2", "v1.2.3", "1.2.3a1", "1.2.3-alpha"])
def test_product_version_rejects_noncanonical_semver(tmp_path: Path, raw: str) -> None:
    (tmp_path / "VERSION").write_text(raw + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="product_version_invalid"):
        product_version(tmp_path)


def test_projected_package_version_drift_is_reported(tmp_path: Path) -> None:
    (tmp_path / "VERSION").write_text("1.2.3\n", encoding="utf-8")
    (tmp_path / "package.json").write_text('{"version":"1.2.2"}\n', encoding="utf-8")
    (tmp_path / "package-lock.json").write_text(
        json.dumps({"version": "1.2.3", "packages": {"": {"version": "1.2.3"}}}),
        encoding="utf-8",
    )
    package = tmp_path / "distributions/npm/package.json"
    package.parent.mkdir(parents=True)
    package.write_text('{"version":"1.2.3"}\n', encoding="utf-8")

    with pytest.raises(ValueError, match="package_version_projection_drift:package.json"):
        projected_package_versions(tmp_path)
