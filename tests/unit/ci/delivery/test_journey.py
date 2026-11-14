"""A published prerelease is qualified on the adopter journey from its release assets alone."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from contextlib import nullcontext
from functools import partial
from pathlib import Path
from unittest.mock import Mock

import pytest

import ethos.repository.release.pin as pin
import tools.ci.delivery.acceptance.journey as journey
import tools.ci.delivery.mise_tool as mise_tool
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
# The expected SHA-256 of each archive body a case publishes.
SHA256 = {body: hashlib.sha256(body).hexdigest() for body in (b"archive", b"other")}
DIGEST, SEED = SHA256[b"archive"], "lockfile_version = 3\n"
# The subject's pin as Mise relocks it into a lock of the format adopters hold.
LOCK = f"""lockfile_version = 3

[[tools."github:HengYangDS/ethos"]]
version = "{VERSION}"

[tools."github:HengYangDS/ethos"."platforms.{PLATFORM}"]
checksum = "sha256:{DIGEST}"
url = "https://example.invalid/{ARCHIVE}"
url_api = "https://api.example.invalid/assets/1"
provenance = "github-attestations"
"""
UNATTESTED, INVALID = LOCK.replace("github-attestations", ""), f"lock_entry_invalid:{ARCHIVE}"
# Class data under which the subject was dispatched from its tag, or is bound by checksums only.
TAGGED, UNBOUND = {"MAIN_DISPATCH_UNTIL": "0.2.0-alpha.28"}, {"DIGEST_UNBOUND": {VERSION}}


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
    ("listed", "declared", "verified", "data", "ref", "gap"),
    [
        (b"archive", b"archive", 0, {}, "refs/heads/main", ""),
        (b"other", b"archive", 0, {}, None, f"release_journey_checksum_mismatch:{ARCHIVE}"),
        (b"archive", b"other", 0, {}, None, f"release_journey_declaration_mismatch:{ARCHIVE}"),
        (b"archive", b"archive", 1, {}, "refs/heads/main", f"attestation_failed:{ARCHIVE}"),
        (b"archive", b"archive", 0, TAGGED, f"refs/tags/v{VERSION}", ""),
        (b"archive", b"archive", 1, UNBOUND, None, ""),
    ],
)
def test_only_verified_release_bytes_reach_the_installation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    listed: bytes,
    declared: bytes,
    verified: int,
    data: dict[str, object],
    ref: str | None,
    gap: str,
) -> None:
    """The archive must match its checksums, its declaration and, by its class, its attestation.

    A class names the signer workflow, the source ref and the commit the signed tag names; a
    `checksum` release gets no attestation call.
    """
    calls: list[tuple[str, ...]] = []

    def gh(_cwd: Path, command: tuple[str, ...], **_options: object) -> subprocess.CompletedProcess:
        calls.append(command)
        if command[1:3] == ("release", "download"):
            target = Path(command[command.index("--dir") + 1])
            (target / ARCHIVE).write_bytes(b"archive")
            (target / "SHA256SUMS").write_text(f"{SHA256[listed]}  {ARCHIVE}\n{DIGEST}  a.whl\n")
            (target / f"ethos-{VERSION}.mise.toml").write_text(
                f'[tools."http:ethos"]\nversion = "{VERSION}"\n\n[tools."http:ethos".platforms]\n'
                f'{PLATFORM} = {{ url = "https://example.invalid/{ARCHIVE}", '
                f'checksum = "sha256:{SHA256[declared]}", bin_path = "ethos/bin" }}\n'
            )
            return subprocess.CompletedProcess(command, 0, "", "")
        return subprocess.CompletedProcess(command, verified, "", "denied" if verified else "")

    monkeypatch.setattr(journey, "run_command", gh)
    monkeypatch.setattr(journey, "run_native", lambda *command: " ".join(command))
    for name, value in data.items():
        monkeypatch.setattr(pin, name, value)
    target = tmp_path / "assets"
    if gap:
        with pytest.raises(ValueError, match=re.escape(gap)):
            journey.download_release(f"v{VERSION}", target, platform=PLATFORM)
    else:
        expected = (target / ARCHIVE, DIGEST, pin.release_class(VERSION), {PLATFORM: DIGEST})
        published = journey.download_release(f"v{VERSION}", target, platform=PLATFORM)
        assert published == journey.PublishedRelease(VERSION, *expected)
    attested = [command[3:] for command in calls if command[1:3] == ("attestation", "verify")]
    identity = (
        str(target / ARCHIVE),
        "--repo",
        "HengYangDS/ethos",
        "--signer-workflow",
        "HengYangDS/ethos/.github/workflows/ci.yml",
        "--source-ref",
        ref,
        "--source-digest",
        f"git rev-parse refs/tags/v{VERSION}^{{commit}}",
    )
    assert attested == ([identity] if ref else [])


@pytest.mark.parametrize(
    ("lock", "verified", "platforms", "gap"),
    [
        (LOCK, "attested-main", (PLATFORM,), ""),
        (UNATTESTED, "checksum", (PLATFORM,), ""),
        (UNATTESTED, "attested-main", (PLATFORM,), INVALID),
        (LOCK.replace(DIGEST, SHA256[b"other"]), "attested-main", (PLATFORM,), INVALID),
        (LOCK.replace(".tar.gz", ".whl"), "attested-main", (PLATFORM,), INVALID),
        (LOCK, "attested-main", (PLATFORM, "macos-arm64"), "lock_entry_invalid:.*-macos-arm64"),
        (LOCK.replace("= 3", "= 4"), "attested-main", (PLATFORM,), "lock_format_changed:4"),
    ],
)
def test_only_a_lock_that_binds_the_release_is_installed(
    tmp_path, monkeypatch, lock, verified, platforms, gap
):
    """Each locked platform names the release's own archive, its listed digest and its class."""
    monkeypatch.setattr(journey, "install_declared", lambda *_a, admit, **_k: admit(lock))
    release = journey.PublishedRelease(VERSION, tmp_path, DIGEST, verified, {PLATFORM: DIGEST})
    locks, options = {}, {"mise": tmp_path, "environment": {}, "platforms": platforms}
    with pytest.raises(ValueError, match=gap) if gap else nullcontext():
        journey.install_pin(release, tmp_path, locks=locks, seed=SEED, **options)
    assert locks == {VERSION: {"format": int(lock.split()[2]), "platforms": list(platforms)}}


