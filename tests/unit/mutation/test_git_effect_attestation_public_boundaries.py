from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import ethos.adapters.repo.attestation_set as attestation_set
import ethos.adapters.repo.git_effect_attestation as attest
import ethos.adapters.repo.git_effect_observation as observation
from ethos.adapters.repo.attestation_set import record_attestations
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.plan import compile_git_effect_plan
from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import Facts
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.semantic import commitment_v2

ISSUER = "agent:test:attestation"


def _case(tmp_path: Path) -> tuple[Path, GitEffect, Any, dict[str, object], dict[str, object]]:
    repo = init_git_repo(tmp_path / "repo")
    old = git(repo, "rev-parse", "HEAD")
    new = git(repo, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    effect = GitEffect(
        updates={"refs/heads/dev": GitRefUpdate(expected=old, desired=new)},
        assertions={},
    )
    observed = datetime.now(UTC) - timedelta(seconds=2)
    facts = Facts(
        repository="repository:repo",
        head=old,
        tree=git(repo, "rev-parse", "HEAD^{tree}"),
        observed_at=observed,
        values={"refs": {"refs/heads/dev": old}, "assertions": {}},
    )
    plan = compile_git_effect_plan(
        commitment_v2(
            id="authority:test:attestation",
            intent="Exercise attestation boundaries.",
            subjects=("repository:repo",),
        ),
        facts,
        prior_attestations={},
        policy={"operation": "git.ref.compare-and-swap", "effect_digest": effect.digest()},
        effect=effect,
    )
    before = {
        "head": old,
        "tree": facts.tree,
        "refs": {"refs/heads/dev": old},
        "assertions": {},
        "observed_at": observed.isoformat(),
    }
    after = {
        "head": new,
        "tree": facts.tree,
        "refs": {"refs/heads/dev": new},
        "observed_at": (observed + timedelta(seconds=1)).isoformat(),
    }
    return repo, effect, plan, before, after


def _issued_record(tmp_path: Path) -> tuple[Path, GitEffect, Any, Attestation]:
    repo, effect, plan, before, after = _case(tmp_path)
    record = attest.issue(
        effect,
        plan=plan,
        issuer=ISSUER,
        evidence=("repository:repo", "applied", before, after),
    )
    return repo, effect, plan, record


def _reissue(record: Attestation, **updates: object) -> Attestation:
    payload = record.model_dump(mode="python", exclude={"id"}) | updates
    return Attestation.issue(payload)


def test_git_effect_observation_uses_canonical_utc_time(tmp_path: Path) -> None:
    repo, effect, _plan, _before, _after = _case(tmp_path)

    observed = observation.observe_git_effect(repo, effect)

    assert str(observed["observed_at"]).endswith("Z")


def test_git_effect_attestation_uses_canonical_utc_time(tmp_path: Path) -> None:
    _repo, _effect, _plan, record = _issued_record(tmp_path)

    observed_at = record.payload.body["observed_at"]

    assert isinstance(observed_at, Mapping)
    assert str(observed_at["before"]).endswith("Z")
    assert str(observed_at["after"]).endswith("Z")


@pytest.mark.parametrize("statement", [(), "not-an-object", ["not", "an", "object"]])
def test_statement_projection_rejects_non_object_claims(statement: object) -> None:
    record = Attestation.model_construct(payload=SimpleNamespace(body=statement))
    with pytest.raises(TypeError, match="git_effect_attestation_statement_invalid"):
        attest.plan_from_attestation(record)


@pytest.mark.parametrize(
    ("gap", "expected"),
    [
        ("ref_intent_missing", None),
        ("ref_intent_ambiguous", "git_effect_recovery_ambiguous"),
        ("ref_intent_corrupt", "git_effect_recovery_unproven"),
    ],
)
def test_recover_plan_classifies_missing_ambiguous_and_unproven_intents(
    monkeypatch: pytest.MonkeyPatch,
    gap: str,
    expected: str | None,
) -> None:
    monkeypatch.setattr(
        attest,
        "committed_ref_intent",
        lambda **_kwargs: {"gap": gap},
    )

    if expected is None:
        assert attest.recover_plan(Path("/repo"), operation="lane.retire", desired="a" * 40) is None
    else:
        with pytest.raises(ValueError, match=expected):
            attest.recover_plan(Path("/repo"), operation="lane.retire", desired="a" * 40)


def test_recover_plan_rejects_missing_or_mismatched_attested_effect(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, effect, plan, _ = _issued_record(tmp_path)
    update = effect.updates["refs/heads/dev"]
    monkeypatch.setattr(
        attest,
        "committed_ref_intent",
        lambda **_kwargs: {
            "gap": "",
            "plan_digest": plan.digest,
            "ref_name": "refs/heads/dev",
            "old_value": update.expected,
        },
    )

    with pytest.raises(ValueError, match="git_effect_recovery_unproven"):
        attest.recover_plan(repo, operation="test.attestation", desired=update.desired)


def test_plan_from_attestation_rejects_missing_carried_plan(tmp_path: Path) -> None:
    _repo, _effect, _plan, record = _issued_record(tmp_path)
    payload = record.model_dump(mode="python", exclude={"id"})
    payload["payload"] = {
        "kind": record.payload.kind,
        "body": {"claim": {"operation": "git.ref.compare-and-swap"}},
    }
    invalid = Attestation.issue(payload)

    with pytest.raises(ValueError, match="git_effect_attestation_plan_invalid"):
        attest.plan_from_attestation(invalid)


def test_plan_from_attestation_only_parses_carried_plan(tmp_path: Path) -> None:
    _repo, _effect, plan, record = _issued_record(tmp_path)

    assert attest.plan_from_attestation(_tamper(record, "verifier")) == plan


def _tamper(record: Attestation, tamper: str) -> Attestation:
    updates: dict[str, object] = {}
    if tamper in {"kind", "time"}:
        body = dict(record.payload.body)
        if tamper == "time":
            observed_at = dict(body["observed_at"])
            observed_at["after"] = str(observed_at["after"]).replace("Z", "+00:00")
            body["observed_at"] = observed_at
        updates["payload"] = {
            "kind": "effect:other" if tamper == "kind" else record.payload.kind,
            "body": body,
        }
    elif tamper == "predicate":
        updates["predicate"] = "effect:other"
    elif tamper == "verifier":
        updates["verifier"] = "agent:test:attestation:other"
    else:
        updates["valid_until"] = record.issued_at
    return _reissue(record, **updates)


@pytest.mark.parametrize(
    ("tamper", "error"),
    [
        ("kind", "git_effect_attestation_content_mismatch"),
        ("predicate", "git_effect_identity_collision"),
        ("verifier", "git_effect_attestation_content_mismatch"),
        ("validity", "git_effect_attestation_stale"),
        ("time", "git_effect_attestation_content_mismatch"),
    ],
)
def test_validate_rejects_noncanonical_envelope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    tamper: str,
    error: str,
) -> None:
    repo, effect, plan, record = _issued_record(tmp_path)
    update = effect.updates["refs/heads/dev"]
    git(repo, "update-ref", "refs/heads/dev", update.desired, update.expected)
    monkeypatch.setattr(
        attest,
        "resolve_git_effect_repository",
        lambda *_args, **_kwargs: "repository:repo",
    )
    monkeypatch.setattr(attest, "_matches", lambda *_args, **_kwargs: True)

    with pytest.raises(ValueError, match=error):
        attest.validate(
            repo,
            effect,
            _tamper(record, tamper),
            issuer=ISSUER,
            plan=plan,
        )


def test_recover_plan_ignores_legacy_plan_receipt_when_attestation_set_has_no_member(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, effect, plan, record = _issued_record(tmp_path)
    update = effect.updates["refs/heads/dev"]
    git(repo, "update-ref", "refs/heads/dev", update.desired, update.expected)
    path = Path(
        repo,
        git(repo, "rev-parse", "--git-common-dir"),
        "ethos",
        "git-effects",
        f"{plan.digest}.json",
    )
    path.parent.mkdir(parents=True)
    path.write_text(record.canonical_json(), encoding="utf-8")
    monkeypatch.setattr(
        attest,
        "committed_ref_intent",
        lambda **_kwargs: {
            "gap": "",
            "plan_digest": plan.digest,
            "ref_name": "refs/heads/dev",
            "old_value": update.expected,
        },
    )

    with pytest.raises(ValueError, match="git_effect_recovery_unproven"):
        attest.recover_plan(
            repo,
            operation="git.ref.compare-and-swap",
            desired=update.desired,
        )


def test_recover_plan_uses_attestation_verifier(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, effect, plan, record = _issued_record(tmp_path)
    update = effect.updates["refs/heads/dev"]
    git(repo, "update-ref", "refs/heads/dev", update.desired, update.expected)
    record_attestations(repo, (record,))
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:unrelated-process")
    monkeypatch.setattr(
        attest,
        "resolve_git_effect_repository",
        lambda *_args, **_kwargs: "repository:repo",
    )
    monkeypatch.setattr(attest, "_matches", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        attest,
        "committed_ref_intent",
        lambda **_kwargs: {
            "gap": "",
            "plan_digest": plan.digest,
            "ref_name": "refs/heads/dev",
            "old_value": update.expected,
        },
    )

    assert (
        attest.recover_plan(
            repo,
            operation="git.ref.compare-and-swap",
            desired=update.desired,
        )
        == plan
    )


def test_recover_plan_accepts_matching_attestation_set_member(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, effect, plan, record = _issued_record(tmp_path)
    update = effect.updates["refs/heads/dev"]
    git(repo, "update-ref", "refs/heads/dev", update.desired, update.expected)
    record_attestations(repo, (record,))
    monkeypatch.setattr(
        attest,
        "resolve_git_effect_repository",
        lambda *_args, **_kwargs: "repository:repo",
    )
    monkeypatch.setattr(attest, "_matches", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        attest,
        "committed_ref_intent",
        lambda **_kwargs: {
            "gap": "",
            "plan_digest": plan.digest,
            "ref_name": "refs/heads/dev",
            "old_value": update.expected,
        },
    )

    assert (
        attest.recover_plan(
            repo,
            operation="git.ref.compare-and-swap",
            desired=update.desired,
        )
        == plan
    )


def test_recover_plan_rejects_attestation_set_member_collision(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, effect, plan, record = _issued_record(tmp_path)
    update = effect.updates["refs/heads/dev"]
    git(repo, "update-ref", "refs/heads/dev", update.desired, update.expected)
    record_attestations(
        repo,
        (record, _reissue(record, verifier="agent:test:other", subject="git-effect:other")),
    )
    monkeypatch.setattr(
        attest,
        "resolve_git_effect_repository",
        lambda *_args, **_kwargs: "repository:repo",
    )
    monkeypatch.setattr(attest, "_matches", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        attest,
        "committed_ref_intent",
        lambda **_kwargs: {
            "gap": "",
            "plan_digest": plan.digest,
            "ref_name": "refs/heads/dev",
            "old_value": update.expected,
        },
    )

    with pytest.raises(ValueError, match="git_effect_recovery_unproven"):
        attest.recover_plan(
            repo,
            operation="git.ref.compare-and-swap",
            desired=update.desired,
        )


def test_records_rejects_corrupt_existing_receipt(tmp_path: Path) -> None:
    repo, _effect, plan, record = _issued_record(tmp_path)
    record_attestations(repo, (record,))
    root = git(repo, "show-ref", "--verify", "--hash", attestation_set.ATTESTATION_SET_REF)
    git(
        repo,
        "update-ref",
        attestation_set.ATTESTATION_SET_REF,
        git(repo, "rev-parse", "HEAD"),
        root,
    )

    with pytest.raises(ValueError, match="git_effect_attestation_invalid"):
        attest.records(repo, plan)


def test_issue_rejects_invalid_observation_time(tmp_path: Path) -> None:
    _repo, effect, plan, before, after = _case(tmp_path)
    before["observed_at"] = "invalid"

    with pytest.raises(ValueError, match="git_effect_attestation_content_mismatch"):
        attest.issue(
            effect,
            plan=plan,
            issuer=ISSUER,
            evidence=("repository:repo", "applied", before, after),
        )


@pytest.mark.parametrize("failure", ["time-order", "repository"])
def test_matches_rejects_temporal_and_repository_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    repo, effect, plan, before, after = _case(tmp_path)
    if failure == "time-order":
        before["observed_at"], after["observed_at"] = (
            after["observed_at"],
            before["observed_at"],
        )
    record = attest.issue(
        effect,
        plan=plan,
        issuer=ISSUER,
        evidence=("repository:repo", "applied", before, after),
    )
    resolutions = iter(("repository:repo",))
    if failure == "repository":
        resolutions = iter(("repository:repo", ValueError("drift")))

    def resolve(*_args: object, **_kwargs: object) -> str:
        result = next(resolutions)
        if isinstance(result, ValueError):
            raise result
        return result

    monkeypatch.setattr(attest, "resolve_git_effect_repository", resolve)

    with pytest.raises(ValueError, match="git_effect_attestation_content_mismatch"):
        attest.validate(repo, effect, record, issuer=ISSUER, plan=plan)
