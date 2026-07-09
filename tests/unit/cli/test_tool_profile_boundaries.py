from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def run_ethos(*args: str) -> dict[str, object]:
    result = subprocess.run(
        ["uv", "run", "--package", "ethos", "ethos", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def test_new_tool_profile_boundaries_are_explicit() -> None:
    payload = run_ethos("quality", "tool-profiles", "--json")
    adapters = {adapter["id"]: adapter for adapter in payload["data"]["tool_adapters"]}

    assert adapters["deptry"]["boundary"] == "package-local-metadata-check-not-vulnerability-audit"
    assert adapters["codespell"]["asset_classes"] == ["markdown-docs"]
    assert adapters["check-jsonschema"]["asset_classes"] == [
        "json-contracts",
        "toml-config",
        "yaml-config",
    ]
    assert (
        adapters["hosted-provider-observation"]["boundary"]
        == "observation-only-not-repository-proof-or-hosted-success-claim"
    )
    assert adapters["nox"]["asset_classes"] == ["adopter-profile"]
    assert (
        adapters["pixi"]["boundary"]
        == "adapter-only-environment-profile-not-ethos-runtime-substrate"
    )
    assert adapters["pants"]["boundary"] == "adapter-only-graph-signal-not-ethos-kernel"
    assert (
        adapters["task-ledger"]["boundary"]
        == "adapter-only-task-ui-not-change-claim-lifecycle-owner"
    )
    assert (
        adapters["agent-method-pack"]["boundary"]
        == "optional-method-pack-not-proof-substitute-or-runtime-dependency"
    )
