"""Invoke product-owned gate verifiers against one exact native observation."""

from __future__ import annotations

import importlib
import inspect
import json
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from time import monotonic
from typing import TYPE_CHECKING
from typing import Any
from typing import cast

import ethos
from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.process import command_scope
from ethos.adapters.repo.content.observation import observed_document_origins
from ethos.adapters.repo.git import current_head
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.runtime.authority import invoking_build_identity
from ethos.contracts.verdict import Verdict
from ethos.contracts.verdict import reduce_verdicts
from ethos.contracts.verdict import report_verdict
from ethos.normalization.coercion import string_sequence
from ethos.repository.policy.gates import PRODUCT_PROVIDER_SOURCE
from ethos.repository.policy.gates import provider_module_sources

if TYPE_CHECKING:
    from ethos.adapters.gates.javascript.execution import NodeAttempt
    from ethos.contracts.gates import Gate
    from ethos.contracts.gates import NativeOutput


@dataclass(frozen=True, slots=True)
class NativeEvidence:
    """Original native bytes and their invocation-local source/producer custody."""

    gate: Gate
    head: str
    tree: str
    subjects: tuple[str, ...]
    output_root: str
    outputs: tuple[tuple[NativeOutput, bytes], ...]
    gaps: tuple[str, ...]
    artifact: str
    dependency_checks: tuple[tuple[NativeOutput, bytes], ...] = ()
    # The exact wheel supplied to this attempt's observers; a source checkout supplies none.
    observer_requirement: str | None = None


@dataclass(frozen=True, slots=True)
class NativeExecution:
    """Invocation-local native output distinct from the canonical gate identity."""

    declared_identity: tuple[str, ...]
    argv: tuple[str, ...]
    cwd: Path
    exit_code: int
    stdout: str
    stderr: str
    # Preserve the invocation path: dereferencing Python changes virtual-environment semantics.
    executable: str = ""
    node_attempt: NodeAttempt | None = None
    evidence: NativeEvidence | None = None


def classify_action_result(
    *,
    exit_code: int | None,
    stdout: str,
    timeout_gap: str | None = None,
) -> tuple[Verdict, tuple[dict[str, Any], ...]]:
    """Interpret native command output independently of execution and scheduling."""
    if exit_code != 0 or timeout_gap is not None:
        verdict: Verdict = "unknown" if timeout_gap is not None else "block"
        diagnostics = (
            ({"kind": "gate_timeout", "required_gaps": [timeout_gap]},)
            if timeout_gap is not None
            else ()
        )
        return verdict, diagnostics
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return "pass", ()
    if not isinstance(payload, dict) or "command" not in payload:
        return "pass", ()
    raw_verdict = payload.get("verdict")
    if not isinstance(raw_verdict, str) or raw_verdict not in {"pass", "block", "unknown"}:
        return "unknown", (
            {
                "kind": "ethos_result",
                "verdict": "unknown",
                "state": str(payload.get("state", "")),
                "required_gaps": ["ethos_result_verdict_missing_or_invalid"],
            },
        )
    required_gaps = string_sequence(payload.get("required_gaps"), drop_empty=True)
    warnings = string_sequence(payload.get("warnings"), drop_empty=True)
    diagnostic_gaps = diagnostic_gaps_for(payload.get("diagnostics"), "ethos_result")
    gaps = tuple(dict.fromkeys((*required_gaps, *diagnostic_gaps)))
    verdict = report_verdict(payload)
    if verdict == "pass":
        return verdict, ()
    warning_gaps = tuple(f"ethos_result_warning:{warning}" for warning in warnings)
    return verdict, (
        {
            "kind": "ethos_result",
            "verdict": verdict,
            "state": str(payload.get("state", "")),
            "required_gaps": list(dict.fromkeys((*gaps, *warning_gaps))),
        },
    )


