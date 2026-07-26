from __future__ import annotations

import importlib.util
import os
import stat
import subprocess
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.resolution.observation as observation_adapter
from ethos.adapters.mutation.resolution.observation import DescriptorIdentity
from ethos.adapters.mutation.resolution.observation import ExactFileSnapshot
from ethos.adapters.mutation.resolution.observation import GitWorktreeRegistrationToken
from ethos.adapters.mutation.resolution.observation import OwnerlessGitFacts
from ethos.adapters.mutation.resolution.observation import OwnerlessGitObservationError
from ethos.adapters.mutation.resolution.observation import git_ancestry
from ethos.adapters.mutation.resolution.observation import git_object_bytes
from ethos.adapters.mutation.resolution.observation import observe_lane
from ethos.adapters.mutation.resolution.observation import observe_ownerless_git
from ethos.adapters.mutation.resolution.observation import read_root_bound_regular_file
from tests.support.contract_helpers import git
from tests.support.lane_helpers import orphan_work_lane

if TYPE_CHECKING:
    from pathlib import Path


def _fixed_git_call(args: list[str], kwargs: dict[str, object]) -> None:
    assert args[0] == "git"
    assert kwargs["check"] is False
    assert kwargs["capture_output"] is True
    assert kwargs["shell"] is False
    environment = kwargs["env"]
    assert isinstance(environment, dict)
    assert environment == {
        "GIT_ATTR_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "LC_ALL": "C",
        "PATH": os.environ.get("PATH", os.defpath),
    }
    assert "executable" not in kwargs
    assert "text" not in kwargs
    assert "encoding" not in kwargs
    assert "universal_newlines" not in kwargs


def _worktree_listing(repo: Path, lane: Path, *, duplicate_target: bool = False) -> bytes:
    accepted_head = git(repo, "rev-parse", "dev").encode()
    target_head = git(repo, "rev-parse", "work/orphan").encode()
    accepted = (
        b"worktree " + bytes(repo) + b"\0HEAD " + accepted_head + b"\0branch refs/heads/dev\0\0"
    )
    target = (
        b"worktree "
        + bytes(lane)
        + b"\0HEAD "
        + target_head
        + b"\0branch refs/heads/work/orphan\0\0"
    )
    return accepted + target + (target if duplicate_target else b"")


def test_observation_is_a_public_concrete_module() -> None:
    assert importlib.util.find_spec("ethos.adapters.mutation.resolution._observation") is None
    assert DescriptorIdentity.__module__.endswith(".observation")
    assert ExactFileSnapshot.__module__.endswith(".observation")
    assert GitWorktreeRegistrationToken.__module__.endswith(".observation")
    assert OwnerlessGitFacts.__module__.endswith(".observation")
    assert callable(observe_lane)
    assert callable(observe_ownerless_git)
    assert callable(read_root_bound_regular_file)
    assert callable(git_object_bytes)
    assert callable(git_ancestry)


def test_root_bound_file_rejects_current_directory_path(tmp_path: Path) -> None:
    with pytest.raises(OwnerlessGitObservationError) as raised:
        read_root_bound_regular_file(tmp_path, ".", maximum_bytes=1)

    assert (raised.value.kind, raised.value.detail) == ("unverifiable", "path")


