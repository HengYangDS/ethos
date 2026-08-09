"""Reference carrier dispatch and product-independence policy tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.repository.policy.references.carriers import reference_carrier
from ethos.repository.policy.references.closure import repository_product_reference_gaps
from tests.support.literal_cases import literal_case

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    ("path", "carrier"),
    literal_case(
        "policy.test_reference_carriers:parametrize:test_reference_carriers_have_one_deterministic_dispatch:0"
    ),
)
def test_reference_carriers_have_one_deterministic_dispatch(path: str, carrier: str) -> None:
    """Every supported path resolves through the one ordered carrier table."""
    assert reference_carrier(path).name == carrier


def test_reference_closure_rejects_wcp_and_workstation_as_undeclared_dependencies(
    tmp_path: Path,
) -> None:
    """ETHOS remains closed when an external workstation product is absent."""
    source = tmp_path / "src/example/runtime.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        """import subprocess

subprocess.run(["workstation", "status"], check=True)
subprocess.run(["wcp", "inspect"], check=True)
""",
        encoding="utf-8",
    )
    (tmp_path / "system").mkdir()
    (tmp_path / "system/surfaces.toml").write_text(
        '[[surface]]\nname = "runtime"\ncarrier = "src/example"\n',
        encoding="utf-8",
    )
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "example"\nversion = "1"\n',
        encoding="utf-8",
    )

    assert repository_product_reference_gaps(tmp_path) == [
        "product_reference_not_admitted_at_baseline:executable:wcp",
        "product_reference_not_admitted_at_baseline:executable:workstation",
    ]


def test_reference_closure_is_green_without_wcp_or_workstation(tmp_path: Path) -> None:
    """An ETHOS-native product requires no external workstation declaration."""
    source = tmp_path / "src/example/runtime.py"
    source.parent.mkdir(parents=True)
    source.write_text("def inspect() -> None:\n    pass\n", encoding="utf-8")
    (tmp_path / "system").mkdir()
    (tmp_path / "system/surfaces.toml").write_text(
        '[[surface]]\nname = "runtime"\ncarrier = "src/example"\n',
        encoding="utf-8",
    )
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "example"\nversion = "1"\n',
        encoding="utf-8",
    )

    assert repository_product_reference_gaps(tmp_path) == []
