"""Each published runtime archive declares its components in two inventories bound to its bytes."""

from __future__ import annotations

import hashlib
import json
import tomllib
from pathlib import Path

import pytest
import yaml

from tests.support.release_legs import VERSION
from tests.support.release_legs import inventory_documents
from tests.support.release_legs import qualified_leg
from tests.support.release_legs import write_inventories
from tools.ci import release_supply_chain
from tools.ci.delivery import release_assets

_ROOT = Path(__file__).resolve().parents[4]
_LEGS = {
    "linux-x64": ("linux", "x86_64", "linux_x86_64"),
    "linux-arm64": ("linux", "arm64", "linux_aarch64"),
    "macos-arm64": ("darwin", "arm64", "macosx_14_0_arm64"),
    "windows-x64": ("windows", "x86_64", "win_amd64"),
}
_ENTRY = f"# Changelog\n\n## [{VERSION}] - 2026-10-21\n\n### Added\n\n- Hosted release.\n"


def _assembled(tmp_path: Path, change=None, host: str = "linux-x64"):
    tmp_path.mkdir(parents=True, exist_ok=True)
    inputs, changelog = tmp_path / "inputs", tmp_path / "CHANGELOG.md"
    changelog.write_text(_ENTRY, encoding="utf-8")
    for leg, platform in _LEGS.items():
        qualified_leg(inputs, leg, *platform)
    if change is not None:
        change(inputs / f"release-runtime-{host}", host)
    options = {
        "tag": f"v{VERSION}",
        "base_url": "https://example.invalid/v",
        "changelog": changelog,
    }
    return tmp_path / "out", release_assets.assemble(inputs, tmp_path / "out", **options)


def test_assembly_publishes_and_sums_each_archives_inventories(tmp_path):
    """The inventories travel beside their archive, under the name the leg cataloged."""
    out, sums = _assembled(tmp_path)
    for host in _LEGS:
        name = f"ethos-{VERSION}-{host}"
        for suffix in (".spdx.json", ".syft.json"):
            published = out / "assets" / f"{name}{suffix}"
            assert sums[published.name] == hashlib.sha256(published.read_bytes()).hexdigest()
        assert (
            json.loads((out / "assets" / f"{name}.spdx.json").read_text())["name"]
            == f"{name}.tar.gz"
        )


def _rewrite(document: str = "both", **change):
    def apply(job: Path, host: str) -> None:
        digest = change.get("digest", hashlib.sha256(host.encode()).hexdigest())
        name = change.get("name", f"ethos-{VERSION}-{host}.tar.gz")
        paths = write_inventories(job, name, digest, components=change.get("parts", 1))
        if document == "missing":
            paths[1].unlink()
        elif document == "garbled":
            paths[0].write_text("{", encoding="utf-8")
        elif document == "oversized":
            paths[0].write_bytes(b" " * (release_assets.INVENTORY_LIMIT + 1))
        elif document == "duplicate":
            (paths[0].parent / "other.spdx.json").write_bytes(paths[0].read_bytes())

    return apply


