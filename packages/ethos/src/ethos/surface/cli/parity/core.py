"""Parity command group — capability-parity ledger, gaps, shadow proof."""

from __future__ import annotations

from pathlib import Path  # noqa: TC003 - cyclopts needs runtime types in signatures
from typing import cast

import ethos.adapters.repo.git as git_adapter
import ethos.domain.land.parity.core as land_parity
from ethos.adapters.admission.prewrite import prewrite_guard
from ethos.repository.evidence.parity.core import build_tracked_parity_evidence
from ethos.repository.evidence.parity.core import parity_gaps_report
from ethos.repository.evidence.parity.core import parity_ledger_report
from ethos.repository.evidence.parity.core import shadow_parity_report
from ethos.repository.evidence.parity.core import write_tracked_parity_evidence
from ethos.repository.evidence.shadow.routing import parity_evidence_path
from ethos.repository.evidence.shadow.routing import parity_evidence_repository_root
from ethos.surface.cli._base import JsonFlag
from ethos.surface.cli._base import RootOption
from ethos.surface.cli._base import emit
from ethos.surface.cli._base import parity_app
from ethos.surface.cli._base import resolve_root
from ethos_core.normalization.core import object_sequence
from ethos_core.normalization.core import string_mapping
from ethos_core.normalization.core import string_sequence
from ethos_core.result import EthosResult


@parity_app.command(name="ledger")
def parity_ledger(*, json_output: JsonFlag = False) -> None:
    """Emit the executable capability parity ledger."""
    report = parity_ledger_report()
    result = EthosResult(
        command="parity ledger",
        ok=bool(report["ok"]),
        state="classified",
        summary=string_mapping(report.get("summary")),
        next_actions=("ethos parity gaps --adopter <adopter>",),
        data={"records": object_sequence(report.get("records"))},
    )
    emit(result, json_output=json_output, enforce=False)


@parity_app.command(name="gaps")
def parity_gaps(
    *,
    adopter: str | None = None,
    target: Path | None = None,
    root: RootOption | None = None,
    json_output: JsonFlag = False,
) -> None:
    """Report remaining product/adopter parity gaps."""
    repo = resolve_root(root)
    self_adopter = adopter in {None, "generic"}
    target_root = target or (repo if self_adopter else None)
    report = parity_gaps_report(
        adopter=adopter,
        root=repo,
        target=target_root,
        current_target_head=git_adapter.current_tracked_head(target_root)
        if target_root is not None
        else "",
        current_product_head=git_adapter.current_tracked_head(repo),
        acceptable_product_heads=land_parity.acceptable_parity_product_heads(repo, adopter),
        acceptable_target_heads=land_parity.acceptable_parity_target_heads(
            repo, target_root, adopter
        ),
    )
    evidence = report.get("evidence") if isinstance(report.get("evidence"), dict) else {}
    refresh = evidence.get("refresh_package") if isinstance(evidence, dict) else None
    refresh_command = str(string_mapping(refresh).get("command") or "")
    result = EthosResult(
        command="parity gaps",
        ok=bool(report["ok"]),
        state="clean" if report.get("ok") is True else "gapped",
        summary={
            "adopter": str(report.get("adopter") or ""),
            "gap_count": len(string_sequence(report.get("required_gaps"))),
        },
        required_gaps=tuple(string_sequence(report.get("required_gaps"))),
        next_actions=(
            (
                refresh_command
                or (
                    "ethos parity shadow --adopter <adopter-id> --target <repo> "
                    "--execute --write-evidence"
                ),
            )
            if string_sequence(report.get("required_gaps"))
            else ("ethos prove --full",)
        ),
        data=report,
    )
    emit(result, json_output=json_output, enforce=False)


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
    repo = resolve_root(root)
    adopter_name = adopter or "generic"
    if execute:
        from ethos.adapters.shadow.core import run_shadow_parity

        report = run_shadow_parity(
            target=target, timeout_seconds=timeout_seconds, product_root=repo
        )
    else:
        report = shadow_parity_report(
            target=target,
            root=repo,
            adopter=adopter,
            current_target_head=git_adapter.current_tracked_head(target),
            current_product_head=git_adapter.current_tracked_head(repo),
            acceptable_product_heads=land_parity.acceptable_parity_product_heads(repo, adopter),
            acceptable_target_heads=land_parity.acceptable_parity_target_heads(
                repo, target, adopter
            ),
        )
    required_gaps = string_sequence(report.get("required_gaps"))
    evidence_path = ""
    write_admission: dict[str, object] = {}
    if write_evidence:
        if not execute:
            required_gaps.append("parity_evidence_write_requires_execute")
        elif report.get("ok") is not True:
            required_gaps.append(f"parity_evidence_write_blocked:{adopter_name}")
        else:
            evidence_root = parity_evidence_repository_root(root=repo, target=target)
            evidence_target = parity_evidence_path(root=evidence_root, adopter=adopter_name)
            write_admission = prewrite_guard(
                root=evidence_root,
                paths=[evidence_target],
                editor_root=evidence_root,
                require_editor_root=True,
            )
            if write_admission["ok"] is not True:
                admission_gaps = cast("list[str]", write_admission["required_gaps"])
                required_gaps.extend(admission_gaps)
                report = {**report, "write_admission": write_admission}
            else:
                evidence = build_tracked_parity_evidence(
                    adopter=adopter_name,
                    target=target,
                    shadow=report,
                    current_product_head=git_adapter.current_tracked_head(repo),
                    current_target_head=git_adapter.current_tracked_head(target),
                    timeout_seconds=timeout_seconds,
                    root=repo,
                )
                written = write_tracked_parity_evidence(
                    root=evidence_root,
                    adopter=adopter_name,
                    evidence=evidence,
                )
                evidence_path = written.relative_to(evidence_root).as_posix()
                report = {
                    **report,
                    "evidence_written": evidence_path,
                    "write_admission": write_admission,
                }
    result = EthosResult(
        command="parity shadow",
        ok=bool(report["ok"]) and not required_gaps,
        state="blocked" if write_evidence and required_gaps else str(report["state"]),
        required_gaps=tuple(required_gaps),
        next_actions=(
            (
                "commit the written parity evidence in the admitted Work Lane",
                "ethos prove --execute --expect-head $(git rev-parse HEAD) --json",
            )
            if evidence_path
            else ("ethos prove --full",)
        )
        if not required_gaps
        else ("ethos parity gaps",),
        data=report,
    )
    emit(result, json_output=json_output, enforce=write_evidence)
