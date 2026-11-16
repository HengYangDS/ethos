"""A published prerelease is qualified on the adopter journey from its release assets alone."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from contextlib import nullcontext
from functools import partial
from pathlib import Path
from unittest.mock import Mock

import pytest

import ethos.repository.release.pin as pin
import tools.ci.delivery.acceptance.acquisition as acquisition
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
# One of the variables that say where the host's tool supply is.
_SUPPLY = "ETHOS_CI_TOOL_CACHE_DIR"
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
    assert acquisition.previous_version(CHANGELOG, VERSION, published=every) == (
        "0.2.0-alpha.28",
        (),
    )
    only_older = {"0.2.0-alpha.27"}.__contains__
    assert acquisition.previous_version(CHANGELOG, VERSION, published=only_older) == (
        "0.2.0-alpha.27",
        ("0.2.0-alpha.28",),
    )
    with pytest.raises(ValueError, match=re.escape("release_journey_entry_missing:0.2.0-alpha.30")):
        acquisition.previous_version(CHANGELOG, "0.2.0-alpha.30", published=every)
    for version, published in (("0.2.0-alpha.27", every), (VERSION, set().__contains__)):
        with pytest.raises(
            ValueError, match=re.escape(f"release_journey_previous_missing:{version}")
        ):
            acquisition.previous_version(CHANGELOG, version, published=published)


@pytest.mark.parametrize(
    ("returncode", "stderr", "expected"),
    [(0, "", "published"), (1, "release not found", "unpublished"), (1, "HTTP 502", "refused")],
)
def test_only_a_missing_release_counts_as_unpublished(
    monkeypatch: pytest.MonkeyPatch, returncode: int, stderr: str, expected: str
) -> None:
    """A forge error other than a missing release refuses instead of skipping the version.

    The forge's client is handed the token; without one it gets no token variable at all.
    """
    handed: list[object] = []

    def gh(_cwd: Path, command: tuple[str, ...], **options: object) -> subprocess.CompletedProcess:
        assert command[:3] == ("gh", "release", "view")
        assert command[3] == "v0.2.0-alpha.28"
        handed.append(options["env"])
        return subprocess.CompletedProcess(command, returncode, "", stderr)

    monkeypatch.setattr(acquisition, "run_command", gh)
    if expected == "refused":
        with pytest.raises(ValueError, match=re.escape("release_journey_release_lookup_failed")):
            acquisition.release_published("0.2.0-alpha.28", token="")
    else:
        published = acquisition.release_published("0.2.0-alpha.28", token="fake")
        assert published is (expected == "published")
    assert handed == [None if expected == "refused" else {"GH_TOKEN": "fake"}]


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

    monkeypatch.setattr(acquisition, "run_command", gh)
    monkeypatch.setattr(acquisition, "run_native", lambda *command, env: " ".join((*command, *env)))
    for name, value in data.items():
        monkeypatch.setattr(pin, name, value)
    target, options = tmp_path / "assets", {"environment": {}, "token": "fake"}
    download = partial(acquisition.download_release, platform=PLATFORM, **options)
    if gap:
        with pytest.raises(ValueError, match=re.escape(gap)):
            download(f"v{VERSION}", target)
    else:
        expected = (target / ARCHIVE, DIGEST, pin.release_class(VERSION), {PLATFORM: DIGEST})
        assert download(f"v{VERSION}", target) == acquisition.PublishedRelease(VERSION, *expected)
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
    monkeypatch.setattr(acquisition, "install_declared", lambda *_a, admit, **_k: admit(lock))
    release = acquisition.PublishedRelease(VERSION, tmp_path, DIGEST, verified, {PLATFORM: DIGEST})
    locks = {}
    options = {"mise": tmp_path, "environment": {}, "platforms": platforms, "token": ""}
    with pytest.raises(ValueError, match=gap) if gap else nullcontext():
        acquisition.install_pin(release, tmp_path, locks=locks, seed=SEED, **options)
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
    release = acquisition.PublishedRelease(VERSION, tmp_path, DIGEST, "attested-main", {})
    tool, work, refusals = Mock(project=tmp_path, mise=tmp_path), tmp_path / "work", {}
    failed = pytest.raises(RuntimeError, match=f"negative_case_failed:{installed}$")
    with failed if installed else nullcontext():
        acquisition.prove_refusals(
            tool, release, work, refusals, platform=PLATFORM, environment={}, token=""
        )
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
    monkeypatch.setenv("CI", "true" if failure else "false")
    session = Mock()
    output = tmp_path / "evidence" / f"journey-{PLATFORM}.json"
    classes = state == "classes_verified"
    journey.run(
        session, tag=f"v{VERSION}", evidence=output, work=tmp_path / "work", classes_only=classes
    )
    receipt = json.loads(output.read_text(encoding="utf-8"))
    assert receipt["tag"] == f"v{VERSION}"
    assert (receipt["platform"], receipt["mise"]) == (PLATFORM, "2026.11.7")
    assert receipt["venue"] == ("ci" if failure else "local")
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
) -> dict[str, list]:
    """Replace every journey effect but its environments and its manifest; return what each saw.

    `tokens` holds, for each download, pin and offline install, the forge token this process
    held, the one in the environment that the step hands its children, and the one it was handed.
    """
    names = ("downloads", "upgrades", "pins", "tokens", "mise", "supply")
    seen: dict[str, list] = {name: [] for name in names}

    def held(environment: dict[str, str]) -> tuple[str | None, str | None]:
        return os.environ.get("GH_TOKEN"), environment.get("GH_TOKEN")

    def download(tag: str, target: Path, *, environment: dict[str, str], token: str, **_k: object):
        seen["downloads"].append(tag)
        seen["supply"].append(("download", os.environ.get(_SUPPLY)))
        seen["tokens"].append(("download", *held(environment), token))
        target.mkdir(parents=True)
        (target / "a.tar.gz").write_bytes(b"archive")
        version, archives = tag.removeprefix("v"), dict.fromkeys((PLATFORM, "macos-arm64"), "")
        return acquisition.PublishedRelease(
            version, target / "a.tar.gz", DIGEST, pin.release_class(version), archives
        )

    def install(declaration: str, _home: Path, **options: object) -> Mock:
        seen["pins"].append((declaration, options["lock"], options["seed"]))
        seen["tokens"].append(("pin", *held(options["environment"]), options["token"]))
        return Mock()

    def offline(
        archive: Path, _home: Path, *, mise: Path, environment: dict[str, str], **_bound: str
    ):
        seen["mise"].append(mise)
        seen["tokens"].append((archive.parent.name, *held(environment), ""))
        return Mock(runtime=tmp_path / "previous-install/runtime/0123456789abcdef")

    def upgrade(
        _successor: object, _predecessor: object, work: Path, *, environment: dict[str, str]
    ) -> dict[str, object]:
        seen["upgrades"].append((work, environment["XDG_DATA_HOME"]))
        return {"state": "passed"}

    def bound(_root: Path) -> Path:
        seen["supply"].append(("mise", os.environ.get(_SUPPLY)))
        return Path(shutil.which("mise") or "bound-mise")

    passed, which = {"state": "passed", "runtime_digest": "f" * 64}, shutil.which
    # A Mise that the host installed is on the host's path, and on no stage's.
    (tmp_path / "host").mkdir()
    (tmp_path / "host/mise").touch(mode=0o755)
    monkeypatch.setenv("PATH", os.pathsep.join((str(tmp_path / "host"), os.environ["PATH"])))
    for owner, name, value in (
        (acquisition, "release_published", lambda version, **_k: version in published),
        (acquisition, "download_release", download),
        (acquisition, "prove_refusals", lambda _t, _r, _w, refused, **_k: refused.update(a="no")),
        (acquisition, "install_declared", install),
        (journey, "prove_installed_supply", lambda *_a, **_k: passed),
        (journey, "require_selected_runtime", lambda path: path),
        (journey, "prove_full", lambda *_a, **_k: passed),
        (journey, "prepare_mise", bound),
        (journey, "mise_version", lambda _mise: (2026, 11, 7)),
        (journey, "install_archive", offline),
        (journey, "require_installed_runtime", lambda path: path),
        (journey, "prove_upgrade", upgrade),
        (shutil, "which", lambda name, **_k: which(name) or (name != "mise" and sys.executable)),
    ):
        monkeypatch.setattr(owner, name, value)
    monkeypatch.setenv("GH_TOKEN", "fake-token")
    monkeypatch.setenv(_SUPPLY, "/fake/supply")
    return seen


def test_the_receipt_names_the_versions_it_skipped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A qualified tag's receipt says which predecessor it used and which entries it skipped.

    The Linux x64 leg relocks every published platform of the subject's pin into a format-3 lock;
    a `checksum` predecessor installs its own platform from the pin line alone. A journey for
    the classes alone stops once each release is verified.
    """
    seen = _journey_without_effects(tmp_path, monkeypatch, {"0.2.0-alpha.27"})
    qualify = partial(journey.qualify, f"v{VERSION}", platform=PLATFORM, changelog=CHANGELOG)
    receipt = qualify(work=tmp_path / "work")
    assert seen["pins"] == [
        (pin.bare_entry(VERSION), ("--platform", "linux-x64,macos-arm64"), SEED),
        (f"[tools]\n{pin.pin_line('0.2.0-alpha.27')}\n", ("--platform", PLATFORM), None),
    ]
    assert (receipt["mise"], receipt["refusals"]) == ("2026.11.7", {"a": "no"})
    classes = {name: asset["class"] for name, asset in receipt["assets"].items()}
    assert classes == {VERSION: "attested-main", "0.2.0-alpha.27": "checksum"}
    assert receipt["attestation_verified"] == "a.tar.gz"
    classes = qualify(work=tmp_path / "classes", classes_only=True)
    assert (classes["assets"], "steps" in classes) == (receipt["assets"], False)
    assert (len(seen["pins"]), "mise" in classes) == (2, False)
    assert seen["downloads"][:2] == [f"v{VERSION}", "v0.2.0-alpha.27"]
    assert (receipt["previous"], receipt["skipped_unpublished"], receipt["previous_named"]) == (
        ["v0.2.0-alpha.27"],
        ["v0.2.0-alpha.28"],
        False,
    )
    assert list(receipt["steps"]["upgrade_and_rollback"]) == ["v0.2.0-alpha.27"]
    assert len(seen["upgrades"]) == 1


