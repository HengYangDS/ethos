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

from ethos.contracts.value import FrozenTuple
from ethos.contracts.value import JsonObject
from ethos.contracts.verdict import Verdict
from ethos.contracts.verdict import require_closed_verdict

PAYLOAD_BUDGETS = {"status": 16 * 1024, "plan": 32 * 1024}
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
    governance_context: JsonObject | None = None
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
    """Externalize oversized command detail while preserving the verdict."""
    limit = PAYLOAD_BUDGETS.get(result.command)
    payload = result.to_json().encode()
    if limit is None or len(payload) <= limit:
        return result
    digest = hashlib.sha256(payload).hexdigest()
    relative = _ARTIFACT_HOME / result.command / f"{digest}.json"
    artifact = root / relative
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_bytes(payload)
    bounded = EthosResult.model_validate(
        result.model_dump(exclude_computed_fields=True)
        | {
            "data": {
                "artifact_reference": {
                    "path": artifact.resolve().as_posix(),
                    "sha256": f"sha256:{digest}",
                    "size_bytes": len(payload),
                    "media_type": "application/json",
                }
            }
        },
    )
    if len(bounded.to_json().encode()) > limit:
        msg = f"bounded {result.command} payload exceeds {limit} bytes"
        raise ValueError(msg)
    return bounded
