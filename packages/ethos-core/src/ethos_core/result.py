from __future__ import annotations

import json
from dataclasses import dataclass
from dataclasses import field
from typing import Any

SCHEMA_VERSION = 1


@dataclass(frozen=True)
class EthosResult:
    command: str
    ok: bool
    state: str
    summary: dict[str, Any] = field(default_factory=dict)
    diagnostics: tuple[dict[str, Any], ...] = ()
    required_gaps: tuple[str, ...] = ()
    next_actions: tuple[str, ...] = ()
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
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

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=False)
