from __future__ import annotations

import tomllib
from pathlib import Path

from ethos._resources import resolve_declaration_path

_TOOL_CATALOG_ARRAY_REQUIRED = "system/tools.toml must declare a tool array"


def _system_path(root: Path, name: str) -> Path:
    path = root / "system" / name
    return resolve_declaration_path(
        path if path.is_file() else None,
        canonical=Path("system") / name,
        module_file=__file__,
    )


def _asset_profiles(root: Path) -> list[dict[str, object]]:
    gates = tomllib.loads(_system_path(root, "gates.toml").read_text(encoding="utf-8"))["gates"]
    asset_classes = dict.fromkeys(
        asset_class for gate in gates for asset_class in gate["asset_classes"]
    )
    return [
        {
            "class": asset_class,
            "role": asset_class.replace("-", " "),
            "dimensions": list(
                dict.fromkeys(
                    dimension
                    for gate in gates
                    if asset_class in gate["asset_classes"]
                    for dimension in gate["dimensions"]
                )
            ),
            "default_adapters": list(
                dict.fromkeys(
                    str(gate["tool_adapter"])
                    for gate in gates
                    if asset_class in gate["asset_classes"]
                )
            ),
        }
        for asset_class in asset_classes
    ]


def product_quality_profile(root: Path) -> dict[str, object]:
    return {
        "schema_version": 1,
        "asset_classes": _asset_profiles(root),
        **tool_profiles(root),
        "format_governance": {
            "human_config": ["toml-config"],
            "machine_contract": ["json-contracts"],
            "host_projection": ["yaml-config"],
            "append_only": ["evidence"],
        },
    }


def tool_profiles(root: Path) -> dict[str, object]:
    catalog_path = _system_path(root, "tools.toml")
    catalog = tomllib.loads(catalog_path.read_text(encoding="utf-8"))
    entries = catalog.get("tool", [])
    if not isinstance(entries, list):
        raise TypeError(_TOOL_CATALOG_ARRAY_REQUIRED)
    return {
        "schema_version": 1,
        "tool_adapters": [
            dict(entry, id=entry["concern"], standard=entry["tool"])
            for entry in entries
            if isinstance(entry, dict)
        ],
    }
