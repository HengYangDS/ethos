"""Digests that keep store records are read through every carrier that encodes them."""

from __future__ import annotations

import base64
import gzip
import io
import tarfile

import pytest

from ethos.adapters.store.retention.roots import carrier_tokens
from tests.support.retention_store import archive

_TOKEN = "b" * 64


def _tar(name: str, content: bytes) -> bytes:
    payload = io.BytesIO()
    with tarfile.open(fileobj=payload, mode="w") as bundle:
        member = tarfile.TarInfo(name)
        member.size = len(content)
        bundle.addfile(member, io.BytesIO(content))
    return payload.getvalue()


@pytest.mark.parametrize(
    "carrier",
    [
        _TOKEN.encode(),
        archive({"note.txt": _TOKEN.encode()}),
        gzip.compress(_TOKEN.encode()),
        _tar("note.txt", _TOKEN.encode()),
        b'{"blob": "' + base64.b64encode(b"named " + _TOKEN.encode()) + b'"}',
        archive({"inner.zip": archive({"deep.gz": gzip.compress(_TOKEN.encode())})}),
    ],
    ids=["plain", "zip", "gzip", "tar", "base64", "nested"],
)
def test_a_digest_is_read_inside_its_carrier(carrier: bytes) -> None:
    """Plain, zip, gzip, tar, base64 and nested content all name the same digest."""
    assert _TOKEN in carrier_tokens(carrier, depth=6, budget=1 << 20, name="carrier")


def test_a_carrier_nested_beyond_the_depth_refuses() -> None:
    """An archive deeper than the declared depth cannot be read, so the preview refuses."""
    nested = archive({"a.zip": archive({"b.zip": archive({"note.txt": _TOKEN.encode()})})})

    with pytest.raises(ValueError, match="record_retirement_carrier_undecodable:carrier"):
        carrier_tokens(nested, depth=1, budget=1 << 20, name="carrier")


@pytest.mark.parametrize(
    "carrier",
    [b"PK\x03\x04 not an archive", b"\x1f\x8b not gzip", b"x" * 64],
    ids=["damaged-zip", "damaged-gzip", "over-budget"],
)
def test_a_damaged_or_oversized_carrier_refuses(carrier: bytes) -> None:
    """A damaged archive or content beyond the byte budget is not read past."""
    with pytest.raises(ValueError, match="record_retirement_carrier_undecodable:carrier"):
        carrier_tokens(carrier, depth=6, budget=32, name="carrier")
