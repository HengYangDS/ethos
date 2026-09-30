"""Invoke product-owned gate verifiers against one exact native observation."""

from __future__ import annotations

import importlib
import inspect
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import cast

import ethos
from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.repo.git import current_head
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.runtime.authority import invoking_build_identity
from ethos.contracts.verdict import Verdict
from ethos.contracts.verdict import reduce_verdicts
from ethos.contracts.verdict import report_verdict
from ethos.normalization.coercion import string_sequence
from ethos.repository.policy.gates import PRODUCT_PROVIDER_SOURCE
from ethos.repository.policy.gates import provider_source_bindings_for_gate

if TYPE_CHECKING:
    from ethos.contracts.gates import Gate


@dataclass(frozen=True, slots=True)
class NativePackageSources:
    """Native build ownership and exact source-to-artifact member correspondence."""

    distribution: str
    members: tuple[tuple[str, str], ...]
    input_digests: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class NativeReportInputs:
    """Caller-owned report scope and source inputs retained before execution."""

    root: Path
    source_digests: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class NativePythonReports(NativeReportInputs):
    """Python native source and build identities retained before its attempt."""

    python_prefix: tuple[str, ...]
    packaged_sources: NativePackageSources | None = None


@dataclass(frozen=True, slots=True)
class NativeGoReports(NativeReportInputs):
    """Go native package-file identities and exact instrumented attempt."""

    command: tuple[str, ...]
    source_paths: tuple[tuple[str, str], ...]
    coverage_path: str = "coverage.out"


@dataclass(frozen=True, slots=True)
class NativeExecution:
    """Invocation-local native output distinct from the canonical gate identity."""

    declared_identity: tuple[str, ...]
    argv: tuple[str, ...]
    cwd: Path
    exit_code: int
    stdout: str
    stderr: str
    reports: NativePythonReports | NativeGoReports | None = None


def provider_reports(
    gate_id: str,
    references: tuple[str, ...],
    root: Path,
    *,
    execution: NativeExecution | None = None,
    preflight: bool = False,
    command: tuple[str, ...] = (),
    gate: Gate | None = None,
) -> tuple[list[dict[str, object]], Verdict, tuple[dict[str, Any], ...]]:
    """Execute the same product-owned provider contract for either gate form."""
    if preflight and execution is not None:
        message = "provider preflight cannot carry completed execution"
        raise ValueError(message)
    reports: list[dict[str, object]] = []
    diagnostics: list[dict[str, Any]] = []
    verdicts: list[Verdict] = []
    for reference in references:
        try:
            report = _provider_report(
                reference,
                root,
                execution=execution,
                preflight=preflight,
                command=command,
                gate=gate,
            )
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
        verdict = report_verdict({**report, "required_gaps": provider_gaps})
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
                    **({"diagnostics": report["diagnostics"]} if report.get("diagnostics") else {}),
                }
            )
    verdict = reduce_verdicts(*verdicts) if len(reports) == len(references) else "block"
    return reports, verdict, tuple(diagnostics)


def diagnostic_gaps_for(value: object, prefix: str) -> tuple[str, ...]:
    """Promote adverse provider diagnostics without treating notes as failures."""
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
    preflight: bool = False,
    command: tuple[str, ...] = (),
    gate: Gate | None = None,
) -> Mapping[str, object]:
    module_name, _, attribute = reference.partition(":")
    provider = getattr(importlib.import_module(module_name), attribute)
    parameters = inspect.signature(provider).parameters
    if preflight and "preflight" not in parameters:
        return {"verdict": "pass", "state": "no_provider_preflight"}
    kwargs: dict[str, object] = {}
    if preflight:
        kwargs["preflight"] = True
        if "command" in parameters:
            kwargs["command"] = command
    if "current_head" in parameters:
        kwargs["current_head"] = current_head(root)
    if "gate" in parameters:
        kwargs["gate"] = gate
    if execution is not None and "execution" in parameters:
        kwargs["execution"] = execution
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
        for reference, relative in provider_source_bindings_for_gate(gate)
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
