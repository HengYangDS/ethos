"""Acquire one published prerelease and its predecessors: the journey's only networked stage.

The stage asks the forge which releases exist and downloads each release's Mise declaration, its
checksums and its platform's archive. It checks the archive against both and, by the release's
class, against its build attestation's signer workflow, source ref and source commit. Mise then
locks each release's exact GitHub pin, the stage admits each locked entry against those checksums,
and Mise installs from the lock as an adopter's repository does. Two locks rebound to other bytes
must each be refused. The stage ends by writing the manifest of the archives it verified, which
is the only input of the offline qualification.
"""

from __future__ import annotations

import json
import re
import shutil
import tomllib
from dataclasses import asdict
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Literal

from packaging.version import Version

import ethos.repository.release.pin as pin
from ethos.adapters.process import run_command
from ethos.adapters.repo.runtime.materialization.effect import remove_generated_tree
from ethos.adapters.toolchain.mise import MISE_LOCK
from ethos.contracts.digest import file_sha256
from tools.ci.delivery.acceptance.invocation import command_label
from tools.ci.delivery.acceptance.invocation import observe_stage
from tools.ci.delivery.acceptance.invocation import run_native
from tools.ci.delivery.mise_tool import install_declared
from tools.ci.delivery.mise_tool import refusal

if TYPE_CHECKING:
    from collections.abc import Callable

    from ethos.repository.release.pin import ReleaseClass
    from tools.ci.delivery.mise_tool import InstalledTool

ROOT = Path(__file__).resolve().parents[4]
_ENTRY = re.compile(r"^## \[([^\]]+)\] - ", re.MULTILINE)
PRERELEASE = re.compile(r"v\d+\.\d+\.\d+-(?:alpha|beta|rc)\.\d+")
# The leg that locks every published platform once; each other install locks its own.
_FULL_LOCK_LEG = "linux-x64"
# An existing lock in the format adopters hold; relocking the pin into it must keep that format.
_SEED = "lockfile_version = 3\n"
# The class of a subject that a rehearsal's own run built: no release publishes it, so it has no
# pin and no attestation, and the assembly's checksum file is what admits its archive.
REHEARSED: Literal["rehearsed"] = "rehearsed"


@dataclass(frozen=True, slots=True)
class PublishedRelease:
    """One release's platform archive as its class verified it, and each archive digest it lists."""

    version: str
    archive: Path
    sha256: str
    verified: ReleaseClass | Literal["rehearsed"]
    archives: dict[str, str]


def previous_version(
    changelog: str, version: str, *, published: Callable[[str], bool]
) -> tuple[str, tuple[str, ...]]:
    """Name the first earlier changelog entry the forge published, and the entries it skipped."""
    versions = _ENTRY.findall(changelog)
    if version not in versions:
        message = f"release_journey_entry_missing:{version}"
        raise ValueError(message)
    skipped: list[str] = []
    for candidate in versions[versions.index(version) + 1 :]:
        if published(candidate):
            return candidate, tuple(skipped)
        skipped.append(candidate)
    message = f"release_journey_previous_missing:{version}"
    raise ValueError(message)


def named_predecessors(
    changelog: str, version: str, names: tuple[str, ...], *, published: Callable[[str], bool]
) -> tuple[str, ...]:
    """Check that each name is an earlier published changelog entry; return them newest first."""
    versions = _ENTRY.findall(changelog)
    if version not in versions:
        message = f"release_journey_entry_missing:{version}"
        raise ValueError(message)
    earlier = versions[versions.index(version) + 1 :]
    selected: set[str] = set()
    for name in names:
        if PRERELEASE.fullmatch(name) is None:
            message = f"release_journey_previous_invalid:{name}"
            raise ValueError(message)
        candidate = name.removeprefix("v")
        if candidate not in earlier:
            message = f"release_journey_previous_not_earlier:{name}"
            raise ValueError(message)
        if candidate in selected:
            continue
        if not published(candidate):
            message = f"release_journey_previous_unpublished:{name}"
            raise ValueError(message)
        selected.add(candidate)
    return tuple(candidate for candidate in earlier if candidate in selected)


def release_published(version: str, *, token: str) -> bool:
    """Ask the forge whether this version's release exists; only a missing release reads False."""
    try:
        _gh(
            "release",
            "view",
            f"v{version}",
            "--repo",
            pin.PIN_REPOSITORY,
            "--json",
            "tagName",
            failure=f"release_journey_release_lookup_failed:v{version}",
            token=token,
        )
    except ValueError as error:
        if "release not found" in str(error):
            return False
        raise
    return True


