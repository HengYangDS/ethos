"""Execute exact Git effects with admission, attestation and recoverable compensation."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING
from typing import Any

import pytest

import ethos.adapters.repo.git_effect_admission as admission
import ethos.adapters.repo.git_effect_attestation as attest
import ethos.adapters.repo.git_effects as runtime
from ethos.adapters.admission.ref_intent import claim_ref_intent
from ethos.adapters.admission.ref_intent import ref_intent_dir
from ethos.adapters.admission.ref_intent import write_ref_intent
from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git_effect_observation import resolve_git_effect_repository
from ethos.adapters.repo.git_effects import admit_git_effect
from ethos.adapters.repo.git_effects import execute_git_effect
from ethos.adapters.repo.status.bindings import lease_generation
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.value import mutable_json
from tests.support.git_effect import effect
from tests.support.git_effect import fixture
from tests.support.git_effect import generation
from tests.support.git_effect import plan
from tests.support.git_effect import proof_plan
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.semantic import Attestation

ISSUER = "agent:test:case:one"


ZERO_OID, ZERO_DIGEST = "0" * 40, "0" * 64


def reject(error: str, call: Any) -> None:
    with pytest.raises((OSError, ValueError), match=error):
        call()


def test_exact_multiref_cas_attestation_recognition_and_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = fixture(tmp_path)
    git(case.repo, "branch", "candidate/dev", case.old)
    value = GitEffect(
        updates={
            ref: GitRefUpdate(expected=case.old, desired=case.new)
            for ref in ("refs/heads/candidate/dev", "refs/heads/dev")
        }
    )
    persisted: list[Attestation] = []
    programs: list[tuple[object, object]] = []
    original = runtime.run_git

    def capture(root: Path, *args: str, **kwargs: object) -> object:
        if args == ("update-ref", "--stdin", "-z"):
            programs.append((kwargs.get("stdin"), kwargs.get("text", True)))
        return original(root, *args, **kwargs)

    monkeypatch.setattr(runtime, "run_git", capture)
    monkeypatch.setattr(
        attest,
        "records",
        lambda _root, _plan, record=None, **_kwargs: (
            persisted.append(record) if record else tuple(persisted)
        ),
    )
    carried = proof_plan(case, value)
    applied = execute_git_effect(case.repo, carried, issuer=ISSUER)
    statement = applied.payload.body
    assert programs == [(value.program(), False)]
    assert (applied.predicate, applied.subject, applied.verdict) == (
        "effect:git-ref-update",
        f"git-effect:{value.digest()}",
        "pass",
    )
    assert (applied.plan_digest, applied.effect_digest) == (carried.digest, value.digest())
    assert statement["command"] == ("git", "update-ref", "--stdin", "-z")
    assert statement["program_sha256"] == value.digest()
    assert mutable_json(statement["plan"]) == carried.model_dump(mode="json")
    assert mutable_json(statement["effect"]) == value.model_dump(mode="json")
    assert statement["input"]["refs"] == dict.fromkeys(value.updates, case.old)
    assert (
        statement["result"]["refs"]
        == statement["output"]["refs"]
        == dict.fromkeys(value.updates, case.new)
    )
    assert (statement["result"]["state"], statement["result"]["executed"]) == ("applied", True)
    assert persisted == [applied]
    assert execute_git_effect(case.repo, carried, issuer=ISSUER) == applied
    assert not list(ref_intent_dir(case.repo).glob("*.json"))


@pytest.mark.parametrize(
    ("issuer", "gap"),
    [("", "git_effect_issuer_invalid"), ("agent:test:other", "git_effect_issuer_mismatch")],
)
def test_effect_issuer_matches_exact_plan_before_ref_mutation(tmp_path, issuer, gap):
    """Missing or mismatched issuers preserve refs and create no intent."""
    case = fixture(tmp_path)
    carried = plan(
        case.repo,
        case.effect,
        policy={
            "operation": "git.ref.compare-and-swap",
            "actor": ISSUER,
            "effect_digest": case.effect.digest(),
        },
    )
    reject(gap, lambda: execute_git_effect(case.repo, carried, issuer=issuer))
    assert git(case.repo, "rev-parse", "dev") == case.old
    assert not list(ref_intent_dir(case.repo).glob("*.json"))


@pytest.mark.parametrize("kind", ["linked", "dirty", "changed", "foreign"])
def test_repository_worktree_identity_matrix(tmp_path: Path, kind: str) -> None:
    identity, case = "repository:portable", fixture(tmp_path, "repository:portable")
    root = case.repo
    if kind == "linked":
        root = tmp_path / "linked"
        git(case.repo, "worktree", "add", "--detach", str(root), "dev")
    elif kind == "dirty":
        profile = root / ".ethos/profile.toml"
        profile.write_text(profile.read_text().replace("portable", "dirty"))
    elif kind == "changed":
        git(root, "checkout", "-q", "-b", "change")
        profile = root / ".ethos/profile.toml"
        case.new = commit_fixture_file(
            root,
            str(profile.relative_to(root)),
            profile.read_text().replace("portable", "changed"),
            "change",
        )
        git(root, "checkout", "-q", "dev")
        case.effect = effect(case.old, case.new)
    elif kind == "foreign":
        other = fixture(tmp_path / "foreign", "repository:foreign")
        git(root, "fetch", str(other.repo), f"{other.old}:refs/heads/foreign")
        case.effect = effect(other.old, case.new)
    if kind in {"changed", "foreign"}:
        reject(
            "git_effect_repository_identity_mismatch",
            lambda: execute_git_effect(root, plan(root, case.effect), issuer=ISSUER),
        )
        assert git_stdout(case.repo, "rev-parse", "--verify", "refs/heads/dev") == case.old
    else:
        assert (
            execute_git_effect(root, plan(root, case.effect), issuer=ISSUER).payload.body[
                "repository"
            ]
            == identity
        )


def test_git_effect_repository_resolution_rejects_invalid_profile_schema(
    tmp_path: Path,
) -> None:
    case = fixture(tmp_path)
    carrier = case.repo / ".ethos/profile.toml"
    carrier.write_text('profile_id = ""\n', encoding="utf-8")
    git(case.repo, "add", ".ethos/profile.toml")
    unsupported = git(
        case.repo,
        "commit-tree",
        git(case.repo, "write-tree"),
        "-p",
        case.old,
        "-m",
        "invalid repository profile",
    )
    git(case.repo, "reset", "--hard", case.old)
    changed = effect(case.old, unsupported)

    with pytest.raises(
        ValueError,
        match=r"repository_profile_invalid:\.ethos/profile\.toml",
    ):
        resolve_git_effect_repository(
            case.repo,
            changed,
            {"head": case.old},
        )


@pytest.mark.parametrize("kind", ["zero", "owned", "unowned", "stale", "assertion"])
def test_ref_recovery_and_cas_failure_matrix(tmp_path: Path, kind: str) -> None:
    case = fixture(tmp_path)
    if kind == "zero":
        value = effect(ZERO_OID, case.old, "refs/heads/work/new")
        record = execute_git_effect(case.repo, plan(case.repo, value), issuer=ISSUER)
        assert (
            git(case.repo, "rev-parse", "work/new"),
            record.payload.body["input"]["refs"],
        ) == (
            case.old,
            {"refs/heads/work/new": ZERO_OID},
        )
        return
    if kind in {"owned", "unowned"}:
        carried, update = proof_plan(case), case.effect.updates["refs/heads/dev"]
        if kind == "owned":
            options = {
                "root": case.repo,
                "ref_name": "refs/heads/dev",
                "update": update,
                "operation": "git.ref.compare-and-swap",
                "plan_digest": carried.digest,
            }
            write_ref_intent(**options)
            claim_ref_intent(**options, phase="prepared")
        git(case.repo, "update-ref", "refs/heads/dev", case.new, case.old)
        if kind == "owned":
            result = execute_git_effect(case.repo, carried, issuer=ISSUER).payload.body["result"]
            assert (result["state"], result["executed"]) == ("recovered", False)
        else:
            reject(
                "git_effect_recovery_intent_missing",
                lambda: execute_git_effect(case.repo, carried, issuer=ISSUER),
            )
        return
    if kind == "stale":
        git(case.repo, "update-ref", "refs/heads/dev", case.new, case.old)
        value, carried = effect(ZERO_OID, case.old), None
    else:
        git(case.repo, "branch", "candidate/dev", case.old)
        value = GitEffect(
            updates=case.effect.updates, assertions={"refs/heads/candidate/dev": case.old}
        )
        carried = plan(case.repo, value)
        git(case.repo, "update-ref", "refs/heads/candidate/dev", case.new, case.old)
    reject(
        "git_effect_cas_mismatch",
        lambda: execute_git_effect(case.repo, carried or plan(case.repo, value), issuer=ISSUER),
    )


@pytest.mark.parametrize(
    ("state", "current_generation", "recover", "detached"),
    [(state, 1, recover, 0) for state in ("expired", "unknown") for recover in (0, 1)]
    + [("valid", 2, recover, 0) for recover in (0, 1)]
    + [("valid", 1, 0, 1)],
)
def test_stale_lease_recovery_and_detached_matrix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    state: str,
    current_generation: int,
    recover: int,
    detached: int,
) -> None:
    case = fixture(tmp_path)
    branch = "work/example" if detached else "dev"
    recorded = generation(branch)
    current = recorded | {
        "generation": current_generation,
        "lane_ref": branch,
        "lease_state": state,
    }
    carried = plan(case.repo, case.effect, values={"lease_generation": recorded})
    monkeypatch.setenv("ETHOS_ACTOR", ISSUER)
    monkeypatch.setattr(admission, "leases_by_branch", lambda *_args, **_kwargs: {branch: current})
    if recover:
        git(case.repo, "update-ref", "refs/heads/dev", case.new, case.old)
    if detached:
        carried = plan(
            case.repo,
            case.effect,
            values={"lease_generation": lease_generation(current)},
            policy={
                "operation": "git.ref.compare-and-swap",
                "effect_digest": case.effect.digest(),
                "execution_branch": branch,
            },
        )
        original = admission.run_git
        monkeypatch.setattr(
            admission,
            "run_git",
            lambda root, *args, **kwargs: (
                type("R", (), {"stdout": "", "returncode": 0})()
                if args == ("branch", "--show-current")
                else original(root, *args, **kwargs)
            ),
        )
    error = "git_effect_lease_branch_mismatch" if detached else "git_effect_lease_generation_stale"
    reject(error, lambda: execute_git_effect(case.repo, carried, issuer=ISSUER))
    assert git_stdout(case.repo, "rev-parse", "--verify", "refs/heads/dev") == (
        case.new if recover else case.old
    )


def test_only_exact_effect_authority_is_admitted(tmp_path: Path) -> None:
    case = fixture(tmp_path)
    admit_git_effect(case.repo, plan(case.repo, case.effect))
    reject(
        "git_effect_permission_denied",
        lambda: execute_git_effect(
            case.repo,
            plan(case.repo, case.effect, policy={"operation": "test.apply"}),
            issuer=ISSUER,
        ),
    )
    assert git(case.repo, "rev-parse", "refs/heads/dev") == case.old


@pytest.mark.parametrize("kind", ["commitment", "facts", "policy", "effect", "prestate"])
def test_plan_binding_and_stale_prestate_matrix(tmp_path: Path, kind: str) -> None:
    case = fixture(tmp_path)
    carried = plan(case.repo, case.effect)
    if kind == "prestate":
        commit_fixture_file(case.repo, "DRIFT.md", "drift\n", "drift")
        error = "git_effect_plan_prestate_stale"
    else:
        carried = carried.model_copy(
            update={"inputs": carried.inputs.model_copy(update={kind: ZERO_DIGEST})}
        )
        error = "git_effect_plan_mismatch"
    reject(error, lambda: execute_git_effect(case.repo, carried, issuer=ISSUER))
    assert git_stdout(case.repo, "rev-parse", "--verify", "refs/heads/dev") != case.new


def _effect_failure_runner(
    case: Any,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
    saved: list[Attestation],
    first: list[bool],
) -> Any:
    carried = proof_plan(case)

    def fail(record: Attestation | None = None) -> object:
        if first[0] and record is not None:
            first[0] = False
            message = f"{failure} unavailable"
            raise OSError(message)
        if record:
            saved.append(record)
        return tuple(saved)

    if failure == "attestation":
        issue = attest.issue

        def issue_once(*args: object, **kwargs: object) -> Attestation:
            if first[0]:
                first[0] = False
                message = "attestation unavailable"
                raise ValueError(message)
            return issue(*args, **kwargs)

        monkeypatch.setattr(attest, "issue", issue_once)
        return lambda: execute_git_effect(case.repo, carried, issuer=ISSUER)
    if failure == "persistence":
        monkeypatch.setattr(
            attest,
            "records",
            lambda _root, _plan, record=None, **_kwargs: fail(record),
        )
        return lambda: execute_git_effect(case.repo, carried, issuer=ISSUER)
    return lambda: execute_git_effect(case.repo, carried, issuer=ISSUER)


def _inject_postcondition_failure(case: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    observe, failed = runtime.observe_git_effect, [False]

    def stale_once(*args: object, **kwargs: object) -> dict[str, object]:
        result = observe(*args, **kwargs)
        desired = {name: update.desired for name, update in case.effect.updates.items()}
        if not failed[0] and result["refs"] == desired:
            failed[0] = True
            result = {
                **result,
                "refs": {name: update.expected for name, update in case.effect.updates.items()},
            }
        return result

    monkeypatch.setattr(runtime, "observe_git_effect", stale_once)


@pytest.mark.parametrize("failure", ["attestation", "persistence", "postcondition"])
def test_atomic_compensation_and_retry_matrix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    case = fixture(tmp_path)
    saved, first = [], [True]
    if failure == "postcondition":
        _inject_postcondition_failure(case, monkeypatch)

        def run() -> Any:
            return execute_git_effect(case.repo, proof_plan(case), issuer=ISSUER)

    else:
        run = _effect_failure_runner(case, monkeypatch, failure, saved, first)

    error = (
        "git_effect_postcondition_failed"
        if failure == "postcondition"
        else f"{failure} unavailable"
    )
    reject(error, run)
    assert git(case.repo, "rev-parse", "dev") == case.old
    assert not list(ref_intent_dir(case.repo).glob("*.json"))
    recovered = run()
    assert git(case.repo, "rev-parse", "dev") == case.new
    assert recovered.payload.body["result"]["state"] == "applied"
    assert (saved == [recovered]) if failure == "persistence" else (not saved)
    assert not list(ref_intent_dir(case.repo).glob("*.json"))


def test_execute_ignores_legacy_plan_receipt_when_attestation_set_is_empty(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = fixture(tmp_path)
    carried = proof_plan(case)
    legacy = attest.issue(
        case.effect,
        plan=carried,
        issuer=ISSUER,
        evidence=(
            f"repository:{case.repo.name}",
            "applied",
            {
                "head": case.old,
                "tree": git(case.repo, "rev-parse", "HEAD^{tree}"),
                "refs": {"refs/heads/dev": case.old},
                "assertions": {},
                "observed_at": "2026-08-01T00:00:00+00:00",
            },
            {
                "head": case.new,
                "tree": git(case.repo, "rev-parse", "HEAD^{tree}"),
                "refs": {"refs/heads/dev": case.new},
                "observed_at": "2026-08-01T00:00:01+00:00",
            },
        ),
    )
    legacy_path = ref_intent_dir(case.repo).parent / "git-effects" / f"{carried.digest}.json"
    legacy_path.parent.mkdir(parents=True, exist_ok=True)
    legacy_path.write_text(legacy.canonical_json(), encoding="utf-8")
    git(case.repo, "update-ref", "refs/heads/dev", case.new, case.old)
    monkeypatch.setattr(
        runtime,
        "_apply_git_ref_transaction",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("legacy receipt reused")),
    )
    reject(
        "git_effect_recovery_intent_missing",
        lambda: execute_git_effect(case.repo, carried, issuer=ISSUER),
    )


def test_prepare_failure_aborts_every_claimed_intent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = fixture(tmp_path)
    value = GitEffect(
        updates={
            ref: GitRefUpdate(expected=ZERO_OID, desired=case.new)
            for ref in ("refs/heads/a", "refs/heads/b")
        }
    )
    claim = runtime.claim_ref_intent
    monkeypatch.setattr(
        runtime,
        "claim_ref_intent",
        lambda **kwargs: (
            {"gap": "forced_prepare_failure"}
            if kwargs["ref_name"] == "refs/heads/b" and kwargs["phase"] == "prepared"
            else claim(**kwargs)
        ),
    )

    reject(
        "git_effect_ref_intent_prepared_forced_prepare_failure",
        lambda: execute_git_effect(case.repo, plan(case.repo, value), issuer=ISSUER),
    )

    assert all(not git_stdout(case.repo, "rev-parse", "--verify", ref) for ref in value.updates)
    assert not list(ref_intent_dir(case.repo).glob("*.json"))


def test_compensation_failure_preserves_exact_recovery_intent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = fixture(tmp_path)
    carried = proof_plan(case)
    original_run_git = runtime.run_git
    updates = 0

    def fail_reverse(root: Path, *args: str, **kwargs: object) -> object:
        nonlocal updates
        if args == ("update-ref", "--stdin", "-z"):
            updates += 1
            if updates == 2:
                return subprocess.CompletedProcess(args, 1, b"", b"reverse rejected")
        return original_run_git(root, *args, **kwargs)

    monkeypatch.setattr(runtime, "run_git", fail_reverse)
    monkeypatch.setattr(
        attest,
        "issue",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("attestation unavailable")),
    )

    reject(
        "git_effect_partial_effect_uncompensated:refs/heads/dev"
        f":expected={case.old}:observed={case.new}",
        lambda: execute_git_effect(case.repo, carried, issuer=ISSUER),
    )

    assert git(case.repo, "rev-parse", "dev") == case.new
    intents = list(ref_intent_dir(case.repo).glob("*.json"))
    assert len(intents) == 1
    assert '"phase":"committed"' in intents[0].read_text(encoding="utf-8")
