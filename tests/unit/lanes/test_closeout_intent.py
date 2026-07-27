"""Closeout-intent marker unit tests — write / consume / lifecycle.

The marker discriminates official closeout from raw ref moves (see
adapters.admission.closeout_intent). These tests cover the mechanism directly: the
one-shot consume, the three distinct refusal gaps, TTL expiry, the stale sweep, and
the linked-worktree-safe path resolution.
"""

from __future__ import annotations

import json
import subprocess
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import TYPE_CHECKING

import ethos.adapters.admission.closeout_intent.marker as closeout_markers

if TYPE_CHECKING:
    from pathlib import Path


def _marker_path(repo: Path, nonce: str) -> Path:
    return closeout_markers.closeout_intent_dir(repo) / f"{nonce}.json"


def _write(repo: Path, *, old: str = "old", new: str = "new") -> dict[str, object]:
    return closeout_markers.write_closeout_intent(
        root=repo,
        transition=closeout_markers.CloseoutTransition(
            ref_name="refs/heads/dev",
            old_value=old,
            new_value=new,
            candidate_head=new,
        ),
        evidence_digest="digest",
    )


def test_write_persists_marker_bound_to_transition(tmp_path: Path) -> None:
    marker = _write(tmp_path)

    path = _marker_path(tmp_path, str(marker["nonce"]))
    assert path.exists()
    stored = json.loads(path.read_text(encoding="utf-8"))
    assert stored["ref_name"] == "refs/heads/dev"
    assert stored["old_value"] == "old"
    assert stored["new_value"] == "new"
    assert stored["candidate_head"] == "new"
    assert stored["evidence_digest"] == "digest"
    assert stored["schema_version"] == 1


def test_consume_matching_marker_is_one_shot(tmp_path: Path) -> None:
    _write(tmp_path)

    first = closeout_markers.consume_closeout_intent(
        root=tmp_path, ref_name="refs/heads/dev", old_value="old", new_value="new"
    )
    second = closeout_markers.consume_closeout_intent(
        root=tmp_path, ref_name="refs/heads/dev", old_value="old", new_value="new"
    )

    assert first == {"present": True, "gap": ""}
    assert second == {"present": False, "gap": "accepted_ref_move_no_closeout_intent"}


def test_consume_reports_no_intent_when_dir_absent(tmp_path: Path) -> None:
    result = closeout_markers.consume_closeout_intent(
        root=tmp_path, ref_name="refs/heads/dev", old_value="old", new_value="new"
    )

    assert result == {"present": False, "gap": "accepted_ref_move_no_closeout_intent"}


def test_consume_reports_mismatch_on_different_old_new(tmp_path: Path) -> None:
    _write(tmp_path, old="other-old", new="new")

    result = closeout_markers.consume_closeout_intent(
        root=tmp_path, ref_name="refs/heads/dev", old_value="old", new_value="new"
    )

    assert result == {"present": True, "gap": "closeout_intent_mismatch"}


def test_consume_reports_stale_and_deletes_expired_marker(tmp_path: Path) -> None:
    marker = _write(tmp_path)
    _expire(tmp_path, str(marker["nonce"]))

    result = closeout_markers.consume_closeout_intent(
        root=tmp_path, ref_name="refs/heads/dev", old_value="old", new_value="new"
    )

    assert result == {"present": True, "gap": "closeout_intent_stale"}
    assert not _marker_path(tmp_path, str(marker["nonce"])).exists()


def test_consume_skips_unrelated_ref_and_unreadable_markers(tmp_path: Path) -> None:
    # A marker for a different ref must not satisfy this transition.
    closeout_markers.write_closeout_intent(
        root=tmp_path,
        transition=closeout_markers.CloseoutTransition(
            ref_name="refs/heads/release",
            old_value="old",
            new_value="new",
            candidate_head="new",
        ),
        evidence_digest="d",
    )
    # A corrupt file in the marker dir must be skipped, not crash.
    (closeout_markers.closeout_intent_dir(tmp_path) / "bad.json").write_text(
        "{not json", encoding="utf-8"
    )

    result = closeout_markers.consume_closeout_intent(
        root=tmp_path, ref_name="refs/heads/dev", old_value="old", new_value="new"
    )

    assert result == {"present": False, "gap": "accepted_ref_move_no_closeout_intent"}


def test_clear_is_idempotent(tmp_path: Path) -> None:
    marker = _write(tmp_path)
    nonce = str(marker["nonce"])

    closeout_markers.clear_closeout_intent(tmp_path, nonce)
    closeout_markers.clear_closeout_intent(tmp_path, nonce)  # second call is a no-op

    assert not _marker_path(tmp_path, nonce).exists()


def test_sweep_removes_expired_and_corrupt_keeps_live(tmp_path: Path) -> None:
    live = _write(tmp_path, old="live-old", new="live-new")
    expired = _write(tmp_path, old="dead-old", new="dead-new")
    _expire(tmp_path, str(expired["nonce"]))
    (closeout_markers.closeout_intent_dir(tmp_path) / "corrupt.json").write_text(
        "nope", encoding="utf-8"
    )

    swept = closeout_markers.sweep_stale_closeout_intents(tmp_path)

    assert str(expired["nonce"]) in swept
    assert "corrupt" in swept
    assert str(live["nonce"]) not in swept
    assert _marker_path(tmp_path, str(live["nonce"])).exists()


def test_sweep_on_absent_dir_is_empty(tmp_path: Path) -> None:
    assert closeout_markers.sweep_stale_closeout_intents(tmp_path) == []


