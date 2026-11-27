"""A rehearsal's journey takes its subject from the run's own assembly, by the checksum file."""

from __future__ import annotations

import argparse
import hashlib
from contextlib import nullcontext
from functools import partial
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest

import ethos.repository.release.pin as pin
import tools.ci.delivery.acceptance.acquisition as acquisition
import tools.ci.delivery.acceptance.journey as journey
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_tree
from tools.ci import sessions

if TYPE_CHECKING:
    from pathlib import Path

CHANGELOG = """# Changelog

## [0.2.0-beta.13] - 2026-12-05

## [0.2.0-beta.12] - 2026-11-28

## [0.2.0-beta.11] - 2026-11-21
"""
VERSION, PLATFORM = "0.2.0-beta.13", "linux-x64"
ARCHIVE, OTHER = f"ethos-{VERSION}-{PLATFORM}.tar.gz", f"ethos-{VERSION}-macos-arm64.tar.gz"
DIGEST, ELSE = (hashlib.sha256(body).hexdigest() for body in (b"archive", b"other"))


BUILT = "build/artifacts/native/0123/ethos-0.2.0b13.tar.gz"
DECLARATION = f"ethos-{VERSION}.mise.toml"


def _assembly(home: Path, listed: str = DIGEST, declared: str = DIGEST) -> Path:
    """Lay out what a journey leg downloads: its build leg's upload, the checksums, the pin."""
    (home / BUILT).parent.mkdir(parents=True)
    (home / BUILT).write_bytes(b"archive")
    (home / "SHA256SUMS").write_text(f"{listed}  {ARCHIVE}\n{ELSE}  {OTHER}\n", encoding="utf-8")
    (home / DECLARATION).write_text(f'checksum = "sha256:{declared}"\n', encoding="utf-8")
    return home


def _acquire(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, previous: tuple[str, ...]) -> dict:
    """Acquire a rehearsed subject with its predecessors; return the receipt and what was seen."""
    seen: dict[str, list] = {"downloads": [], "pins": [], "refusals": []}

    def download(tag: str, target: Path, **_options: object) -> acquisition.PublishedRelease:
        seen["downloads"].append(tag)
        target.mkdir(parents=True)
        (target / "a.tar.gz").write_bytes(b"other")
        version = tag.removeprefix("v")
        return acquisition.PublishedRelease(
            version, target / "a.tar.gz", ELSE, pin.release_class(version), {PLATFORM: ELSE}
        )

    for name, double in (
        ("release_published", lambda _version, **_k: True),
        ("download_release", download),
        ("install_pin", lambda release, _home, **_k: seen["pins"].append(release.version)),
        ("prove_refusals", lambda *_a, **_k: seen["refusals"].append("tried")),
        ("remove_generated_tree", lambda _path: None),
    ):
        monkeypatch.setattr(acquisition, name, double)
    receipt: dict[str, object] = {}
    manifest = acquisition.acquire(
        f"v{VERSION}",
        tmp_path / "work",
        platform=PLATFORM,
        changelog=CHANGELOG,
        previous=previous,
        receipt=receipt,
        environment={},
        token="",
        mise=tmp_path / "mise",
        assembly=_assembly(tmp_path / "assembly"),
    )
    return {"receipt": receipt, "releases": acquisition.read_manifest(manifest), **seen}


def test_a_matching_archive_enters_the_manifest_as_rehearsed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The subject is the assembly's archive; only its predecessors are downloaded and pinned."""
    acquired = _acquire(tmp_path, monkeypatch, previous=())

    subject, earlier = acquired["releases"]
    assert (subject.version, subject.verified, subject.sha256) == (VERSION, "rehearsed", DIGEST)
    assert subject.archive == tmp_path / "work/assets" / VERSION / ARCHIVE
    assert subject.archive.read_bytes() == b"archive"
    assert subject.archives == {PLATFORM: DIGEST, "macos-arm64": ELSE}
    assert (earlier.version, acquired["downloads"]) == ("0.2.0-beta.12", ["v0.2.0-beta.12"])
    # The subject has no published pin and no attestation: neither is tried, and no refusal is
    # claimed for it.
    assert (acquired["pins"], acquired["refusals"]) == (["0.2.0-beta.12"], [])
    receipt = acquired["receipt"]
    listed = {"archive": ARCHIVE, "sha256": DIGEST, "class": "rehearsed"}
    assert (receipt["assets"][VERSION], receipt["attestation_verified"]) == (listed, None)
    assert "refusals" not in receipt


