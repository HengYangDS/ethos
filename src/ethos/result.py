"""Represent immutable public results and bound their projected payload size."""

import hashlib
import json
import time
from collections.abc import Callable
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

from ethos.contracts.next_step import NextStep
from ethos.contracts.next_step import derive_next_step
from ethos.contracts.outcome import Outcome
from ethos.contracts.value import FrozenTuple
from ethos.contracts.value import JsonObject
from ethos.contracts.verdict import Verdict
from ethos.contracts.verdict import require_closed_verdict

# Every command's JSON result is bounded; a command declares a budget only to differ.
DEFAULT_PAYLOAD_BUDGET = 16 * 1024
# Help prints the root catalog: 40,755 bytes measured on 2026-11-08, rounded up to a 16 KiB step.
PAYLOAD_BUDGETS = {"status": DEFAULT_PAYLOAD_BUDGET, "plan": 32 * 1024, "help": 48 * 1024}
_INLINE_LINES = 20
_INLINE_ENTRY_BYTES = 1024
_ARTIFACT_HOME = Path("payloads")
# Detail is a convenience copy of a result, not a receipt; a week covers any continuation.
_DETAIL_RETENTION_SECONDS = 7 * 24 * 3600
_DETAIL_MISMATCH = "result_detail_mismatch"
_DETAIL_UNAVAILABLE = "result_detail_unavailable"
SCHEMA_VERSION = 3
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
        "next",
    )
    model_config = ConfigDict(
        title="ETHOS Result",
        frozen=True,
        strict=True,
        extra="forbid",
        validate_default=True,
        json_schema_extra={"required": [*_WIRE_FIELDS, *_DERIVED_FIELDS]},
    )

    schema_version: Literal[3] = 3
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
    # Only on a bounded result: where the full result is and what the bound left out.
    bound: JsonObject | None = Field(default=None, exclude_if=lambda value: value is None)
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

    @computed_field
    @property
    def next(self) -> NextStep:
        """The step `next_action` renders, as data an agent acts on without parsing text."""
        why = self.required_gaps[0] if self.required_gaps else self.state
        return derive_next_step(self.next_action, continuation=self.continuation, why=why)

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
        if (version := carried.get("schema_version")) != SCHEMA_VERSION:
            message = f"result_schema_version_unsupported:{version}"
            raise ValueError(message)
        derived = {name: carried.pop(name) for name in cls._DERIVED_FIELDS}
        # Each reader re-derives the step with its own classification, so an older runtime's
        # payload of the same schema stays readable; the carried step must only be well formed.
        NextStep.model_validate_json(json.dumps(derived.pop("next")))
        result = cls.model_validate_json(json.dumps(carried))
        actual = result.to_dict()
        if mismatch := next(
            (name for name, value in derived.items() if value != actual[name]),
            "",
        ):
            message = f"result_derived_field_mismatch:{mismatch}"
            raise ValueError(message)
        return result


