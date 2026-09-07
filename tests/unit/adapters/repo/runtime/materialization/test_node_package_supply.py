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


def _prepared_supply(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    source, supply = tmp_path / "source", tmp_path / "prepared/node_modules"
    source.mkdir()
    supply.mkdir(parents=True)
    packages = {"node_modules/tool": {"version": "1.0.0"}}
    _write_lock(source / "package-lock.json", {"": {}, **packages})
    _write_lock(supply / ".package-lock.json", packages)
    monkeypatch.setenv("ETHOS_NODE_PACKAGE_SUPPLY", supply.as_posix())
    return source, supply, packages


@pytest.mark.parametrize(
    "condition", ["explicit", "workspace", "missing", "relative", "mismatch", "linked"]
)
def test_node_package_supply_uses_only_the_exact_prepared_coordinate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, condition: str
) -> None:
    source, supply, packages = _prepared_supply(tmp_path, monkeypatch)
    expected = {
        "missing": "unavailable",
        "relative": "path_not_absolute",
        "mismatch": "lock_mismatch",
        "linked": "unavailable",
    }
    if condition == "workspace":
        for path, version in (
            (source / "package-lock.json", "alpha.5"),
            (supply / ".package-lock.json", "alpha.4"),
        ):
            _write_lock(
                path, {"": {}, "distributions/npm": {"version": version, "link": True}, **packages}
            )
    elif condition == "missing":
        monkeypatch.delenv("ETHOS_NODE_PACKAGE_SUPPLY")
    elif condition == "relative":
        monkeypatch.chdir(source)
        (source / "node_modules").mkdir()
        monkeypatch.setenv("ETHOS_NODE_PACKAGE_SUPPLY", "node_modules")
    elif condition == "mismatch":
        _write_lock(supply / ".package-lock.json", {"node_modules/tool": {"version": "2.0.0"}})
    elif condition == "linked":
        link = source / "node_modules"
        link.symlink_to(supply, target_is_directory=True)
        monkeypatch.setenv("ETHOS_NODE_PACKAGE_SUPPLY", link.as_posix())
    if condition in expected:
        with pytest.raises(ValueError, match="node_package_supply_" + expected[condition]):
            resolve_node_package_supply(source)
    else:
        assert resolve_node_package_supply(source) == supply.resolve()


@pytest.mark.parametrize(
    "invalidity", ["missing", "link", "utf8", "json", "list", "version", "packages"]
)
def test_node_package_supply_rejects_invalid_lock_without_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, invalidity: str
) -> None:
    source, supply, _packages = _prepared_supply(tmp_path, monkeypatch)
    lock = source / "package-lock.json"
    if invalidity in {"missing", "link"}:
        lock.unlink()
        if invalidity == "link":
            lock.symlink_to(supply / ".package-lock.json")
    else:
        lock.write_bytes(
            {
                "utf8": b"\xff",
                "json": b"{",
                "list": b"[]",
                "version": b'{"lockfileVersion":2,"packages":{}}',
                "packages": b'{"lockfileVersion":3,"packages":[]}',
            }[invalidity]
        )
    before = (supply / ".package-lock.json").read_bytes()
    with pytest.raises(ValueError, match="node_package_supply_lock_invalid"):
        resolve_node_package_supply(source)
    assert (supply / ".package-lock.json").read_bytes() == before


def test_node_package_projection_selects_its_coordinate_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, supply, _packages = _prepared_supply(tmp_path, monkeypatch)
    package = supply / "tool/package.json"
    package.parent.mkdir()
    package.write_text('{"name":"tool","version":"1.0.0"}\n', encoding="utf-8")

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


@pytest.mark.parametrize(
    "invalidity", ["none", "missing", "json", "linked-declaration", "version", "undeclared"]
)
def test_node_package_projection_accepts_a_source_local_production_closure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, invalidity: str
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

    declaration = supply / "direct/package.json"
    if invalidity in {"missing", "linked-declaration"}:
        declaration.unlink()
        if invalidity == "linked-declaration":
            declaration.symlink_to(supply / "direct/node_modules/nested/package.json")
    elif invalidity in {"json", "version"}:
        declaration.write_text(
            "{" if invalidity == "json" else '{"version":"different"}', encoding="utf-8"
        )
    elif invalidity == "undeclared":
        (supply / "unlocked").symlink_to(supply / "direct", target_is_directory=True)
    if invalidity == "none":
        assert resolve_node_package_projection(source) == (supply.resolve(), (Path("direct"),))
    else:
        with pytest.raises(ValueError, match="node_package_supply_invalid:node_modules/"):
            resolve_node_package_projection(source)
