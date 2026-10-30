"""Restricted CEL evaluation for immutable declaration facts."""

from __future__ import annotations

from functools import lru_cache

from cel_expr_python import cel


class CelEvaluationError(RuntimeError):
    """Stable kernel boundary for CEL runtime failures."""


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


def validate_cel_expression(expression: str, *, predicate: bool = False) -> str:
    """Compile once and require a statically Boolean type for declared predicates."""
    try:
        program = _cel_program(expression)
    except RuntimeError as exc:
        message = "invalid CEL expression"
        raise ValueError(message) from exc
    if predicate and program.return_type() != cel.Type.BOOL:
        message = "CEL predicate must statically return a boolean"
        raise ValueError(message)
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
