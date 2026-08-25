from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest

import ethos.adapters.mutation.proof as proof_adapter
import ethos.adapters.mutation.publication.attestation as publication_attestation
import ethos.adapters.mutation.remote_publication as remote_publication
import ethos.surface.cli.root.publish as publication_cli
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.hook.activation import install_hook_launchers
from ethos.adapters.repo.runtime.selection import runtime_command
from ethos.adapters.store.state.schema import local_state_root
from ethos.contracts.branch.roles import load_branch_role_policy
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.value import mutable_json
from ethos.domain.land.publication import local_ci_owner_scripts
from ethos.domain.land.publication import publication_readiness
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import adopt_and_commit
from tests.support.governed_repository import apply_accepted_closeout
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import seed_executed_proof
from tests.support.governed_repository import write_role_policy


def _write_local_only_publication(repo: Path) -> None:
    release = repo / ".ethos" / "release.toml"
    release.write_text(
        "[publication]\n"
        'local_verification_command = "dev/verify"\n'
        'local_installation_command = "dev/install"\n',
        encoding="utf-8",
    )


def test_publish_reports_invalid_local_ci_fallback_evidence_manifest(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    head = git(repo, "rev-parse", "HEAD")
    seed_executed_proof(repo, head)
    manifest = repo / "build" / "evidence" / "local-ci" / "fallback.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("{not-json", encoding="utf-8")

    payload = run_ethos("publish", "--json", cwd=repo)

    evidence_status = payload["data"]["local_ci_fallback"]["evidence_status"]
    assert evidence_status == {
        "state": "invalid",
        "path": "build/evidence/local-ci/fallback.json",
        "current_head": head,
        "evidence_head": "",
        "verdict": "block",
        "next_action": "rerun dev/verify to refresh local fallback evidence",
    }


def test_publish_reports_local_readiness_without_remote_push() -> None:
    payload = run_ethos("publish", "--json")
    branch = git(Path.cwd(), "branch", "--show-current") or "detached"

    assert payload["summary"]["remote_push"] == "not_performed"
    assert (
        payload["data"]["local_ci_fallback"] == payload["data"]["publication"]["fallback_evidence"]
    )
    fallback = payload["data"]["local_ci_fallback"]
    assert fallback["owner_scripts"] == local_ci_owner_scripts(
        root=Path.cwd(), command=fallback["command"]
    )

    publication = payload["data"]["publication"]
    assert publication["source_branch"] == branch
    assert publication["source_role"] == load_branch_role_policy(Path.cwd()).role_for_branch(branch)
    assert "proposal_branch" not in publication
    assert "local_proposal_package" not in publication
    assert payload["next_action"]


def test_publish_uses_declared_local_verification_command_as_fallback_ssot(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    command = "uv run --locked --no-sync nox -s full"
    release = repo / ".ethos" / "release.toml"
    release.write_text(
        release.read_text(encoding="utf-8").replace(
            'local_verification_command = "dev/verify"',
            f'local_verification_command = "{command}"',
        ),
        encoding="utf-8",
    )
    head = commit_fixture(repo, "declare canonical local verification")
    seed_executed_proof(repo, head)

    payload = run_ethos("publish", "--json", cwd=repo)

    fallback = payload["data"]["local_ci_fallback"]
    assert fallback["command"] == command
    assert fallback["evidence_status"]["next_action"] == (
        f"run {command} as local fallback evidence"
    )
    assert payload["next_action"] == f"run {command} as local fallback evidence"


def test_publish_rejects_fallback_evidence_from_a_retired_verification_command(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    head = git(repo, "rev-parse", "HEAD")
    seed_executed_proof(repo, head)
    manifest = repo / "build" / "evidence" / "local-ci" / "fallback.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        '{"command":"retired/verify","head":"' + head + '","required_gaps":[],"verdict":"pass"}\n',
        encoding="utf-8",
    )

    payload = run_ethos("publish", "--json", cwd=repo)

    evidence = payload["data"]["local_ci_fallback"]["evidence_status"]
    assert evidence["state"] == "stale"
    assert evidence["command"] == "retired/verify"
    assert evidence["next_action"] == "run dev/verify as local fallback evidence"


def test_publish_observes_gitlab_and_github_independently_without_push(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    head = git(repo, "rev-parse", "HEAD")
    seed_executed_proof(repo, head)
    gitlab = tmp_path / "gitlab.git"
    github = tmp_path / "github.git"
    for remote in (gitlab, github):
        git(tmp_path, "init", "--bare", remote.as_posix())
    git(repo, "remote", "add", "origin", gitlab.as_posix())
    git(repo, "remote", "add", "github", github.as_posix())
    git(repo, "push", "--set-upstream", "origin", "dev")
    git(repo, "push", "--set-upstream", "github", "dev")

    payload = run_ethos("publish", "--probe-remote", "--json", cwd=repo)

    assert payload["summary"]["remote_push"] == "not_performed"
    assert payload["summary"]["hosted_ci_status_claimed"] is False
    observations = payload["data"]["remote_observations"]
    assert set(observations) == {"gitlab", "github"}
    assert observations["gitlab"]["availability"]["remote"] == "origin"
    assert observations["github"]["availability"]["remote"] == "github"
    assert payload["data"]["publication"]["remote_observations"] == observations


def test_publish_local_only_does_not_observe_or_require_a_remote(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    _write_local_only_publication(repo)
    head = commit_fixture(repo, "declare local-only publication")
    seed_executed_proof(repo, head)
    payload = run_ethos("publish", "--probe-remote", "--json", cwd=repo)

    assert payload["verdict"] == "pass"


def test_publish_gitlab_only_observes_only_the_declared_peer(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    release = repo / ".ethos" / "release.toml"
    declaration = release.read_text(encoding="utf-8")
    declaration = declaration.split("[[publication.peers]]", 2)
    release.write_text(declaration[0] + "[[publication.peers]]" + declaration[1], encoding="utf-8")
    head = commit_fixture(repo, "declare GitLab-only publication")
    seed_executed_proof(repo, head)
    remote = tmp_path / "gitlab.git"
    git(tmp_path, "init", "--bare", remote.as_posix())
    git(repo, "remote", "add", "origin", remote.as_posix())
    git(repo, "push", "--set-upstream", "origin", "dev")

    payload = run_ethos("publish", "--probe-remote", "--json", cwd=repo)

    assert set(payload["data"]["remote_observations"]) == {"gitlab"}
    assert payload["data"]["remote_topology"]["state"] == "ready"


def test_publish_reports_peer_tracking_without_claiming_a_collective_push(
    tmp_path: Path,
) -> None:
    """A matching tracking ref is an observation, not an executed publication."""
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    head = git(repo, "rev-parse", "HEAD")
    seed_executed_proof(repo, head)
    remote = tmp_path / "origin.git"
    for root, *args in (
        (tmp_path, "init", "--bare", remote.as_posix()),
        (repo, "remote", "add", "origin", remote.as_posix()),
        (repo, "push", "--set-upstream", "origin", "dev"),
    ):
        git(root, *args)

    payload = run_ethos("publish", "--probe-remote", "--json", cwd=repo)

    assert payload["summary"]["remote_sync_states"]["gitlab"] == "synchronized"
    assert payload["summary"]["remote_sync_states"]["github"] == "remote_tracking_missing"
    assert payload["summary"]["remote_publication_state"] == "target_available"
    assert payload["summary"]["remote_push"] == "not_performed"
    assert payload["data"]["publication"]["remote_state"] == "target_available"
    assert (
        payload["data"]["publication"]["remote_observations"]["gitlab"]["sync"]["state"]
        == "synchronized"
    )
    assert payload["data"]["publication"]["remote_push"] == "not_performed"
    assert payload["data"]["mutation"]["decision"]["verdict"] == "unknown"


def test_publish_projects_declared_peer_collections_without_single_remote_aliases(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    head = git(repo, "rev-parse", "HEAD")
    seed_executed_proof(repo, head)

    payload = run_ethos("publish", "--json", cwd=repo)

    assert not {
        "remote_availability_state",
        "remote_sync_state",
        "remote_ahead",
        "remote_behind",
    } & set(payload["summary"])
    assert not {"remote_availability", "remote_sync"} & set(payload["data"])
    assert not {
        "remote_availability",
        "remote_sync",
    } & set(payload["data"]["publication"])


def test_publication_readiness_uses_local_fallback_when_fallback_omits_evidence_status() -> None:
    policy = load_branch_role_policy(Path.cwd())
    command = "dev/verify"
    for evidence_status in ({}, None):
        publication = publication_readiness(
            branch="dev",
            local_ok=True,
            policy=policy,
            local_ci_fallback={"evidence_status": evidence_status},
            local_verification_command=command,
        )

        assert publication["next_action"] == f"run {command} as local fallback evidence"


def test_publish_local_readiness_does_not_project_a_publication_plan(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    write_role_policy(repo)
    git(repo, "checkout", "-b", "lane/topic")

    payload = run_ethos("publish", "--root", repo.as_posix(), "--json", cwd=repo)

    publication = payload["data"]["publication"]
    assert publication["source_branch"] == "lane/topic"
    assert publication["source_role"] == "work_lane"
    assert "proposal_branch" not in publication
    assert "local_proposal_package" not in publication


_PROPOSAL = "terminal-convergence"
_PROPOSAL_REF = f"refs/heads/proposal/{_PROPOSAL}"


def _branch_publication_fixture(
    tmp_path: Path,
    *,
    source_branch: str = "candidate/dev",
    object_format: str = "sha1",
) -> tuple[Path, dict[str, Path], str]:
    repo = init_git_repo(tmp_path / "proposal-repo", object_format=object_format)
    adopt_and_commit(repo)
    _configure_publication_signer(repo, tmp_path)
    (repo / "proposal.txt").write_text("signed proposal source\n", encoding="utf-8")
    git(repo, "add", "proposal.txt")
    git(repo, "commit", "-m", "feat: sign proposal source")
    head = git(repo, "rev-parse", "HEAD")
    if source_branch != "dev":
        git(repo, "branch", source_branch, head)
        git(repo, "checkout", source_branch)
    seed_executed_proof(repo, head)
    remotes: dict[str, Path] = {}
    for peer_id, remote in (("gitlab", "origin"), ("github", "github")):
        target = tmp_path / f"{peer_id}.git"
        git(tmp_path, "init", "--bare", f"--object-format={object_format}", target.as_posix())
        git(repo, "remote", "add", remote, target.as_posix())
        git(repo, "push", remote, "HEAD:refs/heads/dev")
        remotes[peer_id] = target
    return repo, remotes, head


def _branch_publication(repo: Path, head: str | None, *args: str, blocked: bool = False):
    command = ["publish", "--ref", _PROPOSAL_REF, "--probe-remote", *args]
    if head is not None:
        command += ["--expect-head", head]
    runner = run_ethos_blocked if blocked or head is None else run_ethos
    return runner(*command, "--json", cwd=repo)


def _receipt(repo: Path, receipt: dict[str, object], head: str, *, blocked: bool = False):
    runner = run_ethos_blocked if blocked else run_ethos
    return runner(
        "publish",
        "--receipt",
        str(receipt["path"]),
        "--receipt-sha256",
        str(receipt["sha256"]),
        "--apply",
        "--authorize",
        "--expect-head",
        head,
        "--json",
        cwd=repo,
    )


def _proposal_ref(remote: Path) -> str:
    return git(remote, "for-each-ref", "--format=%(objectname)", _PROPOSAL_REF)


def _configure_publication_signer(repo: Path, root: Path) -> tuple[Path, str]:
    key = root / "publication-signer"
    subprocess.run(
        ("/usr/bin/ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", key.as_posix()),
        check=True,
        capture_output=True,
        text=True,
    )
    public = key.with_suffix(".pub")
    fingerprint = subprocess.run(
        ("/usr/bin/ssh-keygen", "-lf", public.as_posix(), "-E", "sha256"),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split()[1]
    anchor = root / "allowed-signers"
    anchor.write_text(
        f'test@example.com namespaces="git" {public.read_text(encoding="utf-8").strip()}\n',
        encoding="utf-8",
    )
    anchor.chmod(0o600)
    for name, value in (
        ("gpg.format", "ssh"),
        ("gpg.ssh.program", "/usr/bin/ssh-keygen"),
        ("gpg.ssh.allowedSignersFile", anchor.as_posix()),
        ("user.signingkey", public.as_posix()),
        ("user.email", "test@example.com"),
        ("commit.gpgsign", "true"),
    ):
        git(repo, "config", name, value)
    return anchor, fingerprint


def _signed_publication_fixture(
    tmp_path: Path,
) -> tuple[Path, dict[str, Path], str, str, str, str, str]:
    repo = init_git_repo(tmp_path / "publication-repo")
    adopt_and_commit(repo)
    anchor, fingerprint = _configure_publication_signer(repo, tmp_path)
    release = repo / ".ethos/release.toml"
    release.write_text(
        '[protected_refs]\nbranches = ["main", "dev"]\ntags = ["v*"]\n\n'
        + release.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (repo / "release.txt").write_text("release\n", encoding="utf-8")
    git(repo, "add", "release.txt")
    git(repo, "commit", "-m", "feat: publish exact local object")
    commit = git(repo, "rev-parse", "HEAD")
    tree = git(repo, "rev-parse", "HEAD^{tree}")
    git(repo, "tag", "-s", "-m", "release v1.2.3", "v1.2.3")
    tag = git(repo, "rev-parse", "refs/tags/v1.2.3")
    remotes: dict[str, Path] = {}
    for peer_id, remote in (("gitlab", "origin"), ("github", "github")):
        target = tmp_path / f"publication-{peer_id}.git"
        git(tmp_path, "init", "--bare", target.as_posix())
        git(repo, "remote", "add", remote, target.as_posix())
        remotes[peer_id] = target
    return (
        repo,
        remotes,
        commit,
        tag,
        tree,
        fingerprint,
        hashlib.sha256(anchor.read_bytes()).hexdigest(),
    )


def test_publication_projects_one_trusted_annotated_tag_exactly_to_two_peers(
    tmp_path: Path,
) -> None:
    repo, remotes, commit, tag, tree, fingerprint, anchor_sha256 = _signed_publication_fixture(
        tmp_path
    )

    effect, observations, gaps = remote_publication.observe_remote_publication_effect(
        root=repo,
        source_ref="refs/tags/v1.2.3",
        target_refs=("refs/tags/v1.2.3",),
        remotes={"gitlab": "origin", "github": "github"},
        ref_admissions={
            "refs/tags/v1.2.3": {
                "target_ref": "refs/tags/v1.2.3",
                "ref_kind": "tag",
                "role": "release_publication",
                "remote_mutation_allowed": True,
            }
        },
    )

    assert gaps == ()
    assert effect is not None
    assert effect.source.model_dump(mode="json") == {
        "kind": "annotated-tag",
        "object_oid": tag,
        "peeled_commit": commit,
        "tree_oid": tree,
        "signature": {
            "verdict": "pass",
            "principal": "test@example.com",
            "fingerprint": fingerprint,
            "trust_anchor_sha256": anchor_sha256,
            "verifier": "git verify-tag",
            "verifier_version": git(repo, "version"),
        },
    }
    assert all(
        observation["refs"]["refs/tags/v1.2.3"]["object_oid"] == "0" * 40
        for observation in observations.values()
    )

    seed_executed_proof(repo, commit)
    proof = publication_cli.proof_admission_report(repo, commit, repository_transition=True)[
        "attestation"
    ]
    plan = remote_publication.compile_remote_publication_request(
        root=repo,
        effect=effect,
        proof={**proof, "selection": "repository_transition"},
    )
    applied = remote_publication.apply_remote_publication_effect(root=repo, plan=plan)

    assert applied["state"] == "applied"
    for remote in remotes.values():
        assert git(remote, "rev-parse", "refs/tags/v1.2.3") == tag
        assert git(remote, "rev-parse", "refs/tags/v1.2.3^{}") == commit
        assert git(remote, "rev-parse", "refs/tags/v1.2.3^{tree}") == tree


def test_publication_rejects_lightweight_or_untrusted_release_tags(tmp_path: Path) -> None:
    repo, _remotes, commit, _tag, _tree, _fingerprint, _anchor_sha256 = _signed_publication_fixture(
        tmp_path
    )
    git(repo, "tag", "lightweight", commit)

    lightweight, _observations, lightweight_gaps = (
        remote_publication.observe_remote_publication_effect(
            root=repo,
            source_ref="refs/tags/lightweight",
            target_refs=("refs/tags/lightweight",),
            remotes={"gitlab": "origin"},
            ref_admissions={},
        )
    )
    anchor = Path(git(repo, "config", "--path", "--get", "gpg.ssh.allowedSignersFile"))
    anchor.write_text("", encoding="utf-8")
    untrusted, _observations, untrusted_gaps = remote_publication.observe_remote_publication_effect(
        root=repo,
        source_ref="refs/tags/v1.2.3",
        target_refs=("refs/tags/v1.2.3",),
        remotes={"gitlab": "origin"},
        ref_admissions={},
    )

    assert lightweight is None
    assert lightweight_gaps == ("publication_source_not_annotated_tag:refs/tags/lightweight",)
    assert untrusted is None
    assert untrusted_gaps == ("publication_source_signature_untrusted:refs/tags/v1.2.3",)


def test_publication_apply_rechecks_bound_local_object_trust_before_any_push(
    tmp_path: Path,
) -> None:
    repo, remotes, _commit, _tag, _tree, _fingerprint, _anchor_sha256 = _signed_publication_fixture(
        tmp_path
    )
    effect, _observations, gaps = remote_publication.observe_remote_publication_effect(
        root=repo,
        source_ref="refs/tags/v1.2.3",
        target_refs=("refs/tags/v1.2.3",),
        remotes={"gitlab": "origin", "github": "github"},
        ref_admissions={
            "refs/tags/v1.2.3": {
                "target_ref": "refs/tags/v1.2.3",
                "ref_kind": "tag",
                "role": "release_publication",
                "remote_mutation_allowed": True,
            }
        },
    )
    assert gaps == ()
    assert effect is not None
    seed_executed_proof(repo, effect.source.peeled_commit)
    proof = publication_cli.proof_admission_report(
        repo, effect.source.peeled_commit, repository_transition=True
    )["attestation"]
    plan = remote_publication.compile_remote_publication_request(
        root=repo,
        effect=effect,
        proof={**proof, "selection": "repository_transition"},
    )
    anchor = Path(git(repo, "config", "--path", "--get", "gpg.ssh.allowedSignersFile"))
    anchor.write_text("", encoding="utf-8")

    blocked = remote_publication.apply_remote_publication_effect(root=repo, plan=plan)

    assert blocked["state"] == "preflight_blocked"
    assert blocked["required_gaps"] == ["publication_source_signature_drift"]
    for remote in remotes.values():
        assert git(remote, "for-each-ref", "--format=%(objectname)", "refs/tags/v1.2.3") == ""


def test_publish_projects_one_signed_release_tag_through_the_full_ref_command(
    tmp_path: Path,
) -> None:
    repo, remotes, commit, tag, tree, _fingerprint, _anchor_sha256 = _signed_publication_fixture(
        tmp_path
    )
    seed_executed_proof(repo, commit)

    dry_run = run_ethos(
        "publish",
        "--ref",
        "refs/tags/v1.2.3",
        "--probe-remote",
        "--expect-head",
        commit,
        "--json",
        cwd=repo,
    )
    receipt = dry_run["data"]["request_receipt"]
    assert dry_run["state"] == "ready_to_publish"
    assert dry_run["data"]["remote_effect"]["source"]["object_oid"] == tag

    applied = _receipt(repo, receipt, commit)

    assert applied["state"] == "published"
    for remote in remotes.values():
        assert git(remote, "rev-parse", "refs/tags/v1.2.3") == tag
        assert git(remote, "rev-parse", "refs/tags/v1.2.3^{}") == commit
        assert git(remote, "rev-parse", "refs/tags/v1.2.3^{tree}") == tree


def test_publish_signed_accepted_tag_does_not_require_invoking_work_lane_authority(
    tmp_path: Path,
) -> None:
    repo, remotes, accepted_head, tag, tree, _fingerprint, _anchor_sha256 = (
        _signed_publication_fixture(tmp_path)
    )
    seed_executed_proof(repo, accepted_head)
    git(repo, "checkout", "-b", "work/stale-invoker")
    (repo / "invoker.txt").write_text("invoking checkout is not the release subject\n")
    git(repo, "add", "invoker.txt")
    git(repo, "commit", "-m", "test: create unrelated invoking checkout")

    dry_run = run_ethos(
        "publish",
        "--ref",
        "refs/tags/v1.2.3",
        "--probe-remote",
        "--expect-head",
        accepted_head,
        "--json",
        cwd=repo,
    )

    assert dry_run["state"] == "ready_to_publish"
    assert dry_run["summary"]["source_head"] == accepted_head
    assert dry_run["data"]["proof_admission"]["attestation"]["commit"] == accepted_head
    assert dry_run["data"]["remote_effect"]["source"] == {
        "kind": "annotated-tag",
        "object_oid": tag,
        "peeled_commit": accepted_head,
        "tree_oid": tree,
        "signature": dry_run["data"]["remote_effect"]["source"]["signature"],
    }
    assert all(
        git(remote, "for-each-ref", "--format=%(objectname)", "refs/tags/v1.2.3") == ""
        for remote in remotes.values()
    )

    applied = _receipt(repo, dry_run["data"]["request_receipt"], accepted_head)

    assert applied["state"] == "published"
    assert all(git(remote, "rev-parse", "refs/tags/v1.2.3") == tag for remote in remotes.values())


def test_publish_rejects_signed_proven_tag_that_is_not_the_current_product_head(
    tmp_path: Path,
) -> None:
    repo, _remotes, tagged_head, _tag, _tree, _fingerprint, _anchor_sha256 = (
        _signed_publication_fixture(tmp_path)
    )
    seed_executed_proof(repo, tagged_head)
    (repo / "accepted.txt").write_text("accepted advanced after the tag\n")
    git(repo, "add", "accepted.txt")
    git(repo, "commit", "-m", "test: advance accepted product head")

    blocked = run_ethos_blocked(
        "publish",
        "--ref",
        "refs/tags/v1.2.3",
        "--probe-remote",
        "--expect-head",
        tagged_head,
        "--json",
        cwd=repo,
    )

    assert blocked["required_gaps"] == ["release_publication_source_not_current"]


def test_publish_uses_git_ref_grammar_as_the_positive_name_authority(
    tmp_path: Path,
) -> None:
    repo, _remotes, head = _branch_publication_fixture(tmp_path)
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


def test_publish_proposal_target_requires_the_local_candidate_source(tmp_path: Path) -> None:
    repo, _remotes, head = _branch_publication_fixture(tmp_path, source_branch="dev")

    assert _branch_publication(repo, head, blocked=True)["required_gaps"] == [
        "publication_source_role_mismatch:dev:proposal_lane"
    ]


def test_publish_branch_dry_run_and_apply_share_one_plan_and_attestation(
    tmp_path: Path,
) -> None:
    repo, remotes, head = _branch_publication_fixture(tmp_path)
    dry_run = _branch_publication(repo, head)
    receipt = dry_run["data"]["request_receipt"]
    assert Path(receipt["path"]).parent == local_state_root(repo) / "requests" / "publication"
    plan = TransitionPlan.model_validate_json(Path(receipt["path"]).read_bytes())
    assert (dry_run["verdict"], plan.verdict, plan.effect["operation"]) == (
        "pass",
        "pass",
        "git.ref.compare-and-swap",
    )
    assert {_proposal_ref(remote) for remote in remotes.values()} == {""}

    direct = _branch_publication(repo, head, "--apply", "--authorize")
    assert direct["data"]["transition_plan"] == dry_run["data"]["transition_plan"]
    for remote in remotes.values():
        git(remote, "update-ref", "-d", _PROPOSAL_REF)

    applied = _receipt(repo, receipt, head)
    set_root, selected = read_attestation_set(repo)
    attestation = next(item for item in selected if item.predicate == "publication:remote-effect")
    assert applied["state"] == "published"
    assert applied["data"]["remote_effect"]["attestation"]["set_root"] == set_root
    assert mutable_json(attestation.payload.body["plan"]) == applied["data"]["transition_plan"]
    assert {_proposal_ref(remote) for remote in remotes.values()} == {head}


def test_publish_and_pre_push_bind_the_same_exact_proof_attestation(tmp_path: Path) -> None:
    repo, _remotes, head = _branch_publication_fixture(tmp_path)

    payload = _branch_publication(repo, head)
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
    repo, _remotes, head = _branch_publication_fixture(tmp_path)
    install_hook_launchers(repo)
    attestation_root = git(repo, "rev-parse", "--verify", "refs/ethos/attestations-set")
    git(repo, "update-ref", "-d", "refs/ethos/attestations-set", attestation_root)

    payload = _branch_publication(repo, head, blocked=True)
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
    assert "hook install" in report["next_action"]
    assert f"--root {repo.as_posix()}" in report["next_action"]


def test_publish_branch_retry_records_one_terminal_attestation_after_interruption(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A retry records the one terminal effect after remote refs already moved."""
    repo, remotes, head = _branch_publication_fixture(tmp_path)
    receipt = _branch_publication(repo, head)["data"]["request_receipt"]

    with monkeypatch.context() as interrupted:
        interrupted.setattr(
            publication_attestation,
            "record_attestations",
            lambda _root, _attestation: (_ for _ in ()).throw(RuntimeError("interrupted")),
        )
        with pytest.raises(RuntimeError, match="interrupted"):
            _receipt(repo, receipt, head)

    assert {_proposal_ref(remote) for remote in remotes.values()} == {head}

    recovered = _receipt(repo, receipt, head)
    root, attestations = read_attestation_set(repo)
    remote_effects = [
        attestation
        for attestation in attestations
        if attestation.predicate == "publication:remote-effect"
    ]

    assert recovered["state"] == "published"
    assert root == git(repo, "rev-parse", "refs/ethos/attestations-set")
    assert recovered["data"]["remote_effect"]["attempts"] == [
        {
            "id": "gitlab",
            "remote": "origin",
            "state": "already_applied",
            "exit_code": 0,
            "stderr": "",
        },
        {
            "id": "github",
            "remote": "github",
            "state": "already_applied",
            "exit_code": 0,
            "stderr": "",
        },
    ]
    assert len(remote_effects) == 1
    assert remote_effects[0].payload.body["state"] == "applied"


def test_publish_branch_preflights_all_peers_and_retry_converges(tmp_path: Path) -> None:
    repo, remotes, head = _branch_publication_fixture(tmp_path)
    receipt = _branch_publication(repo, head)["data"]["request_receipt"]
    hook = remotes["github"] / "hooks/pre-receive"
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text("#!/bin/sh\nexit 1\n")
    hook.chmod(0o755)
    failed = _receipt(repo, receipt, head, blocked=True)
    assert failed["data"]["remote_effect"]["partial_effects"]["applied_peers"] == ["gitlab"]
    hook.unlink()
    recovered = _receipt(repo, receipt, head)
    assert recovered["data"]["remote_effect"]["attempts"][0]["state"] == "already_applied"
    assert _proposal_ref(remotes["github"]) == head


def test_publish_applies_each_peers_multi_ref_set_atomically(tmp_path: Path) -> None:
    repo, remotes, old = _branch_publication_fixture(tmp_path)
    (repo / "accepted.txt").write_text("accepted projection\n", encoding="utf-8")
    git(repo, "add", "accepted.txt")
    git(repo, "commit", "-m", "feat: prepare accepted projection")
    head = git(repo, "rev-parse", "HEAD")
    seed_executed_proof(repo, head)
    apply_accepted_closeout(repo, old, head)
    git(repo, "update-ref", "refs/heads/main", head)

    dry_run = run_ethos(
        "publish",
        "--ref",
        "refs/heads/main",
        "--ref",
        "refs/heads/dev",
        "--probe-remote",
        "--expect-head",
        head,
        "--json",
        cwd=repo,
    )
    receipt = dry_run["data"]["request_receipt"]
    targets = dry_run["data"]["remote_effect"]["targets"]
    assert {target["id"] for target in targets} == {"gitlab", "github"}
    assert all(
        {update["target_ref"] for update in target["updates"]}
        == {"refs/heads/main", "refs/heads/dev"}
        for target in targets
    )

    hook = remotes["github"] / "hooks/pre-receive"
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text(
        '#!/bin/sh\nwhile read old new ref; do [ "$ref" = refs/heads/main ] && exit 1; done\n',
        encoding="utf-8",
    )
    hook.chmod(0o755)

    blocked = _receipt(repo, receipt, head, blocked=True)
    assert blocked["data"]["remote_effect"]["partial_effects"] == {
        "applied_peers": ["gitlab"],
        "failed_peer": "github",
        "pending_peers": [],
    }
    assert git(remotes["github"], "rev-parse", "refs/heads/dev") == old
    assert git(remotes["github"], "for-each-ref", "--format=%(objectname)", "refs/heads/main") == ""

    hook.unlink()
    recovered = _receipt(repo, receipt, head)
    assert recovered["state"] == "published"
    for remote in remotes.values():
        assert git(remote, "rev-parse", "refs/heads/dev") == head
        assert git(remote, "rev-parse", "refs/heads/main") == head


def test_publish_sha256_ref_creation_uses_native_exact_cas(tmp_path: Path) -> None:
    repo, remotes, head = _branch_publication_fixture(tmp_path, object_format="sha256")

    dry_run = _branch_publication(repo, head)

    effect = dry_run["data"]["remote_effect"]
    assert len(effect["source"]["object_oid"]) == 64
    assert {update["expected"] for target in effect["targets"] for update in target["updates"]} == {
        "0" * 64
    }
    receipt = dry_run["data"]["request_receipt"]

    applied = _receipt(repo, receipt, head)

    assert applied["state"] == "published"
    assert {_proposal_ref(remote) for remote in remotes.values()} == {head}


def test_publish_branch_receipt_rejects_remote_drift_before_any_push(tmp_path: Path) -> None:
    repo, remotes, head = _branch_publication_fixture(tmp_path)
    receipt = _branch_publication(repo, head)["data"]["request_receipt"]
    (repo / "drift.txt").write_text("remote drift\n", encoding="utf-8")
    drift = commit_fixture(repo, "remote drift")
    git(repo, "push", "origin", f"{drift}:{_PROPOSAL_REF}")
    git(repo, "reset", "--hard", head)
    blocked = _receipt(repo, receipt, head, blocked=True)
    assert blocked["required_gaps"] == [f"publication_target_drift:gitlab:proposal/{_PROPOSAL}"]
    assert (_proposal_ref(remotes["gitlab"]), _proposal_ref(remotes["github"])) == (drift, "")


def test_publish_branch_receipt_rejects_selected_proof_drift_before_any_push(
    tmp_path: Path,
) -> None:
    repo, remotes, head = _branch_publication_fixture(tmp_path)
    receipt = _branch_publication(repo, head)["data"]["request_receipt"]
    selected = git(repo, "rev-parse", "--verify", "refs/ethos/attestations-set")
    git(repo, "update-ref", "-d", "refs/ethos/attestations-set", selected)
    seed_executed_proof(repo, head)

    blocked = _receipt(repo, receipt, head, blocked=True)

    assert blocked["required_gaps"] == ["publication_proof_drift"]
    assert {_proposal_ref(remote) for remote in remotes.values()} == {""}


def test_publish_branch_supports_one_declared_gitlab_peer(tmp_path: Path) -> None:
    repo, remotes, _head = _branch_publication_fixture(tmp_path)
    release = repo / ".ethos/release.toml"
    parts = release.read_text(encoding="utf-8").split("[[publication.peers]]", 2)
    release.write_text(parts[0] + "[[publication.peers]]" + parts[1], encoding="utf-8")
    head = commit_fixture(repo, "declare GitLab-only publication")
    seed_executed_proof(repo, head)
    request = _branch_publication(repo, head)["data"]["request_receipt"]
    payload = _receipt(repo, request, head)
    assert [target["id"] for target in payload["data"]["remote_effect"]["targets"]] == ["gitlab"]
    assert _proposal_ref(remotes["gitlab"]) == head


def test_publish_branch_honors_human_output_mode(tmp_path: Path) -> None:
    repo, _remotes, head = _branch_publication_fixture(tmp_path)
    output = run_ethos_raw(
        "publish", "--ref", _PROPOSAL_REF, "--probe-remote", "--expect-head", head, cwd=repo
    ).stdout
    assert output.startswith("publish: ready_to_publish")
