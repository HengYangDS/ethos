"""Native open-file observation, its uninspectable boundary and its bounded rescan."""

from __future__ import annotations

import subprocess
import sys
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.open_files as open_files
from ethos.adapters.process import ProcessExecutionError
from ethos.contracts.retirement import UninspectableProcess

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

_COMMAND = ("-nP", "-F0pcuftDin")
_VALID = b"p12\0cbash\0u1000\0\nfcwd\0tDIR\0D0x10\0i31\0\nf3\0tREG\0D0x20\0i31\0\n"
_HELD = frozenset({(16, 31), (32, 31)})
# lsof 4.99.4 in the pinned supply image, run as its unprivileged user, records the root
# PID 1 only by the /proc entries it was denied; captured verbatim.
_UNINSPECTABLE = (
    b"p1\0csh\0u0\0\n"
    b"fcwd\0tunknown\0n/proc/1/cwd (readlink: Permission denied)\0\n"
    b"frtd\0tunknown\0n/proc/1/root (readlink: Permission denied)\0\n"
    b"ftxt\0tunknown\0n/proc/1/exe (readlink: Permission denied)\0\n"
    b"fNOFD\0n/proc/1/fd (opendir: Permission denied)\0\n"
)
# lsof 4.95.0, which Ubuntu 24.04 and its hosted runners ship, also lists each thread of a
# process as a set of its own; GitHub ETHOS CI 39152217492 at 76e2161ad failed on such a
# thread's denied cwd. Two threads of an uninspectable root process, captured verbatim.
_THREADED_UNINSPECTABLE = (
    b"p2616\0cpython3\0u0\0\n"
    b"fcwd\0tunknown\0n/proc/2616/cwd (readlink: Permission denied)\0\n"
    b"frtd\0tunknown\0n/proc/2616/root (readlink: Permission denied)\0\n"
    b"ftxt\0tunknown\0n/proc/2616/exe (readlink: Permission denied)\0\n"
    b"fNOFD\0n/proc/2616/fd (opendir: Permission denied)\0\n"
    b"p2616\0cpython3\0u0\0\n"
    b"fcwd\0tunknown\0n/proc/2616/task/2619/cwd (readlink: Permission denied)\0\n"
    b"frtd\0tunknown\0n/proc/2616/task/2619/root (readlink: Permission denied)\0\n"
    b"ftxt\0tunknown\0n/proc/2616/task/2619/exe (readlink: Permission denied)\0\n"
    b"fNOFD\0n/proc/2616/task/2619/fd (opendir: Permission denied)\0\n"
    b"p2616\0cpython3\0u0\0\n"
    b"fcwd\0tunknown\0n/proc/2616/task/2620/cwd (readlink: Permission denied)\0\n"
    b"frtd\0tunknown\0n/proc/2616/task/2620/root (readlink: Permission denied)\0\n"
    b"ftxt\0tunknown\0n/proc/2616/task/2620/exe (readlink: Permission denied)\0\n"
    b"fNOFD\0n/proc/2616/task/2620/fd (opendir: Permission denied)\0\n"
)
# A process of the invoking user with another group or extra capabilities keeps its
# descriptor directory readable but denies every link in it: lsof 4.95 on Ubuntu 24.04
# lists each descriptor with its denied readlink instead of NOFD, as GitHub ETHOS CI
# 39161201596 recorded for /proc/1305 at 46cf69663. lsof 4.99.4 in the pinned supply image
# prints the same records. Both captured verbatim.
_DESCRIPTORS_UNINSPECTABLE = {
    "4.95": (
        b"p647930\0cpython3\0u65534\0\n"
        b"fcwd\0tunknown\0n/proc/647930/cwd (readlink: Permission denied)\0\n"
        b"frtd\0tunknown\0n/proc/647930/root (readlink: Permission denied)\0\n"
        b"ftxt\0tunknown\0n/proc/647930/exe (readlink: Permission denied)\0\n"
        b"f0\0tunknown\0n/proc/647930/fd/0 (readlink: Permission denied)\0\n"
        b"f1\0tunknown\0n/proc/647930/fd/1 (readlink: Permission denied)\0\n"
        b"f2\0tunknown\0n/proc/647930/fd/2 (readlink: Permission denied)\0\n"
        b"f3\0tunknown\0n/proc/647930/fd/3 (readlink: Permission denied)\0\n"
        b"f10\0tunknown\0n/proc/647930/fd/10 (readlink: Permission denied)\0\n"
        b"f11\0tunknown\0n/proc/647930/fd/11 (readlink: Permission denied)\0\n"
        b"f12\0tunknown\0n/proc/647930/fd/12 (readlink: Permission denied)\0\n"
    ),
    "4.99.4": (
        b"p644879\0cpython3\0u65534\0\n"
        b"fcwd\0tunknown\0n/proc/644879/cwd (readlink: Permission denied)\0\n"
        b"frtd\0tunknown\0n/proc/644879/root (readlink: Permission denied)\0\n"
        b"ftxt\0tunknown\0n/proc/644879/exe (readlink: Permission denied)\0\n"
        b"f0\0tunknown\0n/proc/644879/fd/0 (readlink: Permission denied)\0\n"
        b"f1\0tunknown\0n/proc/644879/fd/1 (readlink: Permission denied)\0\n"
        b"f2\0tunknown\0n/proc/644879/fd/2 (readlink: Permission denied)\0\n"
        b"f3\0tunknown\0n/proc/644879/fd/3 (readlink: Permission denied)\0\n"
    ),
}
# GitLab verify 54883 at f3d9f85e3: lsof read this process's descriptor directory, then the
# process changed credentials or turned non-dumpable before one link was read. The record
# is verbatim; the process frame carries the fields the current command requests.
_GITLAB_54883 = b"f1\0tunknown\0n/proc/392537/fd/1 (readlink: Permission denied)\0\n"
_DENIED_DESCRIPTOR = b"p392537\0csh\0u65534\0\nfcwd\0tDIR\0D0x10\0i31\0\n" + _GITLAB_54883
# Vanished records captured verbatim from the same image while processes and descriptors
# exited mid-scan; every one of the 728 anomalous scans captured there holds one.
_CAPTURED_VANISHED = {
    "descriptor-link": b"f4\0tunknown\0n/proc/15/fd/4 (readlink: No such file or directory)",
    "entry-link": b"ftxt\0tunknown\0n/proc/5365/exe (readlink: No such file or directory)",
    "descriptor-directory": b"fNOFD\0n/proc/7760/fd (opendir: No such file or directory)",
    "target-stat": b"f4\0tunknown\0n/etc/passwd (stat: No such file or directory)",
    "target-lstat": b"f4\0tunknown\0n/etc/passwd lstat: No such file or directory) "
    b"(stat: No such file or directory)",
}


