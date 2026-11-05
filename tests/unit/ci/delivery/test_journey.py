"""A published prerelease is qualified on the adopter journey from its release assets alone."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

import tools.ci.delivery.acceptance.journey as journey

CHANGELOG = """# Changelog

## [Unreleased]

## [0.2.0-alpha.29] - 2026-11-04

### Fixed

- A fix.

## [0.2.0-alpha.28] - 2026-11-02

## [0.2.0-alpha.27] - 2026-11-02
"""
VERSION, PLATFORM = "0.2.0-alpha.29", "linux-x64"
ARCHIVE = f"ethos-{VERSION}-{PLATFORM}.tar.gz"


def _digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def test_the_previous_release_is_the_next_published_changelog_entry() -> None:
    """The forge, not the changelog, says which earlier version was published."""
    every = {"0.2.0-alpha.28", "0.2.0-alpha.27"}.__contains__
    assert journey.previous_version(CHANGELOG, VERSION, published=every) == ("0.2.0-alpha.28", ())
    only_older = {"0.2.0-alpha.27"}.__contains__
    assert journey.previous_version(CHANGELOG, VERSION, published=only_older) == (
        "0.2.0-alpha.27",
        ("0.2.0-alpha.28",),
    )
    with pytest.raises(ValueError, match=re.escape("release_journey_entry_missing:0.2.0-alpha.30")):
        journey.previous_version(CHANGELOG, "0.2.0-alpha.30", published=every)
    for version, published in (("0.2.0-alpha.27", every), (VERSION, set().__contains__)):
        with pytest.raises(
            ValueError, match=re.escape(f"release_journey_previous_missing:{version}")
        ):
            journey.previous_version(CHANGELOG, version, published=published)


@pytest.mark.parametrize(
    ("returncode", "stderr", "expected"),
    [(0, "", "published"), (1, "release not found", "unpublished"), (1, "HTTP 502", "refused")],
)
def test_only_a_missing_release_counts_as_unpublished(
    monkeypatch: pytest.MonkeyPatch, returncode: int, stderr: str, expected: str
) -> None:
    """A forge error other than a missing release refuses instead of skipping the version."""

    def gh(_cwd: Path, command: tuple[str, ...], **_options: object) -> subprocess.CompletedProcess:
        assert command[:3] == ("gh", "release", "view")
        assert command[3] == "v0.2.0-alpha.28"
        return subprocess.CompletedProcess(command, returncode, "", stderr)

    monkeypatch.setattr(journey, "run_command", gh)
    if expected == "refused":
        with pytest.raises(ValueError, match=re.escape("release_journey_release_lookup_failed")):
            journey.release_published("0.2.0-alpha.28")
    else:
        assert journey.release_published("0.2.0-alpha.28") is (expected == "published")


@pytest.mark.parametrize(
    ("listed", "declared", "verified", "gap"),
    [
        (b"archive", b"archive", 0, ""),
        (b"other", b"archive", 0, f"release_journey_checksum_mismatch:{ARCHIVE}"),
        (b"archive", b"other", 0, f"release_journey_declaration_mismatch:{ARCHIVE}"),
        (b"archive", b"archive", 1, f"release_journey_attestation_failed:{ARCHIVE}"),
    ],
)
def test_only_verified_release_bytes_reach_the_installation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    listed: bytes,
    declared: bytes,
    verified: int,
    gap: str,
) -> None:
    """The archive must match its checksums, its declaration and its build attestation."""
    calls: list[tuple[str, ...]] = []

    def gh(_cwd: Path, command: tuple[str, ...], **_options: object) -> subprocess.CompletedProcess:
        calls.append(command)
        if command[1:3] == ("release", "download"):
            target = Path(command[command.index("--dir") + 1])
            (target / ARCHIVE).write_bytes(b"archive")
            (target / "SHA256SUMS").write_text(f"{_digest(listed)}  {ARCHIVE}\n")
            (target / f"ethos-{VERSION}.mise.toml").write_text(
                f'[tools."http:ethos"]\nversion = "{VERSION}"\n\n[tools."http:ethos".platforms]\n'
                f'{PLATFORM} = {{ url = "https://example.invalid/{ARCHIVE}", '
                f'checksum = "sha256:{_digest(declared)}", bin_path = "ethos/bin" }}\n'
            )
            return subprocess.CompletedProcess(command, 0, "", "")
        return subprocess.CompletedProcess(command, verified, "", "denied" if verified else "")

    monkeypatch.setattr(journey, "run_command", gh)
    target = tmp_path / "assets"
    if gap:
        with pytest.raises(ValueError, match=re.escape(gap)):
            journey.download_release(f"v{VERSION}", target, platform=PLATFORM, attested=True)
    else:
        published = journey.download_release(
            f"v{VERSION}", target, platform=PLATFORM, attested=True
        )
        assert (published.version, published.sha256) == (VERSION, _digest(b"archive"))
        assert published.archive == target / ARCHIVE
        assert f'checksum = "sha256:{_digest(b"archive")}"' in published.declaration
    attested = [command for command in calls if command[1:3] == ("attestation", "verify")]
    expected = (
        []
        if gap.startswith(("release_journey_checksum", "release_journey_declaration"))
        else [("gh", "attestation", "verify", str(target / ARCHIVE), "--repo", journey.REPOSITORY)]
    )
    assert attested == expected


@pytest.mark.parametrize("failure", [None, RuntimeError("journey_step_failed")])
def test_each_leg_writes_its_receipt_whether_it_passes_or_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: Exception | None
) -> None:
    """The receipt names every step's result, and a failure keeps its cause and stage events."""
    steps = {"published_assets": {"state": "passed"}, "uninstall": {"state": "passed"}}

    def qualify(tag: str, **_options: object) -> dict[str, object]:
        if failure is not None:
            raise failure
        return {"tag": tag, "steps": steps}

    monkeypatch.setattr(journey, "qualify", qualify)
    monkeypatch.setattr(journey, "host_platform", lambda: PLATFORM)
    session = Mock()
    output = tmp_path / "evidence" / f"journey-{PLATFORM}.json"
    journey.run(session, tag=f"v{VERSION}", evidence=output, work=tmp_path / "work")
    receipt = json.loads(output.read_text(encoding="utf-8"))
    assert receipt["tag"] == f"v{VERSION}"
    assert receipt["platform"] == PLATFORM
    assert receipt["execution_events"] == output.with_suffix(".events.jsonl").as_posix()
    assert output.with_suffix(".events.jsonl").is_file()
    assert not (tmp_path / "work").exists()
    if failure is None:
        assert (receipt["state"], receipt["steps"]) == ("passed", steps)
        session.error.assert_not_called()
    else:
        assert (receipt["state"], receipt["error"]) == ("failed", "journey_step_failed")
        session.error.assert_called_once()


