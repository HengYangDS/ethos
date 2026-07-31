import hashlib
import json
from pathlib import Path
from typing import Any
from typing import Literal
from typing import Self

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import model_validator

from ethos.contracts.value import FrozenTuple
from ethos.contracts.value import JsonObject
from ethos.contracts.verdict import Verdict
from ethos.contracts.verdict import require_closed_verdict

PAYLOAD_BUDGETS = {"status": 16 * 1024, "plan": 32 * 1024}
_ARTIFACT_HOME = Path("build/ethos/payloads")


class EthosResult(BaseModel):
    model_config = ConfigDict(
        title="ETHOS Result",
        frozen=True,
        strict=True,
        extra="forbid",
        validate_default=True,
    )

    schema_version: Literal[1] = 1
    command: str
    verdict: Verdict
    state: str
    summary: JsonObject = Field(default_factory=dict)
    diagnostics: FrozenTuple[JsonObject] = ()
    required_gaps: tuple[str, ...] = ()
    next_actions: tuple[str, ...] = ()
    governance_context: JsonObject | None = None
    data: JsonObject = Field(default_factory=dict)

    @model_validator(mode="after")
    def reject_false_pass(self) -> Self:
        """Prevent blockers from coexisting with a green command result."""
        adverse = tuple(
            str(item.get("message") or item.get("code") or item.get("severity"))
            for item in self.diagnostics
            if str(item.get("severity") or "").lower() in {"warning", "error"}
        )
        require_closed_verdict(self.verdict, self.required_gaps, adverse)
        return self

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=False)


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
        result.model_dump()
        | {
            "data": {
                "artifact_reference": {
                    "path": relative.as_posix(),
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