def _file_reference_payloads() -> dict[str, bytes]:
    """Declare each observed file-reference counterexample once."""
    payload = _VALID + b"f4\0tIPv4\0\n"
    absent = b"f5\0nsocket: FD unavailable\0\n"
    # Linux lsof records a process or descriptor that exits during its scan by the failed
    # /proc read, with no type, device or inode.
    vanished = (
        b"p77\0csleep\0u1000\0\n"
        b"fcwd\0tunknown\0n/proc/77/cwd (readlink: No such file or directory)\0\n"
        b"frtd\0n/proc/77/root (readlink: No such file or directory)\0\n"
        b"ftxt\0n/proc/77/exe (readlink: No such file or directory)\0\n"
        b"fNOFD\0n/proc/77/fd (opendir: No such file or directory)\0\n"
    )
    fd_vanished = b"f9\0tunknown\0n/proc/12/fd/9 (readlink: No such file or directory)\0\n"
    gone = b"No such file or directory)\0\n"
    unix = b"f6\0tunix\0i50690625\0ntype=STREAM\0\n"
    # lsof 4.95 and 4.99.4 print a bound netlink socket by its socket inode alone; captured
    # verbatim from Ubuntu 24.04 and from the pinned supply image.
    netlink = {
        "4.95": b"f14\0tnetlink\0i2444395\0nROUTE\0\nf15\0tnetlink\0i2444396\0nKOBJECT_UEVENT\0\n",
        "4.99.4": b"f11\0tnetlink\0i2434816\0nROUTE\0\n"
        b"f12\0tnetlink\0i2434817\0nKOBJECT_UEVENT\0\n",
    }
    # A thread lsof cannot inspect inside a process it can is a permission failure, not an
    # uninspectable process: the captured thread sets follow a readable main set.
    threads = _THREADED_UNINSPECTABLE[_THREADED_UNINSPECTABLE.index(b"p2616", 1) :]
    return {
        "unix-inode": payload + unix,
        **{f"linux-netlink-lsof-{version}": payload + netlink[version] for version in netlink},
        "linux-denied-thread-of-inspected-process": payload
        + b"p2616\0cpython3\0u0\0\n"
        + payload.removeprefix(b"p12\0cbash\0u1000\0\n")
        + threads,
        "unix-empty-inode": payload + unix.replace(b"i50690625", b"i"),
        "unix-negative-inode": payload + unix.replace(b"i50690625", b"i-1"),
        "unix-duplicate-inode": payload + unix.replace(b"i50690625", b"i1\0i2"),
        "unix-orphan": unix + payload,
        "regular-inode-only": payload + unix.replace(b"tunix", b"tREG"),
        "directory-inode-only": payload + unix.replace(b"tunix", b"tDIR"),
        "unknown-inode-only": payload + unix.replace(b"tunix", b"tunknown"),
        "fd-gone": payload + absent,
        "process-gone": payload + b"f5\0nvnode: process unavailable\0\n",
        "permission": payload + b"f5\0nsocket: Operation not permitted\0\n",
        "unclassified": payload + b"f5\0\n",
        "unknown-source": payload + absent.replace(b"socket:", b"unknown:"),
        "invalid-gone-fd": payload + absent.replace(b"f5", b"fNOFD"),
        "orphan-gone": absent + payload,
        "non-darwin-gone": payload + absent,
        "linux-process-gone": payload + vanished,
        "linux-fd-gone": payload + fd_vanished,
        "linux-task-gone": payload
        + b"fNOFD\0n/proc/77/task/78/fd (opendir: No such file or directory)\0\n",
        "linux-uninspectable": payload + _UNINSPECTABLE,
        "linux-uninspectable-on-darwin": payload + _UNINSPECTABLE,
        "linux-threaded-uninspectable": payload + _THREADED_UNINSPECTABLE,
        **{
            f"linux-descriptors-uninspectable-lsof-{version}": payload + records
            for version, records in _DESCRIPTORS_UNINSPECTABLE.items()
        },
        "linux-mislabeled-descriptor-denial": payload
        + _DESCRIPTORS_UNINSPECTABLE["4.95"].replace(b"f10\0", b"f9\0"),
        "linux-partial-denial": payload + _DENIED_DESCRIPTOR,
        "linux-other-errno": payload
        + _UNINSPECTABLE.replace(b"Permission denied", b"Input/output error"),
        "linux-readable-holder": payload + _UNINSPECTABLE + b"f3\0tREG\0D0x20\0i31\0\n",
        "linux-mislabeled-denial": payload + _UNINSPECTABLE.replace(b"frtd", b"fcwd"),
        "linux-foreign-path": payload + vanished.replace(b"/proc/77/fd ", b"/tmp/77/fd "),
        "linux-mislabeled": payload + fd_vanished.replace(b"f9", b"f8"),
        "linux-gone-on-darwin": payload + vanished,
        # A descriptor closed after its link was read: lsof records the target it read and
        # the failed stat of the link, with lstat's note printed without its opening paren.
        "linux-stat-gone": payload + b"f7\0tunknown\0n/etc/hostname (stat: " + gone,
        "linux-lstat-gone": payload
        + b"f7\0tunknown\0n/etc/hostname lstat: No such file or directory) (stat: "
        + gone,
        "linux-pipe-stat-gone": payload + b"f8\0tunknown\0npipe (stat: " + gone,
        "linux-cwd-stat-gone": payload + b"fcwd\0tunknown\0n/opt/ethos-supply (stat: " + gone,
        "linux-stat-denied": payload
        + b"f7\0tunknown\0n/etc/hostname (stat: Permission denied)\0\n",
        "linux-stat-typed": payload + b"f7\0tREG\0n/etc/hostname (stat: " + gone,
        "linux-stat-mem": payload + b"fmem\0tunknown\0n/usr/lib/libc.so (stat: " + gone,
        "named-live-file": payload.replace(b"i31\0", b"i31\0nsocket: FD unavailable\0", 1),
        "empty": b"",
        "truncated": payload[:-2],
        "duplicate": payload.replace(b"i31\0", b"i31\0i32\0", 1),
        "pid": payload.replace(b"p12", b"pnot-a-pid"),
        "process-fields": payload.replace(b"\0u1000", b"", 1),
        "uid": payload.replace(b"u1000", b"uroot", 1),
        "nofd": payload + b"fNOFD\0\n",
        "type": payload.replace(b"tDIR\0", b"tunknown\0"),
        "inode": payload.replace(b"i31\0", b"", 1),
        "field": payload.replace(b"fcwd\0", b"fcwd\0gunexpected\0"),
        "empty-fd": payload.replace(b"fcwd\0", b"f\0"),
        "empty-type": payload.replace(b"tDIR\0", b"t\0"),
        "orphan": payload.removeprefix(b"p12\0cbash\0u1000\0\n"),
        "negative-inode": payload.replace(b"i31\0", b"i-1\0", 1),
        **dict.fromkeys(("valid", "status", "fatal", "stderr", "timeout", "missing"), payload),
        "no-match": b"",
        "no-identity": b"p12\0cbash\0u1000\0\nf4\0tIPv4\0\n",
        "linux-only-uninspectable": _UNINSPECTABLE,
    }