def _gh(*arguments: str, failure: str, token: str) -> None:
    """Run the forge's client; it alone, with Mise's forge calls, is handed the job's token."""
    with observe_stage(command_label(("gh", *arguments)), kind="process"):
        handed = {"GH_TOKEN": token} if token else None
        completed = run_command(ROOT, ("gh", *arguments), env=handed, timeout=600)
    if completed.returncode:
        detail = (completed.stderr.strip() or completed.stdout.strip())[-2000:]
        message = f"{failure}:{detail}"
        raise ValueError(message)


def download_release(
    tag: str, target: Path, *, platform: str, environment: dict[str, str], token: str
) -> PublishedRelease:
    """Download one release's assets for this platform and verify them by the release's class."""
    version = tag.removeprefix("v")
    name, declaration = f"ethos-{version}-{platform}.tar.gz", f"ethos-{version}.mise.toml"
    target.mkdir(parents=True)
    patterns = [
        part for asset in (declaration, "SHA256SUMS", name) for part in ("--pattern", asset)
    ]
    _gh(
        "release",
        "download",
        tag,
        "--repo",
        pin.PIN_REPOSITORY,
        "--dir",
        str(target),
        *patterns,
        failure=f"release_journey_download_failed:{tag}",
        token=token,
    )
    archive = target / name
    digest, listed = file_sha256(archive), _listed(target / "SHA256SUMS")
    if listed.get(name) != digest:
        message = f"release_journey_checksum_mismatch:{name}"
        raise ValueError(message)
    _require_declared(target / declaration, name, digest)
    verified = pin.release_class(version)
    # The signed tag names the source commit that the release's attestation must carry.
    peeled = f"refs/tags/{tag}^{{commit}}"
    commit = ""
    if verified != "checksum":
        commit = run_native("git", "rev-parse", peeled, env=environment)
    if identity := pin.attestation_identity(version, tag_commit=commit):
        _gh(
            "attestation",
            "verify",
            str(archive),
            "--repo",
            pin.PIN_REPOSITORY,
            "--signer-workflow",
            identity.signer_workflow,
            "--source-ref",
            identity.source_ref,
            "--source-digest",
            identity.source_digest,
            failure=f"release_journey_attestation_failed:{name}",
            token=token,
        )
    return PublishedRelease(version, archive, digest, verified, _archives(version, listed))


def _require_declared(declaration: Path, name: str, digest: str) -> None:
    """Refuse an archive whose release's Mise declaration does not carry its digest."""
    if f'checksum = "sha256:{digest}"' not in declaration.read_text(encoding="utf-8"):
        message = f"release_journey_declaration_mismatch:{name}"
        raise ValueError(message)


def _listed(checksums: Path) -> dict[str, str]:
    """Read a checksum file: each listed name with its digest."""
    lines = checksums.read_text(encoding="utf-8").splitlines()
    return {name.strip(): digest for digest, _, name in (line.partition("  ") for line in lines)}


def _archives(version: str, listed: dict[str, str]) -> dict[str, str]:
    """Return each platform whose archive of this version a checksum file lists, with its digest."""
    prefix = f"ethos-{version}-"
    return {
        name.removeprefix(prefix).removesuffix(".tar.gz"): digest
        for name, digest in listed.items()
        if name.startswith(prefix) and name.endswith(".tar.gz")
    }


def rehearsed_release(
    version: str, assembly: Path, target: Path, *, platform: str
) -> PublishedRelease:
    """Admit a rehearsal's own archive for this platform by the assembly's checks.

    The assembly is the directory that a journey leg downloads from its run: the build leg's
    upload, which holds the archive under the name its build gave it, and the checksum file and
    the Mise declaration that the run's assembler wrote. An archive is admitted only when its
    digest is the one that file lists for the published name and the one the declaration carries,
    as for a published release, and only then is it copied, under that name, into the journey's
    work directory, where the manifest requires each archive to lie.
    """
    name = f"ethos-{version}-{platform}.tar.gz"
    listed = _listed(assembly / "SHA256SUMS")
    digest = listed.get(name, "")
    built = [path for path in sorted(assembly.rglob("*.tar.gz")) if file_sha256(path) == digest]
    if not built:
        message = f"release_journey_checksum_mismatch:{name}"
        raise ValueError(message)
    _require_declared(assembly / f"ethos-{version}.mise.toml", name, digest)
    target.mkdir(parents=True)
    archive = Path(shutil.copy2(built[0], target / name))
    return PublishedRelease(version, archive, digest, REHEARSED, _archives(version, listed))


