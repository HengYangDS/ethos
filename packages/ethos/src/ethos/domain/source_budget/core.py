"""Source-budget reducers over repository inventory and policy."""

import fnmatch
import hashlib
import json
from collections import Counter
from datetime import UTC
from datetime import date
from datetime import datetime
from pathlib import Path
from typing import Any

import ethos.adapters.repo.git as git_adapter
import ethos.adapters.repo.source_budget.core as source_budget_adapter
from ethos.adapters.config import source_budget_policy
from ethos.adapters.config import source_budget_taxonomy
from ethos_core.contracts.source_budget.core import SourceBudgetCarrier
from ethos_core.contracts.source_budget.core import SourceBudgetTaxonomy
from ethos_core.measure import effective_code_lines

_LIFECYCLE_FIELDS = {"owner", "replacement", "expiry", "allowance", "expected_net_deletion"}


def _data(**values: Any) -> dict[str, Any]:
    return values


def _source_budget_carrier(
    relative: str, taxonomy: SourceBudgetTaxonomy
) -> SourceBudgetCarrier | None:
    path = relative.lower()
    if path.startswith("openspec/changes/archive/") and path.endswith("/.openspec.yaml"):
        return None
    return next(
        (
            item
            for item in taxonomy.carrier
            if path.endswith(item.extensions)
            and (not item.paths or any(fnmatch.fnmatchcase(path, rule) for rule in item.paths))
        ),
        None,
    )


def _carrier_effective_lines(path: Path, carrier: SourceBudgetCarrier) -> int:
    if carrier.measure == "python_ast":
        return effective_code_lines(path)
    return sum(
        not text.startswith(carrier.comment_prefixes)
        and not any(text.startswith(a) and text.endswith(b) for a, b in carrier.comment_wrappers)
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
        if (text := line.strip())
    )


def source_budget_carrier_report(path: Path, relative: str) -> dict[str, object]:
    """Return category and effective lines for one carrier."""
    carrier = _source_budget_carrier(relative, source_budget_taxonomy(Path.cwd()))
    return _data(
        category=carrier.category if carrier else None,
        effective_lines=_carrier_effective_lines(path, carrier) if carrier else 0,
    )


def _source_budget_metrics(
    root: Path, taxonomy: SourceBudgetTaxonomy
) -> tuple[dict[str, int], dict[str, object]]:
    metrics = dict.fromkeys((item.category for item in taxonomy.carrier), 0)
    records: list[dict[str, object]] = []
    counts: dict[str, int] = {}
    for relative in source_budget_adapter.present_worktree_paths(root):
        carrier = _source_budget_carrier(relative, taxonomy)
        if carrier is None:
            continue
        category, lines = carrier.category, _carrier_effective_lines(root / relative, carrier)
        metrics[category] += lines
        counts[category] = counts.get(category, 0) + 1
        records.append(_data(path=relative, category=category, effective_lines=lines))
    metrics.update(
        {
            name: sum(metrics[item] for item in members)
            for name, members in taxonomy.aggregates.items()
        }
    )
    digest = hashlib.sha256(json.dumps(records, sort_keys=True, separators=(",", ":")).encode())
    return metrics, _data(
        digest=digest.hexdigest(),
        file_count=len(records),
        category_counts=dict(sorted(counts.items())),
    )


def _source_budget_today() -> date:
    return datetime.now(UTC).date()


def source_budget_report(root: Path) -> dict[str, object]:
    """Measure global executable source and reject undeclared growth."""
    loaded = source_budget_policy(root)
    if loaded.policy is None:
        return _data(
            ok=False,
            state="blocked",
            metrics={},
            inventory={"file_count": 0},
            terminal_target_met=False,
            required_gaps=list(loaded.required_gaps),
        )
    policy, taxonomy = loaded.policy, source_budget_taxonomy(root)
    metrics, inventory = _source_budget_metrics(root, taxonomy)
    records = policy.debt.records
    debt = sum((Counter(record.allowance_by_category) for record in records), Counter())
    debt_total = sum(record.allowance for record in records)
    overages = [
        (category, current, allowed)
        for category, baseline in sorted(policy.baseline.items())
        if (current := metrics.get(category)) is not None
        if current
        > (
            allowed := baseline
            + sum(debt.get(item, 0) for item in taxonomy.aggregates.get(category, (category,)))
        )
    ]

    def messages(prefix: str) -> list[str]:
        return [
            f"{prefix}:{category}:{current}>{allowed}" for category, current, allowed in overages
        ]

    terminal_met = all(
        metrics.get(category, 0) <= target for category, target in policy.terminal.items()
    )
    verdict = (
        [f"source_budget_debt_exceeded:{debt_total}>{policy.debt.maximum_total}"]
        if debt_total > policy.debt.maximum_total
        else []
    )
    if policy.enforcement == "transition":
        verdict += messages("source_budget_exceeded")
    elif policy.enforcement == "terminal" and not terminal_met:
        verdict += [
            f"source_budget_terminal_exceeded:{category}:{metrics.get(category, 0)}>{target}"
            for category, target in policy.terminal.items()
            if metrics.get(category, 0) > target
        ]
    resolved = bool(
        git_adapter.git_stdout(root, "rev-parse", "--verify", f"{policy.baseline_head}^{{commit}}")
    )
    required = (
        [] if resolved else [f"source_budget_baseline_head_unresolved:{policy.baseline_head}"]
    )
    waves, lifecycle, today = (
        {wave.id: wave for wave in policy.debt.waves},
        [],
        _source_budget_today(),
    )
    for record in records:
        wave = waves[record.deletion_wave]
        status = (
            "expired"
            if date.fromisoformat(record.expiry) < today
            else "stale"
            if wave.state == "settled"
            else "active"
        )
        gaps = [f"source_budget_debt_{status}:{record.id}"] if status != "active" else []
        lifecycle.append(
            _data(
                id=record.id,
                wave=record.deletion_wave,
                wave_due_on=wave.due_on,
                wave_state=wave.state,
            )
            | record.model_dump(include=_LIFECYCLE_FIELDS)
            | _data(status=status, required_gaps=gaps)
        )
        required.extend(gaps)
    required.extend(verdict)
    advisory = (
        messages("source_budget_campaign_growth_overage")
        if policy.enforcement == "campaign_terminal"
        else []
    )
    result = policy.model_dump(include={"baseline", "terminal", "enforcement", "campaign_id"})
    result |= _data(ok=not required, state="clean" if not required else "blocked")
    result |= _data(
        baseline_head={"value": policy.baseline_head, "resolved": resolved},
        campaign_id=getattr(policy, "campaign_id", ""),
    )
    result |= _data(metrics=metrics, inventory=inventory, debt_lifecycle=lifecycle)
    result |= _data(
        active_debt={
            "allowance": debt_total,
            "ids": [record.id for record in records],
            "maximum": policy.debt.maximum_total,
        },
        terminal_target_met=terminal_met,
    )
    result |= _data(advisory_gaps=advisory, required_gaps=required)
    return result
