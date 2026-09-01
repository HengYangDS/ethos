from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING
from typing import cast

import pytest

import tools.ci.openspec_runtime_hook as subject

if TYPE_CHECKING:
    from pathlib import Path

    from hatchling.builders.config import BuilderConfig
    from hatchling.metadata.core import ProjectMetadata


def _hook(root: Path, target: str = "wheel") -> subject.OpenSpecRuntimeHook:
    return subject.OpenSpecRuntimeHook(
        str(root),
        {},
        cast("BuilderConfig", object()),
        cast("ProjectMetadata", object()),
        "openspec-runtime",
        target,
    )


def _prepared_supply(root: Path) -> Path:
    packages = {
        "": {"dependencies": {"direct": "1.0.0"}, "devDependencies": {"dev-only": "1.0.0"}},
        "node_modules/direct": {"version": "1.0.0"},
        "node_modules/direct/node_modules/nested": {"version": "2.0.0"},
        "node_modules/dev-only": {"version": "1.0.0", "dev": True},
    }
    (root / "package.json").write_text('{"dependencies":{"direct":"1.0.0"}}\n')
    (root / "package-lock.json").write_text(
        json.dumps({"lockfileVersion": 3, "packages": packages}) + "\n",
        encoding="utf-8",
    )
    supply = root / "prepared/node_modules"
    for relative, version in (
        ("direct", "1.0.0"),
        ("direct/node_modules/nested", "2.0.0"),
        ("dev-only", "1.0.0"),
    ):
        package = supply / relative / "package.json"
        package.parent.mkdir(parents=True, exist_ok=True)
        package.write_text(json.dumps({"name": relative, "version": version}) + "\n")
    return supply


def test_build_hook_projects_prepared_production_supply_without_npm_or_temp_tree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    supply = _prepared_supply(tmp_path)
    monkeypatch.setenv("ETHOS_BUILD_OPENSPEC_SUPPLY", str(supply))
    monkeypatch.setattr(
        subject,
        "_build_identity_payload",
        lambda _: (b'{"schema_version":2}\n', "0.2.0a3.dev0+gaaaaaaaaaaaa.tbbbbbbbbbbbb"),
    )
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *_args, **_kwargs: pytest.fail("artifact construction must not invoke npm"),
    )
    data: dict[str, dict[str, str]] = {"force_include": {}}

    hook = _hook(tmp_path)
    hook.initialize("standard", data)
    hook.finalize("standard", data, "artifact")

    force_include = data["force_include"]
    assert force_include[str(supply / "direct")] == (
        "ethos/data/openspec-runtime/node_modules/direct"
    )
    assert not any("nested" in source for source in force_include)
    assert not any("dev-only" in source for source in force_include)
    assert not list(tmp_path.glob("ethos-openspec-supply-*"))


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ("missing", "node_modules/direct"),
        ("version", "node_modules/direct"),
        ("symlink", "node_modules/direct"),
        ("undeclared", "node_modules/direct/node_modules/extra"),
    ],
)
def test_build_hook_rejects_absent_or_drifted_prepared_supply(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
    expected: str,
) -> None:
    supply = _prepared_supply(tmp_path)
    direct = supply / "direct"
    if mutation == "missing":
        for path in sorted(direct.rglob("*"), reverse=True):
            path.unlink() if path.is_file() else path.rmdir()
        direct.rmdir()
    elif mutation == "version":
        (direct / "package.json").write_text(
            json.dumps({"name": "direct", "version": "9.9.9"}) + "\n",
            encoding="utf-8",
        )
    else:
        if mutation == "symlink":
            target = tmp_path / "external"
            target.mkdir()
            direct.rename(tmp_path / "direct-real")
            direct.symlink_to(target, target_is_directory=True)
        else:
            extra = direct / "node_modules/extra/package.json"
            extra.parent.mkdir()
            extra.write_text('{"name":"extra","version":"1.0.0"}\n', encoding="utf-8")
    monkeypatch.setenv("ETHOS_BUILD_OPENSPEC_SUPPLY", str(supply))
    monkeypatch.setattr(
        subject,
        "_build_identity_payload",
        lambda _: (b'{"schema_version":2}\n', "0.2.0a3.dev0+gaaaaaaaaaaaa.tbbbbbbbbbbbb"),
    )

    with pytest.raises(RuntimeError, match=expected):
        _hook(tmp_path).initialize("standard", {"force_include": {}})


def test_sdist_carries_the_same_prepared_production_supply(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    supply = _prepared_supply(tmp_path)
    monkeypatch.setenv("ETHOS_BUILD_OPENSPEC_SUPPLY", str(supply))
    monkeypatch.setattr(
        subject,
        "_build_identity_payload",
        lambda _: (b'{"schema_version":2}\n', "0.2.0a3.dev0+gaaaaaaaaaaaa.tbbbbbbbbbbbb"),
    )
    data: dict[str, dict[str, str]] = {"force_include": {}}

    hook = _hook(tmp_path, "sdist")
    hook.initialize("standard", data)
    hook.finalize("standard", data, "artifact")

    assert data["force_include"][str(supply / "direct")] == "node_modules/direct"
