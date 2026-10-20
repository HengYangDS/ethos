"""Bind public integrity reads to finite regular inputs, never path spelling."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest
import tomli_w

import ethos.adapters.gates.provenance.observation as source_observation
import ethos.adapters.repo.content.observation as content_observation
import ethos.adapters.repo.content.source as source_tree
import ethos.repository.profile as profile_model
from ethos.adapters.repo.git import run_git
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_test_profile

if TYPE_CHECKING:
    from pathlib import Path


def _bind_source_inputs(
    repo: Path, relations: tuple[tuple[str, str, bytes], ...]
) -> tuple[Path, Path]:
    """Declare complete native copy relationships for the public integrity observer."""
    declaration = ".config/checks/ci-projection/policy.toml"
    owner = repo / declaration
    owner.parent.mkdir(parents=True)
    projections = []
    members = {}
    for source, output, content in relations:
        for relative in (source, output):
            target = repo / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        projections.append({"template": source, "projection": output})
        members[output] = [declaration, output]
    owner.write_text(
        tomli_w.dumps({"schema": "ethos-ci-template-consistency-v1", "projection": projections})
    )
    profile = write_test_profile(
        repo,
        profile_id="example",
        proof={
            "gate_registry": "system/gates.toml",
            "source_contracts": [
                {
                    "kind": "generated",
                    "input_refs": [declaration],
                    "members": members,
                    "integrity_gate": "integrity",
                }
            ],
        },
    )
    commit_fixture(repo, "bind complete finite source inputs")
    return profile, owner


def test_source_tree_rejects_grown_live_input_before_allocating(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A small committed input cannot authorize an unbounded live allocation."""
    repo = init_git_repo(tmp_path / "repository")
    _bind_source_inputs(repo, (("member.py", "outputs/member.py", b"x"),))
    assert source_observation.integrity_report(repo)["verdict"] == "pass"
    target = repo / "member.py"
    with target.open("r+b") as stream:
        stream.truncate(1024 * 1024 * 1024)
    identity = target.stat()
    original = content_observation.os.fdopen

    def bounded_allocation(descriptor, *args, **kwargs):
        observed = content_observation.os.fstat(descriptor)
        if (observed.st_dev, observed.st_ino) == (identity.st_dev, identity.st_ino):
            pytest.fail("a grown live input must be rejected before opening its read stream")
        return original(descriptor, *args, **kwargs)

    monkeypatch.setattr(content_observation.os, "fdopen", bounded_allocation)
    report = source_observation.integrity_report(repo)
    assert report["verdict"] == "unknown", report
    assert report["diagnostics"] == [{"reason": "source_member_size_exceeded:member.py"}]


@pytest.mark.parametrize("source_count", [1, 2])
def test_source_tree_has_one_aggregate_input_budget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, source_count: int
) -> None:
    """Repeated reads share input identity; another source cannot reset its budget."""
    repo = init_git_repo(tmp_path / "repository")
    content = b"xxxx"
    relations = (
        ("first.py", "outputs/first.py", content),
        ("first.py", "outputs/repeated.py", content),
    )
    if source_count == 2:
        relations += (("second.py", "outputs/second.py", content),)
    metadata = _bind_source_inputs(repo, relations)
    budget = sum(path.stat().st_size for path in metadata) + 3 * len(content)
    monkeypatch.setattr(source_tree, "MAX_OBSERVATION_BYTES", budget)
    reads = []

    def observe_git(root, *args, **kwargs):
        result = run_git(root, *args, **kwargs)
        if args[0] == "show":
            reads.append(args[1].partition(":")[2])
        return result

    monkeypatch.setattr(source_tree, "run_git", observe_git)
    report = source_observation.integrity_report(repo)
    assert reads.count("first.py") == 1
    if source_count == 1:
        assert report["verdict"] == "pass", report
        integrity = report["source_integrity"]
        assert isinstance(integrity, dict)
        assert set(integrity["members"]) == {
            "outputs/first.py",
            "outputs/repeated.py",
        }
    else:
        assert report["verdict"] == "unknown", report
        assert report["diagnostics"] == [{"reason": "source_observation_size_exceeded"}]


