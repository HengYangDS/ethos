"""Represent immutable public results and bound their projected payload size."""

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from typing import ClassVar
from typing import Literal
from typing import Self

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import computed_field
from pydantic import model_validator

from ethos.contracts.outcome import Outcome
from ethos.contracts.value import FrozenTuple
from ethos.contracts.value import JsonObject
from ethos.contracts.verdict import Verdict
from ethos.contracts.verdict import require_closed_verdict

# Every command's JSON result is bounded; a command declares a budget only to differ.
DEFAULT_PAYLOAD_BUDGET = 16 * 1024
PAYLOAD_BUDGETS = {"status": DEFAULT_PAYLOAD_BUDGET, "plan": 32 * 1024}
_INLINE_LINES = 20
_INLINE_ENTRY_BYTES = 1024
_ARTIFACT_HOME = Path("payloads")
_UNKNOWN_WITHOUT_GAPS = "unknown_without_required_gaps"
_BLOCK_WITHOUT_REASON = "block_without_reason"


class EthosResult(BaseModel):
    _WIRE_FIELDS: ClassVar[tuple[str, ...]] = (
        "schema_version",
        "command",
        "verdict",
        "state",
        "summary",
        "diagnostics",
        "required_gaps",
        "next_action",
        "user_decision_required",
        "data",
    )
    _DERIVED_FIELDS: ClassVar[tuple[str, ...]] = (
        "continuation",
        "missing_facts_or_evidence",
    )
    model_config = ConfigDict(
        title="ETHOS Result",
        frozen=True,
        strict=True,
        extra="forbid",
        validate_default=True,
        json_schema_extra={"required": [*_WIRE_FIELDS, *_DERIVED_FIELDS]},
    )

    schema_version: Literal[2] = 2
    command: str
    verdict: Verdict
    state: str
    summary: JsonObject = Field(default_factory=dict)
    diagnostics: FrozenTuple[JsonObject] = ()
    required_gaps: tuple[str, ...] = ()
    next_action: str = ""
    user_decision_required: bool = False
    governance_context: JsonObject | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    data: JsonObject = Field(default_factory=dict)

    @model_validator(mode="after")
    def reject_false_pass(self) -> Self:
        """Require one closed verdict with an explicit non-pass reason."""
        adverse = tuple(
            str(item.get("message") or item.get("code") or item.get("severity"))
            for item in self.diagnostics
            if str(item.get("severity") or "").lower() in {"warning", "error"}
        )
        if self.verdict == "unknown" and not self.required_gaps:
            raise ValueError(_UNKNOWN_WITHOUT_GAPS)
        if self.verdict == "block" and not self.required_gaps and not adverse:
            raise ValueError(_BLOCK_WITHOUT_REASON)
        require_closed_verdict(self.verdict, self.required_gaps, adverse)
        return self

    @computed_field
    @property
    def continuation(self) -> Literal["continue", "await-user", "blocked", "done"]:
        if self.user_decision_required:
            return "await-user"
        if self.verdict != "pass":
            return "blocked"
        return "continue" if self.next_action else "done"

    @computed_field
    @property
    def missing_facts_or_evidence(self) -> tuple[str, ...]:
        return self.required_gaps if self.verdict == "unknown" else ()

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=False)

    @classmethod
    def from_outcome(
        cls,
        command: str,
        outcome: Outcome,
        *,
        state: str = "",
        next_action: str = "",
        fallback: str = "",
        data: Mapping[str, object] | None = None,
    ) -> Self:
        """Build a boundary's result from the decision its parts composed, losing none of it."""
        return cls(
            command=command,
            verdict=outcome.verdict,
            state=state or {"unknown": "unknown", "block": "gapped"}.get(outcome.verdict, "ready"),
            diagnostics=outcome.causes,
            required_gaps=outcome.gaps,
            next_action=next_action or outcome.next_action or fallback,
            data=dict(data or {}),
        )

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> Self:
        """Validate one public payload and recompute every derived field."""
        carried = dict(payload)
        missing = tuple(
            name for name in (*cls._WIRE_FIELDS, *cls._DERIVED_FIELDS) if name not in carried
        )
        if missing:
            message = f"result_payload_field_missing:{missing[0]}"
            raise ValueError(message)
        derived = {name: carried.pop(name) for name in cls._DERIVED_FIELDS}
        result = cls.model_validate_json(json.dumps(carried))
        actual = result.to_dict()
        if mismatch := next(
            (name for name, value in derived.items() if value != actual[name]),
            "",
        ):
            message = f"result_derived_field_mismatch:{mismatch}"
            raise ValueError(message)
        return result


