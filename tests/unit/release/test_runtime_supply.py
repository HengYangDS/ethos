from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import cast

import pytest

from ethos.adapters.repo.runtime.supply import ImmutablePackageSupply
from ethos.adapters.repo.runtime.supply import LockedSourceSupply
from ethos.adapters.repo.runtime.supply import runtime_supply

if TYPE_CHECKING:
    from pathlib import Path


def test_runtime_supply_is_selected_by_explicit_capability_not_source_shape(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    wheel = tmp_path / "ethos.whl"
    wheel.write_bytes(b"wheel")

    locked = runtime_supply(
        mode="locked-source",
        source=source,
        wheel=wheel,
        interpreter=tmp_path / "bootstrap-python",
    )
    packaged = runtime_supply(
        mode="immutable-package",
        source=source,
        wheel=wheel,
        interpreter=tmp_path / "python-home",
    )

    assert isinstance(locked, LockedSourceSupply)
    assert isinstance(packaged, ImmutablePackageSupply)
    assert locked.interpreter == tmp_path / "bootstrap-python"


def test_runtime_supply_rejects_unknown_or_incomplete_capability(tmp_path: Path) -> None:
    wheel = tmp_path / "ethos.whl"
    wheel.write_bytes(b"wheel")

    with pytest.raises(ValueError, match="runtime_supply_mode_invalid"):
        runtime_supply(
            mode=cast("Any", "guess"),
            source=tmp_path,
            wheel=wheel,
        )
    with pytest.raises(ValueError, match="runtime_supply_interpreter_missing"):
        runtime_supply(mode="immutable-package", source=tmp_path, wheel=wheel)
    with pytest.raises(ValueError, match="runtime_supply_interpreter_missing"):
        runtime_supply(mode="locked-source", source=tmp_path, wheel=wheel)
