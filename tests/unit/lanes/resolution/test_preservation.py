from __future__ import annotations

import hashlib
import os
import subprocess
import tarfile
from pathlib import Path
from typing import BinaryIO
from typing import cast

import pytest

import ethos.adapters.mutation.resolution._effects as resolution_effects
import ethos.adapters.mutation.resolution.preservation.core as preservation
from ethos_core.contracts.resolution.lane import LaneObservation

_FIFO_SWAP_WOULD_BLOCK = "regular-to-fifo swap would block without O_NONBLOCK"
_READ_EXCEEDS_PINNED_SIZE = "capture requested bytes beyond the pinned file size"
_TAR_WRITE_FAILED = "tar write failed"


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


def _observation(source: Path) -> LaneObservation:
    return LaneObservation(
        lane_ref="work/example",
        head="a" * 40,
        lane_incarnation_id="lane:one",
        path=source.as_posix(),
        dirty=True,
        foreign=True,
        orphan=True,
        ambiguous=False,
        tracked_digest="b" * 64,
        untracked_digest="c" * 64,
    )


def test_git_payloads_keep_exact_worktree_and_index_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    bundle = tmp_path / "repository.bundle"
    tracked_patch = tmp_path / "tracked.patch"
    index_patch = tmp_path / "index.patch"
    calls: list[tuple[str, ...]] = []

    def fixed_git(root: Path, *args: str, **_kwargs: object):
        assert root == source
        calls.append(args)
        assert args == ("bundle", "create", bundle.as_posix(), "work/example")
        bundle.write_bytes(b"bundle")
        return subprocess.CompletedProcess(["git", *args], 0, stdout="", stderr="")

    def fixed_git_bytes(root: Path, *args: str):
        assert root == source
        calls.append(args)
        payload = b"index\x00patch\xff" if "--cached" in args else b"tracked\x00patch\xfe"
        return subprocess.CompletedProcess(["git", *args], 0, stdout=payload, stderr=b"")

    monkeypatch.setattr(preservation, "run_git", fixed_git)
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
def test_git_payloads_fail_closed_before_manifest_on_byte_command_failure(
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

    def fixed_git(root: Path, *args: str, **_kwargs: object):
        assert root == source
        if failed_command != "bundle":
            bundle.write_bytes(b"bundle")
        return subprocess.CompletedProcess(
            ["git", *args],
            int(failed_command == "bundle"),
            stdout="",
            stderr=diagnostic if failed_command == "bundle" else "",
        )

    def fixed_git_bytes(root: Path, *args: str):
        assert root == source
        command = "index" if "--cached" in args else "tracked"
        return subprocess.CompletedProcess(
            ["git", *args],
            int(command == failed_command),
            stdout=b"patch",
            stderr=diagnostic.encode() if command == failed_command else b"",
        )

    monkeypatch.setattr(preservation, "run_git", fixed_git)
    monkeypatch.setattr(preservation, "run_git_bytes", fixed_git_bytes)

    with pytest.raises(ValueError, match=diagnostic):
        preservation.write_git_preservation_payloads(
            source=source,
            bundle=bundle,
            tracked_patch=tracked_patch,
            index_patch=index_patch,
            lane_ref="work/example",
        )


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


def test_untracked_archive_preserves_raw_non_utf8_member_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    stored_name = "stored.bin"
    (source / stored_name).write_bytes(b"raw member bytes\x00\xff")
    raw_name = b"member-\xff.bin"
    member_name = raw_name.decode(errors="surrogateescape")
    archive_path = tmp_path / "untracked.tar"
    real_open = os.open
    real_stat = os.stat

    def mapped_open(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        mapped = stored_name if path == member_name else path
        return real_open(mapped, flags, mode, dir_fd=dir_fd)

    def mapped_stat(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        dir_fd: int | None = None,
        follow_symlinks: bool = True,
    ) -> os.stat_result:
        mapped = stored_name if path == member_name else path
        return real_stat(mapped, dir_fd=dir_fd, follow_symlinks=follow_symlinks)

    monkeypatch.setattr(os, "open", mapped_open)
    monkeypatch.setattr(os, "stat", mapped_stat)

    preservation.write_untracked_archive(
        source=source,
        archive=archive_path,
        inventory=[raw_name],
    )

    with tarfile.open(
        archive_path,
        "r",
        encoding="utf-8",
        errors="surrogateescape",
    ) as archive:
        assert archive.getnames() == [member_name]
        stored = archive.extractfile(member_name)
        assert stored is not None
        assert stored.read() == b"raw member bytes\x00\xff"


def test_untracked_inventory_digest_binds_empty_regular_and_symlink_payloads(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    content = b"listed bytes\n"
    (source / "listed.bin").write_bytes(content)
    (source / "listed-link").symlink_to("listed.bin")
    inventory = b"listed.bin\0listed-link\0"
    expected = hashlib.sha256(inventory)
    expected.update(tarfile.REGTYPE)
    expected.update(len(content).to_bytes(8, "big"))
    expected.update(content)
    target = b"listed.bin"
    expected.update(tarfile.SYMTYPE)
    expected.update(len(target).to_bytes(8, "big"))
    expected.update(target)

    assert (
        preservation.digest_untracked_inventory(source=source, inventory=b"")
        == hashlib.sha256(b"").hexdigest()
    )
    assert (
        preservation.digest_untracked_inventory(source=source, inventory=inventory)
        == expected.hexdigest()
    )


def test_untracked_archive_fails_closed_on_parent_symlink_swap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    parent = source / "parent"
    parent.mkdir()
    (parent / "listed.bin").write_bytes(b"inside bytes\n")
    outside = tmp_path / "outside"
    outside.mkdir()
    outside_bytes = b"outside bytes must never enter\n"
    (outside / "listed.bin").write_bytes(outside_bytes)
    archive_path = tmp_path / "untracked.tar"
    pinned_parent = source / "pinned-parent"
    swapped = False
    real_open = os.open

    def racing_open(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal swapped
        descriptor = real_open(path, flags, mode, dir_fd=dir_fd)
        if path in {"parent", b"parent"} and dir_fd is not None and flags & os.O_DIRECTORY:
            parent.rename(pinned_parent)
            parent.symlink_to(outside, target_is_directory=True)
            swapped = True
        return descriptor

    monkeypatch.setattr(os, "open", racing_open)

    with pytest.raises(ValueError, match="lane_resolution_untracked_member_changed"):
        preservation.write_untracked_archive(
            source=source,
            archive=archive_path,
            inventory=[b"parent/listed.bin"],
        )

    assert swapped is True
    assert not archive_path.exists() or outside_bytes not in archive_path.read_bytes()


def test_untracked_archive_fails_closed_on_regular_file_swap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    listed = source / "listed.bin"
    listed.write_bytes(b"listed bytes\n")
    pinned = source / "pinned.bin"
    replacement = b"replacement bytes must never enter\n"
    archive_path = tmp_path / "untracked.tar"
    swapped = False
    real_open = os.open

    def racing_open(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal swapped
        descriptor = real_open(path, flags, mode, dir_fd=dir_fd)
        if path in {"listed.bin", b"listed.bin"} and dir_fd is not None:
            listed.rename(pinned)
            listed.write_bytes(replacement)
            swapped = True
        return descriptor

    monkeypatch.setattr(os, "open", racing_open)

    with pytest.raises(ValueError, match="lane_resolution_untracked_member_changed"):
        preservation.write_untracked_archive(
            source=source,
            archive=archive_path,
            inventory=[b"listed.bin"],
        )

    assert swapped is True
    assert not archive_path.exists() or replacement not in archive_path.read_bytes()


def test_untracked_archive_never_blocks_when_regular_member_becomes_fifo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    listed = source / "listed.bin"
    listed.write_bytes(b"listed bytes\n")
    archive_path = tmp_path / "untracked.tar"
    real_open = os.open
    opened_flags: list[int] = []

    def racing_open(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        if path in {"listed.bin", b"listed.bin"} and dir_fd is not None:
            listed.unlink()
            os.mkfifo(listed)
            opened_flags.append(flags)
            if not flags & os.O_NONBLOCK:
                raise AssertionError(_FIFO_SWAP_WOULD_BLOCK)
        return real_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(os, "open", racing_open)

    with pytest.raises(ValueError, match="lane_resolution_untracked_member_changed"):
        preservation.write_untracked_archive(
            source=source,
            archive=archive_path,
            inventory=[b"listed.bin"],
        )

    assert len(opened_flags) == 1
    assert opened_flags[0] & os.O_NONBLOCK


def test_growing_untracked_member_never_reads_beyond_pinned_size(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    listed = source / "listed.bin"
    pinned = b"base"
    listed.write_bytes(pinned)
    archive_path = tmp_path / "untracked.tar"
    real_read = os.read
    requests: list[int] = []
    grew = False

    def racing_read(descriptor: int, size: int) -> bytes:
        nonlocal grew
        requests.append(size)
        if size > len(pinned):
            raise AssertionError(_READ_EXCEEDS_PINNED_SIZE)
        if not grew:
            with listed.open("ab") as stream:
                stream.write(b"concurrent growth")
            grew = True
        return real_read(descriptor, size)

    monkeypatch.setattr(os, "read", racing_read)

    with pytest.raises(ValueError, match="lane_resolution_untracked_member_changed"):
        preservation.write_untracked_archive(
            source=source,
            archive=archive_path,
            inventory=[b"listed.bin"],
        )

    assert grew is True
    assert requests == [len(pinned)]


def test_large_untracked_member_spills_and_closes_spool(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    content = b"large member\n" * (2 * 1024 * 1024 // len(b"large member\n") + 1)
    (source / "large.bin").write_bytes(content)
    archive_path = tmp_path / "untracked.tar"
    captured: list[BinaryIO] = []
    rolled: list[bool] = []
    addfile = tarfile.TarFile.addfile

    def observe_addfile(
        stream: tarfile.TarFile,
        info: tarfile.TarInfo,
        fileobj: BinaryIO | None = None,
    ) -> None:
        assert fileobj is not None
        captured.append(fileobj)
        rolled.append(bool(getattr(fileobj, "_rolled", False)))
        addfile(stream, info, fileobj)

    monkeypatch.setattr(tarfile.TarFile, "addfile", observe_addfile)

    preservation.write_untracked_archive(
        source=source,
        archive=archive_path,
        inventory=[b"large.bin"],
    )

    assert rolled == [True]
    assert len(captured) == 1
    assert captured[0].closed is True
    with tarfile.open(archive_path, "r") as archive:
        stored = archive.extractfile("large.bin")
        assert stored is not None
        assert stored.read() == content


def test_untracked_member_spool_closes_when_tar_write_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "large.bin").write_bytes(b"x" * (2 * 1024 * 1024))
    captured: list[BinaryIO] = []

    def fail_addfile(
        _stream: tarfile.TarFile,
        _info: tarfile.TarInfo,
        fileobj: BinaryIO | None = None,
    ) -> None:
        assert fileobj is not None
        captured.append(fileobj)
        raise RuntimeError(_TAR_WRITE_FAILED)

    monkeypatch.setattr(tarfile.TarFile, "addfile", fail_addfile)

    with pytest.raises(RuntimeError, match="tar write failed"):
        preservation.write_untracked_archive(
            source=source,
            archive=tmp_path / "untracked.tar",
            inventory=[b"large.bin"],
        )

    assert len(captured) == 1
    assert captured[0].closed is True


def test_untracked_archive_rejects_unsupported_member(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    os.mkfifo(source / "unsupported.fifo")

    with pytest.raises(ValueError, match="lane_resolution_untracked_member_unsupported"):
        preservation.write_untracked_archive(
            source=source,
            archive=tmp_path / "untracked.tar",
            inventory=[b"unsupported.fifo"],
        )


def test_preserve_package_uses_fixed_git_stdlib_tar_and_v2_payloads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    stored_bytes = b"binary\x00payload\xff\n"
    (source / "listed.bin").write_bytes(stored_bytes)
    (source / "listed-link").symlink_to("listed.bin")
    (source / "nested").mkdir()
    (source / "nested/listed.bin").write_bytes(b"nested bytes\n")
    (source / "nested/not-in-inventory.txt").write_text("exclude me\n", encoding="utf-8")
    (source / "not-in-inventory.txt").write_text("exclude me\n", encoding="utf-8")
    package = tmp_path / "package"
    package.mkdir()
    calls: list[tuple[str, ...]] = []

    def fixed_git(root: Path, *args: str, **_kwargs: object):
        assert root == source
        calls.append(args)
        assert args[:2] == ("bundle", "create")
        Path(args[2]).write_bytes(b"bundle")
        return subprocess.CompletedProcess(["git", *args], 0, stdout="", stderr="")

    def fixed_git_bytes(root: Path, *args: str):
        assert root == source
        calls.append(args)
        payload = b"index patch\n" if "--cached" in args else b"tracked patch\n"
        return subprocess.CompletedProcess(["git", *args], 0, stdout=payload, stderr=b"")

    monkeypatch.setattr(preservation, "run_git", fixed_git)
    monkeypatch.setattr(preservation, "run_git_bytes", fixed_git_bytes)
    monkeypatch.setattr(
        resolution_effects,
        "untracked_files",
        lambda _source: [b"listed-link", b"listed.bin", b"nested/listed.bin"],
    )
    monkeypatch.setattr(
        resolution_effects.subprocess,
        "run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("preservation must not invoke an external archive executable")
        ),
    )

    result = resolution_effects.preserve_package(
        tmp_path,
        package,
        _observation(source),
        {"decision_id": "decision:one"},
    )

    assert calls == [
        ("bundle", "create", (package / "repository.bundle").as_posix(), "work/example"),
        ("diff", "--no-ext-diff", "--no-textconv", "--binary", "HEAD", "--"),
        ("diff", "--cached", "--no-ext-diff", "--no-textconv", "--binary", "HEAD", "--"),
    ]
    with tarfile.open(package / "untracked.tar", "r") as archive:
        assert archive.getnames() == ["listed-link", "listed.bin", "nested/listed.bin"]
        stored = archive.extractfile("listed.bin")
        assert stored is not None
        assert stored.read() == stored_bytes
        link = archive.getmember("listed-link")
        assert link.issym()
        assert link.linkname == "listed.bin"
        nested = archive.extractfile("nested/listed.bin")
        assert nested is not None
        assert nested.read() == b"nested bytes\n"
        assert "nested/not-in-inventory.txt" not in archive.getnames()
        assert "not-in-inventory.txt" not in archive.getnames()
    assert (package / "tracked.patch").read_bytes() == b"tracked patch\n"
    assert (package / "index.patch").read_bytes() == b"index patch\n"
    manifest = result["manifest"]
    assert isinstance(manifest, dict)
    assert manifest["package_format_version"] == "v2"
    assert manifest["patch_sha256"] == hashlib.sha256(b"tracked patch\n").hexdigest()
    assert manifest["index_patch_sha256"] == hashlib.sha256(b"index patch\n").hexdigest()


@pytest.mark.parametrize("inventory", [[b"/absolute.txt"], [b"../outside.txt"]])
def test_untracked_archive_rejects_inventory_outside_source(
    tmp_path: Path,
    inventory: list[bytes],
) -> None:
    source = tmp_path / "source"
    source.mkdir()

    with pytest.raises(ValueError, match="lane_resolution_untracked_path_invalid"):
        preservation.write_untracked_archive(
            source=source,
            archive=tmp_path / "untracked.tar",
            inventory=inventory,
        )


def test_archive_and_digest_translate_boundary_io_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source"
    source.mkdir()

    def fail_tar(*_args: object, **_kwargs: object) -> tarfile.TarFile:
        message = "broken archive"
        raise tarfile.TarError(message)

    monkeypatch.setattr(preservation.tarfile, "open", fail_tar)
    with pytest.raises(ValueError, match="lane_resolution_untracked_member_unverifiable"):
        preservation.write_untracked_archive(
            source=source,
            archive=tmp_path / "untracked.tar",
            inventory=[b"listed.bin"],
        )


@pytest.mark.parametrize("inventory", ["not-bytes", b"listed.bin", b"\0", b"a\0\0"])
def test_inventory_digest_rejects_nonbytes_or_noncanonical_inventory(
    tmp_path: Path,
    inventory: object,
) -> None:
    with pytest.raises(ValueError, match="lane_resolution_untracked_path_invalid"):
        preservation.digest_untracked_inventory(
            source=tmp_path,
            inventory=cast("bytes", inventory),
        )


def test_bound_source_rejects_non_directory_missing_and_rebound_roots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    regular = tmp_path / "regular"
    regular.write_bytes(b"x")
    with pytest.raises(ValueError, match="lane_resolution_untracked_member_unsupported"):
        preservation.digest_untracked_inventory(source=regular, inventory=b"x\0")

    with pytest.raises(ValueError, match="lane_resolution_untracked_member_unverifiable"):
        preservation.digest_untracked_inventory(source=tmp_path / "missing", inventory=b"x\0")

    source = tmp_path / "source"
    rebound = tmp_path / "rebound"
    source.mkdir()
    rebound.mkdir()
    (rebound / "x").write_bytes(b"x")
    real_open = os.open

    def rebound_open(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        if Path(path) == source and dir_fd is None:
            return real_open(rebound, flags, mode)
        return real_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(os, "open", rebound_open)
    with pytest.raises(ValueError, match="lane_resolution_untracked_member_changed"):
        preservation.digest_untracked_inventory(source=source, inventory=b"x\0")


@pytest.mark.parametrize(
    ("setup", "inventory", "message"),
    [
        ("parent-file", b"parent/member\0", "lane_resolution_untracked_member_unsupported"),
        ("missing-member", b"missing\0", "lane_resolution_untracked_member_unverifiable"),
    ],
)
def test_member_capture_rejects_non_directory_parent_or_missing_member(
    tmp_path: Path,
    setup: str,
    inventory: bytes,
    message: str,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    if setup == "parent-file":
        (source / "parent").write_bytes(b"not a directory")

    with pytest.raises(ValueError, match=message):
        preservation.digest_untracked_inventory(source=source, inventory=inventory)


def test_regular_short_read_and_symlink_replacement_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "listed.bin").write_bytes(b"listed")
    monkeypatch.setattr(preservation.os, "read", lambda _descriptor, _size: b"")
    with pytest.raises(ValueError, match="lane_resolution_untracked_member_changed"):
        preservation.digest_untracked_inventory(source=source, inventory=b"listed.bin\0")

    monkeypatch.undo()
    target = source / "target"
    target.write_bytes(b"target")
    link = source / "listed-link"
    link.symlink_to("target")
    real_readlink = os.readlink

    def replace_link(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        dir_fd: int | None = None,
    ) -> str | bytes:
        value = real_readlink(path, dir_fd=dir_fd)
        link.unlink()
        link.symlink_to("replacement")
        return value

    monkeypatch.setattr(os, "readlink", replace_link)
    with pytest.raises(ValueError, match="lane_resolution_untracked_member_changed"):
        preservation.digest_untracked_inventory(source=source, inventory=b"listed-link\0")


def test_directory_and_root_identity_rechecks_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source"
    parent = source / "parent"
    parent.mkdir(parents=True)
    (parent / "listed.bin").write_bytes(b"listed")
    other = tmp_path / "other"
    other.mkdir()
    real_stat = os.stat
    parent_stats = 0

    def drifting_stat(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        dir_fd: int | None = None,
        follow_symlinks: bool = True,
    ) -> os.stat_result:
        nonlocal parent_stats
        if path in {"parent", b"parent"} and dir_fd is not None:
            parent_stats += 1
            if parent_stats > 1:
                return real_stat(other, follow_symlinks=False)
        return real_stat(path, dir_fd=dir_fd, follow_symlinks=follow_symlinks)

    monkeypatch.setattr(os, "stat", drifting_stat)
    with pytest.raises(ValueError, match="lane_resolution_untracked_member_changed"):
        preservation.digest_untracked_inventory(
            source=source,
            inventory=b"parent/listed.bin\0",
        )

    monkeypatch.undo()
    real_path_stat = Path.stat
    source_stats = 0

    def drifting_root_stat(
        path: Path,
        *,
        follow_symlinks: bool = True,
    ) -> os.stat_result:
        nonlocal source_stats
        if path == source:
            source_stats += 1
            if source_stats > 1:
                return real_path_stat(other, follow_symlinks=False)
        return real_path_stat(path, follow_symlinks=follow_symlinks)

    monkeypatch.setattr(Path, "stat", drifting_root_stat)
    with pytest.raises(ValueError, match="lane_resolution_untracked_member_changed"):
        preservation.digest_untracked_inventory(
            source=source,
            inventory=b"parent/listed.bin\0",
        )


def test_descriptor_contexts_close_only_descriptors_they_acquired(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    listed = source / "listed.bin"
    listed.write_bytes(b"x")
    directory_metadata = source.stat(follow_symlinks=False)
    file_metadata = listed.stat(follow_symlinks=False)
    closed: list[int] = []
    bound_source = preservation._bound_source  # noqa: SLF001, RUF100 - context edge
    capture_regular = preservation._capture_regular  # noqa: SLF001, RUF100 - context edge

    monkeypatch.setattr(preservation.os, "open", lambda *_args, **_kwargs: -1)
    monkeypatch.setattr(preservation.os, "fstat", lambda _descriptor: directory_metadata)
    monkeypatch.setattr(preservation.os, "close", closed.append)
    with bound_source(source) as (descriptor, _identity):
        assert descriptor == -1
    assert closed == []

    monkeypatch.setattr(preservation.os, "fstat", lambda _descriptor: file_metadata)
    monkeypatch.setattr(preservation.os, "read", lambda _descriptor, _size: b"x")
    monkeypatch.setattr(preservation.os, "stat", lambda *_args, **_kwargs: file_metadata)
    with capture_regular(
        parent_descriptor=-1,
        name="listed.bin",
        archive_name="listed.bin",
        visible=file_metadata,
    ) as (info, payload):
        assert info.size == 1
        assert payload.read() == b"x"
    assert closed == []
