from __future__ import annotations

import tomllib
from pathlib import Path

from tests.support.architecture import tool_block

ROOT = Path(__file__).resolve().parents[2]
OWNER = ROOT / "tools/ci/local_install_smoke.py"


def _owner_text() -> str:
    assert OWNER.is_file()
    return OWNER.read_text(encoding="utf-8")


def test_local_install_smoke_has_one_executable_owner() -> None:
    assert OWNER.is_file()
    block = tool_block(ROOT, "local_install_smoke")
    assert 'gate = ".venv/bin/nox -s install_smoke"' in block
    assert 'artifacts = "build/evidence/local-install/"' in block


def test_local_install_smoke_is_offline_isolated_and_head_bound() -> None:
    owner = _owner_text()

    assert "build/artifacts/python" in owner
    assert "build/runtime/work/local-install-smoke" in owner
    assert "build/evidence/local-install/smoke.json" in owner
    assert '"command": ".venv/bin/nox -s install_smoke"' in owner
    assert "ethos-locked-runtime.pth" in owner
    for argument in ("install", "--offline", "--no-deps"):
        assert f'"{argument}"' in owner
    assert '"check", "--python"' in owner
    assert "ethos" in owner
    assert "ethos.__file__" in owner
    assert "ethos.__file__" in owner
    assert "uv cache dir" not in owner
    assert "ETHOS_LOCAL_INSTALL_UV_CACHE_DIR" not in owner
    assert '"--help"' in owner
    assert '"--version"' in owner
    assert '"status", "--root"' in owner
    assert '"plan", "--changed"' in owner
    assert '"archive-change"' in owner
    assert '"--rebuild-from"' in owner
    assert "/Users/" not in owner
    assert '"@fission-ai/openspec@1.7.0"' in owner
    assert '"system/openspec/package.json" = "ethos/data/openspec/package.json"' in (
        ROOT / "pyproject.toml"
    ).read_text(encoding="utf-8")
    assert '"system/schemas/kernel" = "ethos/data/schemas/kernel"' in (
        ROOT / "pyproject.toml"
    ).read_text(encoding="utf-8")
    assert "current_tracked_head(ROOT)" in owner
    assert '"hosted_ci_status_claimed": False' in owner
    assert '"remote_publication_claimed": False' in owner


def test_local_install_smoke_validates_declared_wheel_resources() -> None:
    owner = _owner_text()

    assert '["force-include"]' in owner
    assert "zipfile.ZipFile" in owner
    assert '"lifecycle.toml"' not in owner


def test_local_ci_runs_install_smoke_before_fallback_manifest() -> None:
    local_ci = (ROOT / "tools/ci/scripts/run-local-ci.sh").read_text(encoding="utf-8")

    assert ".venv/bin/nox -s install_smoke" in local_ci
    assert local_ci.index("nox -s install_smoke") < local_ci.index(
        "build/evidence/local-ci/fallback.json"
    )


def test_full_proof_registers_one_trust_bearing_install_smoke() -> None:
    declaration = tomllib.loads((ROOT / "system/gates.toml").read_text(encoding="utf-8"))
    full = declaration["proof_sets"]["full"]
    gates = {gate["id"]: gate for gate in declaration["gates"]}

    assert full.count("local-install-smoke") == 1
    assert full.index("build") < full.index("local-install-smoke")
    assert "local-install-smoke" not in declaration["proof_sets"]["default"]
    assert gates["local-install-smoke"] == {
        "id": "local-install-smoke",
        "registries": ["runtime"],
        "kind": "package",
        "command": [".venv/bin/nox", "-s", "install_smoke"],
        "profile": "product-toolchain",
        "toolchain": "uv-python",
        "depends_on": ["build"],
        "asset_classes": ["release-artifacts"],
        "dimensions": ["installability", "isolation", "provenance"],
        "execution_mode": "adapter",
        "evidence_class": "proof",
        "trust_bearing": True,
        "tool_adapter": "uv-local-install-smoke",
        "writes_files": True,
        "network_policy": "offline",
        "version_source": "locked-toolchain",
    }