def test_every_git_observation_uses_fixed_literal_byte_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, _lane = orphan_work_lane(tmp_path)
    expected_head = git(repo, "rev-parse", "work/orphan")
    real_run = subprocess.run
    calls: list[tuple[list[str], dict[str, object]]] = []
    for name in (
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_INDEX_FILE",
        "GIT_CONFIG_COUNT",
        "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_REPLACE_REF_BASE",
        "GIT_NO_REPLACE_OBJECTS",
        "XDG_CONFIG_HOME",
    ):
        monkeypatch.setenv(name, "/hostile/inherited/value")

    def recording_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        calls.append((list(args), dict(kwargs)))
        sanitized = dict(kwargs)
        sanitized["env"] = {
            key: value
            for key, value in dict(kwargs["env"]).items()  # type: ignore[arg-type]
            if key not in os.environ or os.environ.get(key) != "/hostile/inherited/value"
        }
        return real_run(args, **sanitized)  # type: ignore[return-value]

    monkeypatch.setattr(observation_adapter.subprocess, "run", recording_run)

    facts = observe_ownerless_git(repo, branch="work/orphan", accepted_branch="dev")

    assert facts.observation.head == expected_head
    assert calls
    for args, kwargs in calls:
        _fixed_git_call(args, kwargs)
        assert isinstance(kwargs["cwd"], type(repo))
    diff_calls = [args for args, _kwargs in calls if args[1:2] == ["diff"]]
    assert len(diff_calls) == 4
    for args in diff_calls:
        assert "--no-ext-diff" in args
        assert "--no-textconv" in args


@pytest.mark.parametrize(
    "output",
    [
        b"worktree /tmp/repo\0HEAD " + b"a" * 40,
        b"worktree /tmp/repo\0worktree /tmp/again\0HEAD " + b"a" * 40 + b"\0\0",
        b"worktree /tmp/repo\0HEAD " + b"a" * 40 + b"\0unknown value\0\0",
        b"worktree /tmp/repo\0HEAD \xff\0branch refs/heads/dev\0\0",
    ],
    ids=("unterminated", "duplicate-field", "unknown-field", "non-ascii-head"),
)
def test_worktree_porcelain_z_is_parsed_strictly(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    output: bytes,
) -> None:
    repo, _lane = orphan_work_lane(tmp_path)
    monkeypatch.setattr(
        observation_adapter.subprocess,
        "run",
        lambda args, **_kwargs: subprocess.CompletedProcess(args, 0, output, b""),
    )

    with pytest.raises(OwnerlessGitObservationError) as raised:
        observe_ownerless_git(repo, branch="work/orphan", accepted_branch="dev")

    assert (raised.value.kind, raised.value.detail) == ("unverifiable", "worktree_list")


