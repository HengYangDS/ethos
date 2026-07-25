"""Restricted CEL evaluation for immutable declaration facts."""

from __future__ import annotations

from functools import lru_cache
from typing import Protocol

from cel_expr_python import cel


class CelEvaluationError(RuntimeError):
    """Stable kernel boundary for CEL runtime failures."""


class CelRule(Protocol):
    expression: str
    gap: str


class CelGapGroup(Protocol):
    values: str
    prefix: str


_CEL_VARIABLES = {"facts": cel.Type.DYN, "policy": cel.Type.DYN, "rule": cel.Type.DYN}
_CEL_ENVIRONMENT = cel.NewEnv(variables=_CEL_VARIABLES)


def evaluate_cel_predicate(
    expression: str,
    *,
    facts: dict[str, object],
    policy: dict[str, object],
    rule: dict[str, object],
) -> bool:
    """Evaluate one declaration-owned CEL boolean over typed fact maps."""
    result = _evaluate(expression, facts=facts, policy=policy, rule=rule)
    if result.type() != cel.Type.BOOL:
        msg = "CEL predicate must return a boolean"
        raise TypeError(msg)
    return bool(result.plain_value())


def evaluate_cel_value(
    expression: str,
    *,
    facts: dict[str, object],
    policy: dict[str, object],
    rule: dict[str, object],
) -> object:
    """Evaluate one declaration-owned CEL projection to native values."""
    return _evaluate(expression, facts=facts, policy=policy, rule=rule).plain_value()


def evaluate_cel_rules(
    rules: tuple[CelRule, ...],
    *,
    facts: dict[str, object],
    policy: dict[str, object],
) -> list[str]:
    """Evaluate declaration-owned predicate and gap expressions."""
    return [
        str(evaluate_cel_value(rule.gap, facts=facts, policy=policy, rule={}))
        for rule in rules
        if not evaluate_cel_predicate(rule.expression, facts=facts, policy=policy, rule={})
    ]


def evaluate_cel_gap_groups(
    groups: tuple[CelGapGroup, ...],
    *,
    facts: dict[str, object],
    policy: dict[str, object],
) -> list[str]:
    """Prefix declaration-selected value groups without Python path policy."""
    gaps: list[str] = []
    for group in groups:
        prefix = str(evaluate_cel_value(group.prefix, facts=facts, policy=policy, rule={}))
        values = evaluate_cel_value(group.values, facts=facts, policy=policy, rule={})
        if not isinstance(values, list):
            message = "CEL gap group must return a list"
            raise TypeError(message)
        gaps.extend(f"{prefix}{value}" for value in values)
    return gaps


def validate_cel_expression(expression: str) -> str:
    """Compile one declaration-owned CEL expression and return it unchanged."""
    try:
        _cel_program(expression)
    except RuntimeError as exc:
        message = "invalid CEL expression"
        raise ValueError(message) from exc
    return expression


def _evaluate(
    expression: str,
    *,
    facts: dict[str, object],
    policy: dict[str, object],
    rule: dict[str, object],
) -> cel.Value:
    try:
        result = _cel_program(expression).eval(
            data={"facts": facts, "policy": policy, "rule": rule}
        )
    except RuntimeError as exc:
        raise CelEvaluationError(str(exc)) from exc
    if result.type() == cel.Type.ERROR:
        raise CelEvaluationError(str(result.value()))
    return result


@lru_cache
def _cel_program(expression: str) -> cel.Expression:
    """Compile and cache one declaration-owned CEL expression."""
    return _CEL_ENVIRONMENT.compile(expression)
