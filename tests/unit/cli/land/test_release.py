"""Native accepted release selection preserves source, trust and exact ref effects."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest
from filelock import FileLock

import ethos.adapters.mutation.accepted.release as release_owner
import ethos.adapters.repo.commit.creation as signing_owner
import ethos.adapters.repo.git_effect_attestation as effect_attestation
import ethos.adapters.repo.git_effects as git_effects
from ethos.adapters.admission.git_admission import ref_move_admission_report
from ethos.adapters.admission.publication import push_admission_report
from ethos.adapters.mutation.proof import proof_gaps
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.release import committed_release_version
from ethos.adapters.repo.release import release_ref_subject
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.proof import seed_executed_proof
from tests.support.subprocesses import kill_after_marker
from tests.unit.cli.land.publication.support import accepted_release_fixture
from tests.unit.cli.land.publication.support import assert_signed_publication
from tests.unit.cli.land.publication.support import publication_peers


def native_failed_result(effect, args, options, *, scope, boundary, root):
    """Execute native Git with either a refusing hook or a lost completion observation."""
    if boundary == "hook":
        root.mkdir()
        hook = root / "reference-transaction"
        hook.write_text('#!/bin/sh\n[ "$1" != prepared ] || { echo refused-proof >&2; exit 1; }\n')
        hook.chmod(0o700)
        options["environment"] = {
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "core.hooksPath",
            "GIT_CONFIG_VALUE_0": str(root),
        }
        return effect(*args, **options)
    completed = effect(*args, **options)
    if boundary == "native-observer":
        scope.setattr(
            git_effects, "observe_git_effect", Mock(side_effect=ValueError("observer unavailable"))
        )
    return subprocess.CompletedProcess(completed.args, 1, completed.stdout, b"refused-proof ACK")


def release_cli(
    repo: Path, head: str, old: str, *args: str, tag: str = "v1.2.3", blocked: bool = False
):
    """Invoke the public release surface with exact fixture coordinates."""
    runner = run_ethos_blocked if blocked else run_ethos
    return runner(
        "land",
        "--release",
        "--expect-head",
        head,
        "--release-head",
        old,
        "--tag",
        tag,
        *args,
        "--json",
        cwd=repo,
    )


@pytest.mark.parametrize(
    ("object_format", "native_version"),
    [("sha1", "package.json"), ("sha256", "package.json"), ("sha1", "VERSION")],
)
@pytest.mark.parametrize("release_mirror", ["independent", "accepted_ff"])
def test_public_release_preserves_native_package_and_signed_tag(
    tmp_path: Path, object_format: str, native_version: str, release_mirror: str
) -> None:
    repo, main, old, head = accepted_release_fixture(
        tmp_path,
        object_format,
        native_version=native_version,
        retired_source=True,
        release_mirror=release_mirror,
    )
    assert proof_gaps(repo, head) == ["proof_lease_generation_stale"]
    previous = head if release_mirror == "accepted_ff" else old
    for ref, ref_before, gaps in (
        (
            "refs/heads/main",
            previous,
            ["release_ref_move_no_ref_intent"] if release_mirror == "independent" else [],
        ),
        ("refs/tags/experiment", "0" * len(head), []),
    ):
        report = ref_move_admission_report(
            root=repo, ref_name=ref, old_value=ref_before, new_value=head
        )
        assert report["required_gaps"] == gaps
        assert report["verdict"] == ("block" if gaps else "pass")
    refs = git(repo, "show-ref")
    preview = release_cli(repo, head, previous)
    assert preview["verdict"] == "pass", preview
    assert git(repo, "show-ref") == refs
    store = Path(git_common_dir(repo)) / "ethos/requests/release"
    store.mkdir(parents=True, exist_ok=True)
    with FileLock(store / ".lock", timeout=0, preserve_lock_file=True):
        blocked = release_cli(repo, head, previous, "--apply", "--authorize", blocked=True)
    assert (blocked["state"], blocked["required_gaps"]) == ("waiting", ["release_in_progress"])
    assert not list(store.glob("*.signing"))
    assert git(repo, "show-ref") == refs
    staged = signing_owner.create_signed_tag(
        repo, name="v1.2.3", head=head, staging=tmp_path / "tag"
    )
    rejected = run_ethos_blocked(
        "hook", "ref-transaction", "refs/tags/v1.2.3", "0" * len(head), staged, "--json", cwd=repo
    )
    assert rejected["required_gaps"] == ["release_ref_move_no_ref_intent"]
    assert "land --release" in rejected["next_action"]
    assert f"--release-head {previous}" in rejected["next_action"]
    assert "--tag v1.2.3" in rejected["next_action"]
    applied = release_cli(repo, head, previous, "--apply", "--authorize")
    assert applied["verdict"] == "pass", applied
    assert git(repo, "rev-parse", "main") == head
    assert git(main, "status", "--porcelain") == ""
    tag = git(repo, "rev-parse", "refs/tags/v1.2.3")
    with pytest.raises(ValueError, match="release_tag_name_mismatch"):
        release_ref_subject(repo, ref="refs/tags/v9.9.9", old="0" * len(head), new=tag)
    assert (repo / "VERSION").exists() == (native_version == "VERSION")
    repeated = release_cli(repo, head, previous, "--apply", "--authorize")
    assert repeated["verdict"] == "pass", repeated
    assert git(repo, "rev-parse", "refs/tags/v1.2.3") == tag

    peers = publication_peers(repo, tmp_path, f"{old}:refs/heads/main", object_format=object_format)
    report = push_admission_report(
        root=repo,
        target_ref="refs/heads/main",
        pushed_head=head,
        remote_head=old,
        remote_name="origin",
    )
    assert report["verdict"] == "pass", report
    assert report["commit_policy_admission"]["state"] == "accepted_content"
    assert report["commit_policy_admission"]["checked_commit_count"] == 0
    assert report["commit_policy_admission"]["remote_head"] == old
    assert report["commit_policy_admission"]["baseline_ref"] == "refs/heads/dev"
    assert report["accepted_closeout_effect"]
    assert_signed_publication(repo, peers, head, tag)


@pytest.mark.parametrize(
    "boundary",
    ["plan-store", "ref-ack", "before-cas", "attestation", "hook", "native-ack", "native-observer"],
)
@pytest.mark.parametrize("release_mirror", ["independent", "accepted_ff"])
def test_release_faults_preserve_objects_and_recover_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, boundary: str, release_mirror: str
) -> None:
    """Real effects, compensation and actor fences share one recoverable request."""
    repo, main, old, head = accepted_release_fixture(tmp_path, release_mirror=release_mirror)
    request = {
        "root": repo,
        "head": head,
        "previous": head if release_mirror == "accepted_ff" else old,
        "tag": "" if boundary == "before-cas" and release_mirror == "independent" else "v1.2.3",
        "apply": True,
        "authorized": True,
    }
    refs, attempted = git(repo, "show-ref"), []
    signing = Mock(wraps=signing_owner.run_git)
    monkeypatch.setattr(signing_owner, "run_git", signing)
    owner, name = {
        "hook": (git_effects, "_run_effect_program"),
        "native-ack": (git_effects, "_run_effect_program"),
        "native-observer": (git_effects, "_run_effect_program"),
        "attestation": (effect_attestation, "records"),
        "plan-store": (release_owner, "write_content_addressed"),
    }.get(boundary, (release_owner, "execute_git_effect"))
    effect = getattr(owner, name)

    def lose_ack(*args, **kwargs):
        if boundary == "attestation" and len(args) <= 2:
            return effect(*args, **kwargs)
        attempted.append(True)
        if owner is git_effects:
            return native_failed_result(
                effect, args, kwargs, scope=scope, boundary=boundary, root=tmp_path / "reject-hooks"
            )
        if boundary == "ref-ack":
            effect(*args, **kwargs)
        message = "injected acknowledgement loss"
        raise OSError(message)

    with monkeypatch.context() as scope:
        scope.setattr(owner, name, lose_ack)
        interrupted = release_owner.promote_release(**request)
    assert interrupted["verdict"] == ("block" if boundary == "hook" else "unknown"), interrupted
    if owner is git_effects:
        failure = interrupted["data"]["process_failure"]
        assert failure["code"] == "git_effect_cas_rejected"
        assert failure["cwd"] == str(repo)
        assert "refused-proof" in failure["observation"]["stderr"]
        assert failure["observation"]["returncode"] != 0
        assert failure["observation"]["outcome"] == (
            "unchanged" if boundary == "hook" else "unknown"
        )
    assert attempted == [True]
    if boundary not in {"ref-ack", "native-ack", "native-observer"}:
        assert git(repo, "show-ref") == refs
    if boundary == "before-cas":
        with monkeypatch.context() as scope:
            scope.setenv("ETHOS_ACTOR", "agent:test:case:another")
            rejected = release_owner.promote_release(**request)
        assert rejected["verdict"] == "block", rejected
        assert rejected["required_gaps"] == ["release_request_actor_mismatch"]
        assert git(repo, "show-ref") == refs
    stored = Path(interrupted["data"]["request"])
    original_request = stored.read_bytes() if stored.is_file() else None
    seed_executed_proof(repo, head)
    restored = release_owner.promote_release(**request)
    assert restored["verdict"] == "pass", restored
    if original_request is not None:
        assert stored.read_bytes() == original_request
    assert sum(call.args[1:3] == ("tag", "-s") for call in signing.call_args_list) == bool(
        request["tag"]
    )
    assert git(repo, "rev-parse", "main") == head
    assert git(main, "status", "--porcelain") == ""
    assert not list((Path(git_common_dir(repo)) / "ethos/requests/release").glob("*.signing"))


@pytest.mark.parametrize("boundary", ["tag-object", "ref-cas"])
@pytest.mark.parametrize("release_mirror", ["independent", "accepted_ff"])
def test_killed_release_recovers_exact_native_objects(
    tmp_path: Path, boundary: str, release_mirror: str
) -> None:
    """Kill the writer after native success but before its caller gets the result."""
    repo, main, old, head = accepted_release_fixture(tmp_path, release_mirror=release_mirror)
    previous = head if release_mirror == "accepted_ff" else old
    marker = tmp_path / "effect-ready"
    script = """
