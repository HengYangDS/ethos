"""Public CLI coverage for ref-absent owner-unavailable reconciliation."""

from __future__ import annotations

from pathlib import Path

from tests.support.ethos_cli_runner import run_ethos
from tests.unit.lanes.retirement.test_unbound_and_helpers import (
    _partial_effect_reconciliation_fixture,
)


def test_cli_applies_one_ref_absent_lease_reconciliation(monkeypatch, tmp_path: Path) -> None:
    """The public command emits the native receipt after an exact accepted repair."""
    repo, branch, _head, chronicle, _lease, _attempt, _source_path = (
        _partial_effect_reconciliation_fixture(tmp_path)
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:recovery-operator")

    payload = run_ethos(
        "lane",
        "retire",
        "reconcile-ref-absent",
        "--branch",
        branch,
        "--reason",
        "reconcile exact historical ref-absent lease residue",
        "--chronicle-ref",
        chronicle,
        "--authorize",
        "--break-glass",
        "--confirm-irreversible",
        "--apply",
        "--root",
        repo.as_posix(),
        "--json",
        cwd=repo,
    )

    assert payload["command"] == "lane retire reconcile-ref-absent"
    assert payload["ok"] is True
    assert payload["state"] == "reconciled_ref_absent_owner_unavailable_lease"
    assert Path(str(payload["data"]["receipt_path"])).is_file()
