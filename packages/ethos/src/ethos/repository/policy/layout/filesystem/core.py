from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

POLICY_PATH = Path(".config/checks/module-layout/policy.toml")
DEFAULT_PATHS = ("packages/ethos/src", "packages/ethos-core/src")
DEFAULT_FLAT_DIRECTORY_LIMIT = 8
DEFAULT_SUFFIX_GROUP_MIN = 3
DEFAULT_FLAT_GROWTH_EXISTING_MODULE_LIMIT = 5
DEFAULT_FLAT_GROWTH_ADDED_MODULE_LIMIT = 2


def load_policy(root: Path) -> dict[str, Any]:
    """Load module-layout policy with stable defaults."""
    path = root / POLICY_PATH
    if not path.exists():
        return {
            "paths": list(DEFAULT_PATHS),
            "flat_directory_limit": DEFAULT_FLAT_DIRECTORY_LIMIT,
            "suffix_flat_group_min": DEFAULT_SUFFIX_GROUP_MIN,
            "flat_growth_existing_module_limit": DEFAULT_FLAT_GROWTH_EXISTING_MODULE_LIMIT,
            "flat_growth_added_module_limit": DEFAULT_FLAT_GROWTH_ADDED_MODULE_LIMIT,
        }
    return tomllib.loads(path.read_text(encoding="utf-8"))


def python_files(root: Path, policy: dict[str, Any]) -> list[Path]:
    """Return governed Python files under configured module-layout paths."""
    files: list[Path] = []
    for configured in string_list(policy.get("paths")) or list(DEFAULT_PATHS):
        base = root / configured
        if base.is_file() and base.suffix == ".py":
            files.append(base)
        elif base.exists():
            files.extend(sorted(base.rglob("*.py")))
    return [path for path in files if "__pycache__" not in path.parts]


def string_list(value: object) -> list[str]:
    """Normalize policy list values to strings."""
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]
