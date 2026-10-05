"""Bind public integrity reads to finite regular inputs, never path spelling."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import tomli_w

import ethos.adapters.gates.provenance.observation as source_observation
import ethos.adapters.repo.content.observation as content_observation
import ethos.repository.profile as profile_model
from ethos.adapters.repo.git import run_git
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path


def _bind_source_inputs(
    repo: Path, relations: tuple[tuple[str, str, bytes], ...]
) -> tuple[Path, Path]:
    """Declare complete native copy relationships for the public integrity observer."""
    declaration = ".config/checks/ci/templates.toml"
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
    profile = repo / ".ethos/profile.toml"
    profile.parent.mkdir()
    profile.write_text(
        tomli_w.dumps(
            {
                "profile_id": "example",
                "proof": {
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
            }
        )
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
    monkeypatch.setattr(source_observation, "_MAX_OBSERVATION_BYTES", budget)
    reads = []

    def observe_git(root, *args, **kwargs):
        result = run_git(root, *args, **kwargs)
        if args[0] == "show":
            reads.append(args[1].partition(":")[2])
        return result

    monkeypatch.setattr(source_observation, "run_git", observe_git)
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
    monkeypatch.setattr(source_observation, "_MAX_MEMBER_BYTES", 128)

    def oversized_parse(_text: str):
        pytest.fail("an over-budget profile must not reach its native parser")

    monkeypatch.setattr(profile_model.tomllib, "loads", oversized_parse)
    report = source_observation.integrity_report(repo)
    assert report["verdict"] == "unknown"
    assert report["diagnostics"] == [{"reason": "source_member_size_exceeded:.ethos/profile.toml"}]
