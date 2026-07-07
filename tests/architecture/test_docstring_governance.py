from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_docstring_policy_admits_google_style_with_signature_checks() -> None:
    policy = tomllib.loads(
        (ROOT / ".config/checks/docstrings/policy.toml").read_text(encoding="utf-8")
    )
    ruff = (ROOT / ".config/checks/ruff/ruff.toml").read_text(encoding="utf-8")
    runner = (ROOT / ".config/ci/scripts/run-docstring-coverage.sh").read_text(encoding="utf-8")

    assert policy["style"] == "google"
    assert policy["allow_short_docstrings"] is True
    assert policy["check_structured_signature"] is True
    assert policy["forbid_legacy_sections"] is True
    assert 'convention = "google"' in ruff
    assert "docstring-code-format = true" in ruff
    assert "ethos quality docstrings" in runner


def test_docstring_gate_exposes_broader_nonblocking_inventory() -> None:
    source = (ROOT / "packages/ethos/src/ethos/repository/policy/docstrings/core.py").read_text(
        encoding="utf-8"
    )
    quality = (ROOT / "packages/ethos/src/ethos/surface/cli/quality.py").read_text(encoding="utf-8")

    assert "advisory_public_definition_inventory" in source
    assert '"blocking": False' in source
    assert "advisory_missing_count" in quality
