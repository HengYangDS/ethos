"""Direct deterministic owned-source measurement."""

from __future__ import annotations

import configparser
import fnmatch
import hashlib
import json
import math
import shutil
import subprocess
import tomllib
from collections import Counter
from pathlib import Path
from typing import cast

import yaml

import ethos.adapters.repo.git as git_adapter
from ethos.domain.source_budget.measurement_policy import PYTHON_CATEGORIES
from ethos.domain.source_budget.measurement_policy import TERMINAL_TOTALS
from ethos.domain.source_budget.measurement_policy import Carrier
from ethos.domain.source_budget.measurement_policy import Policy
from ethos.domain.source_budget.measurement_policy import policy_for_root
from ethos.measure import effective_code_lines_for_source


def _table(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError
    return {str(key): item for key, item in value.items()}


def _sequence(value: object) -> list[object]:
    if not isinstance(value, list):
        raise TypeError
    return cast("list[object]", value)


def _blocked(*gaps: str) -> dict[str, object]:
    return {
        "verdict": "block",
        "state": "blocked",
        "terminal": {},
        "metrics": {},
        "enforced_metrics": {},
        "inventory": {"file_count": 0},
        "cross_check": {},
        "required_gaps": list(gaps),
        "advisory_gaps": [],
    }


def _paths(root: Path) -> tuple[tuple[tuple[str, bool], ...] | None, tuple[str, ...]]:
    tracked = git_adapter.git_stdout(root, "ls-files", "--stage", "--cached")
    if not tracked:
        return None, ("source_budget_inventory_unavailable",)
    resolved = root.resolve()
    paths: dict[str, bool] = {}
    for line in tracked.splitlines():
        try:
            metadata, relative = line.split("\t", 1)
        except ValueError:
            return None, ("source_budget_inventory_unavailable",)
        path = (resolved / relative).resolve()
        if path.is_relative_to(resolved) and path.is_file():
            paths[relative] = metadata.startswith("100755 ")
    for relative in git_adapter.git_files(root, "--others", "--exclude-standard"):
        path = (resolved / relative).resolve()
        if path.is_relative_to(resolved) and path.is_file():
            paths[relative] = bool(path.stat().st_mode & 0o111)
    return tuple(sorted(paths.items())), ()


def _carrier(
    relative: str,
    *,
    executable: bool,
    root: Path,
    carriers: tuple[Carrier, ...],
    source: bytes | None = None,
) -> tuple[Carrier | None, str]:
    lowered = relative.lower()
    if lowered.startswith("openspec/changes/archive/") and lowered.endswith("/.openspec.yaml"):
        return None, ""
    interpreter = (
        _interpreter_source(
            source.decode("utf-8", errors="replace")
            if source is not None
            else (root / relative).read_text(encoding="utf-8", errors="replace")
        )
        if executable and not Path(lowered).suffix
        else ""
    )
    matches = tuple(
        item
        for item in carriers
        if (lowered.endswith(item.extensions) or interpreter in item.shebangs)
        and (not item.paths or any(fnmatch.fnmatchcase(lowered, pattern) for pattern in item.paths))
    )
    python_roles = tuple(
        item for item in matches if item.category in PYTHON_CATEGORIES and item.paths
    )
    if len(python_roles) > 1:
        categories = ",".join(sorted(item.category for item in python_roles))
        return None, f"source_budget_python_role_ambiguous:{relative}:{categories}"
    if python_roles:
        return python_roles[0], ""
    return next(iter(matches), None), ""


def _interpreter_source(source: str) -> str:
    first = next(iter(source.splitlines()), "")
    if not first.startswith("#!"):
        return ""
    parts = first[2:].split()
    if parts and Path(parts[0]).name == "env":
        parts = parts[2:] if len(parts) > 1 and parts[1] == "-S" else parts[1:]
    return Path(parts[0]).name if parts else ""


def _effective(path: Path, carrier: Carrier, line_width: int) -> int:
    return _effective_source(
        path.read_text(
            encoding="utf-8",
            errors="strict" if carrier.measure == "python_ast" else "replace",
        ),
        path.suffix.lower(),
        carrier,
        line_width,
    )


def _effective_source(source: str, suffix: str, carrier: Carrier, line_width: int) -> int:
    if carrier.measure == "python_ast":
        return effective_code_lines_for_source(source)
    if carrier.measure == "structured":
        canonical = json.dumps(
            _structured_value(source, suffix),
            separators=(",", ":"),
            ensure_ascii=False,
            default=str,
        )
        measured = math.ceil(sum(not char.isspace() for char in canonical) / line_width)
        return (
            max(
                measured,
                _line_measurement(
                    source,
                    carrier.baseline_comment_prefixes,
                    carrier.baseline_comment_wrappers,
                ),
            )
            if carrier.baseline_measure == "lines"
            else measured
        )
    return _line_measurement(source, carrier.comment_prefixes, carrier.comment_wrappers)


def _line_measurement(
    source: str,
    prefixes: tuple[str, ...],
    wrappers: tuple[tuple[str, str], ...],
    line_width: int = 100,
) -> int:
    lines = (
        text
        for line in source.splitlines()
        if (text := line.strip())
        and not text.startswith(prefixes)
        and not any(text.startswith(start) and text.endswith(end) for start, end in wrappers)
    )
    return math.ceil(sum(not char.isspace() for text in lines for char in text) / line_width)


def _structured_value(source: str, suffix: str) -> object:
    if suffix == ".json":
        return json.loads(source)
    if suffix == ".toml":
        return tomllib.loads(source)
    if suffix in {".yaml", ".yml"}:
        documents = list(yaml.safe_load_all(source))
        return _normalize_yaml(documents[0] if len(documents) == 1 else documents)
    if suffix in {".ini", ".cfg"}:
        parser = configparser.ConfigParser(interpolation=None)
        parser.read_string(source)
        return {
            "DEFAULT": dict(parser.defaults()),
            **{section: dict(parser.items(section, raw=True)) for section in parser.sections()},
        }
    message = f"unsupported structured suffix: {suffix}"
    raise ValueError(message)


def _normalize_yaml(value: object) -> object:
    if isinstance(value, dict):
        return [
            [_normalize_yaml(key), _normalize_yaml(item)]
            for key, item in sorted(value.items(), key=lambda pair: _yaml_key(pair[0]))
        ]
    if isinstance(value, (list, tuple)):
        return [_normalize_yaml(item) for item in value]
    return value


def _yaml_key(value: object) -> tuple[str, str]:
    return type(value).__name__, json.dumps(value, separators=(",", ":"), default=str)


def _measure(
    root: Path,
    paths: tuple[tuple[str, bool], ...],
    policy: Policy,
    *,
    contents: dict[str, bytes] | None = None,
    classify_executables: bool = True,
) -> tuple[dict[str, int], dict[str, object], dict[str, dict[str, object]], tuple[str, ...]]:
    metrics: Counter[str] = Counter(
        {
            **{
                carrier.category: 0 for carrier in policy.carriers if carrier.accounting == "source"
            },
            "record_total": 0,
            "generated_evidence_total": 0,
        }
    )
    records: dict[str, dict[str, object]] = {}
    gaps: list[str] = []
    for relative, executable in paths:
        source = contents.get(relative) if contents is not None else None
        if contents is not None and source is None:
            gaps.append(f"source_budget_carrier_unreadable:{relative}")
            continue
        carrier, classification_gap = _carrier(
            relative,
            executable=executable,
            root=root,
            carriers=policy.carriers,
            source=source,
        )
        if classification_gap:
            gaps.append(classification_gap)
            continue
        if carrier is None:
            if executable and classify_executables:
                gaps.append(f"source_budget_executable_unclassified:{relative}")
            continue
        try:
            count = (
                _effective_source(
                    source.decode(
                        "utf-8", errors="strict" if carrier.measure == "python_ast" else "replace"
                    ),
                    Path(relative).suffix.lower(),
                    carrier,
                    policy.line_width,
                )
                if source is not None
                else _effective(root / relative, carrier, policy.line_width)
            )
        except (
            OSError,
            TypeError,
            UnicodeError,
            SyntaxError,
            ValueError,
            configparser.Error,
            yaml.YAMLError,
        ):
            gaps.append(f"source_budget_carrier_unreadable:{relative}")
            continue
        record = relative.startswith(policy.immutable_record_roots)
        accounting = "record" if record else carrier.accounting
        metric = (
            "record_total"
            if record
            else "generated_evidence_total"
            if carrier.accounting == "generated_evidence"
            else carrier.category
        )
        metrics[metric] += count
        records[relative] = {
            "category": carrier.category,
            "effective_lines": count,
            "record": record,
            "accounting": accounting,
        }
    for name, members in policy.aggregates.items():
        metrics[name] = sum(metrics[member] for member in members)
    encoded = json.dumps(records, sort_keys=True, separators=(",", ":")).encode()
    inventory = {
        "digest": hashlib.sha256(encoded).hexdigest(),
        "file_count": len(records),
        "category_counts": dict(
            sorted(Counter(str(item["category"]) for item in records.values()).items())
        ),
    }
    return dict(metrics), inventory, records, tuple(gaps)


def _relative(root: Path, location: object) -> str | None:
    if not isinstance(location, str) or not location:
        return None
    path = Path(location)
    try:
        return (path if path.is_absolute() else root / path).resolve().relative_to(root).as_posix()
    except (OSError, ValueError):
        return None


def _scc_counts(
    root: Path,
    policy: Policy,
    records: dict[str, dict[str, object]],
) -> tuple[dict[str, int] | None, tuple[str, ...]]:
    config, executable = policy.cross_check, shutil.which(policy.cross_check.command)
    if executable is None:
        return None, (f"source_budget_scc_unavailable:{config.command}",)
    try:
        completed = subprocess.run(
            [executable, *config.args],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
            timeout=config.timeout_seconds,
        )
        payload = _table(json.loads(completed.stdout))
        counts: dict[str, int] = {}
        for raw_language in _sequence(payload.get("languageSummary")):
            language = _table(raw_language)
            for raw_file in _sequence(language.get("Files", [])):
                item = _table(raw_file)
                relative = _relative(root.resolve(), item.get("Location"))
                if relative not in records:
                    continue
                code = item.get("Code")
                if relative in counts or not isinstance(code, int) or isinstance(code, bool):
                    return None, ("source_budget_scc_invalid",)
                counts[relative] = code
    except (
        OSError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
        subprocess.SubprocessError,
    ):
        return None, ("source_budget_scc_invalid",)
    if completed.returncode or completed.stderr:
        return None, ("source_budget_scc_invalid",)
    return counts, ()


def _cross_check(
    root: Path,
    policy: Policy,
    records: dict[str, dict[str, object]],
    canonical: dict[str, int],
) -> tuple[dict[str, object], tuple[str, ...]]:
    implementation_records = {
        relative: record for relative, record in records.items() if record["accounting"] == "source"
    }
    immutable_records = {
        relative: record for relative, record in records.items() if record["accounting"] == "record"
    }
    generated_records = {
        relative: record
        for relative, record in records.items()
        if record["accounting"] == "generated_evidence"
    }
    implementation_counts, invalid = _scc_counts(root, policy, implementation_records)
    if implementation_counts is None:
        return {}, invalid
    record_counts: dict[str, int] = {}
    if immutable_records:
        measured_records, invalid = _scc_counts(root, policy, immutable_records)
        if measured_records is None:
            return {}, invalid
        record_counts = measured_records
    generated_counts: dict[str, int] = {}
    for relative, record in generated_records.items():
        effective_lines = record["effective_lines"]
        if not isinstance(effective_lines, int) or isinstance(effective_lines, bool):
            return {}, ("source_budget_scc_invalid",)
        generated_counts[relative] = effective_lines
    python_categories = set(policy.aggregates["python_total"])
    python_total = sum(
        count
        for relative, count in implementation_counts.items()
        if implementation_records[relative]["category"] in python_categories
    )
    global_total = sum(implementation_counts.values())
    record_total = sum(record_counts.values())
    observed: dict[str, object] = {
        "command": policy.cross_check.command,
        "python_total": python_total,
        "global_total": global_total,
        "record_total": record_total,
        "generated_evidence_total": sum(generated_counts.values()),
        "file_count": len(implementation_counts) + len(record_counts) + len(generated_counts),
    }
    gaps = [
        f"source_budget_scc_file_missing:{relative}"
        for relative in sorted(
            (set(implementation_records) - set(implementation_counts))
            | (set(immutable_records) - set(record_counts))
            | (set(generated_records) - set(generated_counts))
        )
    ]
    comparisons = {
        "python_total": (python_total, canonical["python_total"]),
        "global_total": (
            global_total + record_total,
            canonical["global_total"] + canonical["record_total"],
        ),
    }
    for name, (observed_count, canonical_count) in comparisons.items():
        if not isinstance(observed_count, int):
            return {}, ("source_budget_scc_invalid",)
        tolerance = getattr(policy.cross_check.tolerance, name)
        if observed_count < canonical_count - tolerance:
            gaps.append(f"source_budget_scc_{name}_disagrees:{observed_count}!={canonical_count}")
    return observed, tuple(gaps)


def source_budget_report(root: Path) -> dict[str, object]:
    """Measure implementation and immutable records, then enforce implementation limits."""
    policy, gaps = policy_for_root(root)
    if policy is None:
        return _blocked(*gaps)
    paths, gaps = _paths(root)
    if paths is None:
        return _blocked(*gaps)
    metrics, inventory, records, measure_gaps = _measure(root, paths, policy)
    cross_check, cross_gaps = _cross_check(root, policy, records, metrics)
    enforced = {name: metrics[name] for name in TERMINAL_TOTALS}
    terminal = policy.terminal.model_dump()
    terminal_gaps = tuple(
        f"source_budget_terminal_exceeded:{name}:{enforced[name]}>{terminal[name]}"
        for name in TERMINAL_TOTALS
        if enforced[name] > terminal[name]
    )
    required = list(dict.fromkeys((*measure_gaps, *cross_gaps, *terminal_gaps)))
    return {
        "verdict": "pass" if not required else "block",
        "state": "clean" if not required else "blocked",
        "terminal": terminal,
        "metrics": metrics,
        "enforced_metrics": enforced,
        "inventory": inventory,
        "cross_check": cross_check,
        "required_gaps": required,
        "advisory_gaps": [],
    }
