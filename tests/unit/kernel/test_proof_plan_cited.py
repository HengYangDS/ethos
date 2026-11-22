"""A proof cites its plan by digest: the journey of one lane with many changed paths."""

from __future__ import annotations

import hashlib
from functools import partial
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.proof as proof_module
import ethos.adapters.repo.attestation_set as attestation_set
from ethos.adapters.mutation.proof import persist_proof_attestation
from ethos.adapters.mutation.proof import proof_attestation
from ethos.adapters.mutation.proof import proof_for_repository_transition
from ethos.adapters.mutation.proof import proof_gaps
from ethos.adapters.mutation.proof_artifacts import cite_plan
from ethos.adapters.mutation.proof_artifacts import cited_when_large
from ethos.adapters.mutation.proof_validation import plan_from_statement
from ethos.adapters.repo.git_effect_attestation import plan_from_attestation
from ethos.adapters.repo.git_effect_attestation import validate_git_effect_attestation
from ethos.adapters.store.retention.closure import Closure
from ethos.adapters.store.retention.kinds import classify_store
from ethos.adapters.store.retention.roots import carrier_tokens
from ethos.adapters.store.state.schema import local_state_root
from ethos.contracts.plan import git_effect_from_plan
from ethos.contracts.proof.plan import PROOF_CITED
from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import canonical_json_bytes
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.governed_repository import prepared_work_lane
from tests.support.proof import assert_selected_proof
from tests.support.proof import current_proof_plan
from tests.support.proof import issue_conformant_proof
from tests.support.proof import proof_carrying_plan
from tests.support.proof import proof_repository
from tests.support.proof import seed_executed_proof
from tests.support.semantic import reissue_attestation

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.plan import TransitionPlan


_issue = partial(issue_conformant_proof, issuer="agent:test:case:proof")
_MIB = 1024 * 1024
# Each path is listed twice in a plan; this many long paths put the plan alone over one mebibyte.
_PATHS = 1400


def _cited(
    repo: Path,
    head: str,
    *,
    plan: TransitionPlan | None = None,
    issuer: str = "agent:test:case:proof",
) -> Attestation:
    """Issue a proof and cite its plan, as the writer does for a plan too large to carry."""
    plan = plan or current_proof_plan(repo, expected_head=head)
    return cite_plan(local_state_root(repo), _issue(repo, head, plan=plan, issuer=issuer), plan)


def _size(record: Attestation) -> int:
    return len(record.canonical_json().encode())


def _many_paths(worktree: Path, count: int) -> None:
    """Add files whose two long path parts make each changed path cost about 900 plan bytes."""
    for ordinal in range(count):
        target = worktree / "bulk" / f"{ordinal:05d}-{'d' * 190}" / f"{'f' * 190}.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"# Bulk {ordinal}\n", encoding="utf-8")


def test_a_proof_over_the_bound_is_recorded_and_read_back(tmp_path: Path) -> None:
    """The cited record is small where the carried record is refused, and its plan reads back."""
    fixture = prepared_work_lane(tmp_path)
    _many_paths(fixture.worktree, _PATHS)
    head = commit_fixture(fixture.worktree, "test: change many paths")
    plan = current_proof_plan(fixture.worktree, expected_head=head)

    record = _issue(fixture.worktree, head, plan=plan)
    carried = proof_carrying_plan(record, plan)
    assert attestation_set.MEMBER_BYTES_LIMIT == _MIB
    assert _size(carried) > _MIB > 2_000 > _size(record)
    assert record.predicate == record.payload.kind == PROOF_CITED
    assert "plan" not in record.payload.body
    with pytest.raises(ValueError, match=f"^attestation_member_too_large:{carried.id}$"):
        attestation_set.record_attestations(fixture.worktree, (carried,))

    assert persist_proof_attestation(fixture.worktree, record)["added"] == (record.id,)
    _root, members = attestation_set.read_attestation_set(fixture.worktree)
    stored = next(member for member in members if member.id == record.id)
    assert plan_from_statement(stored, fixture.worktree) == plan
    assert proof_attestation(fixture.worktree, head) == record
    assert proof_gaps(fixture.worktree, head) == []
    # The writer itself does not replace other bytes under the plan's name.
    carrier = local_state_root(fixture.worktree) / "artifacts" / f"{plan.digest}.json"
    carrier.write_bytes(b"[]")
    with pytest.raises(ValueError, match=r"^proof_attestation_plan_artifact_collision$"):
        _issue(fixture.worktree, head, plan=plan)


