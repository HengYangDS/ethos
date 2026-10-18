"""Observe the files that inspectable processes hold open, through the native lsof."""

from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
import sys
from dataclasses import dataclass
from time import monotonic
from typing import TYPE_CHECKING

from ethos.adapters.process import NATIVE_PROCESS_OBSERVER_UNAVAILABLE
from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.process import run_command
from ethos.contracts.retirement import OpenFileBoundary
from ethos.contracts.retirement import UninspectableProcess

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class OpenFileObservation:
    """Identities that inspected processes hold, and the boundary of the observation."""

    identities: frozenset[tuple[int, int]]
    boundary: OpenFileBoundary


def _file_observation_failure(reason: str) -> None:
    raise ValueError(reason)


# lsof records a process or descriptor that exits during its scan without a type, device or
# inode. Only that absence is admitted; any other unreadable entry leaves the observation
# incomplete. Darwin names the vanished object. Linux names the /proc entry it failed to
# read or, when the link read but its stat then failed, the target it read; lsof prints the
# note of a failed lstat before that stat note without its opening parenthesis.
_DARWIN_VANISHED_REFERENCE = re.compile(
    rb"(?:kqueue|pipe|semaphore|POSIX shared memory|vnode|socket): "
    rb"(?:FD unavailable|process unavailable)"
)
# Linux lsof lists each thread it observes as a set of its own, naming that task's entries.
_LINUX_PROC_ENTRY = rb"/proc/[0-9]+(?:/task/[0-9]+)?/"
_LINUX_VANISHED_REFERENCE = re.compile(
    _LINUX_PROC_ENTRY + rb"(?:(?P<entry>cwd|root|exe|fd)|fd/(?P<descriptor>[0-9]+)) "
    rb"\((?:readlink|opendir): No such file or directory\)"
)
_LINUX_VANISHED_TARGET = re.compile(
    rb".+ (?:lstat: No such file or directory\) )?\(stat: No such file or directory\)", re.DOTALL
)
# A process the invoking user may not inspect denies each /proc entry lsof reads first, so
# lsof records only those denials, for the process and each thread it lists. Darwin's lsof
# omits such a process without a record.
_LINUX_DENIED_ENTRY = re.compile(
    _LINUX_PROC_ENTRY + rb"(?:(?P<entry>cwd|root|exe) \(readlink|(?P<directory>fd) \(opendir): "
    rb"Permission denied\)"
)
_LINUX_ENTRY_LABELS = {b"cwd": b"cwd", b"root": b"rtd", b"exe": b"txt", b"fd": b"NOFD"}
# lsof prints a socket it finds in the kernel's socket tables by its socket inode alone; no
# such socket is a file a worktree holds.
_INODE_ONLY_SOCKETS = frozenset({b"unix", b"netlink"})
_UNREADABLE = "file_observation_unreadable"
# A process that changes credentials or turns non-dumpable after lsof opened its descriptor
# directory leaves one record unreadable. A fresh scan observes it settled, so a scan is
# taken again up to this bound within one timeout; a record that stays unreadable fails
# closed.
_FILE_OBSERVATION_SCANS = 3
_FILE_OBSERVATION_SECONDS = 30.0


def _entry_record(fields: dict[bytes, bytes]) -> bytes:
    """Return the name of a Linux record that carries only a /proc entry note, else empty."""
    if (
        not sys.platform.startswith("linux")
        or set(fields) - {b"f", b"t", b"n"}
        or fields.get(b"t", b"unknown") != b"unknown"
    ):
        return b""
    return fields.get(b"n", b"")


def _vanished_reference(fields: dict[bytes, bytes]) -> bool:
    if sys.platform == "darwin":
        return (
            set(fields) == {b"f", b"n"}
            and fields[b"f"].isdigit()
            and _DARWIN_VANISHED_REFERENCE.fullmatch(fields[b"n"]) is not None
        )
    descriptor, name = fields.get(b"f", b""), _entry_record(fields)
    if match := _LINUX_VANISHED_REFERENCE.fullmatch(name):
        return descriptor == (match["descriptor"] or _LINUX_ENTRY_LABELS[match["entry"]])
    return (descriptor.isdigit() or descriptor in {b"cwd", b"rtd", b"txt"}) and bool(
        _LINUX_VANISHED_TARGET.fullmatch(name)
    )


def _denied_entry(fields: dict[bytes, bytes]) -> bool:
    match = _LINUX_DENIED_ENTRY.fullmatch(_entry_record(fields))
    return (
        match is not None
        and fields.get(b"f") == _LINUX_ENTRY_LABELS[match["entry"] or match["directory"]]
    )