@pytest.mark.parametrize(
    ("change", "gap"),
    [
        (_rewrite("missing"), "release_assets_inventory_invalid:linux-x64"),
        (_rewrite("garbled"), "release_assets_inventory_invalid:linux-x64"),
        (_rewrite("oversized"), "release_assets_inventory_invalid:linux-x64"),
        (_rewrite(digest="0" * 64), "release_assets_inventory_mismatch:linux-x64"),
        (_rewrite(name="ethos-other.tar.gz"), "release_assets_inventory_mismatch:linux-x64"),
        (_rewrite(parts=0), "release_assets_inventory_components_missing:linux-x64"),
        (_rewrite("duplicate"), "release_assets_inventory_mismatch:linux-x64"),
    ],
    ids=["missing", "garbled", "oversized", "digest", "name", "one-package", "duplicate"],
)
def test_a_required_host_needs_inventories_that_declare_its_archive(tmp_path, change, gap):
    """A missing, oversized, foreign or one-package inventory stops the release."""
    with pytest.raises(ValueError, match=gap):
        _assembled(tmp_path, change)
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("document", ["missing", "both-missing"])
def test_an_incomplete_windows_declaration_is_left_out_and_named(tmp_path, document):
    """Windows stays optional: an incomplete declaration is none, and the release says so."""

    def change(job: Path, host: str) -> None:
        _rewrite("missing")(job, host)
        if document == "both-missing":
            (job / "evidence/release/runtime.spdx.json").unlink()

    out, sums = _assembled(tmp_path, change, host="windows-x64")
    assert not [name for name in sums if "windows" in name or "win_amd64" in name]
    assert f"ethos-{VERSION}-linux-x64.syft.json" in sums
    assert "windows-x64" in (out / "notes.md").read_text(encoding="utf-8")
    assert json.loads((out / "left-out.json").read_text(encoding="utf-8")) == [
        {"host": "windows-x64", "reason": "inventories_incomplete"}
    ]


@pytest.mark.parametrize(
    "change",
    [_rewrite(digest="0" * 64), _rewrite(name="ethos-other.tar.gz"), _rewrite("duplicate")],
    ids=["digest", "name", "duplicate"],
)
def test_a_mismatched_binding_blocks_even_an_optional_host(tmp_path, change):
    """A wrong digest, name or duplicate is a pipeline defect or tampering, never optional."""
    with pytest.raises(ValueError, match="release_assets_inventory_mismatch:windows-x64"):
        _assembled(tmp_path, change, host="windows-x64")


def test_one_syft_run_writes_both_inventories_of_the_archive_bytes(tmp_path):
    """Syft reads the archive under its published name with the explicit configuration only."""
    archive = tmp_path / "runtime.tar.gz"
    archive.write_bytes(b"runtime archive")
    digest, calls = hashlib.sha256(b"runtime archive").hexdigest(), []
    outputs = (tmp_path / "runtime.spdx.json", tmp_path / "runtime.syft.json")

    def syft(arguments: tuple[str, ...], *, name: str = "ethos-x.tar.gz", parts: int = 1) -> None:
        calls.append(arguments)
        for path, document in zip(
            outputs, inventory_documents(name, digest, components=parts), strict=True
        ):
            path.write_text(json.dumps(document), encoding="utf-8")

    config = tmp_path / "syft.yaml"
    options = {"name": "ethos-x.tar.gz", "outputs": outputs, "config": config}
    spdx, inventory = release_supply_chain.catalog(archive, run=syft, **options)
    assert calls[0][:6] == (
        "scan",
        f"file:{archive}",
        "--source-name",
        "ethos-x.tar.gz",
        "--config",
        str(config),
    )
    assert inventory["source"]["version"] == f"sha256:{digest}"
    assert spdx["spdxVersion"] == "SPDX-2.3"
    with pytest.raises(ValueError, match="release_inventory_components_missing"):
        release_supply_chain.catalog(archive, run=lambda a: syft(a, parts=0), **options)
    with pytest.raises(ValueError, match="release_inventory_subject_mismatch"):
        release_supply_chain.catalog(
            archive, run=lambda a: syft(a, name="ethos-y.tar.gz"), **options
        )


def test_the_policy_configures_syft_explicitly_and_strips_inherited_settings(tmp_path, monkeypatch):
    """No ambient SYFT_ variable or default config file can change what the inventory holds."""
    policy = tomllib.loads((_ROOT / ".config/release/release-sbom/policy.toml").read_text())
    assert policy["syft_config"] == {
        "check-for-app-update": False,
        "golang": {"capture-symbols": "extended-stdlib"},
    }
    seen = {}
    monkeypatch.setattr(
        release_supply_chain, "run_command", lambda *_args, **options: seen.update(options)
    )
    release_supply_chain.native_syft(tmp_path / "syft")(("version",))
    assert {"GIT_", "SYFT_"} <= set(seen["remove_env_prefixes"])


