"""Source-budget policy contracts and baseline comparison."""

from __future__ import annotations

import subprocess
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

import ethos.adapters.repo.git as git_adapter
from ethos.contracts.branch.roles import load_branch_role_policy

POLICY_PATH = Path(".config/checks/format/selection.toml")
TERMINAL_TOTALS = ("python_total", "global_total")
IMMUTABLE_RECORD_ROOTS = ("evidence/", "openspec/changes/archive/")


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


class Policy(_Contract):
    contract_version: Literal[1, 2]
    terminal: Totals
    cross_check: CrossCheck
    aggregates: dict[str, tuple[str, ...]]
    exclude: tuple[str, ...] = ()
    immutable_record_roots: tuple[str, ...] = ()
    line_width: Annotated[int, Field(gt=0, le=200)]
    carriers: tuple[Carrier, ...]

    @model_validator(mode="after")
    def validate_ownership(self) -> Policy:
        categories = {carrier.category for carrier in self.carriers}
        python_categories = {
            carrier.category for carrier in self.carriers if carrier.measure == "python_ast"
        }
        if set(self.aggregates) != set(TERMINAL_TOTALS):
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
        if self.contract_version == 1 and self.immutable_record_roots:
            msg = "source-budget v1 cannot declare immutable record roots"
            raise ValueError(msg)
        if self.contract_version == 2 and self.immutable_record_roots != IMMUTABLE_RECORD_ROOTS:
            msg = "source-budget v2 must declare the exact immutable record roots"
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
    accepted, gaps = _accepted_policy(root, current)
    if gaps:
        return None, gaps
    if accepted is not None and _relaxed(current, accepted):
        return None, ("source_budget_policy_relaxed",)
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
        values = _strings(raw)
        if len(values) != 2:
            raise TypeError
        pairs.append((values[0], values[1]))
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
            contract_version=cast("Literal[1, 2]", _integer(source.get("contract_version"))),
            terminal=terminal,
            cross_check=CrossCheck(
                command=_string(cross.get("command")),
                args=_strings(cross.get("args")),
                timeout_seconds=_integer(cross.get("timeout_seconds")),
                tolerance=tolerance,
            ),
            aggregates=aggregates,
            exclude=_strings(source.get("exclude", []), empty=True),
            immutable_record_roots=_strings(source.get("immutable_record_roots", []), empty=True),
            line_width=_integer(source.get("line_width")),
            carriers=_raw_carriers(payload),
        )
    except (TypeError, ValidationError, ValueError):
        return None


def _accepted_policy(root: Path, current: Policy) -> tuple[Policy | None, tuple[str, ...]]:
    head, gaps = _accepted_head(root)
    if gaps:
        return None, gaps
    try:
        payload = tomllib.loads(
            git_adapter.git_stdout_checked(root, "show", f"{head}:{POLICY_PATH}")
        )
    except tomllib.TOMLDecodeError:
        return None, ("source_budget_accepted_policy_invalid",)
    except (OSError, subprocess.CalledProcessError):
        return None, (f"source_budget_accepted_file_unavailable:{POLICY_PATH}",)
    source = payload.get("source_budget")
    if isinstance(source, dict) and "contract_version" not in source:
        return current, ()
    policy = _policy_contract(payload)
    if not isinstance(source, dict) or policy is None:
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


def _relaxed(current: Policy, accepted: Policy) -> bool:
    if (accepted.contract_version, current.contract_version) not in {(1, 1), (1, 2), (2, 2)}:
        return True
    fixed = current.model_copy(
        update={
            "contract_version": accepted.contract_version,
            "terminal": accepted.terminal,
            "immutable_record_roots": accepted.immutable_record_roots,
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
            for name in TERMINAL_TOTALS
        )
        or current.line_width > accepted.line_width
    )