@pytest.mark.parametrize(
    ("installed", "step"),
    [
        ("", "install"),
        ("changed_checksum", "install"),
        ("foreign_attestation", "install"),
        ("foreign_attestation", "where"),
    ],
)
def test_a_lock_rebound_to_other_bytes_must_be_refused(tmp_path, monkeypatch, installed, step):
    """A rebound lock whose install passes, or fails and still leaves the tool, fails the journey.

    One lock keeps the archive and changes one digit of its checksum; the other names another
    repository's asset by every coordinate, so no byte of this release answers for it. Both
    results are recorded before the journey fails.
    """

    def mise(_cwd, command, **_options):
        kept = Path(command[2]).parent.name == installed and command[3] == step
        refused = command[3] in {"install", "where"} and not kept
        return subprocess.CompletedProcess(command, int(refused), "", "denied")

    monkeypatch.setattr(mise_tool, "run_command", mise)
    (tmp_path / "mise.lock").write_text(LOCK, encoding="utf-8")
    release = journey.PublishedRelease(VERSION, tmp_path, DIGEST, "attested-main", {})
    tool, work, refusals = Mock(project=tmp_path, mise=tmp_path), tmp_path / "work", {}
    failed = pytest.raises(RuntimeError, match=f"negative_case_failed:{installed}$")
    with failed if installed else nullcontext():
        journey.prove_refusals(tool, release, work, refusals, platform=PLATFORM, environment={})
    refused = "shared_supply_package_manager_failed:install --locked:exit=1:denied"
    cases = ("changed_checksum", "foreign_attestation")
    assert refusals == {case: "" if case == installed else refused for case in cases}
    locks = [(work / case / "project/mise.lock").read_text(encoding="utf-8") for case in cases]
    assert (locks[0].count("example.invalid"), DIGEST[:-1] in locks[0]) == (2, True)
    assert DIGEST not in locks[0] + locks[1]
    assert "example.invalid" not in locks[1]


@pytest.mark.parametrize(
    ("failure", "state"),
    [
        (None, "passed"),
        (None, "classes_verified"),
        (RuntimeError("journey_step_failed"), "failed"),
    ],
)
def test_each_leg_writes_its_receipt_whether_it_passes_or_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: Exception | None, state: str
) -> None:
    """The receipt names every step's result, and a failure keeps its cause and stage events.

    A failed leg keeps what it had established, and a journey for the classes alone never reads
    as a passed qualification.
    """
    steps = {"published_assets": {"state": "passed"}, "uninstall": {"state": "passed"}}

    def qualify(tag: str, *, receipt: dict[str, object], **_options: object) -> dict[str, object]:
        receipt["mise"] = "2026.11.7"
        if failure is not None:
            raise failure
        return {"tag": tag, "steps": steps}

    monkeypatch.setattr(journey, "qualify", qualify)
    monkeypatch.setattr(journey, "mise_target", lambda: PLATFORM)
    session = Mock()
    output = tmp_path / "evidence" / f"journey-{PLATFORM}.json"
    classes = state == "classes_verified"
    journey.run(
        session, tag=f"v{VERSION}", evidence=output, work=tmp_path / "work", classes_only=classes
    )
    receipt = json.loads(output.read_text(encoding="utf-8"))
    assert receipt["tag"] == f"v{VERSION}"
    assert (receipt["platform"], receipt["mise"]) == (PLATFORM, "2026.11.7")
    assert receipt["execution_events"] == output.with_suffix(".events.jsonl").as_posix()
    assert output.with_suffix(".events.jsonl").is_file()
    assert not (tmp_path / "work").exists()
    assert receipt["state"] == state
    if failure is None:
        assert receipt["steps"] == steps
        session.error.assert_not_called()
    else:
        assert receipt["error"] == "journey_step_failed"
        session.error.assert_called_once()


