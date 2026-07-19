"""Source-budget domain reducers over repository inventory and policy."""

from __future__ import annotations

import fnmatch
import hashlib
import json
from dataclasses import dataclass
from dataclasses import field
from datetime import UTC
from datetime import date
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import ethos.adapters.repo.git as git_adapter
import ethos.adapters.repo.source_budget.core as source_budget_adapter
from ethos.adapters.config import source_budget_policy
from ethos.adapters.config import source_budget_taxonomy
from ethos_core.measure import effective_code_lines

if TYPE_CHECKING:
    from ethos_core.contracts.source_budget.core import SourceBudgetCarrier
    from ethos_core.contracts.source_budget.core import SourceBudgetPolicy
    from ethos_core.contracts.source_budget.core import SourceBudgetTaxonomy

_LIFECYCLE_FIELDS = {"owner", "replacement", "expiry", "allowance", "expected_net_deletion"}


@dataclass(frozen=True, slots=True)
class _DebtEnvelope:
    total: int = 0
    by_category: dict[str, int] = field(default_factory=dict)
    ids: list[str] = field(default_factory=list)


def _source_budget_carrier(
    relative: str, taxonomy: SourceBudgetTaxonomy
) -> SourceBudgetCarrier | None:
    path = relative.lower()
    if path.startswith("openspec/changes/archive/") and path.endswith("/.openspec.yaml"):
        return None
    return next(
        (
            carrier
            for carrier in taxonomy.carrier
            if path.endswith(carrier.extensions)
            and (
                not carrier.paths
                or any(fnmatch.fnmatchcase(path, pattern) for pattern in carrier.paths)
            )
        ),
        None,
    )


def _carrier_effective_lines(path: Path, carrier: SourceBudgetCarrier) -> int:
    if carrier.measure == "python_ast":
        return effective_code_lines(path)
    return sum(
        not stripped.startswith(carrier.comment_prefixes)
        and not any(
            stripped.startswith(start) and stripped.endswith(end)
            for start, end in carrier.comment_wrappers
        )
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
        if (stripped := line.strip())
    )


def source_budget_carrier_report(path: Path, relative: str) -> dict[str, object]:
    """Return the public category and effective-line read model for one carrier."""
    carrier = _source_budget_carrier(relative, source_budget_taxonomy(Path.cwd()))
    return {
        "category": carrier.category if carrier else None,
        "effective_lines": _carrier_effective_lines(path, carrier) if carrier else 0,
    }


def _source_budget_metrics(
    root: Path, taxonomy: SourceBudgetTaxonomy
) -> tuple[dict[str, int], dict[str, object]]:
    metrics = dict.fromkeys((carrier.category for carrier in taxonomy.carrier), 0)
    records: list[dict[str, object]] = []
    category_counts: dict[str, int] = {}
    for relative in source_budget_adapter.present_worktree_paths(root):
        if (carrier := _source_budget_carrier(relative, taxonomy)) is None:
            continue
        category = carrier.category
        lines = _carrier_effective_lines(root / relative, carrier)
        metrics[category] += lines
        category_counts[category] = category_counts.get(category, 0) + 1
        records.append({"path": relative, "category": category, "effective_lines": lines})
    metrics.update(
        {
            name: sum(metrics[category] for category in members)
            for name, members in taxonomy.aggregates.items()
        }
    )
    # fmt: off
    return metrics, {"digest": hashlib.sha256(json.dumps(records, sort_keys=True, separators=(",", ":")).encode()).hexdigest(), "file_count": len(records), "category_counts": dict(sorted(category_counts.items()))}  # noqa: E501
    # fmt: on


def _source_budget_debt(policy: SourceBudgetPolicy) -> _DebtEnvelope:
    debt = _DebtEnvelope(sum(record.allowance for record in policy.debt.records))
    for record in policy.debt.records:
        debt.ids.append(record.id)
        for category, value in record.allowance_by_category.items():
            debt.by_category[category] = debt.by_category.get(category, 0) + value
    return debt


def _source_budget_overages(
    metrics: dict[str, int],
    policy: SourceBudgetPolicy,
    taxonomy: SourceBudgetTaxonomy,
    debt: _DebtEnvelope,
) -> list[tuple[str, int, int]]:
    overages: list[tuple[str, int, int]] = []
    for category, baseline in sorted(policy.baseline.items()):
        if (current := metrics.get(category)) is None:
            continue
        members = taxonomy.aggregates.get(category, (category,))
        allowed = baseline + sum(debt.by_category.get(member, 0) for member in members)
        if current > allowed:
            overages.append((category, current, allowed))
    return overages


