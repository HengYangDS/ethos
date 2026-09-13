"""Public exact-ref observation independent of detached CI host coordination."""

from __future__ import annotations

import hashlib
import json
import os
import shlex
import subprocess
import sys
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.openspec.observation as openspec_observation
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.governed_repository import adopt_and_commit
from tests.support.governed_repository import commit_active_change
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_role_policy

if TYPE_CHECKING:
    from pathlib import Path


def _fixture(tmp_path: Path) -> tuple[Path, str, str]:
    repo = init_git_repo(tmp_path / "repository")
    adopt_and_commit(repo)
    baseline = git(repo, "rev-parse", "HEAD")
    proposed = commit_active_change(repo, change_id="unfinished")
    git(repo, "checkout", "--detach", proposed)
    return repo, baseline, proposed


def _observe(
    repo: Path, target: str, proposed: str, previous: str, *, baseline: str = "", blocked=False
):
    runner = run_ethos_blocked if blocked else run_ethos
    return runner(
        "hook",
        "ref-update",
        "--target-ref",
        target,
        "--proposed-head",
        proposed,
        "--remote-head",
        previous,
        "--remote",
        "origin",
        *(("--trusted-baseline", baseline) if baseline else ()),
        "--json",
        cwd=repo,
    )


@pytest.mark.parametrize(
    ("target", "role", "admitted"),
    [
        ("refs/heads/proposal/review", "proposal_ref", True),
        ("refs/heads/dev", "accepted_root", False),
        ("refs/heads/main", "release_root", False),
        ("refs/heads/work/topic", "work_lane", False),
        ("refs/heads/candidate/dev", "candidate", False),
    ],
)
def test_detached_ref_observation_uses_target_meaning_without_host_lease(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, target: str, role: str, *, admitted: bool
) -> None:
    """Detachment cannot hide active intent from a protected destination."""
    repo, baseline, proposed = _fixture(tmp_path)
    monkeypatch.delenv("ETHOS_ACTOR", raising=False)
    before_refs = git(repo, "show-ref")
    before_index = hashlib.sha256((repo / ".git/index").read_bytes()).hexdigest()
    before_files = set(repo.rglob("*"))

    report = _observe(repo, target, proposed, baseline, blocked=not admitted)

    assert report["data"]["role"] == role
    assert report["data"]["proposed_commit"] == proposed
    assert report["data"]["openspec"]["changes"] == ["unfinished"]
    assert report["data"]["satisfies_repository_proof"] is False
    assert report["data"]["mints_authority"] is False
    if role in {"accepted_root", "release_root"}:
        assert report["required_gaps"] == [
            f"openspec_ref_active_change_unarchived:{target}:unfinished"
        ]
        assert report["data"]["boundary"] == "accepted_intent"
        command = shlex.split(report["next_action"])
        assert command == [
            "git",
            "-C",
            str(repo),
            "show",
            f"{proposed}:openspec/changes/unfinished/tasks.md",
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=15)
        assert result.returncode == 0
    assert git(repo, "show-ref") == before_refs
    assert hashlib.sha256((repo / ".git/index").read_bytes()).hexdigest() == before_index
    assert set(repo.rglob("*")) == before_files


def test_new_review_ref_uses_explicit_baseline_without_local_tracking_refs(tmp_path: Path) -> None:
    """A detached clone can evaluate one new review range without inventing refs."""
    repo, baseline, proposed = _fixture(tmp_path)

    report = _observe(repo, "refs/heads/proposal/review", proposed, "0" * 40, baseline=baseline)

    assert report["verdict"] == "pass"
    assert report["data"]["commit_policy_admission"]["revisions"] == [proposed]
    assert report["data"]["policy_ref"] == baseline


@pytest.mark.parametrize("missing", ["proposed", "previous", "baseline"])
def test_unknown_ref_coordinates_do_not_fall_back_to_current_head(tmp_path: Path, missing: str):
    """Unavailable immutable input is not replaced with the checkout's identity."""
    repo, baseline, proposed = _fixture(tmp_path)
    invalid = "f" * 40

    report = _observe(
        repo,
        "refs/heads/proposal/review",
        invalid if missing == "proposed" else proposed,
        invalid if missing == "previous" else "0" * 40,
        baseline=invalid if missing == "baseline" else baseline,
        blocked=True,
    )

    assert report["verdict"] != "pass"
    assert any("unreadable" in gap for gap in report["required_gaps"])


def test_candidate_policy_cannot_reclassify_predecessor_accepted_destination(tmp_path: Path):
    """Prior committed role meaning remains the floor when proposed policy changes."""
    repo, baseline, _proposed = _fixture(tmp_path)
    policy = repo / ".ethos/workspace.toml"
    policy.write_text(
        policy.read_text().replace('accepted_branch = "dev"', 'accepted_branch = "new-dev"')
    )
    proposed = commit_fixture(repo, "rename candidate accepted role")

    report = _observe(repo, "refs/heads/dev", proposed, baseline, blocked=True)

    assert report["data"]["role"] == "accepted_root"
    assert report["data"]["policy_ref"] == baseline
    assert report["required_gaps"] == [
        "openspec_ref_active_change_unarchived:refs/heads/dev:unfinished"
    ]