def lock_gap(
    lock: str, release: PublishedRelease, platforms: tuple[str, ...], *, seed: str | None
) -> str:
    """Name what keeps a lock from binding each platform to the release's own verified archive."""
    written = pin.lockfile_version(lock)
    if seed is not None and written != pin.lockfile_version(seed):
        return f"release_journey_lock_format_changed:{written}"
    attested = release.verified != "checksum"
    declared = pin.DeclaredPin("github", release.version, bare=True, verify_provenance=attested)
    for platform in platforms:
        name = f"ethos-{release.version}-{platform}.tar.gz"
        checksum, url, provenance = pin.lock_entry(lock, declared, platform) or ("", "", "")
        if (
            checksum != f"sha256:{release.archives.get(platform)}"
            or not url.endswith(f"/{name}")
            or (attested and provenance != pin.ATTESTED_PROVENANCE)
        ):
            return f"release_journey_lock_entry_invalid:{name}"
    return ""


@observe_stage("shared_package_installation")
def install_pin(
    release: PublishedRelease,
    home: Path,
    *,
    mise: Path,
    environment: dict[str, str],
    platforms: tuple[str, ...],
    locks: dict[str, object],
    token: str,
    seed: str | None = None,
) -> InstalledTool:
    """Lock the release's exact pin, admit each locked entry, then install this host's platform.

    A `checksum` release is pinned without the provenance setting: nothing attests its bytes.
    """

    def admit(lock: str) -> None:
        written = {"format": pin.lockfile_version(lock), "platforms": list(platforms)}
        locks[release.version] = written
        if gap := lock_gap(lock, release, platforms, seed=seed):
            raise ValueError(gap)

    line = f"[tools]\n{pin.pin_line(release.version)}\n"
    return install_declared(
        line if release.verified == "checksum" else pin.bare_entry(release.version),
        home,
        mise=mise,
        environment=environment,
        distribution=str(Version(release.version)),
        offline=False,
        lock=("--platform", ",".join(platforms)),
        seed=seed,
        admit=admit,
        token=token,
    )


@observe_stage("published_refusals")
def prove_refusals(
    tool: InstalledTool,
    release: PublishedRelease,
    work: Path,
    refusals: dict[str, str],
    *,
    platform: str,
    environment: dict[str, str],
    token: str,
) -> None:
    """Rebind the subject's own lock to other bytes twice; a locked install must refuse each.

    Each lock is the one Mise just wrote and installed from, with this platform's entry changed,
    so only the named bytes differ. One changes one digit of the archive's checksum. The other
    names an asset that only another public repository attested, by every coordinate that the
    product's own lock records for it; Mise 2026.11.8 refuses it by the URL's release. Both
    results are recorded before a case that was not refused fails the journey.
    """
    lock, table = (tool.project / "mise.lock").read_text(encoding="utf-8"), f"platforms.{platform}"
    ours = tomllib.loads(lock)["tools"][pin.PIN_KEY][0][table]
    supply = tomllib.loads((ROOT / MISE_LOCK).read_text(encoding="utf-8"))["tools"].values()
    theirs = next(
        entry[table]
        for entries in supply
        for entry in entries
        if entry.get(table, {}).get("provenance") == pin.ATTESTED_PROVENANCE
    )
    changed = {**ours, "checksum": f"sha256:{int(release.sha256, 16) ^ 1:064x}"}
    entry = pin.bare_entry(release.version)
    for case, fields in (("changed_checksum", changed), ("foreign_attestation", theirs)):
        rebound = lock
        # A coordinate of ours that theirs lacks would leave our bytes in reach, so it must fail.
        for name, value in ours.items():
            rebound = rebound.replace(value, fields[name])
        refusals[case] = refusal(
            entry, rebound, work / case, mise=tool.mise, environment=environment, token=token
        )
    if failed := [case for case, refused in refusals.items() if not refused]:
        message = f"release_journey_negative_case_failed:{','.join(failed)}"
        raise RuntimeError(message)


