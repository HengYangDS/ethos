"""Parity command group — capability-parity ledger, gaps, shadow proof."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003 - cyclopts needs runtime types in signatures

from ethos.adapters.repo import git as _gitio
from ethos.domain import land as _land
from ethos.repository.evidence.parity import build_tracked_parity_evidence
from ethos.repository.evidence.parity import parity_gaps_report
from ethos.repository.evidence.parity import parity_ledger_report
from ethos.repository.evidence.parity import shadow_parity_report
from ethos.repository.evidence.parity import write_tracked_parity_evidence
from ethos.surface.cli._base import JsonFlag
from ethos.surface.cli._base import RootOption
from ethos.surface.cli._base import emit as _emit
from ethos.surface.cli._base import parity_app
from ethos.surface.cli._base import resolve_root as _root
from ethos_core.result import EthosResult


@parity_app.command(name="ledger")
def parity_ledger(*, json_output: JsonFlag = False) -> None:
    """Emit the executable capability parity ledger."""
    report = parity_ledger_report()
    result = EthosResult(
        command="parity ledger",
        ok=bool(report["ok"]),
        state="classified",
        summary=report["summary"],
        next_actions=("ethos parity gaps --adopter <adopter>",),
        data={"records": report["records"]},
    )
    _emit(result, json_output, enforce=False)


@parity_app.command(name="gaps")
def parity_gaps(
    *,
    adopter: str | None = None,
    target: Path | None = None,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Report remaining product/adopter parity gaps."""
    repo = _root(root)
    report = parity_gaps_report(
        adopter=adopter,
        root=repo,
        target=target,
        current_target_head=_gitio.current_tracked_head(target) if target is not None else "",
        current_product_head=_gitio.current_tracked_head(repo),
        acceptable_product_heads=_land.acceptable_parity_product_heads(repo, adopter),
        acceptable_target_heads=_land.acceptable_parity_target_heads(repo, target, adopter),
    )
    evidence = report.get("evidence") if isinstance(report.get("evidence"), dict) else {}
    refresh = evidence.get("refresh_package") if isinstance(evidence, dict) else None
    refresh_command = (
        str(refresh["command"]) if isinstance(refresh, dict) and refresh.get("command") else ""
    )
    result = EthosResult(
        command="parity gaps",
        ok=bool(report["ok"]),
        state="clean" if report["ok"] else "gapped",
        summary={"adopter": report["adopter"], "gap_count": len(report["required_gaps"])},
        required_gaps=tuple(report["required_gaps"]),
        next_actions=(
            (
                refresh_command
                or (
                    "ethos parity shadow --adopter <adopter-id> --target <repo> "
                    "--execute --write-evidence"
                ),
            )
            if report["required_gaps"]
            else ("ethos prove --full",)
        ),
        data=report,
    )
    _emit(result, json_output, enforce=False)


@parity_app.command(name="shadow")
def parity_shadow(
    *,
    target: Path,
    adopter: str | None = None,
    execute: bool = False,
    write_evidence: bool = False,
    timeout_seconds: int = 30,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Plan an external shadow parity comparison for an adopter."""
    repo = _root(root)
    adopter_name = adopter or "generic"
    if execute:
        from ethos.adapters.shadow import run_shadow_parity

        report = run_shadow_parity(target=target, timeout_seconds=timeout_seconds)
    else:
        report = shadow_parity_report(
            target=target,
            root=repo,
            adopter=adopter,
            current_target_head=_gitio.current_tracked_head(target),
            current_product_head=_gitio.current_tracked_head(repo),
            acceptable_product_heads=_land.acceptable_parity_product_heads(repo, adopter),
            acceptable_target_heads=_land.acceptable_parity_target_heads(repo, target, adopter),
        )
    required_gaps = list(report["required_gaps"])
    evidence_path = ""
    if write_evidence:
        if not execute:
            required_gaps.append("parity_evidence_write_requires_execute")
        elif report.get("ok") is not True:
            required_gaps.append(f"parity_evidence_write_blocked:{adopter_name}")
        else:
            evidence = build_tracked_parity_evidence(
                adopter=adopter_name,
                target=target,
                shadow=report,
                current_product_head=_gitio.current_tracked_head(repo),
                current_target_head=_gitio.current_tracked_head(target),
                timeout_seconds=timeout_seconds,
            )
            written = write_tracked_parity_evidence(
                root=repo,
                adopter=adopter_name,
                evidence=evidence,
            )
            evidence_path = written.relative_to(repo).as_posix()
            report = {**report, "evidence_written": evidence_path}
    result = EthosResult(
        command="parity shadow",
        ok=bool(report["ok"]) and not required_gaps,
        state=str(report["state"]),
        required_gaps=tuple(required_gaps),
        next_actions=("ethos prove --full",) if not required_gaps else ("ethos parity gaps",),
        data=report,
    )
    _emit(result, json_output, enforce=False)
