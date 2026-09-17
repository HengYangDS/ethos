"""Source, role and introduced-range admission through public publication surfaces."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest

import ethos.adapters.mutation.proof as proof_adapter
import ethos.adapters.mutation.publication.execution as publication_execution
import ethos.adapters.mutation.publication.request as publication_request
import ethos.repository.release.publication as release_publication
from ethos.adapters.admission.publication import ref_update_admission_report
from ethos.adapters.repo.runtime.selection import runtime_command
from ethos.adapters.store.state.schema import local_state_root
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.plan import TransitionPlan
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.unit.cli.land.publication.support import branch_publication
from tests.unit.cli.land.publication.support import branch_publication_fixture
from tests.unit.cli.land.publication.support import proposal_ref
from tests.unit.cli.land.publication.support import signed_publication_fixture
from tests.unit.cli.land.publication.support import unavailable_remote


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


@pytest.mark.parametrize("timeout", [False, True])
def test_publication_remote_failure_matrix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, timeout: bool
) -> None:
    repo, _peers, head = branch_publication_fixture(tmp_path, proof=False)
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
    command = ("git", "ls-remote", "origin", "refs/heads/dev")

    def transport(*_args, **_kwargs):
        if timeout:
            raise subprocess.TimeoutExpired(command, 30, stderr="transport stalled")
        return subprocess.CompletedProcess(command, 1, "", "transport failed")

    monkeypatch.setattr(publication_execution.git, "run_network_git", transport)
    effect, observations, gaps = publication_request.observe_remote_publication_effect(
        root=repo,
        source_ref=head,
        target_refs=("refs/heads/dev",),
        remotes={"gitlab": "origin"},
        ref_admissions={"refs/heads/dev": {}},
    )
    assert effect is None
    assert gaps == ("publication_remote_observation_unavailable:gitlab:origin:refs/heads/dev",)

    observed = observations["gitlab"]["refs"]["refs/heads/dev"]
    if timeout:
        assert observed == {
            **unavailable_remote(repo, "origin", "refs/heads/dev"),
            "command": list(command),
        }
    else:
        assert observed["reason"] == "ls_remote_failed"
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


@pytest.mark.parametrize(
    ("case", "name", "gap"),
    [
        (
            "lightweight",
            "lightweight",
            "publication_source_not_annotated_tag:refs/tags/lightweight",
        ),
        ("trust", "v1.2.3", "publication_source_signature_untrusted:refs/tags/v1.2.3"),
        ("version", "v9.9.9", "publication_source_version_mismatch:v9.9.9!=v1.2.3"),
    ],
)
def test_publication_rejects_invalid_release_objects(
    tmp_path: Path, case: str, name: str, gap: str
) -> None:
    repo, _peers, commit, *_rest = signed_publication_fixture(tmp_path)
    if case == "lightweight":
        git(repo, "tag", name, commit)
    elif case == "version":
        git(repo, "tag", "-s", "-m", "different version", name, commit)
    else:
        Path(git(repo, "config", "--path", "--get", "gpg.ssh.allowedSignersFile")).write_text("")
    ref = f"refs/tags/{name}"
    effect, observations, gaps = publication_request.observe_remote_publication_effect(
        root=repo,
        source_ref=ref,
        target_refs=(ref,),
        remotes={"gitlab": "origin"},
        ref_admissions={},
    )
    assert effect is None
    assert observations == {}
    assert gaps == (gap,)


def test_publish_uses_git_ref_grammar_as_the_positive_name_authority(
    tmp_path: Path,
) -> None:
    repo, _remotes, head = branch_publication_fixture(tmp_path)
    payload = branch_publication(repo, head, blocked=True, target_ref="refs/heads/proposal/topic~1")
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

        def absent(*_args):
            message = "hook_runtime_current_missing"
            raise ValueError(message)

        monkeypatch.setattr(proof_adapter, "runtime_command", absent)
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
        assert {report["proof_admission"]["attestation"]["id"] for report in reports.values()} == {
            proof["id"]
        }
        assert proof["commit"] == head
        assert proof["tree"] == git(repo, "rev-parse", f"{head}^{{tree}}")
        assert proof["verdict"] == "pass"
        assert proof["policy_digest"]
        assert proof["gate_ids"]
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
