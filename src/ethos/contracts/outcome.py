"""Compose one decision from its parts without losing a part's cause or verdict class."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import cast

from ethos.contracts.verdict import Verdict
from ethos.contracts.verdict import close_verdict
from ethos.contracts.verdict import reduce_verdicts
from ethos.normalization.coercion import string_sequence

if TYPE_CHECKING:
    from collections.abc import Iterable

# The cause codes one part keeps beside its class code; its record counts the rest.
CAUSE_LIMIT = 5
# The small facts that a failed check's cause record keeps, from its leading diagnostic and itself.
_CAUSE_FACTS = ("kind", "timeout_seconds", "elapsed_seconds")
_CHECK_FACTS = ("exit_code", "duration_seconds")


@dataclass(frozen=True, slots=True)
class Outcome:
    """A verdict with every part's gaps, one bounded record per non-pass part, and a next action."""

    verdict: Verdict = "pass"
    gaps: tuple[str, ...] = ()
    causes: tuple[dict[str, object], ...] = ()
    next_action: str = ""

    @classmethod
    def of(cls, verdict: Verdict, *gaps: str, next_action: str = "") -> Outcome:
        """Declare one decision; a pass that carries gaps closes to block, as the kernel says."""
        kept = tuple(dict.fromkeys(gap for gap in gaps if gap))
        return cls(close_verdict(verdict, kept), kept, (), next_action)

    @classmethod
    def part(
        cls,
        verdict: Verdict,
        class_gap: str,
        causes: Iterable[str] = (),
        *,
        subject: str,
        facts: Mapping[str, object] | None = None,
        next_action: str = "",
    ) -> Outcome:
        """One non-pass part: its class code first, then at most `CAUSE_LIMIT` of its own codes."""
        codes = tuple(dict.fromkeys(code for code in causes if code and code != class_gap))
        gaps = (class_gap, *codes[:CAUSE_LIMIT])
        omitted = len(codes) - CAUSE_LIMIT
        record = {"subject": subject, "verdict": verdict, "gaps": list(gaps), **dict(facts or {})}
        record |= {"omitted_gap_count": omitted} if omitted > 0 else {}
        return cls(close_verdict(verdict, gaps), gaps, (record,), next_action)

    def combine(self, *others: Outcome) -> Outcome:
        """Reduce the parts' verdicts, never their gaps' presence, and keep every part in order."""
        parts = (self, *others)
        verdict = reduce_verdicts(*(part.verdict for part in parts))
        actions = (
            *(part.next_action for part in parts if part.verdict == verdict),
            *(part.next_action for part in parts),
        )
        return Outcome(
            verdict,
            tuple(dict.fromkeys(gap for part in parts for gap in part.gaps)),
            tuple(record for part in parts for record in part.causes),
            next((action for action in actions if action), ""),
        )


class OutcomeError(ValueError):
    """Carry one decision across an exception; the message stays its leading gap."""

    def __init__(
        self,
        outcome: Outcome,
        *,
        message: str = "",
        observation: Mapping[str, object] | None = None,
    ) -> None:
        super().__init__(message or next(iter(outcome.gaps), outcome.verdict))
        self.outcome = outcome
        self.observation = dict(observation or {})


def refusal(*gaps: str, verdict: Verdict = "block") -> OutcomeError:
    """Return the error that carries every gap of one refusal, ready to raise."""
    return OutcomeError(Outcome.of(verdict, *gaps))


def present[T](value: T | None, *gaps: str) -> T:
    """Return a value the caller requires, or raise the refusal that names why it is absent."""
    if value is None:
        raise refusal(*gaps)
    return value


def instance[T](value: object, kind: type[T], *gaps: str) -> T:
    """Return a value of the kind the caller requires, or raise the refusal that names the gaps."""
    if not isinstance(value, kind):
        raise refusal(*gaps)
    return value


def outcome_of(error: BaseException, *, fallback: str = "") -> Outcome:
    """Read the decision an error carries, or one blocking gap for any other error."""
    if isinstance(error, OutcomeError):
        return error.outcome
    return Outcome.of("block", str(error).strip() or fallback or type(error).__name__)


def gate_outcome(checks: Iterable[Mapping[str, object]]) -> Outcome:
    """One part per executed non-pass check: its class code first, then its diagnostics' gaps."""
    parts = []
    for check in checks:
        verdict = cast("Verdict", check["verdict"])
        if verdict == "pass":
            continue
        gate = str(check["action_id"])
        listed = check.get("diagnostics")
        diagnostics = (
            [item for item in listed or () if isinstance(item, Mapping)]
            if isinstance(listed, list | tuple)
            else []
        )
        leading = next((item for item in diagnostics if item.get("kind")), {})
        facts = {key: leading[key] for key in _CAUSE_FACTS if leading.get(key) is not None}
        facts |= {key: check[key] for key in _CHECK_FACTS if check.get(key) is not None}
        parts.append(
            Outcome.part(
                verdict,
                f"gate_failed:{gate}" if verdict == "block" else f"gate_unknown:{gate}",
                (gap for item in diagnostics for gap in string_sequence(item.get("required_gaps"))),
                subject=gate,
                facts=facts,
            )
        )
    return Outcome().combine(*parts)
