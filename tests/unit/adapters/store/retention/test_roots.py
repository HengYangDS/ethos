"""Digests that keep store records are read through every carrier that encodes them."""

from __future__ import annotations

import base64
import gzip
import io
import tarfile
from zipfile import ZIP_DEFLATED
from zipfile import ZipFile

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


def _deflated(name: str, content: bytes) -> bytes:
    payload = io.BytesIO()
    with ZipFile(payload, "w", compression=ZIP_DEFLATED) as zipped:
        zipped.writestr(name, content)
    return payload.getvalue()


@pytest.mark.parametrize(
    ("carrier", "budget"),
    [
        (b"PK\x03\x04 not an archive", 32),
        (b"\x1f\x8b not gzip", 32),
        (b"x" * 64, 32),
        (_deflated("big.txt", b"x" * 10_000), 1_000),
        (gzip.compress(b"x" * 10_000), 1_000),
        # Tar pads its blocks to 10,240 bytes, so the archive fits where its member does not.
        (_tar("big.txt", b"x" * 2_000), 11_000),
    ],
    ids=["damaged-zip", "damaged-gzip", "over-budget", "zip-member", "gzip-member", "tar-member"],
)
def test_a_damaged_or_oversized_carrier_refuses(carrier: bytes, budget: int) -> None:
    """A damaged archive, or content or members beyond the byte budget, is not read past."""
    with pytest.raises(ValueError, match="record_retirement_carrier_undecodable:carrier"):
        carrier_tokens(carrier, depth=6, budget=budget, name="carrier")


def test_base64_is_read_only_within_the_depth_and_when_valid() -> None:
    """At depth zero only plain digests count; a malformed base64 run is skipped, not fatal."""
    encoded = b'{"blob": "' + base64.b64encode(b"named " + _TOKEN.encode()) + b'"}'
    assert _TOKEN not in carrier_tokens(encoded, depth=0, budget=1 << 20, name="carrier")
    assert carrier_tokens(b"A" * 45, depth=6, budget=1 << 20, name="carrier") == frozenset()
