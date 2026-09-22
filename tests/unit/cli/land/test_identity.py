"""Public integration crosses identity through explicit, independently bound effects."""

from __future__ import annotations

import tomllib
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.landing as landing
import ethos.adapters.repo.git_ref_worktrees as ref_worktrees
import ethos.adapters.repo.status.bindings as bindings
from ethos.adapters.openspec.commitment import load_openspec_commitment
from ethos.adapters.repo.git_effect_attestation import records
from ethos.adapters.repo.git_effect_observation import compile_observed_git_effect
from ethos.adapters.repo.git_effects import admit_git_effect
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.plan import compile_git_effect_plan
from ethos.contracts.plan import git_effect_from_plan
from ethos.contracts.semantic import Facts
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.governed_repository import prepared_work_lane
from tests.support.proof import declare_native_proof_checks
from tests.support.proof import seed_executed_proof
from tests.support.signature import configure_signer
from tests.support.signature import repair_fixture_history

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any


@pytest.mark.parametrize(
    ("mode", "tag", "interrupt"),
    [
        ("independent", "", ""),
        ("independent", "v1.2.3", ""),
        ("accepted_ff", "", ""),
        ("independent", "", "accepted"),
        ("accepted_ff", "", "accepted"),
        ("independent", "", "candidate"),
        ("independent", "", "release"),
    ],
    ids=[
        "branch",
        "signed-tag",
        "accepted-mirror",
        "accepted-sync-loss",
        "mirror-sync-loss",
        "candidate-sync-loss",
        "release-sync-loss",
    ],
)
def test_identity_transition_is_explicit_and_target_scoped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str, tag: str, interrupt: str
) -> None:
    """A renamed work lane advances each declared stage without a global identity alias."""
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    fixture = prepared_work_lane(tmp_path, release_mirror=mode)
    work, repo = fixture.worktree, fixture.repository
    historical_head = git(work, "rev-parse", "HEAD")
    configure_signer(work, tmp_path)
    git(work, "config", "commit.gpgsign", "true")
    old = git(repo, "rev-parse", "HEAD")
    assert git(fixture.candidate, "rev-parse", "HEAD") == old
    git(repo, "-c", f"core.hooksPath={tmp_path / 'fixture-hooks'}", "branch", "main", old)
    release_checkout = tmp_path / "repo-main"
    if interrupt == "release":
        git(repo, "worktree", "add", release_checkout.as_posix(), "main")
    tasks = work / "openspec/changes/fixture-change/tasks.md"
    tasks.write_text(tasks.read_text().replace("[ ]", "[x]"))
    (work / "VERSION").write_text("1.2.3\n")
    workspace = work / ".ethos/workspace.toml"
    workspace.write_text(
        workspace.read_text() + '\n[commit_policy]\nsubject_pattern = ".+"\n'
        'signing_required = true\nsigning_format = "ssh"\n'
    )
    release = work / ".ethos/release.toml"
    release.write_text(
        '[protected_refs]\nbranches = ["main", "dev"]\ntags = ["v*"]\n\n' + release.read_text()
    )
    git(work, "add", tasks.relative_to(work).as_posix(), "VERSION", ".ethos")
    declare_native_proof_checks(
        work,
        test="from pathlib import Path; assert Path('VERSION').read_text() == '1.2.3\\n'",
        typecheck="import tomllib; from pathlib import Path; "
        "assert tomllib.loads(Path('.ethos/profile.toml').read_text())"
        "['profile_id'] == 'renamed-product'",
    )
    profile = work / ".ethos/profile.toml"
    old_profile = tomllib.loads(profile.read_text())["profile_id"]
    head = commit_fixture_file(
        work,
        ".ethos/profile.toml",
        profile.read_text().replace(
            f'profile_id = "{old_profile}"', 'profile_id = "renamed-product"'
        ),
        "feat: transition the repository identity",
    )
    seed_executed_proof(work, head)
    candidate_args = ("--expect-head", head, "--candidate-head", old)
    candidate = _exercise_transition(
        work,
        candidate_args,
        {"refs/heads/candidate/dev": old},
        head,
        "candidate_update",
        interrupt=interrupt == "candidate",
        checkout=fixture.candidate,
    )
    assert git(repo, "rev-parse", "HEAD") == old
    assert tomllib.loads(profile.read_text())["profile_id"] == "renamed-product"
    candidate_plan = candidate["payload"]["body"]["plan"]
    assert (
        candidate_plan["inputs"]["commitment"]
        == candidate_plan["prior_attestations"]["proof"]["commitment_digest"]
    )
    if mode == "independent" and not tag and not interrupt:
        _assert_identity_operation_scope(work, candidate_plan)
    accepted_targets = {"refs/heads/dev": old}
    if mode == "accepted_ff":
        accepted_targets["refs/heads/main"] = old
    accepted = _exercise_transition(
        repo,
        ("--closeout", "--expect-head", old, "--candidate-head", head),
        accepted_targets,
        head,
        "accepted_update",
        interrupt=interrupt == "accepted",
    )
    assert accepted["id"] != candidate["id"]
    assert git(repo, "rev-parse", "HEAD") == head
    assert git(repo, "rev-parse", "main") == (head if mode == "accepted_ff" else old)
    if mode == "independent" and not tag and not interrupt:
        head = _prove_repaired_acceptance(repo, tmp_path, historical_head, accepted["id"])
    if mode == "independent":
        args = ("--release", "--expect-head", head, "--release-head", old)
        released = _exercise_transition(
            repo,
            (*args, *(("--tag", tag) if tag else ())),
            {"refs/heads/main": old},
            head,
            interrupt=interrupt == "release",
            checkout=release_checkout,
        )
        assert released["id"] != accepted["id"]
        if tag:
            assert git(repo, "rev-parse", f"{tag}^{{commit}}") == head