def test_the_recorded_predecessors_are_the_ones_acquired(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Named predecessors, as the head's record gives them, replace the changelog's first."""
    named = ("v0.2.0-beta.11", "v0.2.0-beta.12")
    acquired = _acquire(tmp_path, monkeypatch, previous=named)

    assert acquired["downloads"] == ["v0.2.0-beta.12", "v0.2.0-beta.11"]
    assert acquired["receipt"]["previous"] == ["v0.2.0-beta.12", "v0.2.0-beta.11"]


MISSING = {"no-archive": BUILT, "no-checksums": "SHA256SUMS", "no-declaration": DECLARATION}


@pytest.mark.parametrize("fault", ["another-digest", "unlisted", "another-declaration", *MISSING])
def test_an_archive_the_assembly_does_not_name_is_refused_before_any_install(
    tmp_path: Path, fault: str
) -> None:
    """Only the digest that the assembly lists and declares for the published name admits it."""
    home = _assembly(
        tmp_path / "assembly",
        listed=ELSE if fault == "another-digest" else DIGEST,
        declared=ELSE if fault == "another-declaration" else DIGEST,
    )
    if fault == "unlisted":
        (home / "SHA256SUMS").write_text(f"{ELSE}  {OTHER}\n", encoding="utf-8")
    elif fault in MISSING:
        (home / MISSING[fault]).unlink()
    admit = partial(acquisition.rehearsed_release, VERSION, home, platform=PLATFORM)

    with pytest.raises((ValueError, OSError)) as refused:
        admit(tmp_path / "work/assets" / VERSION)

    assert not (tmp_path / "work").exists()
    if fault == "another-declaration":
        assert str(refused.value) == f"release_journey_declaration_mismatch:{ARCHIVE}"
    elif fault not in {"no-checksums", "no-declaration"}:
        assert str(refused.value) == f"release_journey_checksum_mismatch:{ARCHIVE}"


RECORD = '\n[release.upgrade_from]\n"0.2.0-beta.12" = "attested-main"\n'


@pytest.mark.parametrize(
    ("record", "previous", "source"), [(RECORD, 1, "record"), ("", 0, "changelog")]
)
def test_a_rehearsal_names_its_subject_and_its_predecessors_from_the_committed_head(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, record: str, previous: int, source: str
) -> None:
    """The subject and its predecessors are the head's commit; the receipt names their source."""
    repo = init_git_repo(tmp_path / "product")
    binding = '[release]\nmirror = "independent"\n'
    tree = {"VERSION": f"{VERSION}\n", "CHANGELOG.md": CHANGELOG}
    write_tree(repo, {**tree, ".ethos/release.toml": binding + record})
    commit_fixture(repo, "chore: declare the release")
    edited = binding + RECORD.replace("0.2.0-beta.12", "0.2.0-beta.9")
    write_tree(repo, {"VERSION": "0.2.0-beta.14\n", ".ethos/release.toml": edited})
    calls: list[dict[str, object]] = []

    def qualify(tag: str, **options: object) -> dict[str, object]:
        calls.append({"tag": tag, **options})
        return {}

    monkeypatch.setattr(journey, "qualify", qualify)
    monkeypatch.setattr(journey, "ROOT", repo)
    monkeypatch.setattr(journey, "acceptance_observation", lambda *_a, **_k: nullcontext())
    session, evidence = Mock(), tmp_path / "journey.json"
    session.error.side_effect = AssertionError

    journey.run(session, assembly=tmp_path / "assembly", evidence=evidence, work=tmp_path / "w")

    (call,) = calls
    assert (call["tag"], call["assembly"]) == (f"v{VERSION}", tmp_path / "assembly")
    assert call["previous"] == ("v0.2.0-beta.12",)[:previous]
    assert call["receipt"]["previous_source"] == source


def test_the_session_takes_a_tag_or_an_assembly_and_never_both() -> None:
    """`--rehearse` names the downloaded assembly; with a tag, or with neither, it refuses."""
    calls: list[dict[str, object]] = []
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(journey, "run", lambda _session, **options: calls.append(options))
        sessions.release_journey(Mock(posargs=["--rehearse", "build/release/rehearsal"]))
        for arguments in ([], ["--tag", "v0.2.0-beta.13", "--rehearse", "x"]):
            # Before Python 3.13 a missing required argument ends the parser's process.
            with pytest.raises((argparse.ArgumentError, SystemExit)):
                sessions.release_journey(Mock(posargs=arguments))
        named = Mock(posargs=["--rehearse", "x", "--previous", "v0.2.0-beta.11"])
        named.error.side_effect = SystemExit
        with pytest.raises(SystemExit):
            sessions.release_journey(named)

    (call,) = calls
    assert str(call["assembly"]) == "build/release/rehearsal"
    assert call["tag"] == ""
