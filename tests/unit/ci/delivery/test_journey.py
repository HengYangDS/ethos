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
from tools.ci import sessions

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


def _journey_without_effects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, published: set[str]
) -> tuple[list[str], list[tuple[Path, str]]]:
    """Replace every journey effect; return the downloaded tags and each upgrade's store."""
    downloads: list[str] = []
    upgrades: list[tuple[Path, str]] = []

    def download(tag: str, target: Path, **_options: object) -> journey.PublishedRelease:
        downloads.append(tag)
        return journey.PublishedRelease(tag.removeprefix("v"), "", target / "a.tar.gz", "0" * 64)

    def upgrade(
        _successor: object, _predecessor: object, work: Path, *, environment: dict[str, str]
    ) -> dict[str, object]:
        upgrades.append((work, environment["XDG_DATA_HOME"]))
        return {"state": "passed"}

    generation = tmp_path / "previous-install" / "ethos/runtime" / "0123456789abcdef"
    generation.mkdir(parents=True)
    installed = Mock(installed=tmp_path / "previous-install")
    passed = {"state": "passed", "runtime_digest": "f" * 64}
    for name, value in (
        ("release_published", published.__contains__),
        ("download_release", download),
        ("independent_host_environment", lambda: ({}, "git")),
        ("prove_shared_supply", lambda *_a, **_k: passed),
        ("require_selected_runtime", lambda path: path),
        ("prove_full", lambda *_a, **_k: passed),
        ("prepare_mise", lambda _root: Path("mise")),
        ("install_archive", lambda *_a, **_k: installed),
        ("require_installed_runtime", lambda path: path),
        ("prove_upgrade", upgrade),
    ):
        monkeypatch.setattr(journey, name, value)
    return downloads, upgrades


def test_the_receipt_names_the_versions_it_skipped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A qualified tag's receipt says which predecessor it used and which entries it skipped."""
    downloads, upgrades = _journey_without_effects(tmp_path, monkeypatch, {"0.2.0-alpha.27"})
    receipt = journey.qualify(f"v{VERSION}", work=tmp_path, platform=PLATFORM, changelog=CHANGELOG)
    assert downloads == [f"v{VERSION}", "v0.2.0-alpha.27"]
    assert (receipt["previous"], receipt["skipped_unpublished"], receipt["previous_named"]) == (
        ["v0.2.0-alpha.27"],
        ["v0.2.0-alpha.28"],
        False,
    )
    assert list(receipt["steps"]["upgrade_and_rollback"]) == ["v0.2.0-alpha.27"]
    assert len(upgrades) == 1


def test_named_predecessors_follow_the_changelog_without_duplicates() -> None:
    """Each named predecessor is an earlier published entry, newest first."""
    every = {"0.2.0-alpha.28", "0.2.0-alpha.27"}.__contains__
    names = ("v0.2.0-alpha.27", "v0.2.0-alpha.28", "v0.2.0-alpha.27")
    assert journey.named_predecessors(CHANGELOG, VERSION, names, published=every) == (
        "0.2.0-alpha.28",
        "0.2.0-alpha.27",
    )


@pytest.mark.parametrize(
    ("name", "gap"),
    [
        ("0.2.0-alpha.28", "release_journey_previous_invalid:0.2.0-alpha.28"),
        ("v0.2.0-alpha.29", "release_journey_previous_not_earlier:v0.2.0-alpha.29"),
        ("v0.2.0-alpha.26", "release_journey_previous_not_earlier:v0.2.0-alpha.26"),
        ("v0.2.0-alpha.28", "release_journey_previous_unpublished:v0.2.0-alpha.28"),
    ],
)
def test_a_named_predecessor_outside_the_published_history_refuses(name: str, gap: str) -> None:
    """A malformed, later, unknown or unpublished predecessor refuses with its tag."""
    only_older = {"0.2.0-alpha.27"}.__contains__
    with pytest.raises(ValueError, match=re.escape(gap)):
        journey.named_predecessors(CHANGELOG, VERSION, (name,), published=only_older)


def test_each_named_predecessor_upgrades_in_its_own_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Shared steps run once; each predecessor gets its assets, its upgrade and its own store."""
    published = {"0.2.0-alpha.28", "0.2.0-alpha.27"}
    downloads, upgrades = _journey_without_effects(tmp_path, monkeypatch, published)
    receipt = journey.qualify(
        f"v{VERSION}",
        work=tmp_path,
        platform=PLATFORM,
        changelog=CHANGELOG,
        previous=("v0.2.0-alpha.27", "v0.2.0-alpha.28"),
    )
    assert downloads == [f"v{VERSION}", "v0.2.0-alpha.28", "v0.2.0-alpha.27"]
    assert (receipt["previous"], receipt["skipped_unpublished"], receipt["previous_named"]) == (
        ["v0.2.0-alpha.28", "v0.2.0-alpha.27"],
        [],
        True,
    )
    assert sorted(receipt["assets"]) == ["0.2.0-alpha.27", "0.2.0-alpha.28", VERSION]
    assert list(receipt["steps"]["upgrade_and_rollback"]) == ["v0.2.0-alpha.28", "v0.2.0-alpha.27"]
    assert [work.name for work, _store in upgrades] == ["0.2.0-alpha.28", "0.2.0-alpha.27"]
    assert len({store for _work, store in upgrades}) == 2


@pytest.mark.parametrize(
    ("value", "expected"),
    [("", ()), ("v0.2.0-alpha.29, v0.2.0-alpha.30,", ("v0.2.0-alpha.29", "v0.2.0-alpha.30"))],
)
def test_the_session_passes_the_named_predecessors(
    monkeypatch: pytest.MonkeyPatch, value: str, expected: tuple[str, ...]
) -> None:
    """The dispatch's comma-separated predecessors reach the journey as tags."""
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(journey, "run", lambda _session, **options: calls.append(options))
    session = Mock(posargs=["--tag", "v0.2.0-beta.2", "--previous", value])
    sessions.release_journey(session)
    assert calls == [{"tag": "v0.2.0-beta.2", "previous": expected}]
