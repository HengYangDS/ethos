"""Source-budget domain reducers over repository inventory and policy."""

from __future__ import annotations

import fnmatch
import hashlib
import json
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


def _source_budget_carrier(
    relative: str, taxonomy: SourceBudgetTaxonomy
) -> SourceBudgetCarrier | None:
    """Classify one present executable carrier without inventing a source role."""
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
    """Count non-Python carriers with the same blank/comment rule as the budget."""
    if carrier.measure == "python_ast":
        return effective_code_lines(path)
    count = 0
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(carrier.comment_prefixes):
            continue
        if any(
            stripped.startswith(start) and stripped.endswith(end)
            for start, end in carrier.comment_wrappers
        ):
            continue
        count += 1
    return count


def source_budget_carrier_report(path: Path, relative: str) -> dict[str, object]:
    """Return the public category and effective-line read model for one carrier."""
    carrier = _source_budget_carrier(relative, source_budget_taxonomy(Path.cwd()))
    return {
        "category": carrier.category if carrier else None,
        "effective_lines": _carrier_effective_lines(path, carrier) if carrier else 0,
    }


def _source_budget_allowance(
    policy: SourceBudgetPolicy,
) -> tuple[int, dict[str, int], list[str]]:
    """Compile validated temporary growth allowance without a second ledger model."""
    total = 0
    categories: dict[str, int] = {}
    ids: list[str] = []
    for record in policy.debt.records:
        total += record.allowance
        for category, value in record.allowance_by_category.items():
            categories[category] = categories.get(category, 0) + value
        ids.append(record.id)
    return total, categories, ids


def _source_budget_allowance_for(
    category: str,
    *,
    aggregates: dict[str, tuple[str, ...]],
    by_category: dict[str, int],
) -> int:
    """Derive aggregate allowance only from declared carrier allowances."""
    if members := aggregates.get(category):
        return sum(by_category.get(member, 0) for member in members)
    return by_category.get(category, 0)