_FILE_REFERENCE_PAYLOADS = _file_reference_payloads()
_OBSERVED = {
    "valid",
    "fd-gone",
    "process-gone",
    "linux-process-gone",
    "linux-fd-gone",
    "linux-task-gone",
    "linux-uninspectable",
    "linux-threaded-uninspectable",
    "linux-descriptors-uninspectable-lsof-4.95",
    "linux-descriptors-uninspectable-lsof-4.99.4",
    "linux-stat-gone",
    "linux-lstat-gone",
    "linux-pipe-stat-gone",
    "linux-cwd-stat-gone",
    "named-live-file",
    "unix-inode",
    "linux-netlink-lsof-4.95",
    "linux-netlink-lsof-4.99.4",
}
# Each uninspectable process is reported once, however many of its threads lsof lists.
_REPORTED = {
    "linux-uninspectable": (UninspectableProcess(pid=1, uid=0, command="sh"),),
    "linux-threaded-uninspectable": (UninspectableProcess(pid=2616, uid=0, command="python3"),),
    "linux-descriptors-uninspectable-lsof-4.95": (
        UninspectableProcess(pid=647930, uid=65534, command="python3"),
    ),
    "linux-descriptors-uninspectable-lsof-4.99.4": (
        UninspectableProcess(pid=644879, uid=65534, command="python3"),
    ),
}


