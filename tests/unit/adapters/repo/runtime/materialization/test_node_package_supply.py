"""Lock-bound Node package supply contracts."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from ethos.adapters.repo.runtime.materialization.node_package_supply import (
    resolve_node_package_projection,
)
from ethos.adapters.repo.runtime.materialization.node_package_supply import (
    resolve_node_package_supply,
)


def _write_lock(path: Path, packages: dict[str, object]) -> None:
    path.write_text(
        json.dumps({"lockfileVersion": 3, "packages": packages}) + "\n",
        encoding="utf-8",
    )


def test_node_package_supply_prefers_an_explicit_prepared_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    supply = tmp_path / "prepared/node_modules"
    source.mkdir()
    supply.mkdir(parents=True)
    packages = {"node_modules/tool": {"version": "1.0.0"}}
    _write_lock(source / "package-lock.json", {"": {}, **packages})
    _write_lock(supply / ".package-lock.json", packages)
    monkeypatch.setenv("ETHOS_NODE_PACKAGE_SUPPLY", supply.as_posix())

    assert resolve_node_package_supply(source) == supply.resolve()


def test_node_package_supply_rejects_an_unprepared_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("ETHOS_NODE_PACKAGE_SUPPLY", raising=False)
    with pytest.raises(ValueError, match="node_package_supply_unavailable"):
        resolve_node_package_supply(tmp_path)


def test_node_package_supply_rejects_a_relative_explicit_coordinate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "node_modules").mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ETHOS_NODE_PACKAGE_SUPPLY", "node_modules")

    with pytest.raises(ValueError, match="node_package_supply_path_not_absolute"):
        resolve_node_package_supply(tmp_path)


def test_node_package_supply_rejects_a_tree_from_another_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    supply = tmp_path / "prepared/node_modules"
    source.mkdir()
    supply.mkdir(parents=True)
    _write_lock(
        source / "package-lock.json",
        {"": {}, "node_modules/tool": {"version": "1.0.0"}},
    )
    _write_lock(
        supply / ".package-lock.json",
        {"node_modules/tool": {"version": "2.0.0"}},
    )
    monkeypatch.setenv("ETHOS_NODE_PACKAGE_SUPPLY", supply.as_posix())

    with pytest.raises(ValueError, match="node_package_supply_lock_mismatch"):
        resolve_node_package_supply(source)


def test_node_package_projection_selects_its_coordinate_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    supply = tmp_path / "prepared/node_modules"
    source.mkdir()
    package = supply / "tool/package.json"
    package.parent.mkdir(parents=True)
    package.write_text('{"name":"tool","version":"1.0.0"}\n', encoding="utf-8")
    packages = {"node_modules/tool": {"version": "1.0.0"}}
    _write_lock(source / "package-lock.json", {"": {}, **packages})
    _write_lock(supply / ".package-lock.json", packages)

    class Environment(dict[str, str]):
        reads = 0

        def get(self, key: str, default: str | None = None) -> str | None:
            if key == "ETHOS_NODE_PACKAGE_SUPPLY":
                self.reads += 1
            return super().get(key, default)

    environment = Environment(os.environ)
    environment["ETHOS_NODE_PACKAGE_SUPPLY"] = supply.as_posix()
    monkeypatch.setattr(os, "environ", environment)

    assert resolve_node_package_projection(source) == (supply.resolve(), (Path("tool"),))
    assert environment.reads == 1


def test_node_package_projection_accepts_a_source_local_production_closure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    supply = source / "node_modules"
    source.mkdir()
    packages = {
        "": {"dependencies": {"direct": "1.0.0"}},
        "node_modules/direct": {"version": "1.0.0"},
        "node_modules/direct/node_modules/nested": {"version": "2.0.0"},
        "node_modules/dev-only": {"version": "1.0.0", "dev": True},
    }
    _write_lock(source / "package-lock.json", packages)
    for relative, version in (
        ("direct", "1.0.0"),
        ("direct/node_modules/nested", "2.0.0"),
    ):
        package = supply / relative / "package.json"
        package.parent.mkdir(parents=True, exist_ok=True)
        package.write_text(
            json.dumps({"name": relative, "version": version}) + "\n",
            encoding="utf-8",
        )
    monkeypatch.delenv("ETHOS_NODE_PACKAGE_SUPPLY", raising=False)

    resolved, roots = resolve_node_package_projection(source)

    assert resolved == supply.resolve()
    assert roots == (Path("direct"),)
