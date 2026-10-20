"""Simulate the Windows host conventions that local POSIX tests cannot otherwise observe."""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING

import ethos.adapters.repo.content.observation as observation

if TYPE_CHECKING:
    import pytest


def translate_like_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    """Write implicit text newlines as CRLF, as `Path.write_text` does on Windows."""
    write_text = Path.write_text

    def translated(
        path: Path,
        data: str,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> int:
        if newline is None:
            data, newline = data.replace("\n", "\r\n"), ""
        return write_text(path, data, encoding=encoding, errors=errors, newline=newline)

    monkeypatch.setattr(Path, "write_text", translated)


def without_descriptor_chain(monkeypatch: pytest.MonkeyPatch) -> None:
    """Show the content owner the `os` surface of a host without no-follow descriptor opens."""
    absent = {"O_DIRECTORY", "O_NOFOLLOW", "O_NONBLOCK"}
    host = SimpleNamespace(**{name: getattr(os, name) for name in dir(os) if name not in absent})
    monkeypatch.setattr(observation, "os", host)
    monkeypatch.setattr(observation, "DESCRIPTOR_CHAIN_READS", False)


def with_creation_time_path_ctime(monkeypatch: pytest.MonkeyPatch) -> None:
    """Report a path stat's st_ctime as the creation time, as Python 3.12 does on Windows."""
    lstat = Path.lstat

    def creation_ctime(path: Path) -> SimpleNamespace:
        observed = lstat(path)
        fields = {name: getattr(observed, name) for name in dir(observed) if name.startswith("st_")}
        return SimpleNamespace(**{**fields, "st_ctime": 0.0, "st_ctime_ns": 0})

    monkeypatch.setattr(Path, "lstat", creation_ctime)
