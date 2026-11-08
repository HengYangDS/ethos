"""Read every digest that a kept store record names, through the carriers that encode it.

The scan over-approximates: any 64-hex run is a digest, and a mistaken match only keeps a record.
"""

from __future__ import annotations

import base64
import binascii
import io
import re
import tarfile
import zlib
from zipfile import BadZipFile
from zipfile import ZipFile

_TOKEN = re.compile(rb"[0-9a-f]{64}")
_BASE64 = re.compile(rb"[A-Za-z0-9+/]{44,}={0,2}")
_UNDECODABLE = "record_retirement_carrier_undecodable"


def carrier_tokens(data: bytes, *, depth: int, budget: int, name: str) -> frozenset[str]:
    """Return every digest in a carrier and in the zip, gzip, tar and base64 content it holds.

    Each decoding is one level. An archive below the last level, a damaged archive or more decoded
    bytes than the budget leave the carrier unread, and the caller must refuse rather than guess.
    """
    tokens: set[str] = set()
    pending = [(data, 0)]
    spent = 0
    while pending:
        chunk, level = pending.pop()
        spent += len(chunk)
        if spent > budget:
            _undecodable(name)
        tokens.update(match.decode() for match in _TOKEN.findall(chunk))
        members = _archive_members(chunk, budget - spent, name)
        if members is not None:
            if level >= depth:
                _undecodable(name)
            pending.extend((member, level + 1) for member in members)
        elif level < depth:
            pending.extend((decoded, level + 1) for decoded in _base64_runs(chunk))
    return frozenset(tokens)


def _archive_members(chunk: bytes, room: int, name: str) -> list[bytes] | None:
    """Return a zip, gzip or tar carrier's members, or None for any other content."""
    try:
        if chunk[:4] in {b"PK\x03\x04", b"PK\x05\x06"}:
            with ZipFile(io.BytesIO(chunk)) as archive:
                entries = [entry for entry in archive.infolist() if not entry.is_dir()]
                if sum(entry.file_size for entry in entries) > room:
                    _undecodable(name)
                return [archive.read(entry) for entry in entries]
        if chunk[:2] == b"\x1f\x8b":
            inflater = zlib.decompressobj(16 + zlib.MAX_WBITS)
            inflated = inflater.decompress(chunk, room + 1)
            if len(inflated) > room or not inflater.eof:
                _undecodable(name)
            return [inflated]
        if len(chunk) > 262 and chunk[257:262] == b"ustar":
            with tarfile.open(fileobj=io.BytesIO(chunk)) as bundle:
                files = [member for member in bundle.getmembers() if member.isfile()]
                if sum(member.size for member in files) > room:
                    _undecodable(name)
                streams = [bundle.extractfile(member) for member in files]
                return [stream.read() for stream in streams if stream is not None]
    except (
        BadZipFile,
        EOFError,
        NotImplementedError,
        OSError,
        tarfile.TarError,
        zlib.error,
    ) as error:
        message = f"{_UNDECODABLE}:{name}"
        raise ValueError(message) from error
    return None


def _base64_runs(chunk: bytes) -> list[bytes]:
    decoded: list[bytes] = []
    for match in _BASE64.finditer(chunk):
        run = match.group()
        try:
            decoded.append(base64.b64decode(run + b"=" * (-len(run) % 4)))
        except (binascii.Error, ValueError):
            continue
    return decoded


def _undecodable(name: str) -> None:
    message = f"{_UNDECODABLE}:{name}"
    raise ValueError(message)
