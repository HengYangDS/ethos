"""Observe one committed delivery and its unchanged live source members."""

from __future__ import annotations

import os
import posixpath
import stat
from dataclasses import dataclass
from dataclasses import field
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from ethos.adapters.repo.content.observation import read_link_target
from ethos.adapters.repo.content.observation import read_regular_bytes
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import git_files
from ethos.adapters.repo.git import run_git

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

MAX_MEMBER_BYTES = 64 * 1024 * 1024
MAX_OBSERVATION_BYTES = 128 * 1024 * 1024
MAX_SOURCE_ENTRIES = 20000
MAX_ALIAS_EXPANSIONS = 40


class SourceTargetUnavailableError(ValueError):
    """A resolved target has no member in the selected delivery."""


@dataclass(frozen=True, slots=True)
class SourceTree:
    """Share exact membership, bounded reads, aliases, and freshness across consumers."""

    root: Path
    head: str
    tree: str
    entries: Mapping[str, tuple[str, int]]
    candidate: bool = False
    observed: dict[str, bytes] = field(default_factory=dict)
    aliases: dict[str, str] = field(default_factory=dict)

    @classmethod
    def observe(cls, root: Path, *, candidate: bool = False) -> SourceTree:
        head = current_tracked_head(root)
        if not head:
            run_git(root, "rev-parse", "--git-dir", check=True)
            message = "source_head_missing"
            raise ValueError(message)
        if candidate:
            entries = {}
            for relative in git_files(
                root, "--cached", "--others", "--exclude-standard", check=True
            ):
                member = (root / relative).lstat()
                mode = "120000" if stat.S_ISLNK(member.st_mode) else "100644"
                entries[relative] = (mode, member.st_size)
            return cls(root.resolve(), head, "", entries, candidate=True)
        raw = run_git(root, "ls-tree", "-rlz", head, text=False, check=True).stdout
        entries = {}
        for record in raw.split(b"\0"):
            if not record:
                continue
            metadata, path = record.split(b"\t", 1)
            mode, kind, _oid, size = metadata.split()
            if kind == b"blob":
                entries[path.decode("utf-8")] = (mode.decode("ascii"), int(size))
        tree = current_tree(root, head)
        if not tree:
            message = "source_tree_missing"
            raise ValueError(message)
        return cls(root.resolve(), head, tree, entries)

    def _expected(self, relative: str, modes: frozenset[str]) -> bytes:
        metadata = self.entries.get(relative)
        if metadata is None or metadata[0] not in modes:
            message = f"source_member_unavailable:{relative}"
            raise ValueError(message)
        if metadata[1] > MAX_MEMBER_BYTES:
            message = f"source_member_size_exceeded:{relative}"
            raise ValueError(message)
        if relative not in self.observed:
            if (
                sum(map(len, self.observed.values())) + metadata[1] > MAX_OBSERVATION_BYTES
                or len(self.observed) >= MAX_SOURCE_ENTRIES
            ):
                message = "source_observation_size_exceeded"
                raise ValueError(message)
            self.observed[relative] = (
                self._live(relative, metadata[0])
                if self.candidate
                else run_git(
                    self.root, "show", f"{self.head}:{relative}", text=False, check=True
                ).stdout
            )
        return self.observed[relative]

    def _live(self, relative: str, mode: str) -> bytes:
        unsafe = f"source_member_link_or_type_forbidden:{relative}"
        unstable = f"source_member_changed:{relative}"
        if mode == "120000":
            return os.fsencode(
                read_link_target(self.root, relative, unsafe_gap=unsafe, unstable_gap=unstable)
            )
        return read_regular_bytes(
            self.root,
            relative,
            max_bytes=self.entries[relative][1],
            unsafe_gap=unsafe,
            unstable_gap=unstable,
            size_gap=f"source_member_size_exceeded:{relative}",
        )

    def read(self, relative: str) -> bytes:
        """Reuse exact Git bytes and refuse changed or unsafe live inputs."""
        expected = self._expected(relative, frozenset({"100644", "100755"}))
        actual = self._live(relative, "100644")
        if actual != expected:
            message = f"source_member_changed:{relative}"
            raise ValueError(message)
        return expected

    def _alias(self, relative: str) -> str:
        expected = self._expected(relative, frozenset({"120000"}))
        actual = self._live(relative, "120000")
        if actual != expected:
            message = f"source_member_changed:{relative}"
            raise ValueError(message)
        target = os.fsdecode(actual)
        self.aliases[relative] = target
        return target

    def resolve_target(self, relative: str) -> str:
        """Qualify native file and directory targets, including committed internal aliases."""
        visited: set[str] = set()
        for _ in range(MAX_ALIAS_EXPANSIONS):
            if relative in visited:
                break
            visited.add(relative)
            expanded = self._expand_alias(relative)
            if expanded is not None:
                relative = expanded
                continue
            if relative in self.entries:
                self.read(relative)
            else:
                self._directory_member(relative)
            return relative
        message = f"source_target_alias_cycle:{relative}"
        raise SourceTargetUnavailableError(message)

    def _expand_alias(self, relative: str) -> str | None:
        path = PurePosixPath(relative)
        if path.is_absolute() or ".." in path.parts or "\\" in relative or "\0" in relative:
            message = f"source_target_outside_root:{relative}"
            raise SourceTargetUnavailableError(message)
        for offset in range(1, len(path.parts) + 1):
            prefix = PurePosixPath(*path.parts[:offset]).as_posix()
            member = self.entries.get(prefix)
            if member is not None and member[0] == "120000":
                target = self._alias(prefix)
                if PurePosixPath(target).is_absolute() or "\\" in target or "\0" in target:
                    message = f"source_target_outside_root:{prefix}"
                    raise SourceTargetUnavailableError(message)
                return posixpath.normpath(
                    posixpath.join(posixpath.dirname(prefix), target, *path.parts[offset:])
                )
        return None

    def _directory_member(self, relative: str) -> None:
        """Witness the delivered directory without following a descendant alias."""
        prefix = "" if relative == "." else relative.rstrip("/") + "/"
        children = sorted(name for name in self.entries if name.startswith(prefix))
        if not children:
            message = f"source_target_not_delivered:{relative}"
            raise SourceTargetUnavailableError(message)
        member = children[0]
        if self.entries[member][0] == "120000":
            self._alias(member)
        else:
            self.read(member)

    def recheck(self) -> None:
        """Recheck the same selected identity and every observed source member."""
        if current_tracked_head(self.root) != self.head:
            message = "source_tree_changed"
            raise ValueError(message)
        if self.candidate and set(
            git_files(self.root, "--cached", "--others", "--exclude-standard", check=True)
        ) != set(self.entries):
            message = "source_candidate_membership_changed"
            raise ValueError(message)
        for relative in tuple(self.observed):
            if relative in self.aliases:
                self._alias(relative)
            else:
                self.read(relative)