def test_a_proof_is_cited_only_above_a_third_of_the_bound(tmp_path: Path) -> None:
    """A release's record carries the proof twice, so the writer cites above a third."""
    repo, head = proof_repository(tmp_path / "repo")
    plan = current_proof_plan(repo, expected_head=head)
    small = _issue(repo, head, plan=plan)
    store = local_state_root(repo)
    carrier = store / "artifacts" / f"{plan.digest}.json"
    limit = attestation_set.MEMBER_BYTES_LIMIT // 3
    empty = _size(reissue_attestation(small, body=small.payload.body | {"padding": ""}))
    at, over = (
        reissue_attestation(small, body=small.payload.body | {"padding": "x" * (size - empty)})
        for size in (limit, limit + 1)
    )
    assert (_size(small) < limit, _size(at), _size(over)) == (True, limit, limit + 1)

    assert cited_when_large(store, at, plan) is at
    assert not carrier.exists()
    cited = cited_when_large(store, over, plan)
    assert (cited.predicate, "plan" in cited.payload.body) == (PROOF_CITED, False)
    assert carrier.exists()


def test_a_proof_between_a_third_and_half_of_the_bound_is_cited(tmp_path: Path) -> None:
    """The writer cites the record that a landing could carry and a release could not."""
    fixture = prepared_work_lane(tmp_path)
    _many_paths(fixture.worktree, 450)
    head = commit_fixture(fixture.worktree, "test: change some paths")
    plan = current_proof_plan(fixture.worktree, expected_head=head)

    record = _issue(fixture.worktree, head, plan=plan)

    carried = _size(proof_carrying_plan(record, plan))
    assert _MIB // 3 < carried <= _MIB // 2
    assert (record.predicate, _size(record) < 2_000) == (PROOF_CITED, True)
    assert plan_from_statement(record, fixture.worktree) == plan