def apply_payload_budget(result: EthosResult, *, root: Path) -> EthosResult:
    """Externalize oversized command detail while keeping what an agent needs to act inline.

    The verdict, gaps and continuation always stay. Each failing step keeps its id, exit code and
    first output lines inline, with counts of what was left out. A result that still does not fit
    drops failing steps from the end and counts them; it never refuses for its size.
    """
    limit = PAYLOAD_BUDGETS.get(result.command, DEFAULT_PAYLOAD_BUDGET)
    payload = result.to_json().encode()
    if len(payload) <= limit:
        return result
    digest = hashlib.sha256(payload).hexdigest()
    relative = _ARTIFACT_HOME / result.command / f"{digest}.json"
    artifact = root / relative
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_bytes(payload)
    reference = {
        "path": artifact.resolve().as_posix(),
        "sha256": f"sha256:{digest}",
        "size_bytes": len(payload),
        "media_type": "application/json",
    }
    checks = [item for item in result.data.get("checks") or () if isinstance(item, Mapping)]
    failing = [_inline_step(item) for item in checks if item.get("verdict") != "pass"]
    inline: dict[str, Any] = {
        "failing": failing,
        "passing_count": len(checks) - len(failing),
        "omitted_failing": 0,
        "partial": [],
        "moved": [],
    }
    base = result.model_dump(exclude_computed_fields=True)
    # Small entries are how the next call binds (a receipt, a lane path, a plan digest); they stay.
    # A larger mapping keeps its scalar fields, which name its state; the rest moves to detail.
    kept: dict[str, Any] = {}
    for key, value in result.data.items():
        if _size(value) <= _INLINE_ENTRY_BYTES:
            kept[key] = value
        elif (scalars := _scalars(value)) and _size(scalars) <= _INLINE_ENTRY_BYTES:
            kept[key] = scalars
            inline["partial"].append(key)
        else:
            inline["moved"].append(key)

    def build(gaps: tuple[str, ...]) -> EthosResult:
        data = kept | {"detail": reference, "inline": inline}
        return EthosResult.model_validate(base | {"required_gaps": gaps, "data": data})

    bounded = build(result.required_gaps)
    while len(bounded.to_json().encode()) > limit and inline["failing"]:
        inline["failing"] = inline["failing"][:-1]
        inline["omitted_failing"] += 1
        bounded = build(result.required_gaps)
    while len(bounded.to_json().encode()) > limit and kept:
        largest = max(kept, key=lambda key: _size(kept[key]))
        kept.pop(largest)
        inline["partial"] = [key for key in inline["partial"] if key != largest]
        inline["moved"] = sorted({*inline["moved"], largest})
        bounded = build(result.required_gaps)
    gaps = result.required_gaps
    while len(bounded.to_json().encode()) > limit and len(gaps) > 1:
        gaps = gaps[: max(1, len(gaps) // 2)]
        inline["omitted_gaps"] = len(result.required_gaps) - len(gaps)
        bounded = build(gaps)
    return bounded


def _size(value: object) -> int:
    return len(json.dumps(value, default=str).encode())


def _scalars(value: object) -> dict[str, Any]:
    """Return a mapping's scalar fields, which name its state, without its nested detail."""
    if not isinstance(value, Mapping):
        return {}
    return {
        key: item for key, item in value.items() if not isinstance(item, Mapping | list | tuple)
    }


def _inline_step(check: Mapping[str, Any]) -> dict[str, Any]:
    """Keep one failing step's identity and its first output lines, counting the rest."""
    lines = f"{check.get('stdout') or ''}{check.get('stderr') or ''}".splitlines()
    return {
        "action_id": check.get("action_id"),
        "verdict": check.get("verdict"),
        "exit_code": check.get("exit_code"),
        "output": lines[:_INLINE_LINES],
        "omitted_lines": max(0, len(lines) - _INLINE_LINES),
    }