def _prove_repaired_acceptance(
    root: Path, temporary: Path, historical_head: str, accepted_id: str
) -> str:
    """A real new-HEAD proof retains the original acceptance across history repair."""
    head = repair_fixture_history(
        root, temporary / "identity-before.bundle", corrections={historical_head: {"resign": True}}
    )
    proof = run_ethos("prove", "--execute", "--expect-head", head, "--json", cwd=root)
    assert proof["verdict"] == "pass", proof
    current = run_ethos(
        "land", "--closeout", "--expect-head", head, "--candidate-head", head, "--json", cwd=root
    )
    update = current["data"]["accepted_update"]
    assert update["attestation"].get("id") == accepted_id
    assert update["provenance"]["head"] == head
    assert update["provenance"]["repair_attestation_ids"]
    return head


def _exercise_transition(
    root: Path,
    arguments: tuple[str, ...],
    before: dict[str, str],
    head: str,
    key: str = "",
    *,
    interrupt: bool = False,
    checkout: Path | None = None,
) -> dict[str, Any]:
    """Exercise the same refusal, preview, effect and replay contract at each public stage."""
    args = ("land", *arguments, "--json")
    ordinary = run_ethos_blocked(*args, "--apply", "--authorize", cwd=root)
    detail = ordinary["data"].get(key, ordinary["data"])
    if key == "accepted_update":
        assert detail["stderr"] == "git_effect_repository_identity_mismatch"
    else:
        assert ordinary["required_gaps"] == ["git_effect_repository_identity_mismatch"]
    preview = run_ethos(*args, "--identity-transition", cwd=root)
    assert preview["verdict"] == "pass", preview["required_gaps"]
    assert "--identity-transition" in preview["next_action"]
    detail = preview["data"].get(key, preview["data"])
    assert detail["transition_plan"]["policy"]["repository_identity_transitions"]
    assert {ref: git(root, "rev-parse", ref) for ref in before} == before
    effect_args = (*args, "--identity-transition", "--apply", "--authorize")
    if interrupt:
        original_id = _interrupt_materialization(
            root,
            args,
            effect_args,
            head,
            key,
            checkout or root,
            TransitionPlan.model_validate(detail["transition_plan"]),
        )
    applied = run_ethos(*effect_args, cwd=root)
    assert applied["verdict"] == "pass", applied["required_gaps"]
    assert {ref: git(root, "rev-parse", ref) for ref in before} == dict.fromkeys(before, head)
    statement = applied["data"].get(key, applied["data"])["attestation"]
    if interrupt:
        assert statement["id"] == original_id
    _assert_identity_statement(root, statement, before, head)
    repeated = run_ethos(*effect_args, cwd=root)
    assert repeated["data"].get(key, repeated["data"])["attestation"]["id"] == statement["id"]
    wrong = list(effect_args)
    wrong[wrong.index("--expect-head") + 1] = "0" * len(head)
    assert run_ethos_blocked(*wrong, cwd=root)["verdict"] == "block"
    assert {ref: git(root, "rev-parse", ref) for ref in before} == dict.fromkeys(before, head)
    return statement