@observe_stage("published_pins")
def prove_pins(
    releases: list[PublishedRelease],
    work: Path,
    *,
    platform: str,
    mise: Path,
    environment: dict[str, str],
    token: str,
    receipt: dict[str, object],
) -> None:
    """Lock and install each release's exact pin as an adopter does, then try the rebound locks.

    Each rebound lock is tried right after the prerelease's install, from the lock as Mise wrote
    it. A rehearsed subject has no published pin, so only its predecessors are locked and no
    rebound lock is tried: its receipt carries no refusals at all, rather than an empty set that
    reads as every case refused. The installations are removed afterwards: qualification installs
    the same verified bytes again, offline.
    """
    locks: dict[str, object] = {}
    receipt["locks"] = locks
    subject, *earlier = releases
    install = partial(install_pin, mise=mise, environment=environment, locks=locks, token=token)
    if subject.verified != REHEARSED:
        refusals: dict[str, str] = {}
        receipt["refusals"] = refusals
        platforms = tuple(subject.archives) if platform == _FULL_LOCK_LEG else (platform,)
        tool = install(subject, work / "pins" / subject.version, platforms=platforms, seed=_SEED)
        prove_refusals(
            tool,
            subject,
            work / "refusals",
            refusals,
            platform=platform,
            environment=environment,
            token=token,
        )
    for release in earlier:
        install(release, work / "pins" / release.version, platforms=(platform,))
    remove_generated_tree(work / "pins")


def acquire(
    tag: str,
    work: Path,
    *,
    platform: str,
    changelog: str,
    previous: tuple[str, ...],
    receipt: dict[str, object],
    environment: dict[str, str],
    token: str,
    mise: Path | None,
    assembly: Path | None = None,
) -> Path:
    """Fetch and verify the prerelease and its predecessors, and write their manifest.

    Nothing after this stage reaches the network. Without `mise` the stage stops once each named
    release is verified by its class, and proves no pin. With `assembly` the subject is not
    downloaded: it is the archive that a rehearsal's own run built, admitted by that run's
    checksum file, and only its predecessors come from the forge.
    """
    version, published = tag.removeprefix("v"), partial(release_published, token=token)
    skipped: tuple[str, ...] = ()
    if previous:
        predecessors = named_predecessors(changelog, version, previous, published=published)
    else:
        latest, skipped = previous_version(changelog, version, published=published)
        predecessors = (latest,)
    assets: dict[str, object] = {}
    receipt |= {
        "tag": tag,
        "previous": [f"v{name}" for name in predecessors],
        "previous_named": bool(previous),
        "skipped_unpublished": [f"v{name}" for name in skipped],
        "assets": assets,
    }
    releases = []
    with observe_stage("published_assets"):
        fetch = partial(download_release, platform=platform, environment=environment, token=token)
        for name in (version, *predecessors):
            target = work / "assets" / name
            if assembly is not None and name == version:
                release = rehearsed_release(version, assembly, target, platform=platform)
            else:
                release = fetch(f"v{name}", target)
            releases.append(release)
            assets[name] = {
                "archive": release.archive.name,
                "sha256": release.sha256,
                "class": release.verified,
            }
    subject = releases[0]
    # The prerelease's archive, when its class verified an attestation; `class` says against what.
    attested = None if subject.verified in {"checksum", REHEARSED} else subject.archive.name
    receipt["attestation_verified"] = attested
    if mise is not None:
        prove_pins(
            releases,
            work,
            platform=platform,
            mise=mise,
            environment=environment,
            token=token,
            receipt=receipt,
        )
    manifest = work / "manifest.json"
    entries = [
        asdict(release) | {"archive": release.archive.relative_to(work).as_posix()}
        for release in releases
    ]
    manifest.write_text(json.dumps({"releases": entries}, indent=2) + "\n", encoding="utf-8")
    return manifest


def read_manifest(manifest: Path) -> list[PublishedRelease]:
    """Read the acquired releases, the prerelease first, with each archive's verified digest.

    A manifest refuses unless it is whole: readable, with at least the prerelease, each entry
    with exactly a release's fields, and each archive under the manifest's own directory.
    """
    invalid, home = "release_journey_manifest_invalid", manifest.parent.resolve()
    try:
        entries = json.loads(manifest.read_text(encoding="utf-8"))["releases"]
        releases = [
            PublishedRelease(**entry | {"archive": home / entry["archive"]}) for entry in entries
        ]
    except (OSError, LookupError, TypeError, ValueError) as error:
        raise ValueError(invalid) from error
    inside = all(release.archive.resolve().is_relative_to(home) for release in releases)
    if not (releases and inside):
        raise ValueError(invalid)
    return releases
