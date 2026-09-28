"""Separate reusable image inputs from checkout-owned CI implementation."""

from __future__ import annotations

import shlex
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DOCKERFILE = ROOT / ".config/ci/supply/Dockerfile"
BOOTSTRAP = ROOT / "tools/ci/scripts/bootstrap-python.sh"


def _image_input_paths() -> tuple[str, ...]:
    """Read the one manifest emitted by the image's native checksum command."""
    source = DOCKERFILE.read_text(encoding="utf-8")
    section = source.split("&& sha256sum ", 1)[1].split(" > input.sha256", 1)[0]
    return tuple(shlex.split(section.replace("\\\n", " ")))


def test_image_manifest_binds_supply_declarations_not_build_only_product_code() -> None:
    """A product-code edit must not invalidate unchanged locked tool bytes."""
    inputs = set(_image_input_paths())

    assert {
        ".config/checks/node/runtime.toml",
        ".config/checks/ci/templates.toml",
        ".config/mise/config.toml",
        ".config/mise/mise.lock",
        ".config/ci/supply/Dockerfile",
        ".config/ci/supply/Dockerfile.dockerignore",
        "pyproject.toml",
        "uv.lock",
        "package.json",
        "package-lock.json",
    } <= inputs
    assert all((ROOT / path).is_file() for path in inputs)
    assert not any(path.startswith("src/ethos/") for path in inputs)
    assert "tools/ci/toolchain/native.py" not in inputs


def test_hosted_bootstrap_rechecks_cached_tools_with_current_checkout_code() -> None:
    """Removing source hashes requires an offline payload check before quality gates."""
    source = BOOTSTRAP.read_text(encoding="utf-8")
    assert "tools/ci/toolchain/native.py --root" in source
    installation = source.index("uv sync --locked --group dev")
    verifier = source.index("tools/ci/toolchain/native.py --root")
    assert installation < verifier < source.index("python_image_available()")
    guarded = source[installation : source.index("python_image_available()")]
    assert "ETHOS_CI_SUPPLY_MANIFEST" in guarded
    assert "--mise gitleaks scc syft" in guarded
    assert "${UV_PROJECT_ENVIRONMENT}/bin/python" in guarded


def test_os_supply_is_pinned_in_the_image_owner() -> None:
    """A stable base image must not silently select newer OS packages."""
    source = DOCKERFILE.read_text(encoding="utf-8")
    section = source.split("apt-get install -y --no-install-recommends ", 1)[1].split(
        "&& rm -rf", 1
    )[0]
    packages = shlex.split(section.replace("\\\n", " "))

    assert packages
    assert all("=" in package and package.partition("=")[2] for package in packages)