@pytest.mark.parametrize("fault", ["toml", "role", "tags", "link"])
def test_malformed_prior_policy_cannot_be_replaced_with_candidate_defaults(tmp_path: Path, fault):
    """Invalid prior declarations remain a boundary failure, not permissive defaults."""
    repo, _baseline, proposed = _fixture(tmp_path)
    policy = repo / (".ethos/release.toml" if fault == "tags" else ".ethos/workspace.toml")
    original = policy.read_bytes()
    if fault == "link":
        policy.unlink()
        policy.symlink_to("../README.md")
    else:
        policy.write_text(
            '[protected_refs]\ntags = "v*"\n'
            if fault == "tags"
            else "[branch_roles]\naccepted_branch = 7\n"
            if fault == "role"
            else "["
        )
    baseline = commit_fixture(repo, "invalid prior declaration")
    if policy.is_symlink():
        policy.unlink()
    policy.write_bytes(original)
    proposed = commit_fixture(repo, "restore candidate declaration")

    report = _observe(repo, "refs/heads/proposal/review", proposed, baseline, blocked=True)

    assert any(gap.startswith("publication_policy_invalid:") for gap in report["required_gaps"])
    assert report["data"]["policy_ref"] == baseline


def test_exact_accepted_role_precedes_an_overlapping_review_prefix(tmp_path: Path):
    """A configured accepted name inside a review prefix is still protected."""
    repo, _baseline, _proposed = _fixture(tmp_path)
    write_role_policy(repo, accepted_branch="review/dev", proposal_branch_prefix="review/")
    baseline = git(repo, "rev-parse", "HEAD")
    (repo / "readme.txt").write_text("candidate\n")
    proposed = commit_fixture(repo, "new candidate")

    report = _observe(repo, "refs/heads/review/dev", proposed, baseline, blocked=True)

    assert report["data"]["role"] == "accepted_root"
    assert report["required_gaps"] == [
        "openspec_ref_active_change_unarchived:refs/heads/review/dev:unfinished"
    ]


def test_native_detached_cli_observes_exact_objects_without_a_state_directory(tmp_path: Path):
    """An actual isolated CLI process needs Git facts, not a host coordination store."""
    repo, baseline, proposed = _fixture(tmp_path)
    environment = {key: value for key, value in os.environ.items() if key != "ETHOS_ACTOR"}

    result = subprocess.run(
        [
            sys.executable,
            "-B",
            "-I",
            "-m",
            "ethos.cli",
            "hook",
            "ref-update",
            "--target-ref",
            "refs/heads/proposal/review",
            "--proposed-head",
            proposed,
            "--remote-head",
            baseline,
            "--remote",
            "origin",
            "--root",
            str(repo),
            "--json",
        ],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["verdict"] == "pass"
    assert report["data"]["proposed_commit"] == proposed
    assert not (repo / ".git/ethos").exists()


@pytest.mark.parametrize("object_format", ["sha1", "sha256"])
def test_ref_observation_preserves_native_create_delete_and_non_fast_forward_ranges(
    tmp_path: Path, object_format: str
) -> None:
    """Ref observation inspects an exact range; it never claims effect permission."""
    repo = init_git_repo(tmp_path / object_format, object_format=object_format)
    adopt_and_commit(repo)
    base = git(repo, "rev-parse", "HEAD")
    git(repo, "checkout", "-b", "remote-line")
    (repo / "remote.txt").write_text("remote\n")
    old = commit_fixture(repo, "remote range")
    git(repo, "checkout", "dev")
    (repo / "proposed.txt").write_text("proposed\n")
    proposed = commit_fixture(repo, "proposed range")
    zero = "0" * len(proposed)
    target = "refs/heads/proposal/review"

    created = _observe(repo, target, proposed, zero, baseline=base)
    replaced = _observe(repo, target, proposed, old)
    deleted = _observe(repo, target, zero, proposed)

    assert created["data"]["commit_policy_admission"]["revisions"] == [proposed]
    assert replaced["data"]["commit_policy_admission"]["revisions"] == [proposed]
    assert deleted["data"]["commit_policy_admission"]["revisions"] == []
    assert deleted["data"]["policy_ref"] == proposed
    assert deleted["data"]["openspec"]["changes"] == []
    assert all(not item["data"]["mints_authority"] for item in (created, replaced, deleted))


def test_known_invalid_destination_dominates_unavailable_intent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Independent unknown facts cannot hide a known destination-policy violation."""
    repo, baseline, proposed = _fixture(tmp_path)
    original = openspec_observation.run_git

    def observe(root: Path, *args: str, check: bool = True):
        if args[0] == "ls-tree" and "openspec/changes" in args:
            return subprocess.CompletedProcess(args, 128, "", "unavailable")
        return original(root, *args, check=check)

    monkeypatch.setattr(openspec_observation, "run_git", observe)

    report = _observe(repo, "refs/heads/work/local", proposed, baseline, blocked=True)

    assert report["verdict"] == "block"
    assert (
        "publication_ref_unavailable:branch:work_lane:refs/heads/work/local"
        in report["required_gaps"]
    )
