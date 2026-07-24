"""Source-budget reducers over repository inventory and policy."""

import fnmatch
import hashlib
import json
from collections import Counter
from collections.abc import Mapping
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
from ethos_core.measure import effective_code_lines_for_source

_LIFECYCLE_FIELDS = {"owner", "replacement", "expiry", "allowance", "expected_net_deletion"}
_PATH_CONTENT_PAIR_SIZE = 2
_SHADOW_FIELD_ORDER = (
    "observer",
    "subject",
    "v1",
    "v2",
    "disagreements",
    "required_gaps",
    "comparison_state",
)
_SHADOW_FIELDS = frozenset(_SHADOW_FIELD_ORDER)
_SHADOW_OBSERVER_FIELDS = frozenset(
    {
        "profile_id",
        "commit_sha",
        "tree_sha",
        "taxonomy_path",
        "taxonomy_blob",
        "taxonomy_content_sha256",
        "taxonomy_semantic_sha256",
    }
)
_SHADOW_SUBJECT_FIELDS = frozenset({"commit_sha", "tree_sha", "snapshot_digest"})
_SHADOW_V1_FIELDS = frozenset(
    {
        "declaration_commit",
        "declared_total",
        "replay_total",
        "drift",
        "metrics",
        "category_deltas",
        "inventory",
    }
)
_SHADOW_V2_FIELDS = frozenset(
    {
        "manifest_digest",
        "inventory_digest",
        "contract_set_digest",
        "provider_coverage",
        "coordinates",
        "vector_digest",
        "snapshot_digest",
    }
)


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


def source_budget_carrier_effective_lines(content: bytes, carrier: SourceBudgetCarrier) -> int:
    """Measure one v1 carrier from immutable bytes with canonical semantics."""
    errors = "strict" if carrier.measure == "python_ast" else "replace"
    source = content.decode("utf-8", errors=errors)
    if carrier.measure == "python_ast":
        return effective_code_lines_for_source(source)
    return sum(
        not text.startswith(carrier.comment_prefixes)
        and not any(text.startswith(a) and text.endswith(b) for a, b in carrier.comment_wrappers)
        for line in source.splitlines()
        if (text := line.strip())
    )


def _carrier_effective_lines(path: Path, carrier: SourceBudgetCarrier) -> int:
    return source_budget_carrier_effective_lines(path.read_bytes(), carrier)


def source_budget_carrier_report(path: Path, relative: str) -> dict[str, object]:
    """Return category and effective lines for one carrier."""
    carrier = _source_budget_carrier(relative, source_budget_taxonomy(Path.cwd()))
    return _data(
        category=carrier.category if carrier else None,
        effective_lines=_carrier_effective_lines(path, carrier) if carrier else 0,
    )


def source_budget_taxonomy_digest(taxonomy: SourceBudgetTaxonomy) -> str:
    """Return the canonical semantic digest of one typed v1 taxonomy."""
    payload = taxonomy.model_dump(mode="json")
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def source_budget_metrics_from_bytes(
    contents: tuple[tuple[str, bytes], ...],
    taxonomy: SourceBudgetTaxonomy,
) -> tuple[dict[str, int], dict[str, object]]:
    """Replay v1 category metrics from ordered immutable path/bytes pairs."""
    if type(contents) is not tuple or type(taxonomy) is not SourceBudgetTaxonomy:
        message = "source-budget replay inputs invalid"
        raise ValueError(message)
    if not all(
        type(item) is tuple
        and len(item) == _PATH_CONTENT_PAIR_SIZE
        and type(item[0]) is str
        and type(item[1]) is bytes
        for item in contents
    ):
        message = "source-budget replay inputs invalid"
        raise ValueError(message)
    paths = tuple(item[0] for item in contents)
    if paths != tuple(sorted(set(paths))):
        message = "source-budget replay paths must be unique and ordered"
        raise ValueError(message)
    metrics = dict.fromkeys((item.category for item in taxonomy.carrier), 0)
    records: list[dict[str, object]] = []
    counts: dict[str, int] = {}
    for relative, content in contents:
        carrier = _source_budget_carrier(relative, taxonomy)
        if carrier is None:
            continue
        category = carrier.category
        lines = source_budget_carrier_effective_lines(content, carrier)
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


