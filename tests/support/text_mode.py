"""Observe host-neutral text writes under the Windows newline convention."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

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
