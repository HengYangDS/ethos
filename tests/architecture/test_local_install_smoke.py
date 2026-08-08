from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_package_gate_order_and_offline_contract_have_one_machine_owner() -> None:
    declaration = tomllib.loads((ROOT / "system/gates.toml").read_text(encoding="utf-8"))
    full = declaration["proof_sets"]["full"]
    gates = {item["id"]: item for item in declaration["gates"]}
    smoke = gates["local-install-smoke"]
    assert full.count("local-install-smoke") == 1
    assert full.index("build") < full.index("local-install-smoke")
    assert smoke["depends_on"] == ["build"]
    assert smoke["network_policy"] == "offline"
    assert smoke["writes_files"] is True


def test_package_only_runtime_behavior_remains_owned_by_install_smoke() -> None:
    owner = (ROOT / "tools/ci/local_install_smoke.py").read_text(encoding="utf-8")
    assert "build/runtime/work/local-install-smoke" in owner
    assert '"external_governance_available": False' in owner
    assert '"hosted_ci_status_claimed": False' in owner
