"""Source, role and introduced-range admission through public publication surfaces."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest

import ethos.adapters.mutation.proof as proof_adapter
import ethos.adapters.mutation.publication.execution as publication_execution
import ethos.adapters.mutation.publication.observation as publication_observation
import ethos.adapters.mutation.publication.request as publication_request
import ethos.repository.release.publication as release_publication
from ethos.adapters.repo.runtime.selection import runtime_command
from ethos.adapters.store.state.schema import local_state_root
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.plan import TransitionPlan
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import seed_executed_proof
from tests.support.runtime_scenarios import install_fixture_hook_runtime
from tests.unit.cli.land.publication.support import branch_publication
from tests.unit.cli.land.publication.support import branch_publication_fixture
from tests.unit.cli.land.publication.support import proposal_ref
from tests.unit.cli.land.publication.support import signed_publication_fixture


def test_publish_preserves_source_trust_gap_before_remote_observation(tmp_path: Path) -> None:
    repo, remotes, _signed_head = branch_publication_fixture(tmp_path)
    git(repo, "config", "commit.gpgsign", "false")
    (repo / "unsigned.txt").write_text("unsigned proposal source\n", encoding="utf-8")
    git(repo, "add", "unsigned.txt")
    git(repo, "commit", "-m", "test: create unsigned publication source")
    head = git(repo, "rev-parse", "HEAD")
    seed_executed_proof(repo, head)

    payload = branch_publication(repo, head, blocked=True)

    assert payload["verdict"] == "block"
    assert payload["required_gaps"] == [f"publication_source_signature_untrusted:{head}"]
    assert payload["data"]["remote_observations"] == {}
    assert payload["data"]["push_admission"] == {}
    assert all(proposal_ref(remote) == "" for remote in remotes.values())


def test_publication_contract_failure_matrix(tmp_path: Path) -> None:
    local = {"local_verification_command": "python", "local_installation_command": "python"}
    peer = {
        "id": "gitlab",
        "provider": "gitlab",
        "role": "review",
        "git_remote": "origin",
        "capabilities": ["repository", "publication"],
    }
    (tmp_path / "folder").mkdir()

    def case(gap: str, **updates: object) -> tuple[dict[str, object], str]:
        return {**local, **updates}, gap

    cases = [
        case("declaration_invalid", peers={}),
        case("peer_declaration_invalid", peers=[{**peer, "extra": 1}]),
        case("peer_declaration_invalid", peers=[{**peer, "id": 1}]),
        case("peer_declaration_invalid", peers=[{**peer, "capabilities": [1]}]),
        case("peer_declaration_invalid", peers=[{**peer, "ci_surface": 1}]),
        case("git_remote_invalid", peers=[{**peer, "git_remote": "../x"}]),
        case("capabilities_invalid", peers=[{**peer, "capabilities": []}]),
        case(
            "ci_surface_missing", peers=[{**peer, "capabilities": [*peer["capabilities"], "ci_cd"]}]
        ),
        case("ci_surface_without_capability", peers=[{**peer, "ci_surface": "ci.yml"}]),
        *(
            case(gap, local_verification_command=value, peers=[])
            for value, gap in (
                ("", "command_missing"),
                ("'", "command_invalid"),
                ('""', "command_not_regular"),
                ("/bin/sh", "command_path_escape"),
                ("folder", "command_not_regular"),
            )
        ),
    ]
    for declaration, gap in cases:
        topology = release_publication.publication_topology(tmp_path, {"publication": declaration})
        assert isinstance(topology["required_gaps"], list)
        assert any(gap in item for item in topology["required_gaps"])
    assert release_publication.publication_source_version_gaps(
        source_ref="refs/tags/v1", annotated_tag=True, version_text=None
    ) == ("publication_source_version_invalid:v1",)
    topology = {"required_gaps": [], "remotes": [{"id": "gitlab", "git_remote": "origin"}]}
    admissions = (
        ("invalid", "origin", "ref_unavailable"),
        ("refs/heads/dev", "", "name_missing"),
        ("refs/heads/dev", "other", "target_unknown"),
    )
    for ref, remote, gap in admissions:
        admission = release_publication.publication_ref_admission(
            topology,
            policy=load_branch_role_policy(Path.cwd()),
            target_ref=ref,
            release_tags=("v*",),
            remote_name=remote,
        )
        assert isinstance(admission["enforcement_gaps"], list)
        assert any(gap in item for item in admission["enforcement_gaps"])


def test_publication_remote_failure_matrix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")
    signature = {
        "verdict": "pass",
        "principal": "test",
        "fingerprint": "SHA256:key",
        "trust_anchor_sha256": "a" * 64,
        "verifier": "git verify-commit",
        "verifier_version": "1",
    }
    observation = {
        "kind": "commit",
        "object_oid": head,
        "peeled_commit": head,
        "tree_oid": git(repo, "rev-parse", "HEAD^{tree}"),
        "signature": signature,
    }
    for targets, expected in (
        ((), "ref_kind_mismatch"),
        (("refs/heads/dev", "refs/tags/v1"), "ref_kind_mismatch"),
    ):
        assert (
            expected
            in publication_request.observe_remote_publication_effect(
                root=repo, source_ref=head, target_refs=targets, remotes={}, ref_admissions={}
            )[2][0]
        )
    monkeypatch.setattr(publication_request, "observe_git_object", lambda *_args: observation)
    monkeypatch.setattr(
        publication_observation,
        "observe_remote_ref",
        lambda *_args: {"state": "unavailable", "object_oid": "", "required_gaps": []},
    )
    effect, _observations, gaps = publication_request.observe_remote_publication_effect(
        root=repo,
        source_ref=head,
        target_refs=("refs/heads/dev",),
        remotes={"gitlab": "origin"},
        ref_admissions={"refs/heads/dev": {}},
    )
    assert effect is None
    assert gaps == ("publication_remote_observation_unavailable:gitlab:origin:refs/heads/dev",)

    store = local_state_root(repo) / "requests/publication"
    store.mkdir(parents=True)
    missing = store / f"{'1' * 64}.json"
    failures = [
        (tmp_path / "elsewhere.json", "1" * 64, "path_invalid"),
        (missing, "1" * 64, "receipt_missing"),
    ]
    for path, digest, error in failures:
        with pytest.raises(ValueError, match=error):
            publication_request.load_remote_publication_request(repo, str(path), digest)
    corrupt = store / f"{'2' * 64}.json"
    corrupt.write_text("not the digest")
    with pytest.raises(ValueError, match="sha256_mismatch"):
        publication_request.load_remote_publication_request(repo, str(corrupt), "2" * 64)
    invalid = b"not-json"
    digest = hashlib.sha256(invalid).hexdigest()
    (store / f"{digest}.json").write_bytes(invalid)
    with pytest.raises(ValueError, match="receipt_invalid"):
        publication_request.load_remote_publication_request(
            repo, str(store / f"{digest}.json"), digest
        )


def test_remote_ref_timeout_preserves_the_missing_fact_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")
    command = ("/opt/git/bin/git", "ls-remote", "origin", "refs/heads/dev")
    monkeypatch.setattr(
        publication_request,
        "observe_git_object",
        lambda *_args: {
            "kind": "commit",
            "object_oid": head,
            "peeled_commit": head,
            "tree_oid": git(repo, "rev-parse", "HEAD^{tree}"),
            "signature": {
                "verdict": "pass",
                "principal": "test",
                "fingerprint": "SHA256:key",
                "trust_anchor_sha256": "a" * 64,
                "verifier": "git verify-commit",
                "verifier_version": "1",
            },
        },
    )
    monkeypatch.setattr(
        publication_execution.git,
        "run_network_git",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            subprocess.TimeoutExpired(command, 30.0, output="", stderr="transport stalled")
        ),
    )

    effect, observations, gaps = publication_request.observe_remote_publication_effect(
        root=repo,
        source_ref=head,
        target_refs=("refs/heads/dev",),
        remotes={"gitlab": "origin"},
        ref_admissions={"refs/heads/dev": {}},
    )
    refs = observations["gitlab"]["refs"]
    assert isinstance(refs, dict)
    observed = refs["refs/heads/dev"]

    assert effect is None
    assert gaps == ("publication_remote_observation_unavailable:gitlab:origin:refs/heads/dev",)
    assert observed == {
        "kind": "git_remote_ref_observation",
        "remote": "origin",
        "ref": "refs/heads/dev",
        "state": "unavailable",
        "reason": "timeout",
        "object_oid": "",
        "peeled_commit": "",
        "tree_oid": "",
        "command": list(command),
        "cwd": repo.resolve().as_posix(),
        "timeout_seconds": 30,
        "stderr": "transport stalled",
    }


def test_publish_unknown_remote_never_invents_non_fast_forward(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, _remotes, head = branch_publication_fixture(tmp_path, source_branch="dev")
    monkeypatch.setattr(
        publication_observation,
        "observe_remote_ref",
        lambda _root, remote, ref: {
            "kind": "git_remote_ref_observation",
            "remote": remote,
            "ref": ref,
            "state": "unavailable",
            "reason": "timeout",
            "object_oid": "",
            "peeled_commit": "",
            "tree_oid": "",
            "command": ["git", "ls-remote", remote, ref],
            "cwd": repo.resolve().as_posix(),
            "timeout_seconds": 30,
            "stderr": "transport stalled",
        },
    )

    payload = run_ethos(
        "publish",
        "--ref",
        "refs/heads/dev",
        "--probe-remote",
        "--expect-head",
        head,
        "--json",
        cwd=repo,
    )

    assert payload["verdict"] == "unknown"
    assert payload["required_gaps"] == [
        "publication_remote_observation_unavailable:gitlab:origin:refs/heads/dev",
        "publication_remote_observation_unavailable:github:github:refs/heads/dev",
    ]
    assert payload["missing_facts_or_evidence"] == payload["required_gaps"]
    assert payload["data"]["push_admission"] == {}
    assert not any("non_fast_forward" in gap for gap in payload["required_gaps"])


def test_publication_rejects_lightweight_or_untrusted_release_tags(tmp_path: Path) -> None:
    repo, _remotes, commit, _tag, _tree, _fingerprint, _anchor_sha256 = signed_publication_fixture(
        tmp_path
    )
    git(repo, "tag", "lightweight", commit)

    lightweight, _observations, lightweight_gaps = (
        publication_request.observe_remote_publication_effect(
            root=repo,
            source_ref="refs/tags/lightweight",
            target_refs=("refs/tags/lightweight",),
            remotes={"gitlab": "origin"},
            ref_admissions={},
        )
    )
    anchor = Path(git(repo, "config", "--path", "--get", "gpg.ssh.allowedSignersFile"))
    anchor.write_text("", encoding="utf-8")
    untrusted, _observations, untrusted_gaps = (
        publication_request.observe_remote_publication_effect(
            root=repo,
            source_ref="refs/tags/v1.2.3",
            target_refs=("refs/tags/v1.2.3",),
            remotes={"gitlab": "origin"},
            ref_admissions={},
        )
    )

    assert lightweight is None
    assert lightweight_gaps == ("publication_source_not_annotated_tag:refs/tags/lightweight",)
    assert untrusted is None
    assert untrusted_gaps == ("publication_source_signature_untrusted:refs/tags/v1.2.3",)


def test_publication_rejects_a_signed_tag_that_disagrees_with_version_authority(
    tmp_path: Path,
) -> None:
    repo, _remotes, commit, _tag, _tree, _fingerprint, _anchor_sha256 = signed_publication_fixture(
        tmp_path
    )
    git(repo, "tag", "-s", "-m", "release v9.9.9", "v9.9.9", commit)

    effect, observations, gaps = publication_request.observe_remote_publication_effect(
        root=repo,
        source_ref="refs/tags/v9.9.9",
        target_refs=("refs/tags/v9.9.9",),
        remotes={"gitlab": "origin"},
        ref_admissions={
            "refs/tags/v9.9.9": {
                "target_ref": "refs/tags/v9.9.9",
                "ref_kind": "tag",
                "role": "release_publication",
                "remote_mutation_allowed": True,
            }
        },
    )

    assert effect is None
    assert observations == {}
    assert gaps == ("publication_source_version_mismatch:v9.9.9!=v1.2.3",)


def test_publish_uses_git_ref_grammar_as_the_positive_name_authority(
    tmp_path: Path,
) -> None:
    repo, _remotes, head = branch_publication_fixture(tmp_path)
    payload = run_ethos_blocked(
        "publish",
        "--ref",
        "refs/heads/proposal/topic~1",
        "--probe-remote",
        "--expect-head",
        head,
        "--json",
        cwd=repo,
    )
    assert payload["required_gaps"] == [
        "publication_target_ref_invalid:refs/heads/proposal/topic~1"
    ]


@pytest.mark.parametrize("source_branch", ["dev", "candidate/dev", "work/review"])
def test_review_publication_uses_the_selected_object_not_candidate_checkout(
    tmp_path: Path, source_branch: str
) -> None:
    """Review projection cannot require a local integration role or product proof."""
    repo, remotes, head = branch_publication_fixture(
        tmp_path, source_branch=source_branch, proof=False
    )

    payload = branch_publication(repo, head, "--apply", "--authorize")

    assert payload["state"] == "published"
    assert payload["data"]["proof_admission"]["state"] == "not_required"
    assert payload["data"]["transition_plan"]["prior_attestations"] == {}
    assert {proposal_ref(remote) for remote in remotes.values()} == {head}
    assert git(repo, "rev-parse", "dev") == head
    assert load_branch_role_policy(repo).role_for_branch("proposal/topic") == "other"


def test_publish_and_pre_push_bind_the_same_exact_proof_attestation(tmp_path: Path) -> None:
    repo, remotes, head = branch_publication_fixture(tmp_path)
    for remote in remotes.values():
        git(remote, "update-ref", "refs/heads/main", head)

    payload = branch_publication(repo, head, target_ref="refs/heads/main")
    plan = TransitionPlan.model_validate(payload["data"]["transition_plan"])
    reports = payload["data"]["push_admission"]
    selected = {report["proof_admission"]["attestation"]["id"] for report in reports.values()}

    assert len(selected) == 1
    proof = plan.prior_attestations["proof"]
    assert proof["id"] == selected.pop()
    assert proof["commit"] == head
    assert proof["tree"] == git(repo, "rev-parse", f"{head}^{{tree}}")
    assert proof["verdict"] == "pass"
    assert proof["policy_digest"]
    assert proof["gate_ids"]
    assert all(report["next_action"] == "" for report in reports.values())


def test_publish_and_pre_push_report_the_same_exact_missing_proof_action(tmp_path: Path) -> None:
    repo, remotes, head = branch_publication_fixture(tmp_path)
    for remote in remotes.values():
        git(remote, "update-ref", "refs/heads/main", head)
    install_fixture_hook_runtime(repo)
    attestation_root = git(repo, "rev-parse", "--verify", "refs/ethos/attestations-set")
    git(repo, "update-ref", "-d", "refs/ethos/attestations-set", attestation_root)

    payload = branch_publication(repo, head, blocked=True, target_ref="refs/heads/main")
    action = runtime_command(
        repo,
        "prove",
        "--root",
        repo.as_posix(),
        "--execute",
        "--expect-head",
        head,
        "--json",
    )

    assert payload["required_gaps"] == ["proof_not_proven"]
    assert payload["next_action"] == action
    assert payload["data"]["proof_admission"]["next_action"] == action
    assert {report["next_action"] for report in payload["data"]["push_admission"].values()} == {
        action
    }


def test_missing_selected_runtime_reports_hook_repair_instead_of_crashing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")
    monkeypatch.setattr(
        proof_adapter,
        "proof_for_repository_transition",
        lambda _root, _head: (None, ["proof_not_proven"]),
    )
    monkeypatch.setattr(
        proof_adapter,
        "runtime_command",
        lambda *_args: (_ for _ in ()).throw(ValueError("hook_runtime_current_missing")),
    )
    repair = f"/runtime/bin/ethos hook install --root {repo.as_posix()} --json"
    monkeypatch.setattr(
        proof_adapter,
        "hook_runtime_binding",
        lambda _root: {"next_action": repair},
    )

    report = proof_adapter.proof_admission_report(repo, head, repository_transition=True)

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["proof_not_proven", "hook_runtime_current_missing"]
    assert report["next_action"] == repair


def test_mixed_review_and_release_targets_retain_the_repository_proof_floor(tmp_path: Path):
    """Adding a review target cannot excuse a release target's missing proof."""
    repo, remotes, head = branch_publication_fixture(tmp_path, proof=False)
    for remote in remotes.values():
        git(remote, "update-ref", "refs/heads/main", head)

    report = branch_publication(repo, head, "--ref", "refs/heads/main", blocked=True)

    assert "proof_not_proven" in report["required_gaps"]
    assert report["data"]["proof_admission"]["selection"] == "repository_transition"
    assert {proposal_ref(remote) for remote in remotes.values()} == {""}