def provider_reports(
    gate_id: str,
    references: tuple[str, ...],
    root: Path,
    *,
    execution: NativeExecution | None = None,
    timeout_seconds: float | None = None,
) -> tuple[list[dict[str, object]], Verdict, tuple[dict[str, Any], ...]]:
    """Execute the same product-owned provider contract for either gate form."""
    reports: list[dict[str, object]] = []
    diagnostics: list[dict[str, Any]] = []
    verdicts: list[Verdict] = []
    deadline = monotonic() + timeout_seconds if timeout_seconds is not None else None
    for reference in references:
        try:
            remaining = max(0, deadline - monotonic()) if deadline is not None else None
            if remaining is not None and remaining <= 0:
                raise subprocess.TimeoutExpired(reference, remaining)
            with command_scope(timeout_seconds=remaining):
                report = _provider_report(
                    reference, root, execution=execution, timeout_seconds=remaining
                )
            if deadline is not None and monotonic() >= deadline:
                raise subprocess.TimeoutExpired(reference, timeout_seconds or 0)
        except (
            AttributeError,
            ImportError,
            OSError,
            RuntimeError,
            subprocess.SubprocessError,
            TypeError,
            ValueError,
        ) as exc:
            diagnostics.append(
                {
                    "kind": "gate_provider_error",
                    "provider": reference,
                    "error": f"{type(exc).__name__}: {exc}",
                    "required_gaps": [f"gate_provider_error:{gate_id}:{reference}"],
                }
            )
            continue
        reports.append({"provider": reference, "report": dict(report)})
        gaps = string_sequence(report.get("required_gaps"), drop_empty=True)
        warnings = string_sequence(report.get("warnings"), drop_empty=True)
        warning_gaps = tuple(
            f"gate_provider_warning:{gate_id}:{reference}:{warning}" for warning in warnings
        )
        diagnostic_gaps = diagnostic_gaps_for(
            report.get("diagnostics"), f"gate_provider_diagnostic:{gate_id}:{reference}"
        )
        provider_gaps = tuple(dict.fromkeys((*gaps, *warning_gaps, *diagnostic_gaps)))
        verdict = reduce_verdicts(
            report_verdict(report), report_verdict({**report, "required_gaps": provider_gaps})
        )
        if verdict == "block" and not provider_gaps:
            provider_gaps = (f"gate_provider_blocked:{gate_id}:{reference}",)
        elif verdict == "unknown" and not provider_gaps:
            provider_gaps = (f"gate_provider_unknown:{gate_id}:{reference}",)
        verdicts.append(verdict)
        if verdict != "pass":
            diagnostics.append(
                {
                    "kind": "gate_provider",
                    "provider": reference,
                    "verdict": verdict,
                    "required_gaps": list(provider_gaps),
                }
            )
    verdict = reduce_verdicts(*verdicts) if len(reports) == len(references) else "block"
    return reports, verdict, tuple(diagnostics)


def diagnostic_gaps_for(value: object, prefix: str) -> tuple[str, ...]:
    """Promote adverse provider diagnostics without treating notes as failures."""
    if isinstance(value, Mapping):
        value = (value,)
    if not isinstance(value, (list, tuple)):
        return ()
    gaps = []
    for item in value:
        if not isinstance(item, Mapping):
            continue
        severity = str(item.get("severity", "")).lower()
        if severity not in {"warning", "error"}:
            continue
        message = str(item.get("message") or item.get("code") or severity)
        gaps.append(f"{prefix}:{severity}:{message}")
    return tuple(gaps)


def _provider_report(
    reference: str,
    root: Path,
    *,
    execution: NativeExecution | None = None,
    timeout_seconds: float | None = None,
) -> Mapping[str, object]:
    module_name, _, attribute = reference.partition(":")
    provider = getattr(importlib.import_module(module_name), attribute)
    parameters = inspect.signature(provider).parameters
    kwargs: dict[str, object] = {}
    if "current_head" in parameters:
        kwargs["current_head"] = current_head(root)
    if "retained_origins" in parameters:
        kwargs["retained_origins"] = observed_document_origins(root)
    if execution is not None and "execution" in parameters:
        kwargs["execution"] = execution
    if timeout_seconds is not None and "timeout_seconds" in parameters:
        kwargs["timeout_seconds"] = timeout_seconds
    value = provider(root, **kwargs)
    if not isinstance(value, Mapping):
        message = f"gate provider must return a mapping: {reference}"
        raise TypeError(message)
    return cast("Mapping[str, object]", value)


def assert_provider_execution_source(root: Path, gates: tuple[Gate, ...]) -> None:
    """Reject candidate-bound checks running from a different implementation before effects."""
    bound = tuple(
        (gate.id, reference)
        for gate in gates
        for reference, relative in provider_module_sources(gate)
        if not relative.startswith(PRODUCT_PROVIDER_SOURCE) and (root / relative).is_file()
    )
    package = Path(ethos.__file__).resolve()
    if not bound or package == (root / "src/ethos/__init__.py").resolve():
        return
    try:
        identity = invoking_build_identity()
        head = current_tracked_head(root)
        if head == identity.source_commit and current_tree(root, head) == identity.source_tree:
            return
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError):
        pass
    gate_id, reference = bound[0]
    message = f"gate_provider_source_mismatch:{gate_id}:{reference}"
    raise ProcessExecutionError(
        message,
        reason="candidate_provider_execution_requires_matching_source",
        cwd=str(root),
        observation={
            "runner_module_path": str(package),
            "required_gaps": [f"gate_provider_source_mismatch:{name}:{ref}" for name, ref in bound],
            "next_action": "run proof from the admitted checkout's locked Python environment",
        },
    )