def test_the_receipt_names_the_versions_it_skipped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A qualified tag's receipt says which predecessor it used and which entries it skipped."""
    downloads: list[str] = []

    def download(tag: str, target: Path, **_options: object) -> journey.PublishedRelease:
        downloads.append(tag)
        return journey.PublishedRelease(tag.removeprefix("v"), "", target / "a.tar.gz", "0" * 64)

    generation = tmp_path / "previous-install" / "ethos/runtime" / "0123456789abcdef"
    generation.mkdir(parents=True)
    installed = Mock(installed=tmp_path / "previous-install")
    passed = {"state": "passed", "runtime_digest": "f" * 64}
    for name, value in (
        ("release_published", {"0.2.0-alpha.27"}.__contains__),
        ("download_release", download),
        ("independent_host_environment", lambda: ({}, "git")),
        ("prove_shared_supply", lambda *_a, **_k: passed),
        ("require_selected_runtime", lambda path: path),
        ("prove_full", lambda *_a, **_k: passed),
        ("prepare_mise", lambda _root: Path("mise")),
        ("install_archive", lambda *_a, **_k: installed),
        ("require_installed_runtime", lambda path: path),
        ("prove_upgrade", lambda *_a, **_k: passed),
    ):
        monkeypatch.setattr(journey, name, value)
    receipt = journey.qualify(f"v{VERSION}", work=tmp_path, platform=PLATFORM, changelog=CHANGELOG)
    assert downloads == [f"v{VERSION}", "v0.2.0-alpha.27"]
    assert (receipt["previous"], receipt["skipped_unpublished"]) == (
        "v0.2.0-alpha.27",
        ["v0.2.0-alpha.28"],
    )