_RUNTIME = "ethos/runtime/0123456789abcdef/"
_SITE = "python/lib/python3.14/site-packages/"


def _complete() -> tuple[dict, dict]:
    files = {
        f"{_SITE}ruff-0.15.2.dist-info/METADATA": "",
        f"{_SITE}uv-0.13.7.dist-info/METADATA": "",
        "python/bin/uv": "",
        f"{_SITE}ethos/resources/native/vale/vale": "",
        f"{_SITE}ethos/resources/node/bin/node": "",
    }
    at = "/" + _RUNTIME
    artifacts = [
        {"type": "python", "name": "ruff", "version": "0.15.2", "locations": []},
        {"type": "python", "name": "uv", "version": "0.13.7", "locations": []},
        {
            "type": "rust-crate",
            "name": "uv",
            "version": "0.13.7",
            "locations": [{"path": at + "python/bin/uv"}],
        },
        {
            "type": "go-module",
            "name": "github.com/vale-cli/vale/v3",
            "version": "v3.26.0",
            "locations": [{"path": f"{at}{_SITE}ethos/resources/native/vale/vale"}],
        },
        {
            "type": "binary",
            "name": "node",
            "version": "26.13.0",
            "locations": [{"path": f"{at}{_SITE}ethos/resources/node/bin/node"}],
        },
    ]
    return {"artifacts": artifacts}, {"runtime_files": files}


@pytest.mark.parametrize(
    ("drop", "missing"),
    [
        (None, []),
        ("ruff", ["release_inventory_component_missing:python:ruff@0.15.2"]),
        ("github.com/vale-cli/vale/v3", ["release_inventory_component_missing:go:vale@v3.26.0"]),
        ("uv:rust-crate", ["release_inventory_component_missing:rust:uv@0.13.7"]),
        ("node", ["release_inventory_component_missing:node:node@26.13.0"]),
    ],
)
def test_completeness_names_each_component_its_owner_expects(drop, missing):
    """Go tools, uv's crates, Node and every shipped distribution must each appear."""
    inventory, manifest = _complete()
    inventory["artifacts"] = [
        artifact
        for artifact in inventory["artifacts"]
        if drop not in (artifact["name"], f"{artifact['name']}:{artifact['type']}")
    ]
    found = release_supply_chain.missing_components(
        inventory, manifest, native={"vale": "3.26.0"}, node="26.13.0"
    )
    assert found == missing


def test_each_release_leg_catalogs_its_archive_before_upload_and_proofs_follow_the_smoke():
    """Syft runs where there is no write permission, and the gate reads the smoke's archive."""
    jobs = yaml.safe_load((_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))["jobs"]
    steps = jobs["release-platforms"]["steps"]
    runs = [step.get("run", "") for step in steps]
    catalog = next(
        i for i, run in enumerate(runs) if "nox -s supply_chain -- --host ${{ matrix.host }}" in run
    )
    smoke = next(i for i, run in enumerate(runs) if "nox -s install_smoke" in run)
    upload = next(i for i, step in enumerate(steps) if "upload-artifact" in step.get("uses", ""))
    assert smoke < catalog < upload
    paths = steps[upload]["with"]["path"].split()
    assert {
        "build/evidence/release/runtime.spdx.json",
        "build/evidence/release/runtime.syft.json",
    } <= set(paths)
    assert not [
        step
        for job in jobs.values()
        for step in job.get("steps", [])
        if "attest-sbom" in step.get("uses", "")
    ]
    gates = tomllib.loads((_ROOT / "system/repository-gates.toml").read_text(encoding="utf-8"))[
        "gates"
    ]
    gate = next(gate for gate in gates if gate["id"] == "release-sbom")
    assert gate["depends_on"] == ["local-install-smoke"]
    assert gate["resource_locks"]["artifacts/native"] == "shared"
