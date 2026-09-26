"""Source, role and introduced-range admission through public publication surfaces."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

import ethos.adapters.mutation.proof as proof_adapter
import ethos.adapters.mutation.publication.execution as publication_execution
import ethos.adapters.mutation.publication.request as publication_request
import ethos.adapters.repo.commit.integration as commit_integration
import ethos.repository.release.publication as release_publication
from ethos.adapters.admission.publication import publication_proof_admission
from ethos.adapters.admission.publication import ref_update_admission_report
from ethos.adapters.repo.git_object import zero_oid
from ethos.adapters.repo.runtime.selection import runtime_command
from ethos.adapters.store.state.schema import local_state_root
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.value import mutable_json
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.unit.cli.land.publication.support import branch_publication
from tests.unit.cli.land.publication.support import branch_publication_fixture
from tests.unit.cli.land.publication.support import proposal_ref


@pytest.mark.parametrize("valid", [False, True])
def test_exact_publication_policy_rejects_inconsistent_release_roles(
    tmp_path: Path, *, valid: bool
) -> None:
    """Mutable checkout fixes cannot conceal invalid selected Git-tree policy."""
    repo = init_git_repo(tmp_path / "roles")
    before = git(repo, "rev-parse", "HEAD")
    branches = '["dev", "main"]' if valid else '["dev"]'
    head = commit_fixture_file(
        repo,
        ".ethos/release.toml",
        f"[protected_refs]\nbranches = {branches}\ntags = []\n",
        "declare release roles",
    )
    (repo / ".ethos/release.toml").write_text(
        '[protected_refs]\nbranches = ["dev", "main"]\ntags = []\n', encoding="utf-8"
    )
    report = ref_update_admission_report(
        repo,
        target_ref="refs/heads/dev",
        proposed_head=head,
        remote_head=before,
        remote_name="origin",
    )
    assert report["verdict"] == ("pass" if valid else "block"), report
    if not valid:
        assert any("protected_branches_policy_missing" in gap for gap in report["required_gaps"])
    assert git(repo, "rev-parse", "HEAD") == head


def test_publish_preserves_source_trust_gap_before_remote_observation(tmp_path: Path) -> None:
    repo, remotes, _signed_head = branch_publication_fixture(tmp_path)
    git(repo, "config", "commit.gpgsign", "false")
    head = commit_fixture_file(
        repo,
        "unsigned.txt",
        "unsigned proposal source\n",
        "test: create unsigned publication source",
    )

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
    cases = [({**local, "peers": {}}, "declaration_invalid")]
    for field, value, gap in (
        ("extra", 1, "peer_declaration_invalid"),
        ("id", 1, "peer_declaration_invalid"),
        ("capabilities", [1], "peer_declaration_invalid"),
        ("ci_surface", 1, "peer_declaration_invalid"),
        ("git_remote", "../x", "git_remote_invalid"),
        ("capabilities", [], "capabilities_invalid"),
        ("capabilities", [*peer["capabilities"], "ci_cd"], "ci_surface_missing"),
        ("ci_surface", "ci.yml", "ci_surface_without_capability"),
    ):
        cases.append(({**local, "peers": [{**peer, field: value}]}, gap))
    cases.extend(
        ({**local, "local_verification_command": value, "peers": []}, gap)
        for value, gap in (
            ("", "command_missing"),
            ("'", "command_invalid"),
            ('""', "command_not_regular"),
            ("/bin/sh", "command_path_escape"),
            ("folder", "command_not_regular"),
        )
    )
    for declaration, gap in cases:
        topology = release_publication.publication_topology(tmp_path, {"publication": declaration})
        assert isinstance(topology["required_gaps"], list)
        assert any(gap in item for item in topology["required_gaps"])
    assert release_publication.publication_source_version_gaps(
        source_ref="refs/tags/v1", annotated_tag=True, version_text=None
    ) == ("publication_source_version_invalid:v1",)
    topology = {"required_gaps": [], "remotes": [{"id": "gitlab", "git_remote": "origin"}]}
    for ref, remote, gap in (
        ("invalid", "origin", "ref_unavailable"),
        ("refs/heads/dev", "", "name_missing"),
        ("refs/heads/dev", "other", "target_unknown"),
    ):
        admission = release_publication.publication_ref_admission(
            topology,
            policy=load_branch_role_policy(Path.cwd()),
            target_ref=ref,
            release_tags=("v*",),
            remote_name=remote,
        )
        assert isinstance(admission["enforcement_gaps"], list)
        assert any(gap in item for item in admission["enforcement_gaps"])


def test_ordinary_publication_does_not_validate_history_repair(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Current, created, and advancing refs need no rewritten-history proof."""
    repo, peers, head = branch_publication_fixture(tmp_path, proof=False, peer_ids=("gitlab",))
    repair = Mock(side_effect=AssertionError("ordinary publication queried history repair"))
    monkeypatch.setattr(publication_request, "repaired_peer_ref_provenance", repair)

    def observe(source: str, expected: str) -> None:
        effect, observations, gaps = publication_request.observe_remote_publication_effect(
            root=repo,
            source_ref=source,
            target_refs=("refs/heads/dev",),
            remotes={"gitlab": str(peers["gitlab"])},
            ref_admissions={
                "refs/heads/dev": {"ref_kind": "branch", "remote_mutation_allowed": True}
            },
        )
        assert not gaps, (observations, gaps)
        assert effect is not None
        update = effect.targets[0].updates[0]
        assert (update.expected, update.desired) == (expected, source)

    observe(head, head)
    advanced = commit_fixture_file(repo, "next.txt", "next\n", "fix: next contribution")
    observe(advanced, head)
    git(peers["gitlab"], "update-ref", "-d", "refs/heads/dev")
    observe(advanced, zero_oid(repo))
    repair.assert_not_called()


