"""Exact ref-intent transaction and proof-bound effect tests."""

from __future__ import annotations

import hashlib
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from threading import Event
from threading import Thread
from threading import current_thread
from typing import Literal

import pytest

import ethos.adapters.repo.git_effect_attestation
import ethos.adapters.repo.git_effects
from ethos.adapters.admission.ref_intent import claim_ref_intent
from ethos.adapters.admission.ref_intent import clear_ref_intent
from ethos.adapters.admission.ref_intent import committed_ref_intent
from ethos.adapters.admission.ref_intent import ref_intent_dir
from ethos.adapters.admission.ref_intent import sweep_stale_ref_intents
from ethos.adapters.admission.ref_intent import write_ref_intent
from ethos.adapters.repo.git_effects import execute_git_effect
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.plan import compile_git_effect_plan
from ethos.contracts.semantic import Facts
from ethos.contracts.semantic import canonical_json_digest
from tests.support.semantic import attestation_v2
from tests.support.semantic import commitment_v2


def _oid(label: str) -> str:
    return hashlib.sha1(label.encode(), usedforsecurity=False).hexdigest()


def _update(*, old: str = "old", new: str = "new") -> GitRefUpdate:
    return GitRefUpdate(expected=_oid(old), desired=_oid(new))


def _write(
    root: Path,
    *,
    old: str = "old",
    new: str = "new",
    plan_digest: str | None = None,
) -> dict[str, object]:
    return write_ref_intent(
        root=root,
        ref_name="refs/heads/dev",
        update=_update(old=old, new=new),
        operation="candidate.accept",
        plan_digest=plan_digest or hashlib.sha256(b"plan", usedforsecurity=False).hexdigest(),
    )


def _claim(
    root: Path,
    phase: Literal["prepared", "committed", "aborted", "recover"],
    *,
    old: str = "old",
    new: str = "new",
    plan_digest: str | None = None,
) -> dict[str, object]:
    return claim_ref_intent(
        root=root,
        ref_name="refs/heads/dev",
        update=_update(old=old, new=new),
        operation="candidate.accept",
        phase=phase,
        plan_digest=plan_digest,
    )


def _path(root: Path, nonce: object) -> Path:
    return ref_intent_dir(root) / f"{nonce}.json"


def _expire(root: Path, nonce: object, value: str | None = None) -> None:
    path = _path(root, nonce)
    stored = json.loads(path.read_text(encoding="utf-8"))
    if value is None:
        stored.pop("expires_at", None)
    else:
        stored["expires_at"] = value
    path.write_text(json.dumps(stored), encoding="utf-8")


def _proof():
    issued = datetime(2026, 8, 1, tzinfo=UTC)
    policy = {
        "operation": "git.ref.compare-and-swap",
        "effect_digest": GitEffect(updates={"refs/heads/dev": _update()}).digest(),
    }
    return attestation_v2(
        predicate="proof:execution",
        verifier="agent:test:case:ref-effect",
        subject=f"git:commit:{_oid('new')}",
        issued_at=issued,
        valid_from=issued,
        payload_kind="proof:execution",
        payload_body={"head": _oid("new")},
        commitment_digest="a" * 64,
        policy_digest=canonical_json_digest(policy),
    )


def _effect_plan(proof):
    old, new = _oid("old"), _oid("new")
    effect = GitEffect(updates={"refs/heads/dev": GitRefUpdate(expected=old, desired=new)})
    return compile_git_effect_plan(
        commitment_v2(
            id="commitment:test:ref-effect",
            intent="Test one exact proof-bound ref effect.",
            subjects=("repository:test",),
        ),
        Facts(
            repository="repository:test",
            head=old,
            tree=old,
            observed_at=datetime(2026, 8, 1, tzinfo=UTC),
            values={"refs": {"refs/heads/dev": old}, "assertions": {}},
        ),
        prior_attestations={"proof": proof.model_dump(mode="json")},
        policy={
            "operation": "git.ref.compare-and-swap",
            "effect_digest": effect.digest(),
        },
        effect=effect,
    )


