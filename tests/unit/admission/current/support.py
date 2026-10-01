"""Official report and current-authority inputs for resolution boundary tests."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import ethos.adapters.admission.current.resolution as resolution_adapter
from ethos.adapters.admission.current.authority import CurrentAuthority
from ethos.adapters.admission.current.resolution import CurrentResolution
from ethos.adapters.admission.current.resolution import resolve_current_resolution

if TYPE_CHECKING:
    from ethos.contracts.verdict import Verdict

ROOT = Path("/repository")
HEAD = "a" * 40
ABSENT = object()


def authority(*, verdict: Verdict = "pass", reason: str = "matched") -> CurrentAuthority:
    return CurrentAuthority(
        verdict=verdict,
        reason=reason,
        branch="work/example",
        actor="agent:test" if verdict == "pass" else "",
        lease={
            "lease_state": "valid",
            "holder_ref": "agent:test",
            "generation": 3,
            "expires_at": "2099-01-01T00:00:00Z",
        },
        current_head=HEAD,
        current_tree="b" * 40,
    )


def receipt(payload: object, *, exit_code: int = 0) -> dict[str, object]:
    return {"exit_code": exit_code, "parse_error": "", "json": payload}


def official_artifact(
    identifier: str,
    output: str,
    *,
    status: str = "done",
    requires: tuple[str, ...] = (),
) -> dict[str, object]:
    return {
        "id": identifier,
        "outputPath": output,
        "status": status,
        "requires": list(requires),
    }


def official_report(
    *,
    change: str | None = None,
    gaps: tuple[str, ...] = (),
    artifacts: tuple[object, ...] = (),
    commitment: object = ABSENT,
    change_path: str | None = None,
    scope_binding: dict[str, object] | None = None,
    status_payload: dict[str, object] | None = None,
    validate_payload: dict[str, object] | None = None,
) -> dict[str, object]:
    selected = []
    if change is not None:
        row: dict[str, object] = {
            "name": change,
            "artifacts": list(artifacts),
            "required_gaps": [],
        }
        if change_path is not None:
            row["path"] = change_path
        selected.append(row)
    commands = {"list": receipt({"changes": [] if change is None else [{"name": change}]})}
    if status_payload is not None:
        commands["status"] = receipt(status_payload)
    if validate_payload is not None:
        commands["validate"] = receipt(validate_payload, exit_code=1)
    report: dict[str, object] = {
        "verdict": "block",
        "official_cli": {"available": True},
        "required_gaps": list(gaps),
        "lifecycle": {"scope_binding": scope_binding or {}, "changes": selected},
        "commands": commands,
    }
    if change is not None:
        report["change"] = change
    if commitment is not ABSENT:
        report["commitment"] = commitment
    return report


def resolve_report(
    monkeypatch,
    report: dict[str, object],
    *,
    root: Path = ROOT,
    paths: tuple[str, ...] = (),
    role: str = "work_lane",
) -> CurrentResolution:
    monkeypatch.setattr(resolution_adapter, "openspec_governance_report", lambda *_a, **_k: report)
    return resolve_current_resolution(
        root,
        status={"role": role, "head": HEAD, "changed_paths": []},
        authority=authority(),
        changed=False,
        prewrite_paths=paths,
    )
