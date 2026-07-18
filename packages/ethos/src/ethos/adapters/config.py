"""Config IO adapter — loads tracked TOML config (.ethos/rules.toml).

The impure loader layer: reads config files off disk. Domain reducers receive the
parsed dict and stay pure.
"""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING
from typing import cast

if TYPE_CHECKING:
    from pathlib import Path


def rules_config(root: Path) -> dict[str, object]:
    """Load .ethos/rules.toml as a dict, or {} when absent."""
    path = root / ".ethos" / "rules.toml"
    if not path.exists():
        return {}
    return tomllib.loads(path.read_text(encoding="utf-8"))


def code_size_policy(root: Path) -> dict[str, object]:
    """Project the [quality.code_size] sub-table out of the rules config."""
    rules = rules_config(root)
    quality = rules.get("quality")
    if not isinstance(quality, dict):
        return {}
    code_size = quality.get("code_size")
    return cast("dict[str, object]", code_size) if isinstance(code_size, dict) else {}


def source_budget_policy(root: Path) -> dict[str, object]:
    """Project the global source-budget contract from the rules configuration."""
    rules = rules_config(root)
    quality = rules.get("quality")
    if not isinstance(quality, dict):
        return {}
    budget = quality.get("source_budget")
    return cast("dict[str, object]", budget) if isinstance(budget, dict) else {}