def _source_budget_messages(prefix: str, overages: list[tuple[str, int, int]]) -> list[str]:
    return [f"{prefix}:{category}:{current}>{allowed}" for category, current, allowed in overages]


def _source_budget_today() -> date:
    return datetime.now(UTC).date()


def _source_budget_lifecycle(
    policy: SourceBudgetPolicy, required_gaps: list[str]
) -> list[dict[str, object]]:
    waves = {wave.id: wave for wave in policy.debt.waves}
    lifecycle: list[dict[str, object]] = []
    today = _source_budget_today()
    for record in policy.debt.records:
        wave = waves[record.deletion_wave]
        expired = date.fromisoformat(record.expiry) < today
        stale = wave.state == "settled"
        record_gaps = [
            *([f"source_budget_debt_expired:{record.id}"] if expired else []),
            *([f"source_budget_debt_stale:{record.id}"] if stale else []),
        ]
        lifecycle.append(
            {
                "id": record.id,
                "wave": record.deletion_wave,
                "wave_due_on": wave.due_on,
                "wave_state": wave.state,
                **record.model_dump(include=_LIFECYCLE_FIELDS),
                "status": "expired" if expired else "stale" if stale else "active",
                "required_gaps": record_gaps,
            }
        )
        required_gaps.extend(record_gaps)
    return lifecycle


def source_budget_report(root: Path) -> dict[str, object]:
    """Measure global executable source and reject growth beyond declared debt."""
    loaded = source_budget_policy(root)
    if loaded.policy is None:
        # fmt: off
        return {"ok": False, "state": "blocked", "metrics": {}, "inventory": {"file_count": 0}, "terminal_target_met": False, "required_gaps": list(loaded.required_gaps)}  # noqa: E501
        # fmt: on
    policy = loaded.policy
    taxonomy = source_budget_taxonomy(root)
    metrics, inventory = _source_budget_metrics(root, taxonomy)
    debt = _source_budget_debt(policy)
    overages = _source_budget_overages(metrics, policy, taxonomy, debt)
    terminal_target_met = all(
        metrics.get(category, 0) <= target for category, target in policy.terminal.items()
    )
    verdict_gaps = (
        [f"source_budget_debt_exceeded:{debt.total}>{policy.debt.maximum_total}"]
        if debt.total > policy.debt.maximum_total
        else []
    )
    if policy.enforcement == "transition":
        verdict_gaps.extend(_source_budget_messages("source_budget_exceeded", overages))
    elif policy.enforcement == "terminal" and not terminal_target_met:
        verdict_gaps.extend(
            f"source_budget_terminal_exceeded:{category}:{metrics.get(category, 0)}>{target}"
            for category, target in policy.terminal.items()
            if metrics.get(category, 0) > target
        )
    baseline_resolved = bool(
        git_adapter.git_stdout(root, "rev-parse", "--verify", f"{policy.baseline_head}^{{commit}}")
    )
    required_gaps = (
        []
        if baseline_resolved
        else [f"source_budget_baseline_head_unresolved:{policy.baseline_head}"]
    )
    lifecycle = _source_budget_lifecycle(policy, required_gaps)
    required_gaps.extend(verdict_gaps)
    advisory_gaps = (
        _source_budget_messages("source_budget_campaign_growth_overage", overages)
        if policy.enforcement == "campaign_terminal"
        else []
    )
    # fmt: off
    return {"ok": not required_gaps, "state": "clean" if not required_gaps else "blocked", "enforcement": policy.enforcement, "campaign_id": getattr(policy, "campaign_id", ""), "baseline": dict(policy.baseline), "baseline_head": {"value": policy.baseline_head, "resolved": baseline_resolved}, "terminal": dict(policy.terminal), "metrics": metrics, "inventory": inventory, "active_debt": {"allowance": debt.total, "ids": debt.ids, "maximum": policy.debt.maximum_total}, "debt_lifecycle": lifecycle, "terminal_target_met": terminal_target_met, "advisory_gaps": advisory_gaps, "required_gaps": required_gaps}  # noqa: E501
    # fmt: on
