"""Contracts for owner scripts that re-enter the ETHOS package runtime."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_product_boundary_syncs_the_ethos_package_runtime() -> None:
    """The product-boundary owner script must re-enter uv after handoff."""
    script = (ROOT / "tools/ci/scripts/run-product-boundary.sh").read_text(encoding="utf-8")

    assert "uv run --package ethos python -m ethos.cli quality" in script
    assert "${UV_PROJECT_ENVIRONMENT}/bin/python" not in script


def test_governance_kernel_syncs_before_using_its_optional_python_override() -> None:
    """The default interpreter must come from a synced ETHOS package runtime."""
    script = (ROOT / "tools/ci/scripts/run-governance-kernel.sh").read_text(encoding="utf-8")

    assert "$(uv run --package ethos python -c 'import sys; print(sys.executable)')" in script
    assert '"${ethos_python}" -m ethos.cli quality governance-kernel --json' in script
    assert "${UV_PROJECT_ENVIRONMENT}/bin/python" not in script