def test_duplicate_target_registration_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    output = _worktree_listing(repo, lane, duplicate_target=True)
    real_run = subprocess.run

    def duplicate_listing(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        if list(args)[1:] == ["worktree", "list", "--porcelain", "-z"]:
            return subprocess.CompletedProcess(args, 0, output, b"")
        return real_run(args, **kwargs)  # type: ignore[return-value]

    monkeypatch.setattr(observation_adapter.subprocess, "run", duplicate_listing)

    with pytest.raises(OwnerlessGitObservationError) as raised:
        observe_ownerless_git(repo, branch="work/orphan", accepted_branch="dev")

    assert (raised.value.kind, raised.value.detail) == ("registration", "target")


def test_duplicate_registered_path_across_branches_is_unverifiable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    target_head = git(repo, "rev-parse", "work/orphan").encode()
    listing = _worktree_listing(repo, lane) + (
        b"worktree "
        + bytes(lane)
        + b"\0HEAD "
        + target_head
        + b"\0branch refs/heads/work/other\0\0"
    )
    real_run = subprocess.run

    def duplicate_path(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        if list(args)[1:] == ["worktree", "list", "--porcelain", "-z"]:
            return subprocess.CompletedProcess(args, 0, listing, b"")
        return real_run(args, **kwargs)  # type: ignore[return-value]

    monkeypatch.setattr(observation_adapter.subprocess, "run", duplicate_path)

    with pytest.raises(OwnerlessGitObservationError) as raised:
        observe_ownerless_git(repo, branch="work/orphan", accepted_branch="dev")

    assert (raised.value.kind, raised.value.detail) == ("unverifiable", "worktree_list")


def test_foreign_self_consistent_git_administration_cannot_impersonate_target(
    tmp_path: Path,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    foreign = tmp_path / "foreign-repo"
    git(tmp_path, "clone", repo.as_posix(), foreign.as_posix())
    target_head = git(repo, "rev-parse", "work/orphan")
    git(foreign, "branch", "work/orphan", target_head)
    foreign_lane = tmp_path / "foreign-lane"
    git(foreign, "worktree", "add", foreign_lane.as_posix(), "work/orphan")
    foreign_gitfile = (foreign_lane / ".git").read_bytes()
    foreign_admin = type(repo)(os.fsdecode(foreign_gitfile.removeprefix(b"gitdir: ").strip()))
    (foreign_admin / "gitdir").write_bytes(os.fsencode(lane / ".git") + b"\n")
    (lane / ".git").write_bytes(foreign_gitfile)

    with pytest.raises(OwnerlessGitObservationError) as raised:
        observe_ownerless_git(repo, branch="work/orphan", accepted_branch="dev")

    assert (raised.value.kind, raised.value.detail) == ("registration", "target")


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        pytest.param("registration", ("registration", "target_drift"), id="registration"),
        pytest.param("ref", ("registration", "target_drift"), id="ref"),
        pytest.param("dirt", ("dirty", "worktree"), id="dirt"),
    ],
)
def test_complete_target_snapshot_rejects_between_pass_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
    expected: tuple[str, str],
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    real_run = subprocess.run
    listing_calls = 0

    def run_git(*args: str) -> None:
        real_run(["git", *args], cwd=repo, check=True, capture_output=True)

    def racing_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        nonlocal listing_calls
        command = list(args)
        if command[1:] == ["worktree", "list", "--porcelain", "-z"]:
            listing_calls += 1
            if listing_calls == 3:
                if mutation == "registration":
                    run_git("worktree", "remove", lane.as_posix())
                    run_git("worktree", "add", lane.as_posix(), "work/orphan")
                else:
                    (lane / "README.md").write_text(f"{mutation}\n", encoding="utf-8")
                    if mutation == "ref":
                        run_git("-C", lane.as_posix(), "add", "README.md")
                        run_git(
                            "-C",
                            lane.as_posix(),
                            "-c",
                            "user.name=Test User",
                            "-c",
                            "user.email=test@example.com",
                            "commit",
                            "-m",
                            "race target ref",
                        )
        return real_run(command, **kwargs)  # type: ignore[return-value]

    monkeypatch.setattr(observation_adapter.subprocess, "run", racing_run)

    with pytest.raises(OwnerlessGitObservationError) as raised:
        observe_ownerless_git(repo, branch="work/orphan", accepted_branch="dev")

    assert (raised.value.kind, raised.value.detail) == expected


def test_target_snapshot_rechecks_registration_after_fact_capture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    real_run = subprocess.run
    status_calls = 0

    def run_git(*args: str) -> None:
        real_run(["git", *args], cwd=repo, check=True, capture_output=True)

    def racing_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        nonlocal status_calls
        command = list(args)
        if command[1:3] == ["status", "--porcelain=v2"]:
            status_calls += 1
            if status_calls == 2:
                run_git("worktree", "remove", lane.as_posix())
                run_git("worktree", "add", lane.as_posix(), "work/orphan")
        return real_run(command, **kwargs)  # type: ignore[return-value]

    monkeypatch.setattr(observation_adapter.subprocess, "run", racing_run)

    with pytest.raises(OwnerlessGitObservationError) as raised:
        observe_ownerless_git(repo, branch="work/orphan", accepted_branch="dev")

    assert (raised.value.kind, raised.value.detail) == ("registration", "target_drift")


def test_accepted_registration_is_rechecked_after_target_capture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, _lane = orphan_work_lane(tmp_path)
    real_run = subprocess.run
    advanced = False

    def advance_accepted() -> None:
        (repo / "README.md").write_text("# advanced\n", encoding="utf-8")
        real_run(["git", "add", "README.md"], cwd=repo, check=True, capture_output=True)
        real_run(
            [
                "git",
                "-c",
                "user.name=Test User",
                "-c",
                "user.email=test@example.com",
                "commit",
                "-m",
                "advance accepted during observation",
            ],
            cwd=repo,
            check=True,
            capture_output=True,
        )

    def racing_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        nonlocal advanced
        command = list(args)
        if not advanced and command[1:3] == ["status", "--porcelain=v2"]:
            advanced = True
            advance_accepted()
        return real_run(command, **kwargs)  # type: ignore[return-value]

    monkeypatch.setattr(observation_adapter.subprocess, "run", racing_run)

    with pytest.raises(OwnerlessGitObservationError) as raised:
        observe_ownerless_git(repo, branch="work/orphan", accepted_branch="dev")

    assert (raised.value.kind, raised.value.detail) == ("registration", "accepted_drift")


def test_accepted_snapshot_rechecks_live_head_after_symbolic_branch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, _lane = orphan_work_lane(tmp_path)
    real_run = subprocess.run
    accepted_symbolic_calls = 0

    def advance_accepted() -> None:
        (repo / "README.md").write_text("# advanced late\n", encoding="utf-8")
        real_run(["git", "add", "README.md"], cwd=repo, check=True, capture_output=True)
        real_run(
            [
                "git",
                "-c",
                "user.name=Test User",
                "-c",
                "user.email=test@example.com",
                "commit",
                "-m",
                "advance accepted during terminal branch read",
            ],
            cwd=repo,
            check=True,
            capture_output=True,
        )

    def racing_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        nonlocal accepted_symbolic_calls
        command = list(args)
        if kwargs.get("cwd") == repo and command[1:] == ["symbolic-ref", "-q", "HEAD"]:
            accepted_symbolic_calls += 1
            if accepted_symbolic_calls == 2:
                advance_accepted()
        return real_run(command, **kwargs)  # type: ignore[return-value]

    monkeypatch.setattr(observation_adapter.subprocess, "run", racing_run)

    with pytest.raises(OwnerlessGitObservationError) as raised:
        observe_ownerless_git(repo, branch="work/orphan", accepted_branch="dev")

    assert (raised.value.kind, raised.value.detail) == ("registration", "accepted_drift")


def test_ownerless_observation_rechecks_root_after_terminal_accepted_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, _lane = orphan_work_lane(tmp_path)
    replacement = tmp_path / "replacement"
    git(tmp_path, "clone", repo.as_posix(), replacement.as_posix())
    original = tmp_path / "original"
    real_run = subprocess.run
    listing_calls = 0

    def swapping_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        nonlocal listing_calls
        command = list(args)
        if command[1:] == ["worktree", "list", "--porcelain", "-z"]:
            listing_calls += 1
            if listing_calls == 4:
                repo.rename(original)
                replacement.rename(repo)
        return real_run(command, **kwargs)  # type: ignore[return-value]

    monkeypatch.setattr(observation_adapter.subprocess, "run", swapping_run)

    with pytest.raises(OwnerlessGitObservationError) as raised:
        observe_ownerless_git(repo, branch="work/orphan", accepted_branch="dev")

    assert (raised.value.kind, raised.value.detail) == ("unverifiable", "root")


def test_target_snapshot_rechecks_head_after_all_fact_capture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, _lane = orphan_work_lane(tmp_path)
    old_head = git(repo, "rev-parse", "work/orphan")
    tree = git(repo, "rev-parse", f"{old_head}^{{tree}}")
    new_head = git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit-tree",
        tree,
        "-p",
        old_head,
        "-m",
        "same-tree target advance",
    )
    real_run = subprocess.run
    status_calls = 0

    def advance_target() -> None:
        real_run(
            ["git", "update-ref", "refs/heads/work/orphan", new_head, old_head],
            cwd=repo,
            check=True,
            capture_output=True,
        )

    def racing_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        nonlocal status_calls
        command = list(args)
        if command[1:3] == ["status", "--porcelain=v2"]:
            status_calls += 1
            if status_calls == 2:
                advance_target()
        return real_run(command, **kwargs)  # type: ignore[return-value]

    monkeypatch.setattr(observation_adapter.subprocess, "run", racing_run)

    with pytest.raises(OwnerlessGitObservationError) as raised:
        observe_ownerless_git(repo, branch="work/orphan", accepted_branch="dev")

    assert (raised.value.kind, raised.value.detail) == ("registration", "target_drift")


