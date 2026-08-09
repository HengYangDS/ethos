"""Source-budget policy contracts and baseline comparison."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Annotated
from typing import Literal
from typing import cast

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import ValidationError
from pydantic import model_validator

POLICY_PATH = Path(".config/checks/format/selection.toml")
PYTHON_CATEGORIES = ("python_product", "python_tests", "python_tools", "python_other")
TERMINAL_TOTALS = (*PYTHON_CATEGORIES, "global_total")
AGGREGATE_TOTALS = ("python_total", "global_total")
IMMUTABLE_RECORD_ROOTS = ("evidence/", "openspec/changes/archive/")


class _Contract(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")


class CrossCheckTotals(_Contract):
    python_total: Annotated[int, Field(ge=0)]
    global_total: Annotated[int, Field(ge=0)]


class TerminalTotals(_Contract):
    python_product: Annotated[int, Field(ge=0)]
    python_tests: Annotated[int, Field(ge=0)]
    python_tools: Annotated[int, Field(ge=0)]
    python_other: Annotated[int, Field(ge=0)]
    global_total: Annotated[int, Field(ge=0)]


class CrossCheck(_Contract):
    command: Annotated[str, Field(min_length=1)]
    args: tuple[str, ...]
    timeout_seconds: Annotated[int, Field(gt=0, le=300)]
    tolerance: CrossCheckTotals


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
    accounting: Literal["source", "generated_evidence"] = "source"

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


class Policy(_Contract):
    terminal: TerminalTotals
    cross_check: CrossCheck
    aggregates: dict[str, tuple[str, ...]]
    immutable_record_roots: tuple[str, ...] = ()
    line_width: Annotated[int, Field(gt=0, le=200)]
    carriers: tuple[Carrier, ...]

    @model_validator(mode="after")
    def validate_ownership(self) -> Policy:
        categories = {
            carrier.category for carrier in self.carriers if carrier.accounting == "source"
        }
        python_categories = {
            carrier.category
            for carrier in self.carriers
            if carrier.measure == "python_ast" and carrier.accounting == "source"
        }
        if set(self.aggregates) != set(AGGREGATE_TOTALS):
            msg = "source-budget aggregates must contain exactly the aggregate totals"
            raise ValueError(msg)
        if set(self.aggregates["global_total"]) != categories:
            msg = "global_total must own every carrier category exactly once"
            raise ValueError(msg)
        if tuple(self.aggregates["python_total"]) != PYTHON_CATEGORIES:
            msg = "python_total must own every Python carrier category exactly once"
            raise ValueError(msg)
        if set(PYTHON_CATEGORIES) != python_categories:
            msg = "source-budget must declare every Python carrier role exactly once"
            raise ValueError(msg)
        if any(
            not values or len(values) != len(set(values)) for values in self.aggregates.values()
        ):
            msg = "aggregate members must be non-empty and unique"
            raise ValueError(msg)
        if self.immutable_record_roots != IMMUTABLE_RECORD_ROOTS:
            msg = "source-budget must declare the exact immutable record roots"
            raise ValueError(msg)
        return self


def policy_for_root(root: Path) -> tuple[Policy | None, tuple[str, ...]]:
    try:
        payload = tomllib.loads((root / POLICY_PATH).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        return None, (f"source_budget_policy_invalid:{type(exc).__name__}",)
    current = _policy_contract(payload)
    if current is None:
        return None, ("source_budget_policy_invalid:shape",)
    return current, ()


def _table(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError
    return {str(key): item for key, item in value.items()}


def _sequence(value: object) -> list[object]:
    if not isinstance(value, list):
        raise TypeError
    return list(value)


def _strings(value: object, *, empty: bool = False) -> tuple[str, ...]:
    values = _sequence(value)
    if (not empty and not values) or any(not isinstance(item, str) or not item for item in values):
        raise TypeError
    return tuple(str(item) for item in values)


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
        try:
            first, second = _strings(raw)
        except ValueError:
            raise TypeError from None
        pairs.append((first, second))
    return tuple(pairs)


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
                        'Literal["lines", "python_ast", "structured"]',
                        budget.get("measure", "lines"),
                    ),
                    baseline_measure=cast(
                        'Literal["", "lines"]', budget.get("baseline_measure", "")
                    ),
                    baseline_comment_prefixes=_strings(
                        budget.get("baseline_comment_prefixes", []), empty=True
                    ),
                    baseline_comment_wrappers=_pairs(budget.get("baseline_comment_wrappers", [])),
                    accounting=cast(
                        'Literal["source", "generated_evidence"]',
                        budget.get("accounting", "source"),
                    ),
                )
            )
    return tuple(carriers)


def _policy_contract(payload: dict[str, object]) -> Policy | None:
    try:
        source = _table(payload.get("source_budget"))
        terminal = TerminalTotals.model_validate(_table(source.get("terminal")))
        cross = _table(source.get("cross_check"))
        tolerance = CrossCheckTotals.model_validate(_table(cross.get("tolerance")))
        aggregates = {
            name: _strings(value) for name, value in _table(source.get("aggregates")).items()
        }
        return Policy(
            terminal=terminal,
            cross_check=CrossCheck(
                command=_string(cross.get("command")),
                args=_strings(cross.get("args")),
                timeout_seconds=_integer(cross.get("timeout_seconds")),
                tolerance=tolerance,
            ),
            aggregates=aggregates,
            immutable_record_roots=_strings(source.get("immutable_record_roots", []), empty=True),
            line_width=_integer(source.get("line_width")),
            carriers=_raw_carriers(payload),
        )
    except (TypeError, ValidationError, ValueError):
        return None
