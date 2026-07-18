from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING
from typing import Any

import ethos.repository.policy.layout.git.core as layout_git
from ethos.repository.policy.layout.filesystem.core import POLICY_PATH
from ethos.repository.policy.layout.filesystem.core import string_list

if TYPE_CHECKING:
    from pathlib import Path


BASELINE_KINDS: tuple[tuple[str, str, str], ...] = (
    ("suffix_module", "allowed_suffix_modules", "baseline_suffix_module_limit"),
    ("suffix_flat", "allowed_suffix_flat", "baseline_suffix_flat_limit"),
    ("flat_directory", "allowed_flat_directories", "baseline_flat_directory_limit"),
    ("private_alias", "allowed_private_aliases", "baseline_private_alias_limit"),
    (
        "package_init_facade",
        "allowed_package_init_facades",
        "baseline_package_init_facade_limit",
    ),
    ("module_facade", "allowed_module_facades", "baseline_module_facade_limit"),
)


def baseline_gap_set(policy: dict[str, Any]) -> set[str]:
    """Return all currently allowed module-layout debt gaps."""
    gaps: set[str] = set()
    for _kind, key, _limit_key in BASELINE_KINDS:
        gaps.update(string_list(policy.get(key)))
    return gaps


def baseline_kind_counts(policy: dict[str, Any]) -> dict[str, int]:
    """Return module-layout debt counts by explicit policy kind."""
    return {
        kind: len(set(string_list(policy.get(key)))) for kind, key, _limit_key in BASELINE_KINDS
    }


def baseline_kind_limits(policy: dict[str, Any]) -> dict[str, int | None]:
    """Return per-kind baseline debt limits when declared."""
    return {kind: _integer_value(policy.get(limit_key)) for kind, _key, limit_key in BASELINE_KINDS}


def baseline_kind_limit_findings(
    policy: dict[str, Any],
    counts: dict[str, int],
) -> list[dict[str, object]]:
    """Return gaps for missing or stale per-kind debt ratchets."""
    if not bool(policy.get("enforce_baseline_kind_limits")):
        return []
    limits = baseline_kind_limits(policy)
    findings: list[dict[str, object]] = []
    for kind, _key, _limit_key in BASELINE_KINDS:
        count = counts.get(kind, 0)
        limit = limits.get(kind)
        if limit is None:
            findings.append(
                {
                    "gap": f"module_layout_baseline_{kind}_limit_missing",
                    "kind": kind,
                    "count": count,
                }
            )
            continue
        if count != limit:
            findings.append(
                {
                    "gap": f"module_layout_baseline_{kind}_limit:{count}!={limit}",
                    "kind": kind,
                    "count": count,
                    "limit": limit,
                }
            )
    return findings


def stale_baseline_findings(
    baseline: set[str],
    current_gaps: set[str],
) -> list[dict[str, object]]:
    """Return baseline entries that no longer correspond to current findings."""
    findings: list[dict[str, object]] = []
    for gap in sorted(baseline - current_gaps):
        findings.append({"gap": f"module_layout_stale_baseline:{gap}", "baseline_gap": gap})
    return findings


def baseline_limit(policy: dict[str, Any]) -> int | None:
    """Return the declared baseline gap limit when present."""
    return _integer_value(policy.get("baseline_gap_limit"))


def baseline_limit_gaps(count: int, limit: int | None) -> list[str]:
    """Return gaps for missing, grown, or stale baseline limit values."""
    if count == 0:
        return []
    if limit is None:
        return ["module_layout_baseline_limit_missing"]
    if count == limit:
        return []
    if count > limit:
        return [f"module_layout_baseline_limit:{count}>{limit}"]
    return [f"module_layout_baseline_limit:{count}!={limit}"]


def baseline_growth_findings(
    root: Path,
    policy: dict[str, Any],
    baseline: set[str],
) -> list[dict[str, object]]:
    """Return findings for baseline debt growth relative to the layout reference."""
    previous_policy = previous_policy_at_reference(root, policy)
    if previous_policy is None:
        return []
    previous_baseline = baseline_gap_set(previous_policy)
    findings: list[dict[str, object]] = []
    for gap in sorted(baseline - previous_baseline):
        findings.append({"gap": f"module_layout_baseline_growth:{gap}", "baseline_gap": gap})
    current_limit = baseline_limit(policy)
    previous_limit = baseline_limit(previous_policy)
    if current_limit is not None and previous_limit is not None and current_limit > previous_limit:
        findings.append(
            {
                "gap": f"module_layout_baseline_limit_growth:{current_limit}>{previous_limit}",
                "baseline_limit": current_limit,
                "previous_baseline_limit": previous_limit,
            }
        )
    return findings


def previous_policy_at_reference(root: Path, policy: dict[str, Any]) -> dict[str, Any] | None:
    """Load module-layout policy from the current incremental reference."""
    reference = layout_git.layout_reference(root)
    if reference is None:
        return None
    raw = layout_git.run_git_show(root, f"{reference}:{POLICY_PATH.as_posix()}")
    if raw is None:
        return policy
    return tomllib.loads(raw)


def _integer_value(value: object) -> int | None:
    if isinstance(value, int):
        return value
    return None
