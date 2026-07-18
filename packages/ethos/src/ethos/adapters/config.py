"""Config IO adapter — loads tracked TOML config (.ethos/rules.toml).

The impure loader layer: reads config files off disk. Domain reducers receive the
parsed dict and stay pure.
"""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING
from typing import cast

from pydantic import ValidationError

from ethos_core.contracts.source_budget.core import SourceBudgetPolicy
from ethos_core.contracts.source_budget.core import SourceBudgetPolicyLoad

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


def source_budget_policy(root: Path) -> SourceBudgetPolicyLoad:
    """Load the global source-budget contract without dropping malformed data."""
    rules = rules_config(root)
    quality = rules.get("quality")
    if not isinstance(quality, dict):
        return SourceBudgetPolicyLoad(policy=None, required_gaps=("source_budget_policy_missing",))
    budget = quality.get("source_budget")
    if not isinstance(budget, dict):
        return SourceBudgetPolicyLoad(policy=None, required_gaps=("source_budget_policy_missing",))
    try:
        policy = SourceBudgetPolicy.model_validate(budget)
    except ValidationError as exc:
        gaps = tuple(
            f"source_budget_policy_invalid:{'.'.join(map(str, error['loc']))}"
            for error in exc.errors()
        )
        return SourceBudgetPolicyLoad(policy=None, required_gaps=gaps)
    return SourceBudgetPolicyLoad(policy=policy, required_gaps=())