def _journey_without_effects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, published: set[str]
) -> tuple[list[str], list[tuple[Path, str]], list[tuple[object, ...]]]:
    """Replace every journey effect; return the downloaded tags, upgrade stores and installs."""
    downloads: list[str] = []
    upgrades: list[tuple[Path, str]] = []
    installs: list[tuple[object, ...]] = []

    def download(tag: str, target: Path, **_options: object) -> journey.PublishedRelease:
        downloads.append(tag)
        version, archives = tag.removeprefix("v"), dict.fromkeys((PLATFORM, "macos-arm64"), "")
        return journey.PublishedRelease(
            version, target / "a.tar.gz", "0" * 64, pin.release_class(version), archives
        )

    def install(declaration: str, _home: Path, **options: object) -> Mock:
        installs.append((declaration, options["lock"], options["seed"]))
        return Mock(runtime=tmp_path / "previous-install/runtime/0123456789abcdef")

    def upgrade(
        _successor: object, _predecessor: object, work: Path, *, environment: dict[str, str]
    ) -> dict[str, object]:
        upgrades.append((work, environment["XDG_DATA_HOME"]))
        return {"state": "passed"}

    passed = {"state": "passed", "runtime_digest": "f" * 64}
    for name, value in (
        ("release_published", published.__contains__),
        ("download_release", download),
        ("independent_host_environment", lambda: ({}, "git")),
        ("prove_installed_supply", lambda *_a, **_k: passed),
        ("prove_refusals", lambda _t, _r, _w, refusals, **_k: refusals.update(case="refused")),
        ("require_selected_runtime", lambda path: path),
        ("prove_full", lambda *_a, **_k: passed),
        ("prepare_mise", lambda _root: Path("mise")),
        ("mise_version", lambda _mise: (2026, 11, 7)),
        ("install_declared", install),
        ("require_installed_runtime", lambda path: path),
        ("prove_upgrade", upgrade),
    ):
        monkeypatch.setattr(journey, name, value)
    return downloads, upgrades, installs


def test_the_receipt_names_the_versions_it_skipped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A qualified tag's receipt says which predecessor it used and which entries it skipped.

    The Linux x64 leg relocks every published platform of the subject's pin into a format-3 lock;
    a `checksum` predecessor installs its own platform from the pin line alone. A journey for
    the classes alone stops once each release is verified.
    """
    downloads, upgrades, installs = _journey_without_effects(
        tmp_path, monkeypatch, {"0.2.0-alpha.27"}
    )
    qualify = partial(journey.qualify, f"v{VERSION}", platform=PLATFORM, changelog=CHANGELOG)
    receipt = qualify(work=tmp_path)
    assert installs == [
        (pin.bare_entry(VERSION), ("--platform", "linux-x64,macos-arm64"), SEED),
        (f"[tools]\n{pin.pin_line('0.2.0-alpha.27')}\n", ("--platform", PLATFORM), None),
    ]
    assert (receipt["mise"], receipt["refusals"]) == ("2026.11.7", {"case": "refused"})
    classes = {name: asset["class"] for name, asset in receipt["assets"].items()}
    assert classes == {VERSION: "attested-main", "0.2.0-alpha.27": "checksum"}
    assert receipt["attestation_verified"] == "a.tar.gz"
    classes = qualify(work=tmp_path, classes_only=True)
    assert (classes["assets"], "steps" in classes, len(installs)) == (receipt["assets"], False, 2)
    assert downloads[:2] == [f"v{VERSION}", "v0.2.0-alpha.27"]
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
    downloads, upgrades, _installs = _journey_without_effects(tmp_path, monkeypatch, published)
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
    ("value", "expected", "classes"),
    [
        ("", (), False),
        ("v0.2.0-alpha.29, v0.2.0-alpha.30,", ("v0.2.0-alpha.29", "v0.2.0-alpha.30"), True),
    ],
)
def test_the_session_passes_the_named_predecessors(
    monkeypatch: pytest.MonkeyPatch, value: str, expected: tuple[str, ...], *, classes: bool
) -> None:
    """The dispatch's comma-separated predecessors and its classes-only choice reach the journey."""
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(journey, "run", lambda _session, **options: calls.append(options))
    arguments = ["--tag", "v0.2.0-beta.2", "--previous", value, "--classes-only"]
    sessions.release_journey(Mock(posargs=arguments[: 4 + classes]))
    assert calls == [{"tag": "v0.2.0-beta.2", "previous": expected, "classes_only": classes}]