def test_source_tree_rechecks_the_same_opened_ancestor_chain(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stable open file does not certify a replaced parent directory."""
    repo = init_git_repo(tmp_path / "repository")
    _bind_source_inputs(repo, (("inputs/member.py", "outputs/member.py", b"x"),))
    assert source_observation.integrity_report(repo)["verdict"] == "pass"
    parent = repo / "inputs"
    identity = (parent / "member.py").stat()
    original = content_observation.os.fdopen
    replaced = False

    def replaced_parent(descriptor, *args, **kwargs):
        nonlocal replaced
        observed = content_observation.os.fstat(descriptor)
        if (observed.st_dev, observed.st_ino) == (identity.st_dev, identity.st_ino):
            parent.rename(repo / "preserved-inputs")
            parent.symlink_to(repo / "preserved-inputs", target_is_directory=True)
            replaced = True
        return original(descriptor, *args, **kwargs)

    monkeypatch.setattr(content_observation.os, "fdopen", replaced_parent)
    report = source_observation.integrity_report(repo)
    assert replaced
    assert report["verdict"] == "unknown", report
    assert report["diagnostics"] == [{"reason": "source_member_changed:inputs/member.py"}]


def test_source_profile_is_bounded_before_native_parsing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The native profile parser only receives size-qualified snapshot bytes."""
    repo = init_git_repo(tmp_path / "repository")
    profile = repo / ".ethos/profile.toml"
    profile.parent.mkdir()
    profile.write_text('profile_id = "example"\n#' + "x" * 256)
    commit_fixture(repo, "bind an over-budget native profile")
    monkeypatch.setattr(source_tree, "MAX_MEMBER_BYTES", 128)

    def oversized_parse(_text: str):
        pytest.fail("an over-budget profile must not reach its native parser")

    monkeypatch.setattr(profile_model.tomllib, "loads", oversized_parse)
    report = source_observation.integrity_report(repo)
    assert report["verdict"] == "unknown"
    assert report["diagnostics"] == [{"reason": "source_member_size_exceeded:.ethos/profile.toml"}]


@pytest.mark.parametrize("state", ["unborn", "unprofiled", "invalid"])
def test_source_observation_reads_only_committed_valid_obligations(
    tmp_path: Path, state: str
) -> None:
    """Unborn history fails closed, no profile has no obligations and invalid policy is unproven."""
    repo = tmp_path / "repository"
    if state == "unborn":
        repo.mkdir()
        run_git(repo, "init", "--quiet")
    else:
        init_git_repo(repo)
    if state == "invalid":
        profile = repo / ".ethos/profile.toml"
        profile.parent.mkdir()
        profile.write_text("profile_id = 1\n")
        commit_fixture(repo, "declare invalid profile")
    report = source_observation.integrity_report(repo)
    if state == "unprofiled":
        assert (report["verdict"], report["state"]) == ("pass", "not_applicable")
    else:
        reason = "source_head_missing" if state == "unborn" else profile_model.INVALID_PROFILE_ERROR
        assert report["verdict"] == "unknown", report
        assert report["diagnostics"] == [{"reason": reason}]


@pytest.mark.parametrize("fault", ["absent", "changed", "moved"])
def test_source_observation_binds_one_unchanged_committed_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    """Absent members, equal-size live edits and a moved HEAD cannot verify committed sources."""
    repo = init_git_repo(tmp_path / "repository")
    _bind_source_inputs(repo, (("member.py", "outputs/member.py", b"x"),))
    if fault == "absent":
        run_git(repo, "rm", "--quiet", "outputs/member.py")
        commit_fixture(repo, "remove the declared output")
    elif fault == "changed":
        (repo / "member.py").write_bytes(b"y")
    else:
        heads = iter((source_tree.current_tracked_head(repo), "0" * 40))
        monkeypatch.setattr(source_tree, "current_tracked_head", lambda _root: next(heads))
    report = source_observation.integrity_report(repo)
    reason = {
        "absent": "source_member_unavailable:outputs/member.py",
        "changed": "source_member_changed:member.py",
        "moved": "source_tree_changed",
    }[fault]
    assert report["verdict"] == "unknown", report
    assert report["required_gaps"] == ["source_integrity_unproven:outputs/member.py"]
    assert report["diagnostics"] == [{"reason": reason}]


def test_source_tree_preserves_native_repository_failure(tmp_path: Path) -> None:
    """An unreadable repository keeps Git's own failure; only an unborn HEAD is missing."""
    broken = tmp_path / "broken"
    broken.mkdir()
    (broken / ".git").write_text("gitdir: missing-repository\n")
    with pytest.raises(subprocess.CalledProcessError) as raised:
        source_tree.SourceTree.observe(broken)
    assert raised.value.returncode == 128
    assert raised.value.stderr.startswith("fatal: ")
    report = source_observation.integrity_report(broken)
    assert (report["verdict"], report["state"]) == ("unknown", "unproven")
    unborn = tmp_path / "unborn"
    unborn.mkdir()
    run_git(unborn, "init", "-q")
    with pytest.raises(ValueError, match="source_head_missing"):
        source_tree.SourceTree.observe(unborn)
