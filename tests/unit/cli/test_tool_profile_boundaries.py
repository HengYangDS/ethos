from __future__ import annotations

import json
import subprocess
import tomllib
from pathlib import Path

import pytest

from ethos_core.quality.profiles import tool_profiles

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


def test_tool_profiles_are_derived_from_the_active_catalog() -> None:
    payload = run_ethos("quality", "tool-profiles", "--json")
    adapters = {adapter["concern"]: adapter for adapter in payload["data"]["tool_adapters"]}  # fmt: skip
    catalog = tomllib.loads((ROOT / "system" / "tools.toml").read_text(encoding="utf-8"))["tool"]  # fmt: skip

    assert set(adapters) == {entry["concern"] for entry in catalog}
    for entry in catalog:
        adapter = adapters[entry["concern"]]
        assert adapter["standard"] == entry["tool"]
        assert adapter["profile"] == entry["profile"]
        assert adapter["config"] == entry["config"]
        assert adapter.get("gate") == entry.get("gate")
        assert "planned" not in adapter


def test_tool_catalog_schema_is_active_only_by_construction() -> None:
    schema = json.loads((ROOT / "system" / "schemas" / "contracts" / "tools.schema.json").read_text(encoding="utf-8"))  # fmt: skip
    tool_schema = schema["properties"]["tool"]["items"]

    assert "adoption" not in tool_schema["required"]
    assert "adoption" not in tool_schema["properties"]


def test_tool_profiles_reject_a_non_list_catalog(tmp_path: Path) -> None:
    catalog = tmp_path / "system" / "tools.toml"
    catalog.parent.mkdir()
    catalog.write_text("tool = {}", encoding="utf-8")

    with pytest.raises(TypeError, match="must declare a tool array"):
        tool_profiles(tmp_path)
