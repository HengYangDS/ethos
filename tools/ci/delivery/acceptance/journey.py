"""Qualify one published prerelease on the declared adopter journey from its release assets alone.

The journey downloads the release's Mise declaration, its checksums and its platform's archive
and checks the archive against both and, by the release's class, against its build attestation's
signer workflow, source ref and source commit. Mise then locks the release's exact GitHub pin, the
journey admits each locked entry against those checksums, and Mise installs from the lock as an
adopter's repository does. Two locks rebound to other bytes must each be refused. On fresh host
stores the journey then proves a cold install, host-store pinning, hook binding, status and
uninstall; a full proof in a fixture adopter whose status then guides it to a ready repository;
and an upgrade from the previous release with its rollback. A dispatch may name several earlier
published releases to upgrade from instead; each upgrade and rollback then runs in its own host
store. Each leg writes one receipt with the stage events beside it, whether the journey passes or
fails.
"""

from __future__ import annotations

import hashlib
import json
import re
import tomllib
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from functools import partial
from pathlib import Path
from subprocess import SubprocessError
from typing import TYPE_CHECKING

from packaging.version import Version

import ethos.repository.release.pin as pin
import tools.ci.delivery.acceptance.adopter as adopter_fixture
import tools.ci.delivery.acceptance.runtime as runtime_acceptance
from ethos.adapters.process import run_command
from ethos.adapters.repo.runtime.interpreter import PYTHON_FLAGS
from ethos.adapters.repo.runtime.materialization.effect import remove_generated_tree
from ethos.adapters.repo.runtime.selection import require_installed_runtime
from ethos.adapters.repo.runtime.selection import require_selected_runtime
from ethos.adapters.toolchain.mise import MISE_LOCK
from ethos.adapters.toolchain.mise import mise_version
from ethos.contracts.paradigm.declaration import load_repository_paradigm
from tools.ci.delivery.acceptance.host_environment import independent_host_environment
from tools.ci.delivery.acceptance.invocation import acceptance_observation
from tools.ci.delivery.acceptance.invocation import command_label
from tools.ci.delivery.acceptance.invocation import continuation
from tools.ci.delivery.acceptance.invocation import invoke
from tools.ci.delivery.acceptance.invocation import observe_stage
from tools.ci.delivery.acceptance.invocation import run_native
from tools.ci.delivery.distribution import prove_installed_supply
from tools.ci.delivery.mise_tool import install_declared
from tools.ci.delivery.mise_tool import refusal
from tools.ci.toolchain.native import mise_target
from tools.ci.toolchain.native import prepare_mise

if TYPE_CHECKING:
    from collections.abc import Callable

    from ethos.adapters.repo.runtime.selection import SelectedRuntime
    from ethos.repository.release.pin import ReleaseClass
    from tools.ci.delivery.mise_tool import InstalledTool
    from tools.ci.session import Session

ROOT = Path(__file__).resolve().parents[4]
WORK = ROOT / "build/runtime/work/release-journey"
EVIDENCE = ROOT / "build/evidence/release-journey"
# The adopter whose lane command creates the fixture's candidate branch.
_ACTOR = "agent:test:journey:adopter"
_ENTRY = re.compile(r"^## \[([^\]]+)\] - ", re.MULTILINE)
_PRERELEASE = re.compile(r"v\d+\.\d+\.\d+-(?:alpha|beta|rc)\.\d+")
# The leg that locks every published platform once; each other install locks its own.
_FULL_LOCK_LEG = "linux-x64"
# An existing lock in the format adopters hold; relocking the pin into it must keep that format.
_SEED = "lockfile_version = 3\n"
# A failed step, download or verification; anything else still writes the receipt and propagates.
_STEP_FAILURES = (LookupError, OSError, RuntimeError, SubprocessError, TypeError, ValueError)


@dataclass(frozen=True, slots=True)
class PublishedRelease:
    """One release's platform archive as its class verified it, and each archive digest it lists."""

    version: str
    archive: Path
    sha256: str
    verified: ReleaseClass
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
        if _PRERELEASE.fullmatch(name) is None:
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


def release_published(version: str) -> bool:
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
        )
    except ValueError as error:
        if "release not found" in str(error):
            return False
        raise
    return True


def _gh(*arguments: str, failure: str) -> None:
    with observe_stage(command_label(("gh", *arguments)), kind="process"):
        completed = run_command(ROOT, ("gh", *arguments), timeout=600)
    if completed.returncode:
        detail = (completed.stderr.strip() or completed.stdout.strip())[-2000:]
        message = f"{failure}:{detail}"
        raise ValueError(message)