def test_only_acquisition_holds_the_forge_token_and_qualification_reads_the_manifest_alone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The forge token leaves the environment before either stage, and no child inherits it.

    Acquisition hands it to the forge's client and to Mise's pin calls. Qualification then
    installs, offline and in the manifest's order, the archives that acquisition verified, with
    the Mise that acquisition resolved where no host Mise was on its path. This process's
    environment is the host's again afterwards.
    """
    seen, host = _journey_without_effects(tmp_path, monkeypatch, {"0.2.0-alpha.27"}), {}
    host.update(os.environ)
    journey.qualify(f"v{VERSION}", work=tmp_path / "work", platform=PLATFORM, changelog=CHANGELOG)
    assert seen["tokens"] == [
        ("download", None, None, "fake-token"),
        ("download", None, None, "fake-token"),
        ("pin", None, None, "fake-token"),
        ("pin", None, None, "fake-token"),
        (VERSION, None, None, ""),
        ("0.2.0-alpha.27", None, None, ""),
    ]
    manifest = json.loads((tmp_path / "work/acquisition/manifest.json").read_text())
    assert [(entry["version"], entry["sha256"]) for entry in manifest["releases"]] == [
        (VERSION, DIGEST),
        ("0.2.0-alpha.27", DIGEST),
    ]
    assert set(seen["mise"]) == {Path("bound-mise")}
    # Only the preparation of Mise is shown where the host's tool supply is.
    assert seen["supply"] == [("mise", "/fake/supply"), *[("download", None)] * 2]
    assert not (tmp_path / "work/acquisition/pins").exists()
    assert dict(os.environ) == host


def test_qualification_checks_its_environment_before_its_first_child(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An environment that shows a child more than was declared stops the leg, naming what."""
    seen = _journey_without_effects(tmp_path, monkeypatch, {"0.2.0-alpha.27"})
    monkeypatch.setattr(journey, "hermetic_gap", lambda _root, _executables: "HOME")
    with pytest.raises(RuntimeError, match=r"^journey_environment_not_hermetic:HOME$"):
        journey.qualify(
            f"v{VERSION}", work=tmp_path / "work", platform=PLATFORM, changelog=CHANGELOG
        )
    assert [stage for stage, *_tokens in seen["tokens"]] == ["download", "download", "pin", "pin"]


def test_named_predecessors_follow_the_changelog_without_duplicates() -> None:
    """Each named predecessor is an earlier published entry, newest first."""
    every = {"0.2.0-alpha.28", "0.2.0-alpha.27"}.__contains__
    names = ("v0.2.0-alpha.27", "v0.2.0-alpha.28", "v0.2.0-alpha.27")
    assert acquisition.named_predecessors(CHANGELOG, VERSION, names, published=every) == (
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
        acquisition.named_predecessors(CHANGELOG, VERSION, (name,), published=only_older)


def test_each_named_predecessor_upgrades_in_its_own_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Shared steps run once; each predecessor gets its assets, its upgrade and its own store."""
    published = {"0.2.0-alpha.28", "0.2.0-alpha.27"}
    seen = _journey_without_effects(tmp_path, monkeypatch, published)
    upgrades = seen["upgrades"]
    receipt = journey.qualify(
        f"v{VERSION}",
        work=tmp_path / "work",
        platform=PLATFORM,
        changelog=CHANGELOG,
        previous=("v0.2.0-alpha.27", "v0.2.0-alpha.28"),
    )
    assert seen["downloads"] == [f"v{VERSION}", "v0.2.0-alpha.28", "v0.2.0-alpha.27"]
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
