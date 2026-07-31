from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import model_validator

from ethos.contracts.verdict import Verdict
from ethos.contracts.verdict import require_closed_verdict

PAYLOAD_BUDGETS = {"status": 16 * 1024, "plan": 32 * 1024}
_ARTIFACT_HOME = Path("build/ethos/payloads")


class EthosResult(BaseModel):
    model_config = ConfigDict(title="ETHOS Result", frozen=True, strict=True, extra="forbid")

    schema_version: Literal[1] = 1
    command: str
    verdict: Verdict
    state: str
    summary: dict[str, Any] = Field(default_factory=dict)
    diagnostics: tuple[dict[str, Any], ...] = ()
    required_gaps: tuple[str, ...] = ()
    next_actions: tuple[str, ...] = ()
    governance_context: dict[str, Any] | None = None
    data: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def reject_false_pass(self) -> EthosResult:
        """Prevent blockers from coexisting with a green command result."""
        adverse = tuple(
            str(item.get("message") or item.get("code") or item.get("severity"))
            for item in self.diagnostics
            if str(item.get("severity") or "").lower() in {"warning", "error"}
        )
        require_closed_verdict(self.verdict, self.required_gaps, adverse)
        return self

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "command": self.command,
            "verdict": self.verdict,
            "state": self.state,
            "summary": dict(self.summary),
            "diagnostics": [dict(item) for item in self.diagnostics],
            "required_gaps": list(self.required_gaps),
            "next_actions": list(self.next_actions),
            "data": dict(self.data),
        }
        if self.governance_context is not None:
            payload["governance_context"] = dict(self.governance_context)
        return payload

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
    bounded = result.model_copy(
        update={
            "data": {
                "artifact_reference": {
                    "path": relative.as_posix(),
                    "sha256": f"sha256:{digest}",
                    "size_bytes": len(payload),
                    "media_type": "application/json",
                }
            }
        }
    )
    if len(bounded.to_json().encode()) > limit:
        msg = f"bounded {result.command} payload exceeds {limit} bytes"
        raise ValueError(msg)
    return bounded