def test_expired_marker_with_unparseable_timestamp_is_expired(tmp_path: Path) -> None:
    marker = _write(tmp_path)
    path = _marker_path(tmp_path, str(marker["nonce"]))
    stored = json.loads(path.read_text(encoding="utf-8"))
    stored["expires_at"] = "not-a-timestamp"
    path.write_text(json.dumps(stored), encoding="utf-8")

    result = closeout_markers.consume_closeout_intent(
        root=tmp_path, ref_name="refs/heads/dev", old_value="old", new_value="new"
    )

    assert result == {"present": True, "gap": "closeout_intent_stale"}


def test_marker_missing_expires_at_is_treated_as_expired(tmp_path: Path) -> None:
    marker = _write(tmp_path)
    path = _marker_path(tmp_path, str(marker["nonce"]))
    stored = json.loads(path.read_text(encoding="utf-8"))
    del stored["expires_at"]
    path.write_text(json.dumps(stored), encoding="utf-8")

    result = closeout_markers.consume_closeout_intent(
        root=tmp_path, ref_name="refs/heads/dev", old_value="old", new_value="new"
    )

    assert result == {"present": True, "gap": "closeout_intent_stale"}


def test_marker_with_naive_but_parseable_timestamp_is_expired_not_crash(tmp_path: Path) -> None:
    """A parseable-but-tz-naive expires_at must be treated as expired, never raise.

    Regression for the DoS where `now >= fromisoformat("2099-01-01T00:00:00")` compared an
    aware `now` to a naive value and raised an uncaught TypeError — planting one such
    marker used to brick every closeout via sweep. consume and sweep must both survive it.
    """
    marker = _write(tmp_path)
    path = _marker_path(tmp_path, str(marker["nonce"]))
    stored = json.loads(path.read_text(encoding="utf-8"))
    stored["expires_at"] = "2099-01-01T00:00:00"  # far-future but NAIVE (no offset)
    path.write_text(json.dumps(stored), encoding="utf-8")

    result = closeout_markers.consume_closeout_intent(
        root=tmp_path, ref_name="refs/heads/dev", old_value="old", new_value="new"
    )
    assert result == {"present": True, "gap": "closeout_intent_stale"}


def test_sweep_reclaims_naive_timestamp_marker_without_crashing(tmp_path: Path) -> None:
    """sweep_stale_closeout_intents is the FIRST step of official closeout; a planted
    naive-timestamp marker must be reclaimed there, not brick the sweep."""
    marker = _write(tmp_path)
    path = _marker_path(tmp_path, str(marker["nonce"]))
    stored = json.loads(path.read_text(encoding="utf-8"))
    stored["expires_at"] = "2099-01-01T00:00:00"
    path.write_text(json.dumps(stored), encoding="utf-8")

    swept = closeout_markers.sweep_stale_closeout_intents(tmp_path)

    assert str(marker["nonce"]) in swept
    assert not path.exists()


def testcloseout_intent_dir_resolves_inside_real_git_dir(tmp_path: Path) -> None:
    """In a real repo, `git rev-parse --git-path` resolves the marker dir under the git
    dir (the linked-worktree-safe path), not a hardcoded <root>/.git."""
    subprocess.run(["git", "-C", str(tmp_path), "init", "-q"], check=True)
    marker = _write(tmp_path)

    marker_dir = closeout_markers.closeout_intent_dir(tmp_path)
    assert marker_dir.is_dir()
    assert (tmp_path / ".git" / "ethos" / "closeout-intent").resolve() == marker_dir.resolve()
    assert _marker_path(tmp_path, str(marker["nonce"])).exists()


def _expire(repo: Path, nonce: str) -> None:
    path = _marker_path(repo, nonce)
    stored = json.loads(path.read_text(encoding="utf-8"))
    stored["expires_at"] = (datetime.now(UTC) - timedelta(minutes=5)).isoformat()
    path.write_text(json.dumps(stored), encoding="utf-8")


def test_consume_rejects_evidence_digest_mismatch(tmp_path: Path) -> None:
    """A marker whose bound evidence_digest != the expected one is refused (finding A)."""
    _write(tmp_path, old="o", new="n")  # marker carries evidence_digest="digest"
    result = closeout_markers.consume_closeout_intent(
        root=tmp_path,
        ref_name="refs/heads/dev",
        old_value="o",
        new_value="n",
        expect=closeout_markers.MarkerExpectation(evidence_digest="a-different-digest"),
    )
    assert result == {"present": True, "gap": "closeout_intent_evidence_digest_mismatch"}


def test_consume_rejects_gate_policy_digest_mismatch(tmp_path: Path) -> None:
    """A marker whose bound gate_policy_digest != the expected one is refused (finding A)."""
    closeout_markers.write_closeout_intent(
        root=tmp_path,
        transition=closeout_markers.CloseoutTransition(
            ref_name="refs/heads/dev", old_value="o", new_value="n", candidate_head="n"
        ),
        evidence_digest="ed",
        gate_policy_digest="pd",
    )
    result = closeout_markers.consume_closeout_intent(
        root=tmp_path,
        ref_name="refs/heads/dev",
        old_value="o",
        new_value="n",
        expect=closeout_markers.MarkerExpectation(
            evidence_digest="ed", gate_policy_digest="a-different-policy-digest"
        ),
    )
    assert result == {"present": True, "gap": "closeout_intent_policy_digest_mismatch"}
