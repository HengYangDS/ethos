"""Reference carrier dispatch and product-independence policy tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.repository.policy.references.carriers import reference_carrier
from ethos.repository.policy.references.closure import repository_semantic_closure
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


@pytest.mark.parametrize(
    "declaration",
    [
        ".config/checks/secrets/supply.toml",
        ".config/checks/lychee/supply.toml",
        ".config/release/supply-chain.toml",
    ],
)
def test_native_supply_owns_its_executable_without_an_installer(
    tmp_path: Path, declaration: str
) -> None:
    """Replacing a transport cannot erase or fabricate native tool ownership."""
    source = tmp_path / "src/ethos/runtime.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        'import subprocess\nsubprocess.run(["declared-native-check", "--version"], check=True)\n',
        encoding="utf-8",
    )
    policy = tmp_path / declaration
    policy.parent.mkdir(parents=True)
    policy.write_text('tool = "declared-native-check"\n', encoding="utf-8")

    assert repository_semantic_closure(tmp_path)["required_gaps"] == []

    policy.unlink()
    assert repository_semantic_closure(tmp_path)["required_gaps"] == [
        "semantic_consumer_orphan:executable:declared-native-check:src/ethos/runtime.py"
    ]


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

    assert repository_semantic_closure(tmp_path)["required_gaps"] == [
        "semantic_consumer_orphan:executable:wcp:src/example/runtime.py",
        "semantic_consumer_orphan:executable:workstation:src/example/runtime.py",
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

    assert repository_semantic_closure(tmp_path)["required_gaps"] == []
