from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

import ethos.adapters.mutation.resolution.preservation.core as preservation


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def _repository(path: Path) -> Path:
    path.mkdir()
    _git(path, "init", "-b", "work/example")
    _git(path, "config", "user.name", "Test User")
    _git(path, "config", "user.email", "test@example.com")
    (path / ".gitignore").write_text(
        "not-in-inventory.txt\nnested/not-in-inventory.txt\n",
        encoding="utf-8",
    )
    (path / "tracked.txt").write_bytes(b"base\n")
    _git(path, "add", ".gitignore", "tracked.txt")
    _git(path, "commit", "-m", "base")
    return path


def test_git_payloads_keep_exact_worktree_and_index_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    bundle = tmp_path / "repository.bundle"
    tracked_patch = tmp_path / "tracked.patch"
    index_patch = tmp_path / "index.patch"
    calls: list[tuple[str, ...]] = []

    def fixed_git_bytes(root: Path, *args: str):
        assert root == source
        calls.append(args)
        if args[:2] == ("bundle", "create"):
            assert args == ("bundle", "create", bundle.as_posix(), "work/example")
            bundle.write_bytes(b"bundle")
            return subprocess.CompletedProcess(["git", *args], 0, stdout=b"", stderr=b"")
        payload = b"index\x00patch\xff" if "--cached" in args else b"tracked\x00patch\xfe"
        return subprocess.CompletedProcess(["git", *args], 0, stdout=payload, stderr=b"")

    monkeypatch.setattr(preservation, "run_git_bytes", fixed_git_bytes)

    preservation.write_git_preservation_payloads(
        source=source,
        bundle=bundle,
        tracked_patch=tracked_patch,
        index_patch=index_patch,
        lane_ref="work/example",
    )

    assert calls == [
        ("bundle", "create", bundle.as_posix(), "work/example"),
        ("diff", "--no-ext-diff", "--no-textconv", "--binary", "HEAD", "--"),
        ("diff", "--cached", "--no-ext-diff", "--no-textconv", "--binary", "HEAD", "--"),
    ]
    assert tracked_patch.read_bytes() == b"tracked\x00patch\xfe"
    assert index_patch.read_bytes() == b"index\x00patch\xff"


def test_git_payloads_ignore_hostile_git_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = _repository(tmp_path / "source")
    hostile = _repository(tmp_path / "hostile")
    (hostile / "attacker.txt").write_bytes(b"attacker\n")
    _git(hostile, "add", "attacker.txt")
    _git(hostile, "commit", "-m", "attacker")
    (source / "tracked.txt").write_bytes(b"source index change\n")
    _git(source, "add", "tracked.txt")
    (source / "tracked.txt").write_bytes(b"source worktree change\n")
    source_head = _git(source, "rev-parse", "work/example").stdout.strip()
    hostile_head = _git(hostile, "rev-parse", "work/example").stdout.strip()
    assert source_head != hostile_head

    bundle = tmp_path / "repository.bundle"
    tracked_patch = tmp_path / "tracked.patch"
    index_patch = tmp_path / "index.patch"
    hostile_git_dir = hostile / ".git"
    monkeypatch.setenv("GIT_DIR", hostile_git_dir.as_posix())
    monkeypatch.setenv("GIT_WORK_TREE", hostile.as_posix())
    monkeypatch.setenv("GIT_INDEX_FILE", (hostile_git_dir / "index").as_posix())

    preservation.write_git_preservation_payloads(
        source=source,
        bundle=bundle,
        tracked_patch=tracked_patch,
        index_patch=index_patch,
        lane_ref="work/example",
    )

    monkeypatch.delenv("GIT_DIR")
    monkeypatch.delenv("GIT_WORK_TREE")
    monkeypatch.delenv("GIT_INDEX_FILE")
    bundle_head = _git(source, "bundle", "list-heads", bundle).stdout.split()[0]

    assert bundle_head == source_head
    assert b"source worktree change" in tracked_patch.read_bytes()
    assert b"source index change" in index_patch.read_bytes()


@pytest.mark.parametrize("driver", ["textconv", "external"])
@pytest.mark.parametrize("scope", ["tracked", "index"])
def test_git_payloads_bypass_repository_diff_drivers(
    tmp_path: Path, driver: str, scope: str
) -> None:
    source = _repository(tmp_path / "source")
    if driver == "textconv":
        (source / ".gitattributes").write_text("tracked.txt diff=constant\n", encoding="utf-8")
        _git(source, "add", ".gitattributes")
        _git(source, "commit", "-m", "configure textconv")
        _git(source, "config", "diff.constant.textconv", "sed -e 's/.*/constant/'")
    else:
        _git(source, "config", "diff.external", "true")

    def capture(name: str, raw: bytes) -> bytes:
        (source / "tracked.txt").write_bytes(raw)
        if scope == "index":
            _git(source, "add", "tracked.txt")
        package = tmp_path / name
        package.mkdir()
        preservation.write_git_preservation_payloads(
            source=source,
            bundle=package / "repository.bundle",
            tracked_patch=package / "tracked.patch",
            index_patch=package / "index.patch",
            lane_ref="work/example",
        )
        return (package / f"{scope}.patch").read_bytes()

    first = capture("first", b"bravo\n")
    second = capture("second", b"cello\n")

    assert first
    assert first != second