def _mapping_has_fields(value: object, fields: frozenset[str]) -> bool:
    return isinstance(value, Mapping) and set(value) == fields


def _valid_shadow_observation(observation: Mapping[str, object]) -> bool:
    if set(observation) != _SHADOW_FIELDS:
        return False
    observer = observation.get("observer")
    subject = observation.get("subject")
    v1 = observation.get("v1")
    v2 = observation.get("v2")
    gaps = observation.get("required_gaps")
    disagreements = observation.get("disagreements")
    state = observation.get("comparison_state")
    string_lists = (
        isinstance(gaps, list)
        and len(gaps) == len(set(gaps))
        and all(type(item) is str and item for item in gaps)
        and isinstance(disagreements, list)
        and len(disagreements) == len(set(disagreements))
        and all(type(item) is str and item for item in disagreements)
    )
    shapes = (
        _mapping_has_fields(observer, _SHADOW_OBSERVER_FIELDS)
        and _mapping_has_fields(subject, _SHADOW_SUBJECT_FIELDS)
        and _mapping_has_fields(v1, _SHADOW_V1_FIELDS)
        and (v2 is None or _mapping_has_fields(v2, _SHADOW_V2_FIELDS))
    )
    coherent = (
        state in {"blocked", "unresolved", "reviewed_observation"}
        and (state != "reviewed_observation" or not gaps)
        and (state == "reviewed_observation" or bool(gaps or disagreements))
    )
    return bool(string_lists and shapes and coherent)


def source_budget_shadow_report(
    v1_report: Mapping[str, object],
    observation: Mapping[str, object] | None,
) -> dict[str, object]:
    """Attach a fail-closed inactive-v2 observer without changing v1 authority."""
    report = dict(v1_report)
    if observation is None:
        report["v2_shadow"] = {
            "mode": "v1_authoritative_v2_shadow",
            "authoritative": "v1",
            "observer": None,
            "subject": None,
            "v1": None,
            "v2": None,
            "disagreements": [],
            "required_gaps": ["source_budget_v2_shadow_observation_missing"],
            "comparison_state": "blocked",
        }
        return report
    gaps = observation.get("required_gaps")
    disagreements = observation.get("disagreements")
    if not _valid_shadow_observation(observation):
        observed_gaps = list(gaps) if isinstance(gaps, list) else []
        observed_gaps.append("source_budget_v2_shadow_observation_invalid")
        shadow = {
            "observer": observation.get("observer"),
            "subject": observation.get("subject"),
            "v1": observation.get("v1"),
            "v2": observation.get("v2"),
            "disagreements": list(disagreements) if isinstance(disagreements, list) else [],
            "required_gaps": sorted(set(observed_gaps)),
            "comparison_state": "blocked",
        }
    else:
        shadow = {key: observation[key] for key in _SHADOW_FIELD_ORDER}
    report["v2_shadow"] = {
        "mode": "v1_authoritative_v2_shadow",
        "authoritative": "v1",
        **shadow,
    }
    return report


def _source_budget_today() -> date:
    return datetime.now(UTC).date()


def source_budget_report(
    root: Path, shadow_observation: Mapping[str, object] | None = None
) -> dict[str, object]:
    """Measure global executable source and reject undeclared growth."""
    loaded = source_budget_policy(root)
    if loaded.policy is None:
        return source_budget_shadow_report(
            _data(
                ok=False,
                state="blocked",
                metrics={},
                inventory={"file_count": 0},
                terminal_target_met=False,
                required_gaps=list(loaded.required_gaps),
            ),
            shadow_observation,
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
    return source_budget_shadow_report(result, shadow_observation)
