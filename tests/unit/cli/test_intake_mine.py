from __future__ import annotations

from typing import TYPE_CHECKING

from tests.support.ethos_cli_runner import run_ethos

if TYPE_CHECKING:
    from pathlib import Path


def test_intake_mine_projects_signals_without_mutating_root(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / "evidence" / "claims").mkdir(parents=True)
    claim = root / "evidence" / "claims" / "stale-proof.toml"
    claim.write_text(
        'id = "stale-proof"\n'
        'status = "accepted"\n'
        "[evidence]\n"
        'head = "0000000000000000000000000000000000000000"\n',
        encoding="utf-8",
    )

    before = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))

    payload = run_ethos("intake", "mine", "--root", str(root), "--json")

    after = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
    assert after == before
    assert payload["ok"] is True
    assert payload["command"] == "intake mine"
    assert payload["state"] == "mined"
    assert payload["data"]["truth_boundary"] == "repository-readmodel"
    assert payload["data"]["repository_truth"] is False
    assert payload["data"]["writes"] == []

    envelopes = payload["data"]["intake_envelopes"]
    candidates = payload["data"]["issue_candidates"]
    assert len(envelopes) == 1
    assert len(candidates) == 1
    assert envelopes[0]["source_kind"] == "claim"
    assert envelopes[0]["source_path"] == "evidence/claims/stale-proof.toml"
    assert envelopes[0]["external_provider_truth"] is False

    candidate = candidates[0]
    assert candidate == {
        "candidate_id": "claim-stale-proof-head-stale-proof",
        "source_envelope_id": envelopes[0]["envelope_id"],
        "subject": "evidence/claims/stale-proof.toml",
        "violated_commitment": "evidence must bind claims to current repository head",
        "invalid_state": "evidence.head_stale",
        "scope": "evidence",
        "severity": "medium",
        "dedupe_key": "evidence.head_stale:evidence/claims/stale-proof.toml",
        "suggested_disposition": "admit_change_claim",
        "suggested_proof": "refresh claim evidence and run ethos quality claims --json",
        "auto_raise_allowed": False,
        "auto_dispatch_allowed": False,
    }


def test_intake_mine_reports_clean_when_no_signals(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()

    payload = run_ethos("intake", "mine", "--root", str(root), "--json")

    assert payload["ok"] is True
    assert payload["command"] == "intake mine"
    assert payload["state"] == "clean"
    assert payload["data"]["intake_envelopes"] == []
    assert payload["data"]["issue_candidates"] == []
    assert payload["summary"] == {
        "signal_count": 0,
        "candidate_count": 0,
        "auto_raise_allowed": False,
        "auto_dispatch_allowed": False,
    }
