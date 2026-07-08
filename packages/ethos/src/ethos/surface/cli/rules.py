"""Rules command group — check, eval, coverage, compile, explain, exceptions.

A surface command module: binds args, calls the rules-kernel reports, emits.
Registers onto the shared rules_app from _base; cli.py imports this module so the
decorators run. Imports only what this group needs.
"""

from __future__ import annotations

from typing import cast

from ethos.adapters.repo import git as _gitio
from ethos.adapters.repo.status import workspace_status
from ethos.domain import plan as _plan
from ethos.repository.policy.rules.check import rules_check_report
from ethos.repository.policy.rules.compile import compile_rules
from ethos.repository.policy.rules.coverage import coverage_report
from ethos.repository.policy.rules.evaluation import rules_evaluation_report
from ethos.repository.policy.rules.exceptions import policy_exceptions_report
from ethos.repository.policy.rules.explain import explain_rules_target
from ethos.surface.cli._base import JsonFlag
from ethos.surface.cli._base import RootOption
from ethos.surface.cli._base import emit
from ethos.surface.cli._base import resolve_root
from ethos.surface.cli._base import rules_app
from ethos_core.result import EthosResult


@rules_app.command(name="check")
def rules_check(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Check Rules Product Kernel readiness."""
    repo = resolve_root(root)
    report = rules_check_report(repo)
    result = EthosResult(
        command="rules check",
        ok=bool(report["ok"]),
        state="clean" if report["ok"] else "blocked",
        summary={
            "coverage_tier": report["coverage_tier"],
            "rule_count": len(cast("list[object]", report["resolved_rules"])),
        },
        required_gaps=tuple(cast("list[str]", report["required_gaps"])),
        next_actions=tuple(cast("list[str]", report["next_action_contract"])),
        data=report,
    )
    emit(result, json_output=json_output, enforce=False)


@rules_app.command(name="eval")
def rules_eval(
    *,
    root: RootOption | None = None,
    phase: str = "plan",
    changed_path: tuple[str, ...] = (),
    mutation: bool = False,
    authorized: bool = False,
    actor: str = "local",
    scope: str = "repository",
    json_output: JsonFlag = False,
) -> None:
    """Evaluate repository rules for a phase."""
    repo = resolve_root(root)
    current_head = _gitio.current_head(repo)
    report = rules_evaluation_report(
        repo,
        phase=phase,
        changed_paths=tuple(changed_path),
        mutation=mutation,
        authorized=authorized,
        actor=actor,
        scope=scope,
        head=current_head,
        fact_snapshot=_plan.rule_fact_snapshot(
            repo,
            phase=phase,
            changed_paths=tuple(changed_path),
            mutation=mutation,
            authorized=authorized,
            actor=actor,
            scope=scope,
            head=current_head,
        ),
    )
    attestation = _plan.rule_attestation_for_evaluation(report, actor=actor, scope=scope)
    result = EthosResult(
        command="rules eval",
        ok=not report["required_gaps"],
        state="blocked" if report["state"] == "block" else str(report["state"]),
        summary={
            "phase": phase,
            "digest": report["digest"],
            "attestation": attestation,
        },
        required_gaps=tuple(cast("list[str]", report["required_gaps"])),
        next_actions=tuple(cast("list[str]", report["next_action_contract"])),
        data=report,
    )
    emit(result, json_output=json_output)


@rules_app.command(name="coverage")
def rules_coverage(
    *,
    root: RootOption | None = None,
    changed: bool = False,
    changed_path: tuple[str, ...] = (),
    json_output: JsonFlag = False,
) -> None:
    """Report changed-path rule coverage."""
    repo = resolve_root(root)
    paths = (
        tuple(cast("list[str]", workspace_status(repo)["changed_paths"]))
        if changed
        else tuple(changed_path)
    )
    report = coverage_report(repo, changed_paths=paths)
    result = EthosResult(
        command="rules coverage",
        ok=bool(report["ok"]),
        state="covered" if report["ok"] else "gapped",
        summary={
            "covered_path_count": len(cast("list[object]", report["covered_paths"])),
            "uncovered_path_count": len(cast("list[object]", report["uncovered_paths"])),
        },
        required_gaps=tuple(cast("list[str]", report["required_gaps"])),
        next_actions=tuple(cast("list[str]", report["next_action_contract"])),
        data=report,
    )
    emit(result, json_output=json_output, enforce=False)


@rules_app.command(name="compile")
def rules_compile(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Compile repository rules deterministically."""
    repo = resolve_root(root)
    report = compile_rules(repo)
    result = EthosResult(
        command="rules compile",
        ok=True,
        state="compiled",
        summary={"rule_count": len(cast("list[object]", report["rules"]))},
        data=report,
    )
    emit(result, json_output=json_output, enforce=False)


@rules_app.command(name="explain")
def rules_explain(
    target: str,
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Explain a rule, gap, or path."""
    repo = resolve_root(root)
    report = explain_rules_target(repo, target)
    result = EthosResult(
        command="rules explain",
        ok=True,
        state="explained",
        summary={"target": target},
        next_actions=tuple(cast("list[str]", report["next_action_contract"])),
        data=report,
    )
    emit(result, json_output=json_output, enforce=False)


@rules_app.command(name="exceptions")
def rules_exceptions(
    *,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """List policy exceptions."""
    report = policy_exceptions_report(resolve_root(root))
    result = EthosResult(
        command="rules exceptions",
        ok=bool(report["ok"]),
        state="clean" if report["ok"] else "blocked",
        required_gaps=tuple(cast("list[str]", report["required_gaps"])),
        data=report,
    )
    emit(result, json_output=json_output, enforce=False)