def test_terminal_target_registration_failure_is_classified_as_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, _lane = orphan_work_lane(tmp_path)
    real_token = vars(observation_adapter)["_registration_token"]
    calls = 0

    def failing_token(*args: object, **kwargs: object) -> GitWorktreeRegistrationToken:
        nonlocal calls
        calls += 1
        if calls == 2:
            fail = vars(observation_adapter)["_fail"]
            fail("registration", "target")
        return real_token(*args, **kwargs)

    monkeypatch.setattr(observation_adapter, "_registration_token", failing_token)

    with pytest.raises(OwnerlessGitObservationError) as raised:
        observe_ownerless_git(repo, branch="work/orphan", accepted_branch="dev")

    assert (raised.value.kind, raised.value.detail) == ("registration", "target_drift")


def test_terminal_accepted_failure_is_classified_as_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, _lane = orphan_work_lane(tmp_path)
    real_snapshot = vars(observation_adapter)["_accepted_snapshot"]
    calls = 0

    def failing_snapshot(*args: object, **kwargs: object) -> tuple[object, ...]:
        nonlocal calls
        calls += 1
        if calls == 2:
            fail = vars(observation_adapter)["_fail"]
            fail("unverifiable", "accepted_ref")
        return real_snapshot(*args, **kwargs)

    monkeypatch.setattr(observation_adapter, "_accepted_snapshot", failing_snapshot)

    with pytest.raises(OwnerlessGitObservationError) as raised:
        observe_ownerless_git(repo, branch="work/orphan", accepted_branch="dev")

    assert (raised.value.kind, raised.value.detail) == ("registration", "accepted_drift")


