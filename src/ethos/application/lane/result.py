"""The one projection of a Work Lane report into its command's result.

Every lane command, whether a catalog half or a command still outside the catalog, projects its
report here, so a lane result reads the same way whichever command produced it.
"""

from collections.abc import Mapping

from ethos.contracts.verdict import Verdict
from ethos.contracts.verdict import report_verdict
from ethos.normalization.coercion import string_sequence
from ethos.result import EthosResult


def _public_state(report: Mapping[str, object], verdict: Verdict, passed: str) -> str:
    """Name a report's public state: a partial transition stays one, else its verdict's state."""
    declared = str(report.get("state") or "")
    if declared == "partial_transition":
        return declared
    if verdict != "pass":
        return "blocked" if verdict == "block" else "unknown"
    return passed or declared or "ready"


def lane_result(
    command: str,
    report: Mapping[str, object],
    *,
    summary: Mapping[str, object] | None = None,
    fields: tuple[str, ...] = (),
    diagnostics: tuple[dict[str, object], ...] = (),
    data: Mapping[str, object] | None = None,
    passed: str = "",
) -> EthosResult:
    """Project one lane report into a result with the report's verdict, gaps and next action.

    The summary is the one given, else the named report fields, each `""` when absent. A passing
    report keeps its own state unless the command names its pass, as `lane prewrite` names it
    `admitted`.
    """
    verdict = report_verdict(report)
    return EthosResult(
        command=command,
        verdict=verdict,
        state=_public_state(report, verdict, passed),
        summary=summary or {name: report.get(name, "") for name in fields},
        diagnostics=diagnostics,
        required_gaps=tuple(string_sequence(report.get("required_gaps"))),
        next_action=str(report.get("next_action") or ""),
        user_decision_required=bool(report.get("user_decision_required")),
        data=report if data is None else data,
    )