def test_intent_persists_only_exact_operation_transition_and_recovery(tmp_path: Path) -> None:
    intent = _write(tmp_path)

    stored = json.loads(_path(tmp_path, intent["nonce"]).read_text(encoding="utf-8"))

    assert stored | {"created_at": "", "expires_at": "", "nonce": ""} == {
        "schema_version": 2,
        "operation": "candidate.accept",
        "ref_name": "refs/heads/dev",
        "old_value": _oid("old"),
        "new_value": _oid("new"),
        "plan_digest": hashlib.sha256(b"plan", usedforsecurity=False).hexdigest(),
        "nonce": "",
        "phase": "issued",
        "created_at": "",
        "expires_at": "",
    }


def test_identical_intent_write_reuses_one_file(tmp_path: Path) -> None:
    first, second = _write(tmp_path), _write(tmp_path)

    assert first == second
    assert [path.name for path in ref_intent_dir(tmp_path).glob("*.json")] == [
        f"{first['nonce']}.json"
    ]


def test_concurrent_identical_intent_write_converges_to_one_file(tmp_path: Path) -> None:
    with ThreadPoolExecutor(max_workers=8) as executor:
        intents = list(executor.map(lambda _index: _write(tmp_path), range(32)))

    assert len({str(intent["nonce"]) for intent in intents}) == 1
    assert len(list(ref_intent_dir(tmp_path).glob("*.json"))) == 1


def test_malformed_deterministic_intent_is_reclaimed_on_write(tmp_path: Path) -> None:
    intent = _write(tmp_path)
    path = _path(tmp_path, intent["nonce"])
    path.write_text("{", encoding="utf-8")

    rewritten = _write(tmp_path)

    assert rewritten["nonce"] == intent["nonce"]
    assert json.loads(path.read_text(encoding="utf-8"))["phase"] == "issued"


def test_committed_intent_supports_exact_crash_recovery(tmp_path: Path) -> None:
    intent = _write(tmp_path)

    assert _claim(tmp_path, "prepared")["gap"] == ""
    assert _claim(tmp_path, "committed")["gap"] == ""
    assert json.loads(_path(tmp_path, intent["nonce"]).read_text())["phase"] == "committed"
    assert _claim(tmp_path, "recover")["gap"] == ""

    clear_ref_intent(tmp_path, str(intent["nonce"]))
    assert not _path(tmp_path, intent["nonce"]).exists()


def test_committed_intent_carries_the_exact_plan_digest(tmp_path: Path) -> None:
    plan_digest = hashlib.sha256(b"candidate-plan", usedforsecurity=False).hexdigest()
    _write(tmp_path, plan_digest=plan_digest)
    assert _claim(tmp_path, "prepared", plan_digest=plan_digest)["gap"] == ""
    assert _claim(tmp_path, "committed", plan_digest=plan_digest)["gap"] == ""

    recovered = committed_ref_intent(
        root=tmp_path,
        ref_name="refs/heads/dev",
        operation="candidate.accept",
        desired=_oid("new"),
    )

    assert recovered["gap"] == ""
    assert recovered["plan_digest"] == plan_digest
    assert recovered["old_value"] == _oid("old")


def test_expired_prepared_intent_recovers_after_observed_git_cas(
    tmp_path: Path,
) -> None:
    intent = _write(tmp_path)
    assert _claim(tmp_path, "prepared")["gap"] == ""
    _expire(
        tmp_path,
        intent["nonce"],
        (datetime.now(UTC) - timedelta(minutes=1)).isoformat(),
    )

    assert _claim(tmp_path, "recover")["gap"] == ""
    assert json.loads(_path(tmp_path, intent["nonce"]).read_text())["phase"] == "committed"


def test_concurrent_committed_and_aborted_callbacks_preserve_committed_recovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    intent = _write(tmp_path)
    assert _claim(tmp_path, "prepared")["gap"] == ""
    aborted_read, committed = Event(), Event()
    intent_path = _path(tmp_path, intent["nonce"])
    read_text = Path.read_text
    delayed = False

    def delayed_read(path: Path, *args, **kwargs):
        nonlocal delayed
        value = read_text(path, *args, **kwargs)
        if path == intent_path and current_thread().name == "intent-aborted" and not delayed:
            delayed = True
            aborted_read.set()
            assert committed.wait(timeout=5)
        return value

    results = {}
    monkeypatch.setattr(Path, "read_text", delayed_read)
    threads = (
        Thread(
            target=lambda: results.__setitem__("aborted", _claim(tmp_path, "aborted")),
            name="intent-aborted",
        ),
        Thread(
            target=lambda: (
                aborted_read.wait(timeout=5),
                results.__setitem__("committed", _claim(tmp_path, "committed")),
                committed.set(),
            ),
            name="intent-committed",
        ),
    )
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)

    assert results["committed"]["gap"] == ""
    assert results["aborted"]["gap"] == ""
    assert json.loads(_path(tmp_path, intent["nonce"]).read_text())["phase"] == "committed"


