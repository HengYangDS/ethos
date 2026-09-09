from __future__ import annotations

import errno
import hashlib
import json
import multiprocessing
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.admission.ref_intent as intent
from ethos.contracts.plan import GitRefUpdate

if TYPE_CHECKING:
    from multiprocessing.synchronize import Event


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


def _claim(
    root, *, operation="candidate.accept", plan="plan", old="old", new="new", phase="prepared"
):
    return intent.claim_ref_intent(
        root=root,
        ref_name="refs/heads/dev",
        update=_update(old, new),
        operation=operation,
        phase=phase,
        plan_digest=_digest(plan),
    )


def _committed(root):
    return intent.committed_ref_intent(root=root, operation="candidate.accept", desired=_oid("new"))


def test_ref_intent_dir_falls_back_to_repository_git_path(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(intent, "git_stdout", lambda *_args: "")
    assert intent.ref_intent_dir(tmp_path) == tmp_path / ".git/ethos/ref-intent"


def test_ref_intent_refuses_unsupported_native_lock(tmp_path, monkeypatch) -> None:
    native = pytest.importorskip("fcntl")

    def unsupported(*_args):
        raise OSError(errno.ENOSYS, "native locking unavailable")

    monkeypatch.setattr(native, "flock", unsupported)
    with pytest.raises(OSError, match="native locking unavailable") as failure:
        _write(tmp_path)
    assert failure.value.errno == errno.ENOSYS
    assert not list(intent.ref_intent_dir(tmp_path).glob("*.json"))


def _hold_ref_intent(root: Path, ready: Event, release: Event) -> None:
    replace = Path.replace

    def pause(path: Path, target: str | Path) -> Path:
        result = replace(path, target)
        ready.set()
        release.wait(30)
        return result

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(Path, "replace", pause)
        _write(root)


@pytest.mark.parametrize("termination", ["release", "kill"])
@pytest.mark.parametrize("contender", ["write", "claim", "sweep", "clear"])
def test_ref_intent_protects_live_owner_and_recovers_after_exit(
    tmp_path: Path, termination: str, contender: str
) -> None:
    context = multiprocessing.get_context("spawn")
    ready, release = context.Event(), context.Event()
    owner = context.Process(target=_hold_ref_intent, args=(tmp_path, ready, release))
    owner.start()
    try:
        assert ready.wait(10), "intent writer did not become ready"
        path = next(intent.ref_intent_dir(tmp_path).glob("*.json"))
        before = path.read_bytes()
        action = {
            "write": lambda: _write(tmp_path),
            "claim": lambda: _claim(tmp_path),
            "sweep": lambda: intent.sweep_stale_ref_intents(
                tmp_path, now=datetime.now(UTC) + timedelta(minutes=2)
            ),
            "clear": lambda: intent.clear_ref_intent(tmp_path, path.stem),
        }[contender]
        with pytest.raises(ValueError, match=r"^ref_intent_lock_timeout$"):
            action()
        assert owner.is_alive()
        assert path.read_bytes() == before, "contender changed the active transaction"
    finally:
        if termination == "release":
            release.set()
            owner.join(timeout=10)
        if owner.is_alive():
            owner.kill()
            owner.join(timeout=10)
        assert not owner.is_alive()
        owner.close()
    report = _claim(tmp_path)
    assert not report["gap"], report
    assert report["phase"] == "prepared"
    assert path.exists(), "recovery discarded the transaction"
    intent.clear_ref_intent(tmp_path, path.stem)
    intent.clear_ref_intent(tmp_path, path.stem)
    assert not path.exists()


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


@pytest.mark.parametrize("phase", ["issued", "committed"])
def test_ref_intent_claim_rejects_duplicate_exact_intents(tmp_path, phase) -> None:
    written = _write(tmp_path)
    if phase == "committed":
        assert _claim(tmp_path)["gap"] == ""
        assert _claim(tmp_path, phase=phase)["gap"] == ""
    directory = intent.ref_intent_dir(tmp_path)
    source = directory / f"{written['nonce']}.json"
    (directory / f"{'f' * 64}.json").write_bytes(source.read_bytes())

    report = _claim(tmp_path) if phase == "issued" else _committed(tmp_path)

    assert report["present"] is True
    assert report["gap"] == "ref_intent_ambiguous"


def test_write_preserves_valid_foreign_record_at_requested_path(tmp_path) -> None:
    requested, foreign = _write(tmp_path), _write(tmp_path, operation="candidate.refresh")
    path = intent.ref_intent_dir(tmp_path) / f"{requested['nonce']}.json"
    stored = json.dumps(foreign)
    path.write_text(stored, encoding="utf-8")
    with pytest.raises(ValueError, match=r"^ref_intent_collision$"):
        _write(tmp_path)
    assert path.read_text(encoding="utf-8") == stored


@pytest.mark.parametrize(
    ("initial", "concurrent_state", "reader", "gap"),
    [
        ("expired", "unchanged", "claim", "ref_intent_stale"),
        ("expired", "renewed", "claim", "ref_intent_changed"),
        ("expired", "prepared", "claim", "ref_intent_changed"),
        ("expired", "committed", "claim", "ref_intent_changed"),
        ("issued", "missing", "claim", "ref_intent_missing"),
        ("issued", "replaced", "claim", "ref_intent_changed"),
        ("invalid", "issued", "claim", "ref_intent_payload_invalid"),
        ("invalid", "issued", "lookup", "ref_intent_missing"),
    ],
)
def test_intent_observation_rechecks_current_storage_before_effect(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    initial: str,
    concurrent_state: str,
    reader: str,
    gap: str,
) -> None:
    written = _write(tmp_path)
    path = intent.ref_intent_dir(tmp_path) / f"{written['nonce']}.json"
    payload = written | {"expires_at": (datetime.now(UTC) - timedelta(seconds=1)).isoformat()}
    path.write_text(
        "{" if initial == "invalid" else json.dumps(payload if initial == "expired" else written),
        encoding="utf-8",
    )
    replacement = (payload if initial == "expired" else written) | {"phase": concurrent_state}
    if concurrent_state == "renewed":
        replacement = written
    if concurrent_state == "replaced":
        (tmp_path / "other").mkdir()
        replacement = _write(tmp_path / "other", operation="candidate.refresh")
    read_text = Path.read_text
    changed = False

    def change_after_observation(
        observed: Path, encoding: str | None = None, errors: str | None = None
    ) -> str:
        nonlocal changed
        text = read_text(observed, encoding=encoding, errors=errors)
        if observed == path and not changed and concurrent_state != "unchanged":
            changed = True
            if concurrent_state == "missing":
                path.unlink()
            else:
                path.write_text(json.dumps(replacement), encoding="utf-8")
        return text

    monkeypatch.setattr(Path, "read_text", change_after_observation)

    report = _claim(tmp_path) if reader == "claim" else _committed(tmp_path)

    assert path.exists() is (concurrent_state not in {"unchanged", "missing"})
    if path.exists():
        assert json.loads(path.read_text(encoding="utf-8")) == replacement
        if initial == "expired":
            assert report["phase"] == replacement["phase"]
    assert report["gap"] == gap
    if concurrent_state == "missing":
        assert report["present"] is False


def test_committed_ref_intent_rejects_ambiguous_committed_receipts(tmp_path) -> None:
    for old in ("one", "two"):
        _write(tmp_path, old=old)
        for phase in ("prepared", "committed"):
            assert _claim(tmp_path, old=old, phase=phase)["gap"] == ""

    report = _committed(tmp_path)
    assert report["present"] is True
    assert report["gap"] == "ref_intent_ambiguous"


def test_sweep_removes_malformed_and_expired_issued_but_preserves_prepared(tmp_path) -> None:
    expired = _write(tmp_path, old="expired")
    prepared = _write(tmp_path, old="prepared")
    assert _claim(tmp_path, old="prepared")["gap"] == ""
    malformed = intent.ref_intent_dir(tmp_path) / f"{'e' * 64}.json"
    malformed.write_text("{", encoding="utf-8")

    swept = intent.sweep_stale_ref_intents(
        tmp_path,
        now=datetime.now(UTC) + timedelta(minutes=2),
    )

    assert set(swept) == {malformed.stem, str(expired["nonce"])}
    assert {path.name for path in intent.ref_intent_dir(tmp_path).iterdir()} == {
        ".lock",
        f"{prepared['nonce']}.json",
    }, "coordination files grow with transaction history"


@pytest.mark.parametrize(
    "overrides", [{"nonce": "f" * 64}, {"operation": "candidate.refresh"}, {"phase": "unexpected"}]
)
@pytest.mark.parametrize("reader", ["prepared", "aborted", "lookup"])
def test_invalid_intent_rejected_and_uncommitted_lookup_ignored(
    tmp_path, overrides, reader
) -> None:
    written = _write(tmp_path)
    path = intent.ref_intent_dir(tmp_path) / f"{written['nonce']}.json"
    assert _committed(tmp_path)["gap"] == "ref_intent_missing"
    path.write_text(json.dumps(written | overrides), encoding="utf-8")
    report = _committed(tmp_path) if reader == "lookup" else _claim(tmp_path, phase=reader)
    assert report["gap"] == (
        "ref_intent_missing" if reader == "lookup" else "ref_intent_payload_invalid"
    )
    assert not path.exists()