import sys
from pathlib import Path
from tests.support.subprocesses import pause_after_effect
import ethos.adapters.mutation.accepted.release as release
import ethos.adapters.repo.git_effects as effects
repo, old, head, boundary, marker = sys.argv[1:]
owner, name = ((release, 'create_signed_tag') if boundary == 'tag-object'
               else (effects, '_run_effect_program'))
pause_after_effect(owner, name, Path(marker))
print(release.promote_release(root=Path(repo),head=head,previous=old,tag='v1.2.3',apply=True,authorized=True),flush=True)
"""
    kill_after_marker(
        repo, script, (str(repo), previous, head, boundary, str(marker)), marker, timeout=30
    )
    before = (
        marker.read_text()
        if boundary == "tag-object"
        else git(repo, "rev-parse", "refs/tags/v1.2.3")
    )
    result = release_cli(repo, head, previous, "--apply", "--authorize")
    assert result["verdict"] == "pass", result
    assert git(repo, "rev-parse", "refs/tags/v1.2.3") == before
    assert git(main, "status", "--porcelain") == ""
    assert not list((Path(git_common_dir(repo)) / "ethos/requests/release").glob("*.signing"))


@pytest.mark.parametrize("gap", ["authorization", "dirty", "source", "main", "tag", "proof"])
@pytest.mark.parametrize("release_mirror", ["independent", "accepted_ff"])
def test_release_public_rejection_preserves_all_refs(
    tmp_path: Path, gap: str, release_mirror: str
) -> None:
    """Each independent precondition fails before signing or moving any source."""
    repo, main, old, head = accepted_release_fixture(tmp_path, release_mirror=release_mirror)
    previous = head if release_mirror == "accepted_ff" else old
    if gap == "proof":
        git(repo, "update-ref", "-d", "refs/ethos/attestations-set")
    refs = git(repo, "show-ref")
    if release_mirror == "accepted_ff" and gap == "main":
        unchanged = release_cli(repo, head, head, "--apply", "--authorize", tag="")
        assert unchanged["verdict"] == "pass", unchanged
        assert "attestation" not in unchanged["data"]
        assert git(repo, "show-ref") == refs
    if gap == "dirty":
        (main / "untracked").write_text("preserve me")
    if gap == "main":
        previous = old if release_mirror == "accepted_ff" else "1" * 40
    result = release_cli(
        repo,
        old if gap == "source" else head,
        previous,
        "--apply",
        *(("--authorize",) if gap != "authorization" else ()),
        tag="v9.9.9" if gap == "tag" else "v1.2.3",
        blocked=True,
    )
    assert result["required_gaps"], result
    if gap == "main" and release_mirror == "accepted_ff":
        assert result["required_gaps"] == ["release_mirror_requires_accepted_closeout"]
        assert "land --closeout" in result["next_action"]
    assert git(repo, "show-ref") == refs


@pytest.mark.parametrize(
    ("path", "content", "gap"),
    [
        ("package.json", '{"version":"1.2.3"}', ""),
        ("pyproject.toml", '[project]\nversion="1.2.3"\n', ""),
        (
            "pyproject.toml",
            '[project]\nversion="1.2.3"\ndynamic=["version"]\n',
            "release_version_source_invalid",
        ),
        ("package.json", '{"version":3}', "release_version_source_invalid"),
        ("package.json", "[]", "release_version_source_invalid"),
    ],
)
def test_native_version_sources_are_explicit(
    tmp_path: Path, path: str, content: str, gap: str
) -> None:
    repo = init_git_repo(tmp_path / "version")
    commit_fixture_file(repo, path, content, "version fixture")
    if gap:
        with pytest.raises(ValueError, match=gap):
            committed_release_version(repo, "HEAD")
    else:
        assert committed_release_version(repo, "HEAD") == {"version": "1.2.3", "source": path}
