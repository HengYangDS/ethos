from __future__ import annotations

import stat
import tomllib
from pathlib import Path

from tests.support.architecture import tool_block

ROOT = Path(__file__).resolve().parents[2]
OWNER = ROOT / "tools/ci/scripts/run-local-install-smoke.sh"


def _owner_text() -> str:
    assert OWNER.is_file()
    return OWNER.read_text(encoding="utf-8")


def test_local_install_smoke_has_one_executable_owner() -> None:
    assert OWNER.is_file()
    assert OWNER.stat().st_mode & stat.S_IXUSR
    block = tool_block(ROOT, "local_install_smoke")
    assert 'gate = "tools/ci/scripts/run-local-install-smoke.sh"' in block
    assert 'artifacts = "build/evidence/local-install/"' in block


def test_local_install_smoke_is_offline_isolated_and_head_bound() -> None:
    owner = _owner_text()

    assert "build/artifacts/python" in owner
    assert "build/runtime/work/local-install-smoke" in owner
    assert "build/evidence/local-install/smoke.json" in owner
    assert 'uv build --offline --wheel --out-dir "${artifact_dir}"' in owner
    assert "uv export --locked --offline --no-dev --no-emit-project" in owner
    assert 'printf \'%s\\n\' "${source_site}" > "${smoke_site}/ethos-locked-runtime.pth"' in owner
    assert 'uv pip install --offline --no-deps --python "${smoke_python}" "${wheel}"' in owner
    assert 'uv pip check --python "${source_python}"' in owner
    assert "ethos" in owner
    assert "ethos.__file__" in owner
    assert "ethos.__file__" in owner
    assert "uv cache dir" not in owner
    assert "ETHOS_LOCAL_INSTALL_UV_CACHE_DIR" not in owner
    assert '"${venv_dir}/bin/ethos" --help' in owner
    assert '"${venv_dir}/bin/ethos" --version' in owner
    assert owner.count("require-stable-head.sh") == 2
    assert " capture)" in owner
    assert ' verify "${head}" "$0"' in owner
    assert '"hosted_ci_status_claimed": False' in owner
    assert '"remote_publication_claimed": False' in owner


def test_local_ci_runs_install_smoke_before_fallback_manifest() -> None:
    local_ci = (ROOT / "tools/ci/scripts/run-local-ci.sh").read_text(encoding="utf-8")

    assert "tools/ci/scripts/run-local-install-smoke.sh" in local_ci
    assert local_ci.index("run-local-install-smoke.sh") < local_ci.index(
        "build/evidence/local-ci/fallback.json"
    )


def test_full_proof_registers_one_trust_bearing_install_smoke() -> None:
    declaration = tomllib.loads((ROOT / "system/gates.toml").read_text(encoding="utf-8"))
    full = declaration["proof_sets"]["product_full"]
    gates = {gate["id"]: gate for gate in declaration["gates"]}

    assert full.count("local-install-smoke") == 1
    assert full.index("build") < full.index("local-install-smoke")
    assert "local-install-smoke" not in declaration["proof_sets"]["product_default"]
    assert gates["local-install-smoke"] == {
        "id": "local-install-smoke",
        "registries": ["runtime"],
        "kind": "package",
        "command": ["tools/ci/scripts/run-local-install-smoke.sh"],
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
