from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

SCHEMA_VERSION = 1


class EthosResult(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    command: str
    ok: bool
    state: str
    summary: dict[str, Any] = Field(default_factory=dict)
    diagnostics: tuple[dict[str, Any], ...] = ()
    required_gaps: tuple[str, ...] = ()
    next_actions: tuple[str, ...] = ()
    governance_context: dict[str, Any] | None = None
    data: dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "command": self.command,
            "ok": self.ok,
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