@pytest.mark.parametrize("fault", _FILE_REFERENCE_PAYLOADS)
def test_native_file_references_are_bounded_and_incomplete_observation_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    executable = tmp_path / "lsof"
    executable.write_text("native observer\n")
    observed = []
    monkeypatch.setenv("PATH", str(tmp_path / "ambient"))

    def resolve(name: str, *, path: str) -> str | None:
        observed.append((name, path))
        return None if fault == "missing" else str(executable)

    monkeypatch.setattr(open_files.shutil, "which", resolve)
    linux = fault == "non-darwin-gone" or (
        fault.startswith("linux-") and not fault.endswith("-on-darwin")
    )
    monkeypatch.setattr(sys, "platform", "linux" if linux else "darwin")
    payload = _FILE_REFERENCE_PAYLOADS[fault]

    def capture(root: Path, command: tuple[str, ...], **kwargs: object) -> object:
        assert root == tmp_path
        assert command == (str(executable), *_COMMAND)
        timeout = kwargs["timeout"]
        assert isinstance(timeout, float)
        assert 0 < timeout <= 30
        assert kwargs["text"] is False
        assert kwargs["env"] == {"LC_ALL": "C"}
        if fault == "timeout":
            raise subprocess.TimeoutExpired(command, timeout)
        status = 2 if fault == "fatal" else 1 if fault in {"status", "no-match"} else 0
        stderr = b"permission denied" if fault == "stderr" else b""
        return subprocess.CompletedProcess(command, status, payload, stderr)

    monkeypatch.setattr(open_files, "run_command", capture)
    observe = open_files.observe_open_files
    if fault in _OBSERVED:
        observation = observe(tmp_path, tree=tmp_path, index=executable)
        assert observation.identities == _HELD
        uninspectable = observation.boundary.uninspectable_processes
        assert uninspectable == (_REPORTED.get(fault, ()) if linux else None)
    else:
        with pytest.raises(ProcessExecutionError) as error:
            observe(tmp_path, tree=tmp_path, index=executable)
        assert error.value.code == "native_process_observer_unavailable"
        assert error.value.reason == "file_references_unavailable"
        assert error.value.cwd == str(tmp_path)
        if fault == "empty-type":
            assert repr(b"fcwd\0t\0D0x10\0i31") in str(error.value.cause)
    assert (observed[0][0], str(tmp_path / "ambient") in observed[0][1]) == ("lsof", False)