def _interrupt_materialization(root, args, effect_args, head, key, target, plan):
    """Interrupt real ref progress and reject unauthorized or edited checkout recovery."""
    stage = key.removesuffix("_update") or "release"

    def fail_sync(*_args, **_kwargs):
        message = "fixture_worktree_sync_failed"
        raise ValueError(message)

    with pytest.MonkeyPatch.context() as context:
        context.setattr(
            landing if stage == "candidate" else ref_worktrees, "sync_worktree", fail_sync
        )
        failed = run_ethos_blocked(*effect_args, cwd=root)
        suffix = "pending" if stage == "release" else "failed"
        assert failed["required_gaps"] == [f"{stage}_worktree_sync_{suffix}"]
        assert failed["verdict"] == ("unknown" if stage == "release" else "block")
    assert git(target, "rev-parse", "HEAD") == head
    assert git(target, "status", "--short")
    pending = run_ethos(*args, "--identity-transition", cwd=root)
    detail = pending["data"].get(key, pending["data"])
    expected = "ready_to_release" if stage == "release" else f"{stage}_materialization_pending"
    assert detail.get("state", pending["state"]) == expected, pending["required_gaps"]
    for flag in ("--expect-head", "--release-head" if stage == "release" else "--candidate-head"):
        assert f"{flag} {args[args.index(flag) + 1]}" in pending["next_action"]
    assert git(target, "status", "--short")
    denied = run_ethos_blocked(*args, "--identity-transition", "--apply", cwd=root)
    assert "authorization_required" in denied["required_gaps"]
    with pytest.MonkeyPatch.context() as context:
        context.setenv("ETHOS_ACTOR", "agent:test:case:other")
        assert run_ethos_blocked(*effect_args, cwd=root)["verdict"] == "block"
    original = (target / "README.md").read_bytes()
    (target / "README.md").write_text("User work must survive recovery.\n")
    assert run_ethos_blocked(*effect_args, cwd=root)["verdict"] == "block"
    assert (target / "README.md").read_text() == "User work must survive recovery.\n"
    (target / "README.md").write_bytes(original)
    original = records(root, plan)
    assert len(original) == 1
    return original[0].id


def _assert_identity_statement(
    root: Path, statement: dict[str, Any], before: dict[str, str], head: str
) -> None:
    """Check independent native coordinates, identity edges and carried proof on every result."""
    plan = statement["payload"]["body"]["plan"]
    common = root / git(root, "rev-parse", "--git-common-dir")
    common = common.resolve()
    relations = {
        item["target_ref"]: item for item in plan["policy"]["repository_identity_transitions"]
    }
    assert set(relations) == set(before)
    for ref, old in before.items():
        old_profile = tomllib.loads(git(root, "show", f"{old}:.ethos/profile.toml"))["profile_id"]
        assert relations[ref] == {
            "operation": "repository.identity-transition",
            "target_ref": ref,
            "expected_head": old,
            "expected_tree": git(root, "rev-parse", f"{old}^{{tree}}"),
            "desired_head": head,
            "desired_tree": git(root, "rev-parse", f"{head}^{{tree}}"),
            "old_identity": f"repository:{old_profile}",
            "new_identity": "repository:renamed-product",
            "common_directory": common.as_posix(),
            "common_device": common.stat().st_dev,
            "common_inode": common.stat().st_ino,
        }
    assert plan["authority"]["actor"] == "agent:test:case:agent-test"
    assert plan["facts"]["values"]["lease_generation"]["generation"] > 0
    assert plan["digest"] == statement["plan_digest"]


