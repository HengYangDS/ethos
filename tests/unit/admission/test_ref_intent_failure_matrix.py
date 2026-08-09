from __future__ import annotations

import hashlib
import json
from datetime import UTC
from datetime import datetime
from datetime import timedelta

import pytest

import ethos.adapters.admission.ref_intent as intent
from ethos.contracts.plan import GitRefUpdate


def _oid(label: str) -> str:
    return hashlib.sha1(label.encode(), usedforsecurity=False).hexdigest()


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode(), usedforsecurity=False).hexdigest()


def _update(old: str = "old", new: str = "new") -> GitRefUpdate:
    return GitRefUpdate(expected=_oid(old), desired=_oid(new))


def _write(root, *, operation="candidate.accept", plan="plan", old="old", new="new"):
    return intent.write_ref_intent(
        root=root,
        ref_name="refs/heads/dev",
        update=_update(old, new),
        operation=operation,
        plan_digest=_digest(plan),
    )


def _claim(root, *, operation="candidate.accept", plan="plan", old="old", new="new"):
    return intent.claim_ref_intent(
        root=root,
        ref_name="refs/heads/dev",
        update=_update(old, new),
        operation=operation,
        phase="prepared",
        plan_digest=_digest(plan),
    )


def test_ref_intent_dir_falls_back_to_repository_git_path(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(intent, "git_stdout", lambda *_args: "")
    assert intent.ref_intent_dir(tmp_path) == tmp_path / ".git/ethos/ref-intent"


def test_ref_intent_lock_timeout_preserves_existing_lock(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(intent, "_LOCK_ATTEMPTS", 1)
    monkeypatch.setattr(intent, "ref_intent_dir", lambda _root: tmp_path)

    def locked(*_args, **_kwargs):
        raise FileExistsError

    monkeypatch.setattr(intent.os, "open", locked)
    with pytest.raises(ValueError, match=r"^ref_intent_lock_timeout$"):
        _write(tmp_path)
    assert not list(tmp_path.glob("*.json"))


@pytest.mark.parametrize(
    ("overrides", "gap"),
    [
        ({"old": "other"}, "ref_intent_mismatch"),
        ({"operation": "candidate.refresh"}, "ref_intent_operation_mismatch"),
        ({"plan": "other"}, "ref_intent_plan_mismatch"),
    ],
)
def test_ref_intent_claim_rejects_identity_drift(
    tmp_path, overrides: dict[str, str], gap: str
) -> None:
    _write(tmp_path)
    report = _claim(tmp_path, **overrides)
    assert report["present"] is True
    assert report["gap"] == gap


def test_ref_intent_claim_rejects_duplicate_exact_intents(tmp_path) -> None:
    written = _write(tmp_path)
    directory = intent.ref_intent_dir(tmp_path)
    source = directory / f"{written['nonce']}.json"
    (directory / f"{'f' * 64}.json").write_bytes(source.read_bytes())

    report = _claim(tmp_path)

    assert report["present"] is True
    assert report["gap"] == "ref_intent_ambiguous"


def test_expired_issued_intent_is_reclaimed_before_prepare(tmp_path) -> None:
    written = _write(tmp_path)
    path = intent.ref_intent_dir(tmp_path) / f"{written['nonce']}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["expires_at"] = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()
    path.write_text(json.dumps(payload), encoding="utf-8")

    report = _claim(tmp_path)

    assert report["gap"] == "ref_intent_stale"
    assert not path.exists()


def test_committed_ref_intent_rejects_ambiguous_committed_receipts(tmp_path) -> None:
    first = _write(tmp_path, old="one")
    second = _write(tmp_path, old="two")
    for _written, old in ((first, "one"), (second, "two")):
        update = _update(old, "new")
        for phase in ("prepared", "committed"):
            report = intent.claim_ref_intent(
                root=tmp_path,
                ref_name="refs/heads/dev",
                update=update,
                operation="candidate.accept",
                phase=phase,
                plan_digest=_digest("plan"),
            )
            assert report["gap"] == ""

    report = intent.committed_ref_intent(
        root=tmp_path,
        operation="candidate.accept",
        desired=_oid("new"),
    )
    assert report["present"] is True
    assert report["gap"] == "ref_intent_ambiguous"


def test_sweep_removes_malformed_and_expired_issued_but_preserves_prepared(tmp_path) -> None:
    expired = _write(tmp_path, old="expired")
    prepared = _write(tmp_path, old="prepared")
    prepared_update = _update("prepared", "new")
    assert (
        intent.claim_ref_intent(
            root=tmp_path,
            ref_name="refs/heads/dev",
            update=prepared_update,
            operation="candidate.accept",
            phase="prepared",
            plan_digest=_digest("plan"),
        )["gap"]
        == ""
    )
    malformed = intent.ref_intent_dir(tmp_path) / f"{'e' * 64}.json"
    malformed.write_text("{", encoding="utf-8")

    swept = intent.sweep_stale_ref_intents(
        tmp_path,
        now=datetime.now(UTC) + timedelta(minutes=2),
    )

    assert set(swept) == {malformed.stem, str(expired["nonce"])}
    assert (intent.ref_intent_dir(tmp_path) / f"{prepared['nonce']}.json").exists()