def test_ordinary_commit_range_does_not_validate_history_repair(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Introduced-commit admission checks normal ancestry before repair provenance."""
    repo, _peers, head = branch_publication_fixture(tmp_path, proof=False, peer_ids=("gitlab",))
    repair = Mock(side_effect=AssertionError("ordinary commit range queried history repair"))
    monkeypatch.setattr(commit_integration, "repaired_peer_ref_provenance", repair)

    def admit(source: str, remote: str, *, trusted_baseline: str = "") -> None:
        report = commit_integration.commit_range_admission_report(
            repo,
            target_ref="refs/heads/dev",
            proposed_head=source,
            remote_head=remote,
            remote_name="origin",
            trusted_baseline=trusted_baseline,
        )
        assert report["verdict"] == "pass", report

    admit(head, head)
    advanced = commit_fixture_file(repo, "next.txt", "next\n", "fix: next contribution")
    admit(advanced, head)
    admit(advanced, zero_oid(repo), trusted_baseline=head)
    repair.assert_not_called()


def test_publication_remote_failure_matrix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """One peer advertisement preserves every ref and failed receipt boundary."""
    repo, _peers, head = branch_publication_fixture(tmp_path, proof=False)
    for targets in ((), ("refs/heads/dev", "refs/tags/v1")):
        assert publication_request.observe_remote_publication_effect(
            root=repo, source_ref=head, target_refs=targets, remotes={}, ref_admissions={}
        )[2] == ("publication_target_ref_kind_mismatch",)
    refs = ("refs/heads/dev", "refs/heads/main")
    command = ("git", "ls-remote", "origin", *refs)
    row = f"{head}\t{refs[0]}\n"
    faults = (
        (subprocess.TimeoutExpired(command, 30, stderr="transport stalled"), "timeout"),
        (subprocess.TimeoutExpired(command, 30, stderr=b"transport stalled"), "timeout"),
        (
            publication_execution.git.GitExecutionError("spawn_failed", reason="missing"),
            "spawn_failed",
        ),
        (subprocess.CompletedProcess(command, 1, "", "failed"), "ls_remote_failed"),
        *(
            (subprocess.CompletedProcess(command, 0, raw, ""), "remote_ref_observation_ambiguous")
            for raw in (
                row + row,
                row + f"{head}\trefs/heads/extra\n",
                "malformed",
                f"{head}\trefs/tags/v1^{{}}\n",
            )
        ),
    )
    for fault, reason in faults:
        monkeypatch.setattr(publication_execution.git, "run_network_git", Mock(side_effect=[fault]))
        effect, observations, gaps = publication_request.observe_remote_publication_effect(
            root=repo,
            source_ref=head,
            target_refs=refs,
            remotes={"gitlab": "origin"},
            ref_admissions={},
        )
        assert effect is None
        assert gaps == tuple(
            f"publication_remote_observation_unavailable:gitlab:origin:{ref}" for ref in refs
        )
        for observed in observations["gitlab"]["refs"].values():
            assert [observed[k] for k in ("state", "reason", "object_oid")] == [
                "unavailable",
                reason,
                "",
            ]
            if reason == "timeout":
                assert observed["command"] == list(command)
                assert observed["cwd"] == repo.resolve().as_posix()
                assert (observed["timeout_seconds"], observed["stderr"]) == (
                    30,
                    "transport stalled",
                )
                assert (observed["peeled_commit"], observed["tree_oid"]) == ("", "")
    store = local_state_root(repo) / "requests/publication"
    store.mkdir(parents=True)
    failures = (
        (tmp_path / "elsewhere.json", "1" * 64, "path_invalid"),
        (store / f"{'1' * 64}.json", "1" * 64, "receipt_missing"),
    )
    invalid = b"not-json"
    for digest, error in (
        ("2" * 64, "sha256_mismatch"),
        (hashlib.sha256(invalid).hexdigest(), "receipt_invalid"),
    ):
        path = store / f"{digest}.json"
        path.write_bytes(invalid)
        failures += ((path, digest, error),)
    for path, digest, error in failures:
        with pytest.raises(ValueError, match=error):
            publication_request.load_remote_publication_request(repo, str(path), digest)


def test_publish_uses_git_ref_grammar_as_the_positive_name_authority(
    tmp_path: Path,
) -> None:
    repo, _remotes, head = branch_publication_fixture(tmp_path)
    payload = branch_publication(repo, head, blocked=True, target_ref="refs/heads/proposal/topic~1")
    assert payload["required_gaps"] == [
        "publication_target_ref_invalid:refs/heads/proposal/topic~1"
    ]


@pytest.mark.parametrize(
    ("options", "gap"),
    [
        (("--peer", "unknown"), "publication_peer_unknown:unknown"),
        (("--peer", "github", "--peer", "github"), "publication_peer_duplicate:github"),
    ],
)
def test_publish_rejects_invalid_peer_selection_before_remote_observation(
    tmp_path: Path, options: tuple[str, ...], gap: str
) -> None:
    repo, _peers, head = branch_publication_fixture(tmp_path, proof=False)

    payload = branch_publication(repo, head, *options, blocked=True)

    assert payload["required_gaps"] == [gap]
    assert payload["data"]["remote_observations"] == {}
    assert payload["data"]["request_receipt"] == {}


def test_selected_proposal_peer_does_not_borrow_repository_proof(tmp_path: Path) -> None:
    repo, peers, head = branch_publication_fixture(tmp_path, proof=False)
    git(repo, "remote", "set-url", "origin", str(tmp_path / "unavailable-gitlab.git"))

    payload = branch_publication(repo, head, "--peer", "github", "--apply", "--authorize")

    assert (payload["verdict"], payload["state"]) == ("pass", "published")
    assert payload["data"]["proof_admission"]["state"] == "not_required"
    assert proposal_ref(peers["github"]) == head
    assert proposal_ref(peers["gitlab"]) == ""


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


@pytest.mark.parametrize("state", ["proven", "missing", "runtime-missing", "mixed"])
def test_publication_and_pre_push_share_exact_proof_and_continuation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, state: str
) -> None:
    """One proof owner supplies both successful bindings and the missing-proof action."""
    repo, peers, head = branch_publication_fixture(tmp_path, accepted=True)
    for remote in peers.values():
        git(remote, "update-ref", "refs/heads/main", head)
    proven = state == "proven"
    if not proven:
        monkeypatch.setattr(
            proof_adapter,
            "proof_for_repository_transition",
            lambda *_: (None, ["proof_not_proven"]),
        )
    if state == "runtime-missing":
        monkeypatch.setattr(
            proof_adapter,
            "runtime_command",
            Mock(side_effect=ValueError("hook_runtime_current_missing")),
        )
        repair = f"/runtime/bin/ethos hook install --root {repo} --json"
        monkeypatch.setattr(
            proof_adapter, "hook_runtime_binding", lambda _: {"next_action": repair}
        )
        result = proof_adapter.proof_admission_report(repo, head, repository_transition=True)
        assert result["required_gaps"] == ["proof_not_proven", "hook_runtime_current_missing"]
        assert result["verdict"] == "block"
        assert result["next_action"] == repair
        return
    payload = branch_publication(
        repo,
        head,
        *(("--ref", "refs/heads/proposal/mixed") if state == "mixed" else ()),
        blocked=not proven,
        target_ref="refs/heads/main",
    )
    assert payload["data"]["proof_admission"]["selection"] == "repository_transition"
    assert {proposal_ref(remote) for remote in peers.values()} == {""}
    reports = payload["data"]["push_admission"]
    if proven:
        plan = TransitionPlan.model_validate(payload["data"]["transition_plan"])
        proof = plan.prior_attestations["proof"]
        observed = payload["data"]["proof_admission"]
        wrong_head = {**observed, "attestation": {**proof, "commit": "0" * 40}}
        actual = publication_proof_admission(repo, head, ("release_root",), observed=wrong_head)
        assert mutable_json(actual) == observed
        assert {report["proof_admission"]["attestation"]["id"] for report in reports.values()} == {
            proof["id"]
        }
        tree = git(repo, "rev-parse", f"{head}^{{tree}}")
        assert (proof["commit"], proof["tree"], proof["verdict"]) == (head, tree, "pass")
        assert all(proof[key] for key in ("policy_digest", "gate_ids"))
        action = ""
    else:
        action = runtime_command(
            repo, "prove", "--root", str(repo), "--execute", "--expect-head", head, "--json"
        )
        assert payload["required_gaps"] == ["proof_not_proven"]
        assert payload["next_action"] == action
        assert payload["data"]["proof_admission"]["next_action"] == action
    assert {report["next_action"] for report in reports.values()} == (
        {"", action} if state == "mixed" else {action}
    )
