"""Build wheel and source distributions from one exact OpenSpec supply owner."""

from __future__ import annotations

import json
import subprocess
import tomllib
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

import pytest
import tomli_w

import ethos.repository.policy.quality.dependency_acceptance as audit_owner
import ethos.repository.release.resources as resource_layout
import tools.ci.openspec_runtime_hook as subject
from ethos.adapters.repo.runtime.materialization.native_supply import ensure_native_directory

if TYPE_CHECKING:
    from hatchling.builders.config import BuilderConfig
    from hatchling.metadata.core import ProjectMetadata


def _hook(root: Path, target: str = "wheel") -> subject.OpenSpecRuntimeHook:
    policy = root / audit_owner.AUDIT_POLICY_PATH
    if not policy.exists():
        policy.parent.mkdir(parents=True, exist_ok=True)
        policy.write_bytes(
            audit_owner.product_audit_projection(
                (Path(__file__).resolve().parents[3] / audit_owner.AUDIT_POLICY_PATH).read_bytes()
            )
        )
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
    (supply / ".package-lock.json").write_text(
        json.dumps(
            {
                "lockfileVersion": 3,
                "packages": {key: value for key, value in packages.items() if key},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return supply


@pytest.fixture
def prepared_native_policy_tool(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Unrelated build tests supply the native prerequisite, never an ambient installer."""
    native = tmp_path / "fixture-vale"
    native.mkdir()
    (native / "vale").write_bytes(b"native fixture")
    (native / "LICENSE").write_bytes(b"publisher fixture")
    monkeypatch.setattr(subject, "_native_tool_projection", lambda _root, _directory: native)


@pytest.mark.usefixtures("prepared_native_policy_tool")
def test_build_hook_loads_the_single_source_supply_owner_without_installed_ethos(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    supply = tmp_path / "prepared/node_modules"
    supply.mkdir(parents=True)
    source_path = (tmp_path / "src").as_posix()
    observed: list[tuple[str, Path]] = []

    class SupplyOwner:
        @staticmethod
        def resolve_node_package_projection(root: Path) -> tuple[Path, tuple[Path, ...]]:
            observed.append(("resolve", root))
            return supply, (Path("direct"),)

    class NativeSupply:
        archive = "official.tar.gz"
        tag = "py3-none-macosx_14_0_arm64"

        @classmethod
        def read(cls, root: Path) -> type[NativeSupply]:
            assert root == tmp_path
            observed.append(("node", root))
            return cls

        @staticmethod
        def cache(root: Path) -> Path:
            return root / "native-cache"

        @staticmethod
        def project(archive: Path, destination: Path, *, bootstrap_npm: bool = True) -> Path:
            assert archive == tmp_path / "native-cache/official.tar.gz"
            assert bootstrap_npm is False
            destination.mkdir()
            return destination

    class NodeOwner:
        NodeSupply = NativeSupply

    def import_owner(name: str) -> object:
        if name == "ethos.repository.policy.quality.dependency_acceptance":
            assert source_path in subject.sys.path
            return audit_owner
        if name == "ethos.repository.release.resources":
            assert source_path in subject.sys.path
            return resource_layout
        if name == "ethos.adapters.repo.runtime.materialization.node.supply":
            assert source_path in subject.sys.path
            return NodeOwner
        assert name == ("ethos.adapters.repo.runtime.materialization.node_package_supply")
        assert source_path in subject.sys.path
        return SupplyOwner

    monkeypatch.delenv("ETHOS_NODE_PACKAGE_SUPPLY", raising=False)
    monkeypatch.setattr(subject, "import_module", import_owner)
    monkeypatch.setattr(
        subject,
        "_build_identity_payload",
        lambda _: (b'{"schema_version":2}\n', "0.2.0a3.dev0+gaaaaaaaaaaaa.tbbbbbbbbbbbb"),
    )
    data: dict[str, dict[str, str]] = {"force_include": {}}

    hook = _hook(tmp_path)
    hook.initialize("standard", data)
    hook.finalize("standard", data, "artifact")

    assert observed == [("resolve", tmp_path), ("node", tmp_path)]
    assert source_path not in subject.sys.path
    assert data["force_include"][str(supply / "direct")] == ("ethos/resources/node_modules/direct")


@pytest.mark.usefixtures("prepared_native_policy_tool")
def test_build_hook_projects_prepared_production_supply_without_npm_or_temp_tree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    supply = _prepared_supply(tmp_path)
    monkeypatch.setenv("ETHOS_NODE_PACKAGE_SUPPLY", str(supply))
    native = tmp_path / "complete-node"
    native.mkdir()
    monkeypatch.setattr(
        subject, "_node_projection", lambda _root, _directory: (native, "py3-none-linux_x86_64")
    )
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
    assert force_include[str(supply / "direct")] == ("ethos/resources/node_modules/direct")
    assert not any("nested" in source for source in force_include)
    assert not any("dev-only" in source for source in force_include)
    assert not list(tmp_path.glob("ethos-openspec-supply-*"))


@pytest.mark.parametrize("target", ["sdist", "wheel"])
@pytest.mark.parametrize("include_dispositions", [False, True])
@pytest.mark.usefixtures("prepared_native_policy_tool")
def test_build_policy_projection_retains_release_authority_and_cleans_rejection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, target: str, *, include_dispositions: bool
) -> None:
    """The real policy projector never ships host approvals or leaks failed staging."""
    supply = _prepared_supply(tmp_path)
    monkeypatch.setenv("ETHOS_NODE_PACKAGE_SUPPLY", str(supply))
    native = tmp_path / "native"
    native.mkdir()
    monkeypatch.setattr(
        subject, "_node_projection", lambda *_args: (native, "py3-none-linux_x86_64")
    )
    monkeypatch.setattr(subject, "_build_identity_payload", lambda _: (b"{}", "0.0.0"))
    hook = _hook(tmp_path, target)
    policy = tmp_path / audit_owner.AUDIT_POLICY_PATH
    source = Path(__file__).resolve().parents[3] / audit_owner.AUDIT_POLICY_PATH
    release = audit_owner.AuditDisposition(
        ecosystem="npm",
        advisory_url="https://example.invalid/advisories/fixture",
        package="fixture-package",
        version="1.0.0",
        integrity="fixture-integrity",
        scope="production-release",
        owner="fixture-owner",
        approval_ref="fixture-approval",
        rationale="Exercise portable policy projection independently of current findings.",
    )
    local = release.model_copy(
        update={
            "scope": "local-development",
            "host": "fixture:local",
            "lock_sha256": "a" * 64,
            "nodes": ["node_modules/fixture-package"],
            "expires_at": datetime(2050, 1, 1, tzinfo=UTC),
        }
    )
    audit_policy = audit_owner.AuditPolicy.model_validate(tomllib.loads(source.read_text()))
    audit_policy = audit_policy.model_copy(
        update={"dispositions": [release, local] if include_dispositions else []}
    )
    policy.write_text(tomli_w.dumps(audit_policy.model_dump(mode="python", exclude_none=True)))
    data = {"force_include": {}}
    try:
        hook.initialize("standard", data)
        projected = next(
            Path(path)
            for path, destination in data["force_include"].items()
            if destination.endswith(audit_owner.AUDIT_POLICY_PATH)
        )
        records = tomllib.loads(projected.read_text())["dispositions"]
        expected = (
            [release.model_dump(mode="python", exclude_none=True)] if include_dispositions else []
        )
        assert records == expected
        assert projected.read_bytes() == audit_owner.product_audit_projection(policy.read_bytes())
        staging = projected.parent
    finally:
        hook.finalize("standard", data, "fixture")
    assert not staging.exists()

    changed = audit_policy.model_copy(
        update={"dispositions": [release.model_copy(update={"host": "fixture:host-bound-release"})]}
    )
    policy.write_text(tomli_w.dumps(changed.model_dump(mode="python", exclude_none=True)))
    created = []
    temporary = subject.tempfile.TemporaryDirectory

    def owned_directory(*args, **kwargs):
        owned = temporary(*args, **kwargs)
        created.append(Path(owned.name))
        return owned

    monkeypatch.setattr(subject.tempfile, "TemporaryDirectory", owned_directory)
    with pytest.raises(ValueError, match="product_audit_policy_host_bound"):
        hook.initialize("standard", {"force_include": {}})
    assert created
    assert all(not path.exists() for path in created)


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
    monkeypatch.setenv("ETHOS_NODE_PACKAGE_SUPPLY", str(supply))
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
    monkeypatch.setenv("ETHOS_NODE_PACKAGE_SUPPLY", str(supply))
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


@pytest.mark.usefixtures("prepared_native_policy_tool")
def test_wheel_projects_the_complete_native_runtime_with_a_platform_tag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pure Python metadata must not misrepresent a wheel carrying native Node."""
    supply = _prepared_supply(tmp_path)
    native = tmp_path / "native-node"
    native.mkdir()
    monkeypatch.setenv("ETHOS_NODE_PACKAGE_SUPPLY", str(supply))
    monkeypatch.setattr(
        subject,
        "_build_identity_payload",
        lambda _: (b'{"schema_version":2}\n', "0.2.0a3.dev0+gaaaaaaaaaaaa.tbbbbbbbbbbbb"),
    )
    monkeypatch.setattr(
        subject,
        "_node_projection",
        lambda _root, _directory: (native, "py3-none-linux_x86_64"),
        raising=False,
    )
    data: dict = {"force_include": {}}
    hook = _hook(tmp_path)
    try:
        hook.initialize("standard", data)
        assert data["force_include"][str(native)] == "ethos/resources/node"
        assert data["pure_python"] is False
        assert data["tag"] == "py3-none-linux_x86_64"
    finally:
        hook.finalize("standard", data, "artifact")


def test_native_tool_build_projection_uses_locked_product_owner_without_install(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The build hook delegates exact native payloads to the same installed owner."""
    cache = tmp_path / "cache"
    cache.mkdir()
    archive = cache / "vale.tar.gz"
    archive.write_bytes(b"locked archive")
    physical_temp = tmp_path / "physical-temp"
    physical_temp.mkdir()
    native_temp = tmp_path / "native-temp"
    native_temp.symlink_to(physical_temp, target_is_directory=True)
    monkeypatch.setattr(subject.tempfile, "tempdir", str(native_temp))

    class Supply:
        archive = "vale.tar.gz"

        @staticmethod
        def read(root: Path, name: str):
            assert root == tmp_path
            assert name == "vale"
            return Supply()

        @staticmethod
        def cache(root: Path):
            assert root == tmp_path
            return cache

        @staticmethod
        def project(source: Path, destination: Path):
            assert source == archive
            ensure_native_directory(destination.parent)
            destination.mkdir()
            (destination / "vale").write_bytes(b"native executable")
            (destination / "LICENSE").write_bytes(b"publisher license")
            return destination

    class Owner:
        NativeSupply = Supply

    def import_owner(name: str):
        if name == "ethos.repository.release.resources":
            return resource_layout
        if name == "ethos.repository.policy.quality.dependency_acceptance":
            return audit_owner
        assert name == "ethos.adapters.repo.runtime.materialization.native_supply"
        return Owner

    monkeypatch.setattr(subject, "import_module", import_owner)
    monkeypatch.setattr(
        subprocess, "run", lambda *_args, **_kwargs: pytest.fail("build attempted provisioning")
    )

    hook = _hook(tmp_path)
    monkeypatch.setattr(subject, "_prepared_projection", lambda _root: (tmp_path, ()))
    monkeypatch.setattr(subject, "_build_identity_payload", lambda _root: (b"{}", "0.0.0"))
    monkeypatch.setattr(
        subject, "_node_projection", lambda _root, _directory: (tmp_path, "py3-none-linux_x86_64")
    )
    data = {"force_include": {}}
    try:
        hook.initialize("standard", data)
        projected = next(
            Path(path)
            for path, destination in data["force_include"].items()
            if destination == "ethos/resources/native/vale"
        )
        assert (projected / "vale").read_bytes() == b"native executable"
        assert (projected / "LICENSE").read_bytes() == b"publisher license"
    finally:
        hook.finalize("standard", data, "artifact")

    assert not projected.exists()
    assert archive.read_bytes() == b"locked archive"