def test_aborted_intent_cleans_only_the_exact_prepared_transaction(tmp_path: Path) -> None:
    intent = _write(tmp_path)
    other = _write(tmp_path, old="other-old", new="other-new")
    assert _claim(tmp_path, "prepared")["gap"] == ""

    assert _claim(tmp_path, "aborted")["gap"] == ""

    assert not _path(tmp_path, intent["nonce"]).exists()
    assert _path(tmp_path, other["nonce"]).exists()


def test_intent_reports_absence_transition_and_operation_mismatch(tmp_path: Path) -> None:
    assert _claim(tmp_path, "prepared")["gap"] == "ref_intent_missing"
    _write(tmp_path, old="other-old")
    assert _claim(tmp_path, "prepared")["gap"] == "ref_intent_mismatch"

    root = tmp_path / "operation"
    root.mkdir()
    write_ref_intent(
        root=root,
        ref_name="refs/heads/dev",
        update=_update(),
        operation="candidate.refresh",
        plan_digest=hashlib.sha256(b"other-plan", usedforsecurity=False).hexdigest(),
    )
    assert _claim(root, "prepared")["gap"] == "ref_intent_operation_mismatch"
    plan_root = tmp_path / "plan"
    plan_root.mkdir()
    _write(plan_root)
    assert (
        _claim(
            plan_root,
            "prepared",
            plan_digest=hashlib.sha256(b"other-plan", usedforsecurity=False).hexdigest(),
        )["gap"]
        == "ref_intent_plan_mismatch"
    )


@pytest.mark.parametrize("expires_at", [None, "not-a-timestamp", "2099-01-01T00:00:00"])
def test_invalid_expiry_is_stale_and_removed(tmp_path: Path, expires_at: str | None) -> None:
    intent = _write(tmp_path)
    _expire(tmp_path, intent["nonce"], expires_at)

    assert _claim(tmp_path, "prepared")["gap"] == "ref_intent_payload_invalid"
    assert not _path(tmp_path, intent["nonce"]).exists()


def test_sweep_removes_expired_and_malformed_but_keeps_live(tmp_path: Path) -> None:
    live = _write(tmp_path, old="live-old", new="live-new")
    expired = _write(tmp_path, old="dead-old", new="dead-new")
    _expire(
        tmp_path,
        expired["nonce"],
        (datetime.now(UTC) - timedelta(minutes=5)).isoformat(),
    )
    (ref_intent_dir(tmp_path) / "malformed.json").write_text("nope", encoding="utf-8")

    swept = sweep_stale_ref_intents(tmp_path)

    assert set(swept) == {str(expired["nonce"]), "malformed"}
    assert _path(tmp_path, live["nonce"]).exists()


def test_intent_path_is_linked_worktree_safe(tmp_path: Path) -> None:
    subprocess.run(["git", "-C", str(tmp_path), "init", "-q"], check=True)
    _write(tmp_path)

    assert (
        ref_intent_dir(tmp_path).resolve() == (tmp_path / ".git" / "ethos" / "ref-intent").resolve()
    )


def test_git_effect_does_not_reread_proof_store_before_intent_or_cas(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        ethos.adapters.repo.git_effect_attestation,
        "records",
        lambda *_args, **_kwargs: (),
    )
    monkeypatch.setattr(
        ethos.adapters.repo.git_effects,
        "current_tracked_head",
        lambda _root: _oid("stale"),
    )

    with pytest.raises(ValueError, match="git_effect_plan_prestate_stale"):
        execute_git_effect(tmp_path, _effect_plan(_proof()), issuer="agent:test:case:ref-effect")

    assert not ref_intent_dir(tmp_path).exists()