def _source_budget_metrics(
    root: Path, taxonomy: SourceBudgetTaxonomy
) -> tuple[dict[str, int], dict[str, object]]:
    """Measure every present declared source carrier and return its identity."""
    categories = tuple(carrier.category for carrier in taxonomy.carrier)
    metrics = dict.fromkeys(categories, 0)
    records: list[dict[str, object]] = []
    category_counts: dict[str, int] = {}
    for relative in source_budget_adapter.present_worktree_paths(root):
        carrier = _source_budget_carrier(relative, taxonomy)
        path = root / relative
        if carrier is None:
            continue
        category = carrier.category
        effective_lines = _carrier_effective_lines(path, carrier)
        metrics[category] += effective_lines
        category_counts[category] = category_counts.get(category, 0) + 1
        records.append({"path": relative, "category": category, "effective_lines": effective_lines})
    metrics.update(
        {
            name: sum(metrics[category] for category in members)
            for name, members in taxonomy.aggregates.items()
        }
    )
    digest = hashlib.sha256(
        json.dumps(records, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return metrics, {
        "digest": digest,
        "file_count": len(records),
        "category_counts": dict(sorted(category_counts.items())),
    }


def _source_budget_verdict(
    metrics: dict[str, int],
    policy: SourceBudgetPolicy,
    taxonomy: SourceBudgetTaxonomy,
) -> tuple[dict[str, int], dict[str, int], int, list[str], int, bool, list[str], list[str]]:
    """Compile baseline, debt, and terminal verdicts from measured carriers."""
    baseline = {str(key): value for key, value in policy.baseline.items()}
    terminal = {str(key): value for key, value in policy.terminal.items()}
    debt_total, debt_by_category, debt_ids = _source_budget_allowance(policy)
    maximum_debt = policy.debt.maximum_total
    gaps: list[str] = []
    if debt_total > maximum_debt:
        gaps.append(f"source_budget_debt_exceeded:{debt_total}>{maximum_debt}")
    baseline_overages = _source_budget_overages(
        metrics,
        baseline,
        aggregates=taxonomy.aggregates,
        by_category=debt_by_category,
    )
    if policy.enforcement == "transition":
        gaps.extend(
            f"source_budget_exceeded:{category}:{current}>{allowed}"
            for category, current, allowed in baseline_overages
        )
    terminal_target_met = all(
        metrics.get(category, 0) <= target for category, target in terminal.items()
    )
    if policy.enforcement == "terminal" and not terminal_target_met:
        gaps.extend(
            f"source_budget_terminal_exceeded:{category}:{metrics.get(category, 0)}>{target}"
            for category, target in terminal.items()
            if metrics.get(category, 0) > target
        )
    advisories = (
        [
            f"source_budget_campaign_growth_overage:{category}:{current}>{allowed}"
            for category, current, allowed in baseline_overages
        ]
        if policy.enforcement == "campaign_terminal"
        else []
    )
    return (
        baseline,
        terminal,
        debt_total,
        debt_ids,
        maximum_debt,
        terminal_target_met,
        gaps,
        advisories,
    )


def _source_budget_overages(
    metrics: dict[str, int],
    baseline: dict[str, int],
    *,
    aggregates: dict[str, tuple[str, ...]],
    by_category: dict[str, int],
) -> list[tuple[str, int, int]]:
    """Return measured categories above baseline plus declared allowance."""
    overages: list[tuple[str, int, int]] = []
    for category, baseline_value in sorted(baseline.items()):
        current = metrics.get(category)
        if current is None:
            continue
        allowed = baseline_value + _source_budget_allowance_for(
            category,
            aggregates=aggregates,
            by_category=by_category,
        )
        if current > allowed:
            overages.append((category, current, allowed))
    return overages


def _source_budget_today() -> date:
    """Return the UTC calendar date used by debt-expiry evaluation."""
    return datetime.now(UTC).date()


def _source_budget_lifecycle(
    policy: SourceBudgetPolicy,
) -> tuple[list[dict[str, object]], list[str]]:
    """Project every declared debt record and fail closed on stale lifecycle state."""
    today = _source_budget_today()
    waves = {wave.id: wave for wave in policy.debt.waves}
    records: list[dict[str, object]] = []
    gaps: list[str] = []
    for record in policy.debt.records:
        record_gaps: list[str] = []
        if date.fromisoformat(record.expiry) < today:
            record_gaps.append(f"source_budget_debt_expired:{record.id}")
        if waves[record.deletion_wave].state == "settled":
            record_gaps.append(f"source_budget_debt_stale:{record.id}")
        status = "expired" if record_gaps and "expired" in record_gaps[0] else "stale"
        if not record_gaps:
            status = "active"
        records.append(
            {
                "id": record.id,
                "wave": record.deletion_wave,
                "wave_due_on": waves[record.deletion_wave].due_on,
                "wave_state": waves[record.deletion_wave].state,
                "owner": record.owner,
                "replacement": record.replacement,
                "expiry": record.expiry,
                "allowance": record.allowance,
                "expected_net_deletion": record.expected_net_deletion,
                "status": status,
                "required_gaps": record_gaps,
            }
        )
        gaps.extend(record_gaps)
    return records, gaps


def source_budget_report(root: Path) -> dict[str, object]:
    """Measure global executable source and reject growth beyond declared debt."""
    loaded = source_budget_policy(root)
    if loaded.policy is None:
        return {
            "ok": False,
            "state": "blocked",
            "metrics": {},
            "inventory": {"file_count": 0},
            "terminal_target_met": False,
            "required_gaps": list(loaded.required_gaps),
        }
    policy = loaded.policy
    taxonomy = source_budget_taxonomy(root)
    metrics, inventory = _source_budget_metrics(root, taxonomy)
    (
        baseline,
        terminal,
        debt_total,
        debt_ids,
        maximum_debt,
        terminal_target_met,
        gaps,
        advisory_gaps,
    ) = _source_budget_verdict(metrics, policy, taxonomy)
    lifecycle, lifecycle_gaps = _source_budget_lifecycle(policy)
    baseline_resolved = bool(
        git_adapter.git_stdout(root, "rev-parse", "--verify", f"{policy.baseline_head}^{{commit}}")
    )
    required_gaps = (
        []
        if baseline_resolved
        else [f"source_budget_baseline_head_unresolved:{policy.baseline_head}"]
    )
    required_gaps.extend(lifecycle_gaps)
    required_gaps.extend(gaps)
    return {
        "ok": not required_gaps,
        "state": "clean" if not required_gaps else "blocked",
        "enforcement": policy.enforcement,
        "campaign_id": getattr(policy, "campaign_id", ""),
        "baseline": baseline,
        "baseline_head": {"value": policy.baseline_head, "resolved": baseline_resolved},
        "terminal": terminal,
        "metrics": metrics,
        "inventory": inventory,
        "active_debt": {
            "allowance": debt_total,
            "ids": debt_ids,
            "maximum": maximum_debt,
        },
        "debt_lifecycle": lifecycle,
        "terminal_target_met": terminal_target_met,
        "advisory_gaps": advisory_gaps,
        "required_gaps": required_gaps,
    }
