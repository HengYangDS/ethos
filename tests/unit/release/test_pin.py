"""One exact GitHub pin names an ETHOS release: its declared forms, lock entries and class."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import ethos.repository.release.pin as pin

VERSION = "0.2.0-beta.11"
PIN = pin.DeclaredPin("github", VERSION, bare=True, verify_provenance=True)
UNVERIFIED = PIN._replace(verify_provenance=False)
LEGACY = pin.DeclaredPin("http", VERSION, bare=False, verify_provenance=False)
BARE = """[tools]
"github:HengYangDS/ethos" = "0.2.0-beta.11"

[settings]
locked_verify_provenance = true
"""
TABLE = '[tools."http:ethos"]\nversion = "0.2.0-beta.11"\n'
OPTIONS = '[tools."github:HengYangDS/ethos"]\nversion = "0.2.0-beta.11"\nbin_path = "bin"\n'
# A lock as Mise 2026.11 writes it for the pin, and one as adopters hold for the copied table.
LOCK = """lockfile_version = 4

[[tools."github:HengYangDS/ethos"]]
version = "0.2.0-beta.11"
backend = "github:HengYangDS/ethos"

[tools."github:HengYangDS/ethos"."platforms.linux-x64"]
checksum = "sha256:aa"
url = "https://example.invalid/ethos-0.2.0-beta.11-linux-x64.tar.gz"
provenance = "github-attestations"
"""
LEGACY_LOCK = """lockfile_version = 3

[[tools."http:ethos"]]
version = "0.2.0-beta.11"

[tools."http:ethos"."platforms.linux-x64"]
checksum = "sha256:aa"
url = "https://example.invalid/ethos-0.2.0-beta.11-linux-x64.tar.gz"
"""
RECORDED = ("sha256:aa", "https://example.invalid/ethos-0.2.0-beta.11-linux-x64.tar.gz")
INEXACT = ('"0.2"', '"latest"', '"0.2.0b11"', '"0.2.0-dev.1"', '"0.2.0-beta.01"', "[]")


@pytest.mark.parametrize(
    ("config", "expected"),
    [
        (BARE, PIN),
        (BARE.replace("true", "false"), UNVERIFIED),
        ('[tools]\n"github:HengYangDS/ethos" = "0.2.0-beta.11"\n', UNVERIFIED),
        (OPTIONS, UNVERIFIED._replace(bare=False)),
        (TABLE, LEGACY),
        ('[tools]\nnode = "26"\n', None),
    ],
)
def test_a_configuration_declares_the_pin_in_either_form(config, expected):
    """Only the string form of the GitHub key is bare; only a true setting verifies provenance."""
    assert pin.declared_pin(config) == expected


def test_the_pin_renders_as_one_line_and_as_a_whole_configuration():
    """The whole entry is the text that reads back as the bare, verified pin."""
    assert pin.bare_entry(VERSION) == BARE
    assert pin.pin_line(VERSION) == BARE.splitlines()[1]
    assert (PIN.key, LEGACY.key) == ("github:HengYangDS/ethos", "http:ethos")


@pytest.mark.parametrize(
    ("config", "gap"),
    [
        (BARE + TABLE, "runtime_pin_ambiguous"),
        ("[tools", "runtime_pin_invalid"),
        *((BARE.replace('"0.2.0-beta.11"', value), "runtime_pin_invalid") for value in INEXACT),
    ],
)
def test_an_ambiguous_unreadable_or_inexact_pin_refuses(config, gap):
    """A configuration names one exact release version, once."""
    with pytest.raises(ValueError, match=gap):
        pin.declared_pin(config)


def test_a_lock_entry_is_read_for_the_pinned_version_and_platform():
    """Formats 3 and 4 read alike under the pin's own key; an unrecorded field reads as empty."""
    assert pin.lock_entry(LOCK, PIN, "linux-x64") == (*RECORDED, "github-attestations")
    assert pin.lock_entry(LEGACY_LOCK, LEGACY, "linux-x64") == (*RECORDED, "")
    for lock, declared, platform in (
        (LOCK, PIN, "macos-arm64"),
        (LOCK, PIN._replace(version="0.2.0-beta.10"), "linux-x64"),
        ('lockfile_version = 3\ntools = "none"\n', PIN, "linux-x64"),
    ):
        assert pin.lock_entry(lock, declared, platform) is None
    assert (pin.lockfile_version(LOCK), pin.lockfile_version("")) == (4, None)


def test_an_unreadable_lock_refuses_both_readers():
    """Unreadable TOML is a named gap, never an empty lock."""
    with pytest.raises(ValueError, match="runtime_pin_lock_invalid"):
        pin.lockfile_version("[[tools")
    with pytest.raises(ValueError, match="runtime_pin_lock_invalid"):
        pin.lock_entry("[[tools", PIN, "linux-x64")


@pytest.mark.parametrize(
    ("version", "cutoff", "expected", "ref"),
    [
        ("0.2.0-alpha.29", None, "attested-main", "refs/heads/main"),
        ("0.2.0b3", None, "checksum", None),
        ("0.2.0-beta.11", "0.2.0-beta.11", "attested-main", "refs/heads/main"),
        ("0.2.0-beta.12", "0.2.0-beta.11", "attested", "refs/tags/v0.2.0-beta.12"),
    ],
)
def test_a_release_class_follows_its_dispatch_and_names_its_attestation(
    monkeypatch, version, cutoff, expected, ref
):
    """A main-dispatched release binds `main` and its tag's commit; a later one, its tag ref."""
    monkeypatch.setattr(pin, "MAIN_DISPATCH_UNTIL", cutoff)
    identity = ref and ("HengYangDS/ethos/.github/workflows/ci.yml", ref, "c0ffee")
    assert pin.release_class(version) == expected
    assert pin.attestation_identity(version, tag_commit="c0ffee") == identity


@pytest.mark.parametrize("cutoff", [None, "0.2.0-beta.6"])
def test_every_changelog_version_has_the_class_of_its_dispatch(monkeypatch, cutoff):
    """Changelog order, not version arithmetic, says which releases each kind of dispatch built.

    Every released version is also an exact pin, so the pin refuses no release ETHOS made.
    """
    monkeypatch.setattr(pin, "MAIN_DISPATCH_UNTIL", cutoff)
    changelog = (Path(__file__).parents[3] / "CHANGELOG.md").read_text(encoding="utf-8")
    versions = re.findall(r"^## \[(\d[^\]]*)\] - ", changelog, re.MULTILINE)
    assert all(pin.declared_pin(pin.bare_entry(version)) for version in versions)
    tagged, attested = versions.index(cutoff or versions[0]), versions.index(pin.ATTESTED_SINCE)
    assert [pin.release_class(version) for version in versions] == [
        "checksum"
        if index > attested or version in pin.DIGEST_UNBOUND
        else "attested"
        if index < tagged
        else "attested-main"
        for index, version in enumerate(versions)
    ]
