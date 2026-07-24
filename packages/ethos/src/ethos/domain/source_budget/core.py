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
from pathlib import PurePosixPath
from typing import Annotated
from typing import Any
from typing import Literal
from typing import Self

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import StrictStr
from pydantic import ValidationError
from pydantic import field_validator
from pydantic import model_validator

import ethos.adapters.repo.git as git_adapter
import ethos.adapters.repo.source_budget.core as source_budget_adapter
from ethos.adapters.config import source_budget_policy
from ethos.adapters.config import source_budget_taxonomy
from ethos_core.contracts.source_budget.core import SourceBudgetCarrier
from ethos_core.contracts.source_budget.core import SourceBudgetTaxonomy
from ethos_core.measure import effective_code_lines_for_source

_LIFECYCLE_FIELDS = {"owner", "replacement", "expiry", "allowance", "expected_net_deletion"}
_PATH_CONTENT_PAIR_SIZE = 2
_GIT_OID = r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$"
_SHA256 = r"^[0-9a-f]{64}$"
_NONSPACE_PATTERN = r"^\S+$"
_SHADOW_TAXONOMY_PATH_INVALID = "shadow taxonomy path invalid"
_SHADOW_INVENTORY_COUNT_INVALID = "shadow inventory count invalid"
_SHADOW_V1_TOTALS_INVALID = "shadow v1 totals invalid"
_SHADOW_V2_COORDINATES_INVALID = "shadow v2 coordinates invalid"
_SHADOW_TOKENS_NOT_UNIQUE = "shadow tokens must be unique"
_SHADOW_COMPARISON_STATE_INVALID = "shadow comparison state invalid"
_ShadowToken = Annotated[StrictStr, Field(min_length=1, pattern=_NONSPACE_PATTERN)]
_ShadowGitOid = Annotated[StrictStr, Field(pattern=_GIT_OID)]
_ShadowSha256 = Annotated[StrictStr, Field(pattern=_SHA256)]
_ShadowCount = Annotated[int, Field(strict=True, ge=0)]


class _ShadowStrict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class _ShadowObserver(_ShadowStrict):
    profile_id: _ShadowToken
    commit_sha: _ShadowGitOid
    tree_sha: _ShadowGitOid
    taxonomy_path: StrictStr
    taxonomy_blob: _ShadowGitOid
    taxonomy_content_sha256: _ShadowSha256
    taxonomy_semantic_sha256: _ShadowSha256

    @field_validator("taxonomy_path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if (
            not value
            or "\x00" in value
            or "\\" in value
            or path.is_absolute()
            or str(path) != value
            or any(part in {"", ".", ".."} for part in path.parts)
        ):
            raise ValueError(_SHADOW_TAXONOMY_PATH_INVALID)
        return value


class _ShadowSubject(_ShadowStrict):
    commit_sha: _ShadowGitOid
    tree_sha: _ShadowGitOid
    snapshot_digest: _ShadowSha256


class _ShadowInventory(_ShadowStrict):
    file_count: _ShadowCount
    digest: _ShadowSha256
    category_counts: dict[_ShadowToken, _ShadowCount]

    @model_validator(mode="after")
    def validate_file_count(self) -> Self:
        if self.file_count != sum(self.category_counts.values()):
            raise ValueError(_SHADOW_INVENTORY_COUNT_INVALID)
        return self


class _ShadowV1(_ShadowStrict):
    declaration_commit: _ShadowGitOid
    declared_total: _ShadowCount
    replay_total: _ShadowCount
    drift: int = Field(strict=True)
    metrics: dict[_ShadowToken, _ShadowCount]
    category_deltas: dict[_ShadowToken, int]
    inventory: _ShadowInventory

    @model_validator(mode="after")
    def validate_totals(self) -> Self:
        if (
            self.drift != self.replay_total - self.declared_total
            or self.metrics.get("global_total") != self.replay_total
        ):
            raise ValueError(_SHADOW_V1_TOTALS_INVALID)
        return self


class _ShadowCoordinate(_ShadowStrict):
    scope_id: _ShadowToken
    metric_id: _ShadowToken
    unit: Literal[
        "lexical_token",
        "semantic_node",
        "normalized_byte",
        "normalized_scalar_byte",
        "template_dynamic_byte",
        "template_dynamic_unit",
        "template_static_byte",
    ]
    value: _ShadowCount


class _ShadowV2(_ShadowStrict):
    manifest_digest: _ShadowSha256
    inventory_digest: _ShadowSha256
    contract_set_digest: _ShadowSha256
    provider_coverage: dict[_ShadowToken, _ShadowCount]
    coordinates: list[_ShadowCoordinate]
    vector_digest: _ShadowSha256
    snapshot_digest: _ShadowSha256

    @model_validator(mode="after")
    def validate_snapshot_state(self) -> Self:
        keys = tuple((item.scope_id, item.metric_id, item.unit) for item in self.coordinates)
        if keys != tuple(sorted(set(keys))):
            raise ValueError(_SHADOW_V2_COORDINATES_INVALID)
        return self


class SourceBudgetShadowObservation(_ShadowStrict):
    """Reviewed Task 4 replay observation consumed by later pure reducers."""

    observer: _ShadowObserver
    subject: _ShadowSubject
    v1: _ShadowV1
    v2: _ShadowV2 | None
    disagreements: list[_ShadowToken]
    required_gaps: list[_ShadowToken]
    comparison_state: Literal["blocked", "unresolved", "reviewed_observation"]

    @field_validator("disagreements", "required_gaps")
    @classmethod
    def validate_unique_tokens(cls, values: list[str]) -> list[str]:
        if len(values) != len(set(values)):
            raise ValueError(_SHADOW_TOKENS_NOT_UNIQUE)
        return values

    @model_validator(mode="after")
    def validate_state(self) -> Self:
        if (self.comparison_state == "reviewed_observation" and self.required_gaps) or (
            self.comparison_state != "reviewed_observation"
            and not (self.required_gaps or self.disagreements)
        ):
            raise ValueError(_SHADOW_COMPARISON_STATE_INVALID)
        return self


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


def _blocked_shadow(gap: str) -> dict[str, object]:
    return {
        "mode": "v1_authoritative_v2_shadow",
        "authoritative": "v1",
        "observer": None,
        "subject": None,
        "v1": None,
        "v2": None,
        "disagreements": [],
        "required_gaps": [gap],
        "comparison_state": "blocked",
    }


def source_budget_shadow_report(
    v1_report: Mapping[str, object],
    observation: Mapping[str, object] | None,
) -> dict[str, object]:
    """Attach a fail-closed inactive-v2 observer without changing v1 authority."""
    report = dict(v1_report)
    if observation is None:
        report["v2_shadow"] = _blocked_shadow("source_budget_v2_shadow_observation_missing")
        return report
    if type(observation) is not dict:
        report["v2_shadow"] = _blocked_shadow("source_budget_v2_shadow_observation_invalid")
        return report
    try:
        shadow = SourceBudgetShadowObservation.model_validate(observation).model_dump(mode="json")
    except (AttributeError, TypeError, ValueError, ValidationError):
        report["v2_shadow"] = _blocked_shadow("source_budget_v2_shadow_observation_invalid")
        return report
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
    elif policy.enforcement in {"campaign_terminal", "terminal"} and not terminal_met:
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