@pytest.mark.parametrize("drift", ["accepted", "target"])
def test_live_head_drift_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    drift: str,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    real_run = subprocess.run

    def drifting_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        command = list(args)
        cwd = kwargs.get("cwd")
        if command[1:] == ["rev-parse", "--verify", "HEAD^{commit}"] and (
            (drift == "accepted" and cwd == repo) or (drift == "target" and cwd == lane)
        ):
            return subprocess.CompletedProcess(command, 0, b"f" * 40 + b"\n", b"")
        return real_run(command, **kwargs)  # type: ignore[return-value]

    monkeypatch.setattr(observation_adapter.subprocess, "run", drifting_run)

    with pytest.raises(OwnerlessGitObservationError) as raised:
        observe_ownerless_git(repo, branch="work/orphan", accepted_branch="dev")

    assert raised.value.kind == "registration"
    assert raised.value.detail == f"{drift}_head"


@pytest.mark.parametrize(
    ("mutation", "detail"),
    [
        pytest.param("worktree", "worktree", id="worktree-diff"),
        pytest.param("index", "index", id="staged-index-diff"),
        pytest.param("untracked", "untracked", id="untracked-inventory"),
        pytest.param("assume", "assume_unchanged", id="assume-unchanged"),
        pytest.param("skip", "skip_worktree", id="skip-worktree"),
    ],
)
def test_ownerless_observation_rejects_the_complete_dirt_matrix(
    tmp_path: Path,
    mutation: str,
    detail: str,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    if mutation in {"worktree", "index"}:
        (lane / "README.md").write_text(f"{mutation}\n", encoding="utf-8")
        if mutation == "index":
            git(lane, "add", "README.md")
    elif mutation == "untracked":
        (lane / "untracked.bin").write_bytes(b"untracked\x00bytes")
    elif mutation == "assume":
        git(lane, "update-index", "--assume-unchanged", "README.md")
    else:
        git(lane, "update-index", "--skip-worktree", "README.md")

    with pytest.raises(OwnerlessGitObservationError) as raised:
        observe_ownerless_git(repo, branch="work/orphan", accepted_branch="dev")

    assert (raised.value.kind, raised.value.detail) == ("dirty", detail)
    observed, gaps = observe_lane(repo, "work/orphan")
    assert gaps == []
    assert observed.dirty is True


@pytest.mark.parametrize("driver", ["textconv", "external"])
@pytest.mark.parametrize("scope", ["worktree", "index"])
def test_tracked_digest_bypasses_repository_diff_drivers(
    tmp_path: Path, driver: str, scope: str
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    if driver == "textconv":
        (lane / ".gitattributes").write_text("README.md diff=constant\n", encoding="utf-8")
        git(lane, "add", ".gitattributes")
        git(
            lane,
            "-c",
            "user.name=Test User",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-m",
            "configure textconv",
        )
        git(lane, "config", "diff.constant.textconv", "sed -e 's/.*/constant/'")
    else:
        git(lane, "config", "diff.external", "true")

    def observe(raw: bytes):
        (lane / "README.md").write_bytes(raw)
        if scope == "index":
            git(lane, "add", "README.md")
        value, gaps = observe_lane(repo, "work/orphan")
        assert gaps == []
        assert value.dirty is True
        return value

    first = observe(b"bravo\n")
    second = observe(b"cello\n")

    assert first.tracked_digest != second.tracked_digest


def test_untracked_digest_binds_inventory_and_regular_member_bytes(tmp_path: Path) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    member = lane / "untracked.bin"
    member.write_bytes(b"first\x00bytes")
    first, first_gaps = observe_lane(repo, "work/orphan")
    member.write_bytes(b"second\x00bytes")
    second, second_gaps = observe_lane(repo, "work/orphan")
    (lane / "other.bin").write_bytes(b"second\x00bytes")
    third, third_gaps = observe_lane(repo, "work/orphan")

    assert first_gaps == second_gaps == third_gaps == []
    assert first.untracked_digest != second.untracked_digest
    assert second.untracked_digest != third.untracked_digest


def test_untracked_digest_binds_symlink_target_without_following_it(tmp_path: Path) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    link = lane / "untracked-link"
    link.symlink_to("first-target")
    first, first_gaps = observe_lane(repo, "work/orphan")
    link.unlink()
    link.symlink_to("second-target")
    second, second_gaps = observe_lane(repo, "work/orphan")

    assert first_gaps == second_gaps == []
    assert first.untracked_digest != second.untracked_digest


def test_inventoried_untracked_fifo_makes_observation_unverifiable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    os.mkfifo(lane / "untracked-fifo")
    real_run = subprocess.run

    def inventory_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        if list(args)[1:] == ["ls-files", "--others", "--exclude-standard", "-z"]:
            return subprocess.CompletedProcess(args, 0, b"untracked-fifo\0", b"")
        return real_run(args, **kwargs)  # type: ignore[return-value]

    monkeypatch.setattr(observation_adapter.subprocess, "run", inventory_run)

    observed, gaps = observe_lane(repo, "work/orphan")

    assert gaps == ["lane_resolution_target_unverifiable"]
    assert observed.ambiguous is True


def test_complete_target_snapshot_rejects_untracked_content_change_between_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    member = lane / "untracked.bin"
    member.write_bytes(b"first")
    real_run = subprocess.run
    listing_calls = 0

    def racing_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        nonlocal listing_calls
        command = list(args)
        if command[1:] == ["worktree", "list", "--porcelain", "-z"]:
            listing_calls += 1
            if listing_calls == 3:
                member.write_bytes(b"second")
        return real_run(command, **kwargs)  # type: ignore[return-value]

    monkeypatch.setattr(observation_adapter.subprocess, "run", racing_run)

    observed, gaps = observe_lane(repo, "work/orphan")

    assert gaps == ["lane_resolution_target_unverifiable"]
    assert observed.ambiguous is True


def test_unknown_index_marker_is_unverifiable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, _lane = orphan_work_lane(tmp_path)
    real_run = subprocess.run

    def unknown_marker(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        if list(args)[1:] == ["ls-files", "-v", "-z"]:
            return subprocess.CompletedProcess(args, 0, b"X README.md\0", b"")
        return real_run(args, **kwargs)  # type: ignore[return-value]

    monkeypatch.setattr(observation_adapter.subprocess, "run", unknown_marker)

    with pytest.raises(OwnerlessGitObservationError) as raised:
        observe_ownerless_git(repo, branch="work/orphan", accepted_branch="dev")

    assert (raised.value.kind, raised.value.detail) == ("unverifiable", "index_flags")


def test_missing_observation_uses_repository_object_format(tmp_path: Path) -> None:
    repo = tmp_path / "sha256-repo"
    repo.mkdir()
    git(repo, "init", "--initial-branch=dev", "--object-format=sha256")
    (repo / "README.md").write_text("fixture\n", encoding="utf-8")
    git(repo, "add", "README.md")
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "initial",
    )

    observed, gaps = observe_lane(repo, "work/missing")

    assert gaps == ["lane_resolution_target_missing"]
    assert observed.head == "0" * 64


@pytest.mark.parametrize("mode", ["failure", "unknown"])
def test_existing_repository_object_format_failure_is_unverifiable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    repo, _lane = orphan_work_lane(tmp_path)
    real_run = subprocess.run

    def object_format(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        if list(args)[1:] == ["rev-parse", "--show-object-format"]:
            return subprocess.CompletedProcess(
                args,
                1 if mode == "failure" else 0,
                b"" if mode == "failure" else b"sha512\n",
                b"",
            )
        return real_run(args, **kwargs)  # type: ignore[return-value]

    monkeypatch.setattr(observation_adapter.subprocess, "run", object_format)

    observed, gaps = observe_lane(repo, "work/missing")

    assert gaps == ["lane_resolution_target_unverifiable"]
    assert observed.head == "0" * 40


def test_missing_observation_rechecks_pinned_root_after_object_format(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, _lane = orphan_work_lane(tmp_path)
    git(repo, "worktree", "remove", _lane.as_posix())
    replacement = tmp_path / "replacement"
    replacement.mkdir()
    git(replacement, "init", "--initial-branch=dev", "--object-format=sha256")
    original = tmp_path / "original"
    real_run = subprocess.run
    swapped = False

    def swapping_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        nonlocal swapped
        command = list(args)
        if not swapped and command[1:] == ["rev-parse", "--show-object-format"]:
            swapped = True
            repo.rename(original)
            replacement.rename(repo)
        return real_run(command, **kwargs)  # type: ignore[return-value]

    monkeypatch.setattr(observation_adapter.subprocess, "run", swapping_run)

    observed, gaps = observe_lane(repo, "work/missing")

    assert gaps == ["lane_resolution_target_unverifiable"]
    assert observed.head == "0" * 40


def test_registration_token_supplies_the_lane_incarnation(
    tmp_path: Path,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)

    facts = observe_ownerless_git(repo, branch="work/orphan", accepted_branch="dev")
    observed, gaps = observe_lane(repo, "work/orphan")
    token = facts.registration_token

    assert gaps == []
    assert observed == facts.observation
    assert token.registered_path == lane.absolute().as_posix()
    assert token.administration_path.startswith((repo / ".git/worktrees").as_posix() + "/")
    assert stat.S_ISDIR(token.worktree_identity.mode)
    assert stat.S_ISREG(token.gitfile_identity.mode)
    assert stat.S_ISDIR(token.administration_identity.mode)
    assert stat.S_ISREG(token.backlink_identity.mode)
    assert observed.lane_incarnation_id.startswith("git-worktree-registration:v1:")
    assert observed.lane_ref not in observed.lane_incarnation_id
    assert observed.head not in observed.lane_incarnation_id


def test_same_path_ref_and_head_delete_recreate_changes_registration_token(
    tmp_path: Path,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    first = observe_ownerless_git(repo, branch="work/orphan", accepted_branch="dev")

    git(repo, "worktree", "remove", lane.as_posix())
    git(repo, "branch", "-D", "work/orphan")
    git(repo, "worktree", "add", "-b", "work/orphan", lane.as_posix(), first.observation.head)
    second = observe_ownerless_git(repo, branch="work/orphan", accepted_branch="dev")

    assert second.observation.path == first.observation.path
    assert second.observation.head == first.observation.head
    assert second.registration_token != first.registration_token
    assert second.observation.lane_incarnation_id != first.observation.lane_incarnation_id


def test_root_symlink_is_unverifiable(tmp_path: Path) -> None:
    repo, _lane = orphan_work_lane(tmp_path)
    linked_root = tmp_path / "linked-root"
    linked_root.symlink_to(repo, target_is_directory=True)

    with pytest.raises(OwnerlessGitObservationError) as raised:
        observe_ownerless_git(linked_root, branch="work/orphan", accepted_branch="dev")

    assert (raised.value.kind, raised.value.detail) == ("unverifiable", "root")


def test_target_worktree_symlink_is_not_a_registration(
    tmp_path: Path,
) -> None:
    repo, lane = orphan_work_lane(tmp_path)
    moved = tmp_path / "moved-lane"
    lane.rename(moved)
    lane.symlink_to(moved, target_is_directory=True)

    with pytest.raises(OwnerlessGitObservationError) as raised:
        observe_ownerless_git(repo, branch="work/orphan", accepted_branch="dev")

    assert (raised.value.kind, raised.value.detail) == ("registration", "target")


def test_non_utf8_oid_output_is_unverifiable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, _lane = orphan_work_lane(tmp_path)
    real_run = subprocess.run

    def invalid_oid(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        command = list(args)
        if command[1:] == [
            "rev-parse",
            "--verify",
            "refs/heads/work/orphan^{commit}",
        ]:
            return subprocess.CompletedProcess(command, 0, b"\xff\n", b"")
        return real_run(command, **kwargs)  # type: ignore[return-value]

    monkeypatch.setattr(observation_adapter.subprocess, "run", invalid_oid)

    with pytest.raises(OwnerlessGitObservationError) as raised:
        observe_ownerless_git(repo, branch="work/orphan", accepted_branch="dev")

    assert (raised.value.kind, raised.value.detail) == ("unverifiable", "target_ref")


@pytest.mark.parametrize(
    ("returncode", "stderr"),
    [(1, b""), (0, b"warning")],
    ids=("nonzero", "stderr"),
)
def test_git_failure_or_stderr_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    returncode: int,
    stderr: bytes,
) -> None:
    repo, _lane = orphan_work_lane(tmp_path)
    monkeypatch.setattr(
        observation_adapter.subprocess,
        "run",
        lambda args, **_kwargs: subprocess.CompletedProcess(args, returncode, b"", stderr),
    )

    with pytest.raises(OwnerlessGitObservationError) as raised:
        git_object_bytes(repo, "HEAD:README.md")

    assert raised.value.kind == "unverifiable"


def test_git_ancestry_has_exact_three_state_literals(tmp_path: Path) -> None:
    repo, _lane = orphan_work_lane(tmp_path)
    ancestor = git(repo, "rev-parse", "dev")
    (repo / "accepted.txt").write_text("accepted\n", encoding="utf-8")
    git(repo, "add", "accepted.txt")
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "advance accepted",
    )
    descendant = git(repo, "rev-parse", "dev")

    assert git_ancestry(repo, ancestor, descendant) == "ancestor"
    assert git_ancestry(repo, descendant, ancestor) == "diverged"
    assert git_ancestry(repo, "not-an-object", descendant) == "unverifiable"