def download_release(tag: str, target: Path, *, platform: str) -> PublishedRelease:
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
    )
    archive = target / name
    with archive.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    listed = {
        name.strip(): listed_digest
        for listed_digest, _, name in (
            line.partition("  ")
            for line in (target / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
        )
    }
    if listed.get(name) != digest:
        message = f"release_journey_checksum_mismatch:{name}"
        raise ValueError(message)
    text = (target / declaration).read_text(encoding="utf-8")
    if f'checksum = "sha256:{digest}"' not in text:
        message = f"release_journey_declaration_mismatch:{name}"
        raise ValueError(message)
    verified = pin.release_class(version)
    # The signed tag names the source commit that the release's attestation must carry.
    peeled = f"refs/tags/{tag}^{{commit}}"
    commit = "" if verified == "checksum" else run_native("git", "rev-parse", peeled)
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
        )
    prefix = f"ethos-{version}-"
    archives = {
        published.removeprefix(prefix).removesuffix(".tar.gz"): listed[published]
        for published in listed
        if published.startswith(prefix) and published.endswith(".tar.gz")
    }
    return PublishedRelease(version, archive, digest, verified, archives)


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
) -> None:
    """Rebind the subject's own lock to other bytes twice; a locked install must refuse each.

    Each lock is the one Mise just wrote and installed from, with this platform's entry changed,
    so only the named bytes differ. One changes one digit of the archive's checksum. The other
    names an asset that only another public repository attested, by every coordinate that the
    product's own lock records for it, so that only an attestation check can refuse it. Both
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
            entry, rebound, work / case, mise=tool.mise, environment=environment
        )
    if failed := [case for case, refused in refusals.items() if not refused]:
        message = f"release_journey_negative_case_failed:{','.join(failed)}"
        raise RuntimeError(message)


@observe_stage("published_full_proof")
def prove_full(
    runtime: SelectedRuntime, work: Path, *, environment: dict[str, str]
) -> dict[str, object]:
    """Prove a signed fixture adopter's full floor, then follow its status to a ready repository.

    A new adopter has no candidate branch; its status names the command that creates one, and the
    journey runs that command before it requires a passing status.
    """
    repo = work / "proof-adopter"
    adopter_fixture.materialize_adopter(
        repo, openspec_config=ROOT / "openspec/config.yaml", run=run_native
    )
    run_native("git", "add", *adopter_fixture.declare_trust_registry(repo), cwd=repo)
    run_native("git", "commit", "--quiet", "-m", "chore: declare the trust floor", cwd=repo)
    head = run_native("git", "rev-parse", "HEAD", cwd=repo)
    runtime_acceptance.activate_from_runtime(runtime.python, repo, environment=environment)
    prefix = (str(runtime.python), *PYTHON_FLAGS, "-m", "ethos.cli")
    code, proof, detail = invoke(
        repo,
        (
            *prefix,
            "prove",
            "--full",
            "--execute",
            "--expect-head",
            head,
            "--root",
            str(repo),
            "--json",
        ),
        environment=environment,
    )
    if code or proof.get("verdict") != "pass":
        message = f"release_journey_full_proof_failed:{detail}"
        raise RuntimeError(message)
    reading = (*prefix, "status", "--root", str(repo), "--json")
    _code, guidance, detail = invoke(repo, reading, environment=environment)
    following = continuation(guidance)
    if guidance.get("required_gaps") != ["candidate_branch_missing"] or following[:3] != (
        "ethos",
        "lane",
        "candidate",
    ):
        message = f"release_journey_candidate_guidance_invalid:{detail}"
        raise RuntimeError(message)
    code, candidate, detail = invoke(
        repo, (*prefix, *following[1:]), environment={**environment, "ETHOS_ACTOR": _ACTOR}
    )
    if code or candidate.get("verdict") != "pass":
        message = f"release_journey_candidate_failed:{detail}"
        raise RuntimeError(message)
    code, status, detail = invoke(repo, reading, environment=environment)
    data = status.get("data")
    selected = data.get("hook_runtime") if isinstance(data, dict) else None
    if (
        code
        or status.get("verdict") != "pass"
        or not isinstance(selected, dict)
        or selected.get("current") is not True
    ):
        message = f"release_journey_status_failed:{detail}"
        raise RuntimeError(message)
    return {
        "state": "passed",
        "head": head,
        "proof": {"verdict": proof["verdict"], "state": proof.get("state")},
        "candidate": {"guided_by": guidance["required_gaps"], "state": candidate.get("state")},
        "status": {"verdict": status["verdict"], "state": status.get("state")},
    }


@observe_stage("published_upgrade")
def upgrade_from(
    release: PublishedRelease,
    successor: SelectedRuntime,
    work: Path,
    *,
    install: Callable[[PublishedRelease, Path], InstalledTool],
    environment: dict[str, str],
) -> dict[str, object]:
    """Install one predecessor, then prove the upgrade from it and its rollback in its own store."""
    tool = install(release, work / "previous" / release.version)
    store = work / "upgrade" / release.version
    return prove_upgrade(
        successor,
        require_installed_runtime(tool.runtime),
        store,
        environment={**environment, "XDG_DATA_HOME": str(store / "host-data")},
    )


def prove_upgrade(
    successor: SelectedRuntime,
    predecessor: SelectedRuntime,
    work: Path,
    *,
    environment: dict[str, str],
) -> dict[str, object]:
    """Upgrade a retained adopter from the previous release, roll back and upgrade again."""
    retained = work / "retained-adopter"
    adopter_fixture.materialize_adopter(
        retained, openspec_config=ROOT / "openspec/config.yaml", run=run_native, retained=True
    )
    return runtime_acceptance.prove_retained_upgrade(
        successor, retained, predecessor=predecessor, environment=environment
    )


def qualify(
    tag: str,
    *,
    work: Path,
    platform: str,
    changelog: str,
    previous: tuple[str, ...] = (),
    classes_only: bool = False,
    receipt: dict[str, object] | None = None,
) -> dict[str, object]:
    """Run every journey step on one published prerelease and return each step's result.

    The receipt is filled as the journey goes, so a failed leg keeps what it had established.
    With `classes_only` the journey stops once each named release is verified by its class.
    Each rebound lock is tried right after the prerelease's install, from the lock as Mise wrote
    it, so a refusal that does not hold fails the leg before its long steps.
    """
    receipt = {} if receipt is None else receipt
    version = tag.removeprefix("v")
    skipped: tuple[str, ...] = ()
    if previous:
        predecessors = named_predecessors(changelog, version, previous, published=release_published)
    else:
        latest, skipped = previous_version(changelog, version, published=release_published)
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
        for name in (version, *predecessors):
            release = download_release(f"v{name}", work / "assets" / name, platform=platform)
            releases.append(release)
            assets[name] = {
                "archive": release.archive.name,
                "sha256": release.sha256,
                "class": release.verified,
            }
    subject, *earlier = releases
    # The prerelease's archive, when its class verified an attestation; `class` says against what.
    attested = None if subject.verified == "checksum" else subject.archive.name
    receipt["attestation_verified"] = attested
    if classes_only:
        return receipt
    environment = independent_host_environment()[0]
    mise = prepare_mise(ROOT)
    locks: dict[str, object] = {}
    refusals: dict[str, str] = {}
    version_read = ".".join(map(str, mise_version(mise) or ()))
    receipt |= {"mise": version_read, "locks": locks, "refusals": refusals}
    install = partial(install_pin, mise=mise, environment=environment, locks=locks)
    cold = work / "cold"
    platforms = tuple(subject.archives) if platform == _FULL_LOCK_LEG else (platform,)
    with observe_stage("shared_supply"):
        tool = install(subject, cold / "package-manager", platforms=platforms, seed=_SEED)
        prove_refusals(
            tool, subject, work / "refusals", refusals, platform=platform, environment=environment
        )
        # Pins in the host store, binds repositories, reads status, uninstalls.
        shared = prove_installed_supply(tool, cold, environment=environment)
    digest = str(shared["runtime_digest"])
    pinned = require_selected_runtime(
        cold / "host-data/ethos/installations" / digest[:16] / "runtime" / digest
    )
    full = prove_full(
        pinned,
        work / "proof",
        environment={**environment, "XDG_DATA_HOME": str(cold / "host-data")},
    )
    upgrades = {
        f"v{release.version}": upgrade_from(
            release,
            pinned,
            work,
            install=partial(install, platforms=(platform,)),
            environment=environment,
        )
        for release in earlier
    }
    receipt["steps"] = {
        "cold_install_pinning_binding_and_uninstall": shared,
        "full_proof_and_status": full,
        "upgrade_and_rollback": upgrades,
    }
    return receipt


def run(
    session: Session,
    *,
    tag: str,
    previous: tuple[str, ...] = (),
    classes_only: bool = False,
    evidence: Path | None = None,
    work: Path = WORK,
) -> None:
    """Qualify the tag on this host and keep its receipt and stage events, passing or not."""
    if _PRERELEASE.fullmatch(tag) is None:
        session.error(f"release journey needs a published prerelease tag, not {tag!r}")
    host = mise_target()
    output = evidence if evidence is not None else EVIDENCE / f"journey-{host}.json"
    events = output.with_suffix(".events.jsonl")
    payload: dict[str, object] = {"tag": tag, "platform": host, "state": "failed"}
    failure: Exception | None = None
    try:
        with acceptance_observation(events, head=tag, wheel_sha256=""):
            try:
                if work.exists():
                    remove_generated_tree(work)
                work.mkdir(parents=True)
                changelog = ROOT / load_repository_paradigm().release.changelog
                history = changelog.read_text(encoding="utf-8")
                payload |= qualify(
                    tag,
                    work=work,
                    platform=host,
                    changelog=history,
                    previous=previous,
                    classes_only=classes_only,
                    receipt=payload,
                )
                # Verified classes alone qualify nothing, so that run never reads as passed.
                payload["state"] = "classes_verified" if classes_only else "passed"
            finally:
                remove_generated_tree(work)
    except _STEP_FAILURES as error:
        failure = error
        payload["error"] = str(error)
    finally:
        payload["execution_events"] = events.as_posix()
        payload["generated_at"] = datetime.now(UTC).isoformat()
        rendered = json.dumps(payload, indent=2, sort_keys=True)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n", encoding="utf-8")
        session.log(rendered)
    if failure is not None:
        session.error(f"release journey failed for {tag} on {host}: {failure}")