def apply_payload_budget(result: EthosResult, *, root: Path | Callable[[], Path]) -> EthosResult:
    """Bound a result while keeping what an agent needs to act, never refusing for its size.

    The wire fields always stay. `data` keeps the command's own small entries and the scalar
    fields of larger mappings. `bound` names the full result's detail artifact, each failing
    step's id, exit code and first output lines, and what was shortened, moved or left out.
    """
    limit = PAYLOAD_BUDGETS.get(result.command, DEFAULT_PAYLOAD_BUDGET)
    payload = result.to_json().encode()
    if len(payload) <= limit:
        return result
    checks = [item for item in result.data.get("checks") or () if isinstance(item, Mapping)]
    failing = [_inline_step(item) for item in checks if item.get("verdict") != "pass"]
    bound: dict[str, Any] = {
        "budget_bytes": limit,
        "full_bytes": len(payload),
        **_write_detail(payload, result.command, root),
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
            bound["partial"].append(key)
        else:
            bound["moved"].append(key)

    def build(gaps: tuple[str, ...]) -> EthosResult:
        return EthosResult.model_validate(
            base | {"required_gaps": gaps, "data": kept, "bound": bound}
        )

    bounded = build(result.required_gaps)
    while len(bounded.to_json().encode()) > limit and bound["failing"]:
        bound["failing"] = bound["failing"][:-1]
        bound["omitted_failing"] += 1
        bounded = build(result.required_gaps)
    while len(bounded.to_json().encode()) > limit and kept:
        largest = max(kept, key=lambda key: _size(kept[key]))
        kept.pop(largest)
        bound["partial"] = [key for key in bound["partial"] if key != largest]
        bound["moved"] = sorted({*bound["moved"], largest})
        bounded = build(result.required_gaps)
    gaps = result.required_gaps
    while len(bounded.to_json().encode()) > limit and len(gaps) > 1:
        gaps = gaps[: max(1, len(gaps) // 2)]
        bound["omitted_gaps"] = len(result.required_gaps) - len(gaps)
        bounded = build(gaps)
    return bounded


def expand_result(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return the full result a bounded payload names, verified against its digest and size.

    A payload that was never bounded is returned as it is. The full result must agree with the
    bounded one on every field the bound keeps, so a changed or substituted artifact refuses. It
    comes back as its producer wrote it, so another build's result stays readable; a caller that
    needs this build's model validates it with `EthosResult.from_payload`.
    """
    bound = payload.get("bound")
    if not isinstance(bound, Mapping):
        return dict(payload)
    if "detail" not in bound:
        raise ValueError(_DETAIL_UNAVAILABLE)
    try:
        full = json.loads(_detail_bytes(bound["detail"]))
    except ValueError as error:
        raise ValueError(_DETAIL_MISMATCH) from error
    if not isinstance(full, dict) or "bound" in full:
        raise ValueError(_DETAIL_MISMATCH)
    # The bound may truncate the gaps, and an unknown verdict repeats them.
    reduced = {"bound", "data", "required_gaps", "missing_facts_or_evidence"}
    if any(full.get(key) != value for key, value in payload.items() if key not in reduced):
        raise ValueError(_DETAIL_MISMATCH)
    return full


def _write_detail(payload: bytes, command: str, root: Path | Callable[[], Path]) -> dict[str, Any]:
    """Write the full result as a cache; a store that refuses it leaves the result inline.

    `root` may be a callable, so a caller resolves its store only when detail is written.
    """
    digest = hashlib.sha256(payload).hexdigest()
    try:
        store = root if isinstance(root, Path) else root()
        # An agent passes the path unquoted, so the command's words join with hyphens.
        artifact = store / _ARTIFACT_HOME / command.replace(" ", "-") / f"{digest}.json"
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_bytes(payload)
    except OSError as error:
        return {"detail_unavailable": type(error).__name__}
    _remove_stale_detail(store / _ARTIFACT_HOME, keep=artifact)
    return {
        "detail": {
            "path": artifact.resolve().as_posix(),
            "sha256": f"sha256:{digest}",
            "size_bytes": len(payload),
            "media_type": "application/json",
        }
    }


def _remove_stale_detail(home: Path, *, keep: Path) -> None:
    """Remove detail older than the retention window whenever new detail is written."""
    cutoff = time.time() - _DETAIL_RETENTION_SECONDS
    for stale in home.glob("*/*.json"):
        try:
            if stale != keep and stale.stat().st_mtime < cutoff:
                stale.unlink()
        except OSError:
            continue


def _detail_bytes(reference: Any) -> bytes:
    """Read one detail artifact, refusing any bytes its reference does not name."""
    try:
        content = Path(str(reference["path"])).read_bytes()
        expected = (reference["size_bytes"], reference["sha256"])
    except (OSError, KeyError, TypeError) as error:
        raise ValueError(_DETAIL_MISMATCH) from error
    if (len(content), f"sha256:{hashlib.sha256(content).hexdigest()}") != expected:
        raise ValueError(_DETAIL_MISMATCH)
    return content


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