def _record_identity(frame: bytes, fields: dict[bytes, bytes]) -> set[tuple[int, int]]:
    fields = {key: value for key, value in fields.items() if key != b"n"}
    if (
        set(fields) not in ({b"f", b"t"}, {b"f", b"t", b"D", b"i"}, {b"f", b"t", b"i"})
        or not all(fields.values())
        or fields.get(b"f", b"NOFD") == b"NOFD"
        or fields.get(b"t", b"unknown") == b"unknown"
        or (b"i" in fields and not fields[b"i"].isdigit())
        or (b"i" in fields and b"D" not in fields and fields[b"t"] not in _INODE_ONLY_SOCKETS)
        or (fields[b"t"] in {b"REG", b"DIR"} and b"i" not in fields)
    ):
        _file_observation_failure(f"{_UNREADABLE}:{frame[:256]!r}")
    return {(int(fields[b"D"], 16), int(fields[b"i"]))} if b"D" in fields else set()


def _process_records(
    payload: bytes,
) -> list[tuple[dict[bytes, bytes], list[tuple[bytes, dict[bytes, bytes]]]]]:
    """Group lsof frames by process, its thread sets included, dropping vanished records."""
    if not payload.endswith(b"\0\n"):
        _file_observation_failure("file_observation_incomplete")
    processes: dict[bytes, tuple[dict[bytes, bytes], list[tuple[bytes, dict[bytes, bytes]]]]] = {}
    records: list[tuple[bytes, dict[bytes, bytes]]] | None = None
    for frame in payload[:-2].split(b"\0\n"):
        fields = {item[:1]: item[1:] for item in frame.split(b"\0")}
        if len(fields) != frame.count(b"\0") + 1:
            _file_observation_failure("file_observation_duplicate_field")
        if b"p" in fields:
            if (
                set(fields) != {b"p", b"c", b"u"}
                or not fields[b"p"].isdigit()
                or not fields[b"u"].isdigit()
            ):
                _file_observation_failure("file_observation_process_invalid")
            records = processes.setdefault(fields[b"p"], (fields, []))[1]
        elif records is None:
            _file_observation_failure(f"{_UNREADABLE}:{frame[:256]!r}")
        elif not _vanished_reference(fields):
            records.append((frame, fields))
    return list(processes.values())


def _file_identities(
    payload: bytes,
) -> tuple[frozenset[tuple[int, int]], tuple[UninspectableProcess, ...]]:
    identities: set[tuple[int, int]] = set()
    uninspectable: list[UninspectableProcess] = []
    for process, records in _process_records(payload):
        if records and all(_denied_entry(fields) for _frame, fields in records):
            uninspectable.append(
                UninspectableProcess(
                    pid=int(process[b"p"]),
                    uid=int(process[b"u"]),
                    command=process[b"c"].decode(errors="replace"),
                )
            )
            continue
        for frame, fields in records:
            identities.update(_record_identity(frame, fields))
    if not identities:
        _file_observation_failure("file_observation_empty")
    return frozenset(identities), tuple(uninspectable)


def _scan(root: Path, command: tuple[str, ...]) -> OpenFileObservation:
    """Take the native scan, and again while an unreadable record leaves it incomplete."""
    scans = _FILE_OBSERVATION_SCANS
    deadline = monotonic() + _FILE_OBSERVATION_SECONDS
    while True:
        scans -= 1
        remaining = deadline - monotonic()
        if remaining <= 0:
            _file_observation_failure("file_observation_deadline_exhausted")
        # The C locale fixes lsof's error text, which identifies a vanished /proc entry.
        result = run_command(
            root,
            command,
            text=False,
            timeout=remaining,
            env={"LC_ALL": "C"},
            remove_env_prefixes=("GIT_",),
        )
        if result.returncode != 0 or result.stderr:
            _file_observation_failure(
                result.stderr.decode(errors="replace") or "file_observation_incomplete"
            )
        if not result.stdout:
            _file_observation_failure("file_observation_empty_success")
        try:
            identities, uninspectable = _file_identities(result.stdout)
        except ValueError as error:
            if not scans or not str(error).startswith(f"{_UNREADABLE}:"):
                raise
            continue
        linux = sys.platform.startswith("linux")
        return OpenFileObservation(
            identities,
            OpenFileBoundary(uninspectable_processes=uninspectable if linux else None),
        )


def observe_open_files(root: Path, *, tree: Path, index: Path) -> OpenFileObservation:
    """Observe complete native identities; the reviewed manifest selects retirement consumers."""
    command: tuple[str, ...] = ()
    try:
        executable = shutil.which("lsof", path=os.defpath + os.pathsep + "/usr/sbin")
        if os.name != "posix" or executable is None:
            _file_observation_failure("native_file_observer_missing")
        try:
            tree_status = tree.lstat()
        except FileNotFoundError:
            tree_status = None
        if (
            not tree.is_absolute()
            or not index.is_absolute()
            or index.is_symlink()
            or (tree_status is not None and not stat.S_ISDIR(tree_status.st_mode))
            or not index.is_file()
        ):
            _file_observation_failure("file_observation_scope_unavailable")
        command = (str(executable), "-nP", "-F0pcuftDin")
        return _scan(root, command)
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        raise ProcessExecutionError(
            NATIVE_PROCESS_OBSERVER_UNAVAILABLE,
            reason="file_references_unavailable",
            command=command,
            cwd=root.as_posix(),
            cause=str(error),
        ) from error