def test_the_writer_checks_the_record_that_it_returns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A cited record that fails its structural check is refused at issuance."""
    repo, head = proof_repository(tmp_path / "repo")
    plan = current_proof_plan(repo, expected_head=head)

    def cited_with_its_plan(store: Path, carried: Attestation, plan: TransitionPlan) -> Attestation:
        cited = cite_plan(store, carried, plan)
        return reissue_attestation(cited, body=cited.payload.body | {"plan": {}})

    monkeypatch.setattr(proof_module, "cited_when_large", cited_with_its_plan)
    with pytest.raises(ValueError, match="model_gap"):
        _issue(repo, head, plan=plan)


def _assert_landing_records(repo: Path, proof: Attestation) -> None:
    """Both ref effects of the landing carry the cited proof, stay small and validate."""
    _root, members = attestation_set.read_attestation_set(repo)
    landing: dict[str, Attestation] = {}
    for member in members:
        if member.predicate != "effect:git-ref-update":
            continue
        transition = str(plan_from_attestation(member).policy.get("transition"))
        if transition in {"candidate.integrate", "candidate.accept"}:
            landing[transition] = member
    assert set(landing) == {"candidate.integrate", "candidate.accept"}
    assert max(_size(member) for member in members) < _MIB
    for transition, member in landing.items():
        effect_plan = plan_from_attestation(member)
        carried_proof = effect_plan.prior_attestations["proof"]
        assert carried_proof["id"] == proof.id
        assert carried_proof["predicate"] == PROOF_CITED
        # The record validates as the product validates it: issued again and compared whole.
        validate_git_effect_attestation(
            repo,
            git_effect_from_plan(effect_plan),
            member,
            issuer=member.verifier,
            plan=effect_plan,
            current_postconditions=False,
        )
        named = carrier_tokens(
            member.model_dump_json().encode(), depth=2, budget=64 * _MIB, name=transition
        )
        assert proof.plan_digest in named


def test_b_a_landing_of_many_paths_keeps_every_record_under_the_bound(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Prove, archive, integrate and accept one lane whose carried proof would be refused."""
    fixture = prepared_work_lane(tmp_path)
    repo, worktree = fixture.repository, fixture.worktree
    accepted_head = git(repo, "rev-parse", "HEAD")
    _many_paths(worktree, _PATHS)
    commit_fixture(worktree, "test: change many paths")
    head = commit_fixture_file(
        worktree,
        "openspec/changes/fixture-change/tasks.md",
        "- [x] Exercise fixture lifecycle\n",
        "test: complete fixture change",
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    seed_executed_proof(worktree, head)
    archive = run_ethos_blocked(
        "lane", "archive-change", "--change", "fixture-change", "--expect-head", head,
        "--apply", "--json", cwd=worktree,
    )  # fmt: skip
    assert archive["required_gaps"] == ["proof_not_proven"]
    archived_head = git(worktree, "rev-parse", "HEAD")
    seed_executed_proof(worktree, archived_head)
    run_ethos(
        "land", "--apply", "--authorize", "--expect-head", archived_head, "--json", cwd=worktree
    )
    proof, gaps = proof_for_repository_transition(fixture.candidate, archived_head)
    assert gaps == []
    assert proof is not None
    plan = plan_from_statement(proof, repo)
    assert _size(proof_carrying_plan(proof, plan)) > _MIB

    payload = run_ethos(
        "land", "--closeout", "--apply", "--authorize", "--expect-head", accepted_head, "--json",
        cwd=repo,
    )  # fmt: skip
    assert payload["state"] == "accepted_validated"
    assert git(repo, "rev-parse", "dev") == archived_head

    _assert_landing_records(repo, proof)


def test_c_a_record_that_carries_its_plan_is_still_admitted(tmp_path: Path) -> None:
    """A record in today's form, beside no artifact of its plan, is read and selected."""
    repo, head = proof_repository(tmp_path / "repo")
    plan = current_proof_plan(repo, expected_head=head)
    cited = _cited(repo, head, plan=plan)
    carried = proof_carrying_plan(cited, plan)
    (local_state_root(repo) / "artifacts" / f"{plan.digest}.json").unlink()
    assert set(carried.payload.body) - set(cited.payload.body) == {"plan"}

    assert persist_proof_attestation(repo, carried)["added"] == (carried.id,)
    assert plan_from_statement(carried, repo) == plan
    assert_selected_proof(repo, head, selected=carried)
    assert proof_for_repository_transition(repo, head) == (carried, [])


def test_c_both_forms_of_one_proof_select_one_record(tmp_path: Path) -> None:
    """A head proven before and after the change of form keeps one deterministic selection."""
    repo, head = proof_repository(tmp_path / "repo")
    plan = current_proof_plan(repo, expected_head=head)
    cited = _cited(repo, head, plan=plan)
    carried = proof_carrying_plan(cited, plan)
    persist_proof_attestation(repo, carried)
    persist_proof_attestation(repo, cited)

    assert_selected_proof(repo, head, selected=min((cited, carried), key=lambda item: item.id))


@pytest.mark.parametrize("case", ["absent", "altered", "another-plan", "not-a-plan"])
def test_d_plan_bytes_that_are_not_the_cited_plan_are_refused_by_name(
    tmp_path: Path, case: str
) -> None:
    """Absent bytes and bytes of another digest each name their gap and yield no plan."""
    repo, earlier_head = proof_repository(tmp_path / "repo")
    earlier = current_proof_plan(repo, expected_head=earlier_head)
    head = commit_fixture_file(repo, "FEATURE.md", "# Feature\n", "docs: add a feature note")
    plan = current_proof_plan(repo, expected_head=head)
    record = _cited(repo, head, plan=plan)
    persist_proof_attestation(repo, record)
    carrier = local_state_root(repo) / "artifacts" / f"{record.plan_digest}.json"
    exact = carrier.read_bytes()
    gap = "proof_attestation_plan_artifact_digest_mismatch"
    if case == "absent":
        carrier.unlink()
        gap = "proof_attestation_plan_artifact_missing"
    elif case == "altered":
        carrier.write_bytes(exact.replace(b'"verdict":"pass"', b'"verdict":"block"'))
        assert carrier.read_bytes() != exact
    elif case == "another-plan":
        # A whole valid plan of another head, under the name of the cited one.
        assert earlier.digest != plan.digest
        carrier.write_bytes(
            canonical_json_bytes(earlier.model_dump(mode="json", exclude={"digest"}))
        )
    else:
        carrier.write_bytes(b"[]")

    with pytest.raises(ValueError, match=f"^{gap}$"):
        plan_from_statement(record, repo)
    assert_selected_proof(repo, head, gap=gap)
    assert proof_for_repository_transition(repo, head) == (None, [gap])
    before = attestation_set.read_attestation_set(repo)
    if case != "absent":
        # The same plan is not written over bytes that are not its own: the writer names it.
        with pytest.raises(ValueError, match=r"^proof_attestation_plan_artifact_collision$"):
            _cited(repo, head, plan=plan, issuer="agent:test:case:second")
        carrier.unlink()
    again = _cited(repo, head, plan=plan, issuer="agent:test:case:second")
    carrier.unlink()
    with pytest.raises(ValueError, match=r"^proof_attestation_plan_artifact_missing$"):
        persist_proof_attestation(repo, again)
    assert attestation_set.read_attestation_set(repo) == before


def test_d_cited_bytes_that_are_no_plan_document_name_their_gap(tmp_path: Path) -> None:
    """Bytes that match the cited digest and are no plan document name their own gap."""
    repo, head = proof_repository(tmp_path / "repo")
    record = _cited(repo, head)
    digest = hashlib.sha256(b"[]").hexdigest()
    (local_state_root(repo) / "artifacts" / f"{digest}.json").write_bytes(b"[]")
    forged = Attestation.issue(
        record.model_dump(mode="python", exclude={"id"}) | {"plan_digest": digest}
    )
    with pytest.raises(ValueError, match=r"^proof_attestation_plan_invalid$"):
        plan_from_statement(forged, repo)


def test_f_plan_bytes_stay_while_a_live_record_names_them(tmp_path: Path) -> None:
    """Retention owns the plan's file: unnamed it is a candidate, named by a member it is kept."""
    repo, head = proof_repository(tmp_path / "repo")
    record = _cited(repo, head)
    store = local_state_root(repo)

    def reached() -> tuple[list[str], list[str]]:
        items, unowned = classify_store(store)
        plans = [item for item in items if item.kind == "proof-plan"]
        closure = Closure(
            repo,
            store,
            git(repo, "branch", "--show-current"),
            depth=2,
            budget=64 * _MIB,
            owned=frozenset(path for item in items for path in item.paths),
        )
        closure.refresh()
        assert [path.name for item in plans for path in item.paths] == [
            f"{record.plan_digest}.json"
        ]
        return [item.kind for item in closure.reached(plans)], [path.name for path in unowned]

    assert reached() == ([], [])
    persist_proof_attestation(repo, record)
    assert reached() == (["proof-plan"], [])
    assert not (store / "custody" / "sha256").exists()