def _scanner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, payloads: list[bytes]
) -> tuple[list[tuple[str, ...]], Callable[[], open_files.OpenFileObservation]]:
    executable = tmp_path / "lsof"
    executable.write_text("native observer\n")
    monkeypatch.setattr(open_files.shutil, "which", lambda *_args, **_options: str(executable))
    monkeypatch.setattr(sys, "platform", "linux")
    scans: list[tuple[str, ...]] = []

    def capture(_root: Path, command: tuple[str, ...], **_options: object) -> object:
        scans.append(command)
        return subprocess.CompletedProcess(command, 0, payloads[len(scans) - 1], b"")

    monkeypatch.setattr(open_files, "run_command", capture)

    def observe() -> open_files.OpenFileObservation:
        return open_files.observe_open_files(tmp_path, tree=tmp_path, index=executable)

    return scans, observe


def test_a_record_left_unreadable_mid_scan_is_observed_again(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The settled second scan supplies the complete identities."""
    scans, observe = _scanner(tmp_path, monkeypatch, [_VALID + _DENIED_DESCRIPTOR, _VALID])
    assert observe().identities == _HELD
    assert len(scans) == 2


def test_a_record_that_stays_unreadable_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Three unreadable scans leave the observation incomplete."""
    scans, observe = _scanner(tmp_path, monkeypatch, [_VALID + _DENIED_DESCRIPTOR] * 3)
    with pytest.raises(ProcessExecutionError) as error:
        observe()
    assert len(scans) == 3
    assert error.value.code == "native_process_observer_unavailable"
    assert "readlink: Permission denied" in str(error.value.cause)


@pytest.mark.parametrize("record", _CAPTURED_VANISHED.values(), ids=_CAPTURED_VANISHED)
def test_vanished_records_captured_from_the_pinned_image_are_admitted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, record: bytes
) -> None:
    """Each real vanished record leaves the observation complete without another scan."""
    payload = _VALID + b"p15\0cpython3\0u65534\0\n" + record + b"\0\n"
    scans, observe = _scanner(tmp_path, monkeypatch, [payload])
    observation = observe()
    assert observation.identities == _HELD
    assert observation.boundary.uninspectable_processes == ()
    assert len(scans) == 1


def test_scans_share_one_observer_timeout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A rescan never extends the observation past the observer's one timeout."""
    clock = iter((0.0, 0.0, 31.0))
    monkeypatch.setattr(open_files, "monotonic", lambda: next(clock))
    scans, observe = _scanner(tmp_path, monkeypatch, [_VALID + _DENIED_DESCRIPTOR] * 3)
    with pytest.raises(ProcessExecutionError) as error:
        observe()
    assert len(scans) == 1
    assert "file_observation_deadline_exhausted" in str(error.value.cause)


def test_a_malformed_scan_is_not_taken_again(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only an unreadable record earns another scan."""
    duplicate = _VALID.replace(b"i31\0", b"i31\0i32\0", 1)
    scans, observe = _scanner(tmp_path, monkeypatch, [duplicate] * 3)
    with pytest.raises(ProcessExecutionError) as error:
        observe()
    assert len(scans) == 1
    assert "file_observation_duplicate_field" in str(error.value.cause)