@pytest.mark.parametrize(
    ("failed_command", "diagnostic"),
    [
        ("bundle", "bundle failed"),
        ("tracked", "tracked diff failed"),
        ("index", "index diff failed"),
    ],
)
def test_git_payloads_fail_closed_before_manifest_on_command_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failed_command: str,
    diagnostic: str,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    bundle = tmp_path / "repository.bundle"
    tracked_patch = tmp_path / "tracked.patch"
    index_patch = tmp_path / "index.patch"

    def fixed_git_bytes(root: Path, *args: str):
        assert root == source
        command = (
            "bundle"
            if args[:2] == ("bundle", "create")
            else "index"
            if "--cached" in args
            else "tracked"
        )
        if command == "bundle" and failed_command != command:
            Path(args[2]).write_bytes(b"bundle")
        return subprocess.CompletedProcess(
            ["git", *args],
            int(command == failed_command),
            stdout=b"patch",
            stderr=diagnostic.encode() if command == failed_command else b"",
        )

    monkeypatch.setattr(preservation, "run_git_bytes", fixed_git_bytes)

    with pytest.raises(ValueError, match=diagnostic):
        preservation.write_git_preservation_payloads(
            source=source,
            bundle=bundle,
            tracked_patch=tracked_patch,
            index_patch=index_patch,
            lane_ref="work/example",
        )


@pytest.mark.parametrize(
    ("failed_command", "diagnostic"),
    [
        ("bundle", "bundle warning"),
        ("tracked", "tracked diff warning"),
        ("index", "index diff warning"),
    ],
)
def test_git_payloads_fail_closed_on_stderr_with_success_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failed_command: str,
    diagnostic: str,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    bundle = tmp_path / "repository.bundle"
    tracked_patch = tmp_path / "tracked.patch"
    index_patch = tmp_path / "index.patch"
    generic_calls: list[tuple[str, ...]] = []

    def fixed_git(root: Path, *args: str, **_kwargs: object):
        assert root == source
        generic_calls.append(args)
        if args[:2] == ("bundle", "create") and failed_command != "bundle":
            bundle.write_bytes(b"bundle")
        return subprocess.CompletedProcess(
            ["git", *args],
            0,
            stdout="",
            stderr=diagnostic if failed_command == "bundle" else "",
        )

    def fixed_git_bytes(root: Path, *args: str):
        assert root == source
        command = (
            "bundle"
            if args[:2] == ("bundle", "create")
            else "index"
            if "--cached" in args
            else "tracked"
        )
        if command == "bundle" and failed_command != command:
            Path(args[2]).write_bytes(b"bundle")
        return subprocess.CompletedProcess(
            ["git", *args],
            0,
            stdout=b"patch",
            stderr=diagnostic.encode() if command == failed_command else b"",
        )

    monkeypatch.setattr(preservation, "run_git", fixed_git, raising=False)
    monkeypatch.setattr(preservation, "run_git_bytes", fixed_git_bytes)

    with pytest.raises(ValueError, match=diagnostic):
        preservation.write_git_preservation_payloads(
            source=source,
            bundle=bundle,
            tracked_patch=tracked_patch,
            index_patch=index_patch,
            lane_ref="work/example",
        )

    assert generic_calls == []


def test_binary_git_runner_uses_literal_git_and_retains_byte_diagnostic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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

    def run(command: list[str], **kwargs: object):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 1, stdout=b"", stderr=b"bad bytes")

    monkeypatch.setattr(preservation.subprocess, "run", run)

    completed = preservation.run_git_bytes(tmp_path, "diff", "--binary", "HEAD", "--")

    assert completed.returncode == 1
    assert completed.stderr == b"bad bytes"
    assert calls == [
        (
            ["git", "diff", "--binary", "HEAD", "--"],
            {
                "cwd": tmp_path,
                "check": False,
                "capture_output": True,
                "env": {
                    "GIT_ATTR_NOSYSTEM": "1",
                    "GIT_CONFIG_GLOBAL": os.devnull,
                    "GIT_CONFIG_NOSYSTEM": "1",
                    "GIT_NO_REPLACE_OBJECTS": "1",
                    "GIT_OPTIONAL_LOCKS": "0",
                    "LC_ALL": "C",
                    "PATH": os.environ.get("PATH", os.defpath),
                },
                "shell": False,
            },
        )
    ]