def _assert_identity_operation_scope(root: Path, payload: dict[str, Any]) -> None:
    """Recomputed digests cannot authorize altered identity, storage or coordination."""
    plan = TransitionPlan.model_validate(payload)
    commitment = load_openspec_commitment(root, tree_ref=plan.facts["head"])

    def rebuild(value: dict[str, Any], intent=commitment) -> TransitionPlan:
        return compile_git_effect_plan(
            intent,
            Facts.model_validate(
                {**value["facts"], "observed_at": datetime.now(UTC)}, strict=False
            ),
            prior_attestations=value["prior_attestations"],
            policy=value["policy"],
            effect=GitEffect.model_validate(value["effect"]),
        )

    assert rebuild(payload).digest == plan.digest
    admit_git_effect(root, plan)
    before = git(root, "show-ref")
    edge = payload["policy"]["repository_identity_transitions"][0]
    for field, replacement in {
        "target_ref": "refs/heads/unrelated",
        "expected_head": "0" * len(edge["expected_head"]),
        "desired_head": "0" * len(edge["desired_head"]),
        "expected_tree": "0" * len(edge["expected_tree"]),
        "desired_tree": "0" * len(edge["desired_tree"]),
        "old_identity": "repository:unrelated",
        "new_identity": "repository:unrelated",
        "common_directory": root.as_posix(),
        "common_device": edge["common_device"] + 1,
        "common_inode": edge["common_inode"] + 1,
    }.items():
        altered = plan.model_dump(mode="json")
        altered["policy"]["repository_identity_transitions"][0][field] = replacement
        reason = "scope" if field == "target_ref" else "binding"
        with pytest.raises(ValueError, match=f"repository_identity_transition_{reason}_mismatch"):
            admit_git_effect(root, rebuild(altered))
    for path, replacement, reason in (
        (
            ("policy", "actor"),
            "agent:test:case:other",
            "repository_identity_transition_authority_mismatch",
        ),
        (("policy", "execution_branch"), "work/other", "git_effect_lease_branch_mismatch"),
        (
            ("facts", "values", "lease_generation", "generation"),
            0,
            "git_effect_lease_generation_stale",
        ),
        (
            ("facts", "values", "lease_generation"),
            None,
            "repository_identity_transition_authority_mismatch",
        ),
        (("prior_attestations", "proof"), None, "Attestation"),
        (
            ("policy", "repository_identity_transitions"),
            [],
            "repository_identity_transition_invalid",
        ),
    ):
        altered = plan.model_dump(mode="json")
        target = altered
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = replacement
        with pytest.raises(ValueError, match=reason):
            admit_git_effect(root, rebuild(altered))
    with pytest.raises(ValueError, match="repository_identity_transition_authority_mismatch"):
        admit_git_effect(
            root, rebuild(payload, commitment.model_copy(update={"acceptance": ("unaccepted",)}))
        )
    with pytest.MonkeyPatch.context() as context:
        context.setenv("ETHOS_ACTOR", "agent:test:case:other")
        with pytest.raises(ValueError, match="lease_actor_mismatch"):
            admit_git_effect(root, plan)
    expiry = datetime.fromisoformat(payload["facts"]["values"]["lease_generation"]["expires_at"])
    native = bindings.lease_observations
    with pytest.MonkeyPatch.context() as context:
        context.setattr(
            bindings,
            "lease_observations",
            lambda db: native(db, observed_at=expiry + timedelta(microseconds=1)),
        )
        with pytest.raises(ValueError, match="git_effect_lease_generation_stale"):
            admit_git_effect(root, plan)
    orphan = git(root, "commit-tree", edge["expected_tree"], "-m", "unrelated identity history")
    for previous in (edge["desired_head"], orphan):
        altered = plan.model_dump(mode="json")
        altered["effect"]["updates"][edge["target_ref"]]["expected"] = previous
        altered["policy"]["effect_digest"] = GitEffect.model_validate(altered["effect"]).digest()
        altered["facts"]["values"]["refs"][edge["target_ref"]] = previous
        altered["policy"]["repository_identity_transitions"][0]["expected_head"] = previous
        reason = "binding" if previous == orphan else "scope"
        with pytest.raises(ValueError, match=f"repository_identity_transition_{reason}_mismatch"):
            admit_git_effect(root, rebuild(altered))
    foreign = root.parent / "foreign.git"
    git(root, "clone", "--mirror", "--no-hardlinks", root.as_posix(), foreign.as_posix())
    with pytest.raises(ValueError, match="repository_identity_transition_database_mismatch"):
        admit_git_effect(root, plan, environment={"GIT_DIR": foreign.as_posix()})
    with pytest.MonkeyPatch.context() as context:
        context.delenv("ETHOS_ACTOR")
        for operation, reason in {
            "lane.retire": "operation_unsupported",
            "candidate.integrate": "live_authority_required",
        }.items():
            with pytest.raises(ValueError, match=f"repository_identity_transition_{reason}"):
                compile_observed_git_effect(
                    root,
                    None,
                    git_effect_from_plan(plan),
                    head=plan.facts["head"],
                    policy={"operation": operation},
                    prior_attestations=plan.prior_attestations,
                    identity_transition=True,
                )
    assert git(root, "show-ref") == before
