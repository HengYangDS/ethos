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
from typing import Annotated
from typing import Literal
from typing import cast

import yaml
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import ValidationError
from pydantic import model_validator

import ethos.adapters.repo.git as git_adapter
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.measure import effective_code_lines_for_source

_POLICY = Path(".config/checks/format/selection.toml")
_TOTALS = ("python_total", "global_total")


class _Contract(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")


class Totals(_Contract):
    python_total: Annotated[int, Field(ge=0)]
    global_total: Annotated[int, Field(ge=0)]


class CrossCheck(_Contract):
    command: Annotated[str, Field(min_length=1)]
    args: tuple[str, ...]
    timeout_seconds: Annotated[int, Field(gt=0, le=300)]
    tolerance: Totals


class Carrier(_Contract):
    category: Annotated[str, Field(min_length=1)]
    extensions: tuple[str, ...]
    paths: tuple[str, ...] = ()
    shebangs: tuple[str, ...] = ()
    comment_prefixes: tuple[str, ...] = ()
    comment_wrappers: tuple[tuple[str, str], ...] = ()
    measure: Literal["lines", "python_ast", "structured"] = "lines"
    baseline_measure: Literal["", "lines"] = ""
    baseline_comment_prefixes: tuple[str, ...] = ()
    baseline_comment_wrappers: tuple[tuple[str, str], ...] = ()

    @model_validator(mode="after")
    def validate_shape(self) -> Carrier:
        if not self.extensions or any(not value.startswith(".") for value in self.extensions):
            msg = "carrier extensions must be non-empty dotted suffixes"
            raise ValueError(msg)
        for values in (
            self.extensions,
            self.paths,
            self.shebangs,
            self.comment_prefixes,
            self.baseline_comment_prefixes,
        ):
            if any(not value for value in values) or len(values) != len(set(values)):
                msg = "carrier string lists must contain unique non-empty values"
                raise ValueError(msg)
        return self

    @property
    def scope(self) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
        return self.category, self.extensions, self.paths


class Policy(_Contract):
    contract_version: Literal[1]
    terminal: Totals
    cross_check: CrossCheck
    aggregates: dict[str, tuple[str, ...]]
    exclude: tuple[str, ...] = ()
    line_width: Annotated[int, Field(gt=0, le=200)]
    carriers: tuple[Carrier, ...]

    @model_validator(mode="after")
    def validate_ownership(self) -> Policy:
        categories = {carrier.category for carrier in self.carriers}
        python_categories = {
            carrier.category for carrier in self.carriers if carrier.measure == "python_ast"
        }
        if set(self.aggregates) != set(_TOTALS):
            msg = "source-budget aggregates must contain exactly the terminal totals"
            raise ValueError(msg)
        if set(self.aggregates["global_total"]) != categories:
            msg = "global_total must own every carrier category exactly once"
            raise ValueError(msg)
        if set(self.aggregates["python_total"]) != python_categories:
            msg = "python_total must own every Python carrier category exactly once"
            raise ValueError(msg)
        if any(
            not values or len(values) != len(set(values)) for values in self.aggregates.values()
        ):
            msg = "aggregate members must be non-empty and unique"
            raise ValueError(msg)
        return self


def _table(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError
    return {str(key): item for key, item in value.items()}


def _sequence(value: object) -> list[object]:
    if not isinstance(value, list):
        raise TypeError
    return cast("list[object]", value)


def _strings(value: object, *, empty: bool = False) -> tuple[str, ...]:
    values = _sequence(value)
    if (not empty and not values) or any(not isinstance(item, str) or not item for item in values):
        raise TypeError
    return tuple(cast("str", item) for item in values)


def _string(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise TypeError
    return value


def _integer(value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError
    return value


def _pairs(value: object) -> tuple[tuple[str, str], ...]:
    pairs: list[tuple[str, str]] = []
    for raw in _sequence(value):
        values = _strings(raw)
        if len(values) != 2:
            raise TypeError
        pairs.append((values[0], values[1]))
    return tuple(pairs)


def _blocked(*gaps: str) -> dict[str, object]:
    return {
        "ok": False,
        "state": "blocked",
        "terminal": {},
        "metrics": {},
        "enforced_metrics": {},
        "inventory": {"file_count": 0},
        "cross_check": {},
        "required_gaps": list(gaps),
        "advisory_gaps": [],
    }


def _raw_carriers(payload: dict[str, object]) -> tuple[Carrier, ...]:
    carriers: list[Carrier] = []
    for raw_format in _sequence(payload.get("format")):
        format_record = _table(raw_format)
        extensions = _strings(format_record.get("extensions"))
        shebangs = _strings(format_record.get("shebangs", []), empty=True)
        for raw_budget in _sequence(format_record.get("budget", [])):
            budget = _table(raw_budget)
            carriers.append(
                Carrier(
                    category=_string(budget.get("category")),
                    extensions=extensions,
                    paths=_strings(budget.get("paths", []), empty=True),
                    shebangs=shebangs,
                    comment_prefixes=_strings(budget.get("comment_prefixes", []), empty=True),
                    comment_wrappers=_pairs(budget.get("comment_wrappers", [])),
                    measure=cast(
                        "Literal['lines', 'python_ast', 'structured']",
                        budget.get("measure", "lines"),
                    ),
                    baseline_measure=cast(
                        "Literal['', 'lines']", budget.get("baseline_measure", "")
                    ),
                    baseline_comment_prefixes=_strings(
                        budget.get("baseline_comment_prefixes", []), empty=True
                    ),
                    baseline_comment_wrappers=_pairs(budget.get("baseline_comment_wrappers", [])),
                )
            )
    return tuple(carriers)


def _policy_contract(payload: dict[str, object]) -> Policy | None:
    try:
        source = _table(payload.get("source_budget"))
        terminal = Totals.model_validate(_table(source.get("terminal")))
        cross = _table(source.get("cross_check"))
        tolerance = Totals.model_validate(_table(cross.get("tolerance")))
        aggregates = {
            name: _strings(value) for name, value in _table(source.get("aggregates")).items()
        }
        return Policy(
            contract_version=cast("Literal[1]", _integer(source.get("contract_version"))),
            terminal=terminal,
            cross_check=CrossCheck(
                command=_string(cross.get("command")),
                args=_strings(cross.get("args")),
                timeout_seconds=_integer(cross.get("timeout_seconds")),
                tolerance=tolerance,
            ),
            aggregates=aggregates,
            exclude=_strings(source.get("exclude", []), empty=True),
            line_width=_integer(source.get("line_width")),
            carriers=_raw_carriers(payload),
        )
    except (TypeError, ValidationError, ValueError):
        return None


def _policy(root: Path) -> tuple[Policy | None, tuple[str, ...]]:
    try:
        payload = tomllib.loads((root / _POLICY).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        return None, (f"source_budget_policy_invalid:{type(exc).__name__}",)
    current = _policy_contract(payload)
    if current is None:
        return None, ("source_budget_policy_invalid:shape",)
    accepted, gaps = _accepted_policy(root, current)
    if gaps:
        return None, gaps
    if accepted is not None and _relaxed(current, accepted):
        return None, ("source_budget_policy_relaxed",)
    return current, ()


def _accepted_policy(root: Path, current: Policy) -> tuple[Policy | None, tuple[str, ...]]:
    head, gaps = _accepted_head(root)
    if gaps:
        return None, gaps
    text, gaps = _committed_text(root, head, _POLICY.as_posix())
    if gaps or text is None:
        return None, gaps
    try:
        payload = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return None, ("source_budget_accepted_policy_invalid",)
    source = payload.get("source_budget")
    if isinstance(source, dict) and "contract_version" not in source:
        return current, ()
    policy = _policy_contract(payload)
    if not isinstance(source, dict) or source.get("contract_version") != 1 or policy is None:
        return None, ("source_budget_accepted_policy_invalid",)
    return policy, ()


def _accepted_head(root: Path) -> tuple[str, tuple[str, ...]]:
    branch = load_branch_role_policy(root).accepted_branch
    try:
        head = git_adapter.git_stdout_checked(
            root, "rev-parse", "--verify", f"refs/heads/{branch}^{{commit}}"
        )
    except (OSError, subprocess.CalledProcessError):
        head = ""
    return (head, ()) if head else ("", ("source_budget_accepted_ref_unavailable",))


def _committed_text(root: Path, head: str, path: str) -> tuple[str | None, tuple[str, ...]]:
    try:
        return git_adapter.git_stdout_checked(root, "show", f"{head}:{path}"), ()
    except (OSError, subprocess.CalledProcessError):
        return None, (f"source_budget_accepted_file_unavailable:{path}",)


def _relaxed(current: Policy, accepted: Policy) -> bool:
    fixed = current.model_copy(
        update={
            "terminal": accepted.terminal,
            "line_width": accepted.line_width,
            "cross_check": current.cross_check.model_copy(
                update={"tolerance": accepted.cross_check.tolerance}
            ),
        }
    )
    return (
        fixed != accepted
        or any(
            getattr(current.terminal, name) > getattr(accepted.terminal, name)
            or getattr(current.cross_check.tolerance, name)
            > getattr(accepted.cross_check.tolerance, name)
            for name in _TOTALS
        )
        or current.line_width > accepted.line_width
    )


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
) -> Carrier | None:
    lowered = relative.lower()
    if lowered.startswith("openspec/changes/archive/") and lowered.endswith("/.openspec.yaml"):
        return None
    interpreter = (
        _interpreter_source(
            source.decode("utf-8", errors="replace")
            if source is not None
            else (root / relative).read_text(encoding="utf-8", errors="replace")
        )
        if executable and not Path(lowered).suffix
        else ""
    )
    return next(
        (
            item
            for item in carriers
            if (lowered.endswith(item.extensions) or interpreter in item.shebangs)
            and (
                not item.paths
                or any(fnmatch.fnmatchcase(lowered, pattern) for pattern in item.paths)
            )
        ),
        None,
    )


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
    metrics: Counter[str] = Counter({carrier.category: 0 for carrier in policy.carriers})
    records: dict[str, dict[str, object]] = {}
    gaps: list[str] = []
    for relative, executable in paths:
        if any(fnmatch.fnmatchcase(relative, pattern) for pattern in policy.exclude):
            continue
        source = contents.get(relative) if contents is not None else None
        if contents is not None and source is None:
            gaps.append(f"source_budget_carrier_unreadable:{relative}")
            continue
        carrier = _carrier(
            relative,
            executable=executable,
            root=root,
            carriers=policy.carriers,
            source=source,
        )
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
        metrics[carrier.category] += count
        records[relative] = {"category": carrier.category, "effective_lines": count}
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
    counts, invalid = _scc_counts(root, policy, records)
    if counts is None:
        return {}, invalid
    observed: dict[str, object] = {
        "command": policy.cross_check.command,
        "python_total": sum(
            count
            for relative, count in counts.items()
            if str(records[relative]["category"]).startswith("python_")
        ),
        "global_total": sum(counts.values()),
        "file_count": len(counts),
    }
    gaps = [
        f"source_budget_scc_file_missing:{relative}"
        for relative in sorted(set(records) - set(counts))
    ]
    for name in _TOTALS:
        observed_count = observed[name]
        if not isinstance(observed_count, int):
            return {}, ("source_budget_scc_invalid",)
        if abs(observed_count - canonical[name]) > getattr(policy.cross_check.tolerance, name):
            gaps.append(f"source_budget_scc_{name}_disagrees:{observed_count}!={canonical[name]}")
    return observed, tuple(gaps)


def source_budget_report(root: Path) -> dict[str, object]:
    """Measure every owned executable carrier and enforce terminal limits."""
    policy, gaps = _policy(root)
    if policy is None:
        return _blocked(*gaps)
    paths, gaps = _paths(root)
    if paths is None:
        return _blocked(*gaps)
    metrics, inventory, records, measure_gaps = _measure(root, paths, policy)
    cross_check, cross_gaps = _cross_check(root, policy, records, metrics)
    enforced = {
        name: max(
            metrics[name],
            value if isinstance(value := cross_check.get(name), int) else metrics[name],
        )
        for name in _TOTALS
    }
    terminal = policy.terminal.model_dump()
    terminal_gaps = tuple(
        f"source_budget_terminal_exceeded:{name}:{enforced[name]}>{terminal[name]}"
        for name in _TOTALS
        if enforced[name] > terminal[name]
    )
    required = list(dict.fromkeys((*measure_gaps, *cross_gaps, *terminal_gaps)))
    return {
        "ok": not required,
        "state": "clean" if not required else "blocked",
        "terminal": terminal,
        "metrics": metrics,
        "enforced_metrics": enforced,
        "inventory": inventory,
        "cross_check": cross_check,
        "required_gaps": required,
        "advisory_gaps": [],
    }
