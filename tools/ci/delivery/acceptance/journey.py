"""Qualify one published prerelease on the declared adopter journey from its release assets alone.

The journey downloads the release's Mise declaration, its checksums and its platform's archive,
checks the archive against both and against its build attestation, and lets Mise install the
declared URL as an adopter's repository does. On fresh host stores it then proves a cold install,
host-store pinning, hook binding, status and uninstall; a full proof in a fixture adopter whose
status then guides it to a ready repository; and an upgrade from the previous release with its
rollback. A dispatch may name several earlier published releases to upgrade from instead; each
upgrade and rollback then runs in its own host store. Each leg writes one receipt with the stage
events beside it, whether the journey passes or fails.
"""

from __future__ import annotations

import hashlib
import json
import platform
import re
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from pathlib import Path
from subprocess import SubprocessError
from typing import TYPE_CHECKING

import tools.ci.delivery.acceptance.adopter as adopter_fixture
import tools.ci.delivery.acceptance.runtime as runtime_acceptance
from ethos.adapters.process import run_command
from ethos.adapters.repo.runtime.interpreter import PYTHON_FLAGS
from ethos.adapters.repo.runtime.materialization.effect import remove_generated_tree
from ethos.adapters.repo.runtime.selection import require_installed_runtime
from ethos.adapters.repo.runtime.selection import require_selected_runtime
from ethos.contracts.paradigm.declaration import load_repository_paradigm
from tools.ci.delivery.acceptance.host_environment import independent_host_environment
from tools.ci.delivery.acceptance.invocation import acceptance_observation
from tools.ci.delivery.acceptance.invocation import command_label
from tools.ci.delivery.acceptance.invocation import continuation
from tools.ci.delivery.acceptance.invocation import invoke
from tools.ci.delivery.acceptance.invocation import observe_stage
from tools.ci.delivery.distribution import install_archive
from tools.ci.delivery.distribution import prove_shared_supply
from tools.ci.toolchain.native import prepare_mise

if TYPE_CHECKING:
    from collections.abc import Callable

    import nox

    from ethos.adapters.repo.runtime.selection import SelectedRuntime

ROOT = Path(__file__).resolve().parents[4]
WORK = ROOT / "build/runtime/work/release-journey"
EVIDENCE = ROOT / "build/evidence/release-journey"
REPOSITORY = "HengYangDS/ethos"
# The adopter whose lane command creates the fixture's candidate branch.
_ACTOR = "agent:test:journey:adopter"
_ENTRY = re.compile(r"^## \[([^\]]+)\] - ", re.MULTILINE)
_PRERELEASE = re.compile(r"v\d+\.\d+\.\d+-(?:alpha|beta|rc)\.\d+")
_SYSTEMS = {"darwin": "macos", "linux": "linux"}
_MACHINES = {"arm64": "arm64", "aarch64": "arm64", "x86_64": "x64"}
# A failed step, download or verification; anything else still writes the receipt and propagates.
_STEP_FAILURES = (LookupError, OSError, RuntimeError, SubprocessError, TypeError, ValueError)


@dataclass(frozen=True, slots=True)
class PublishedRelease:
    """One release's verified platform archive and the Mise declaration that names it."""

    version: str
    declaration: str
    archive: Path
    sha256: str


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
            REPOSITORY,
            "--json",
            "tagName",
            failure=f"release_journey_release_lookup_failed:v{version}",
        )
    except ValueError as error:
        if "release not found" in str(error):
            return False
        raise
    return True


def host_platform() -> str:
    """Name this host as the release names its archives."""
    system, machine = platform.system().lower(), platform.machine().lower()
    if system not in _SYSTEMS or machine not in _MACHINES:
        message = f"release_journey_platform_unsupported:{system}-{machine}"
        raise RuntimeError(message)
    return f"{_SYSTEMS[system]}-{_MACHINES[machine]}"


def _gh(*arguments: str, failure: str) -> None:
    with observe_stage(command_label(("gh", *arguments)), kind="process"):
        completed = run_command(ROOT, ("gh", *arguments), timeout=600)
    if completed.returncode:
        detail = (completed.stderr.strip() or completed.stdout.strip())[-2000:]
        message = f"{failure}:{detail}"
        raise ValueError(message)


def download_release(tag: str, target: Path, *, platform: str, attested: bool) -> PublishedRelease:
    """Download one release's assets for this platform and verify them before any install."""
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
        REPOSITORY,
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
    if attested:
        _gh(
            "attestation",
            "verify",
            str(archive),
            "--repo",
            REPOSITORY,
            failure=f"release_journey_attestation_failed:{name}",
        )
    return PublishedRelease(version, text, archive, digest)


def _run(*command: str, cwd: Path = ROOT, env: dict[str, str] | None = None) -> str:
    with observe_stage(command_label(command), kind="process", target=cwd.name):
        completed = run_command(
            cwd, command, env=env, inherit_environment=env is None, remove_env_prefixes=("GIT_",)
        )
    if completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip()
        message = f"command failed ({completed.returncode}): {' '.join(command)}\n{detail}"
        raise RuntimeError(message)
    return completed.stdout.strip()


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
        repo, openspec_config=ROOT / "openspec/config.yaml", run=_run
    )
    _run("git", "add", *adopter_fixture.declare_trust_registry(repo), cwd=repo)
    _run("git", "commit", "--quiet", "-m", "chore: declare the trust floor", cwd=repo)
    head = _run("git", "rev-parse", "HEAD", cwd=repo)
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
    environment: dict[str, str],
) -> dict[str, object]:
    """Install one predecessor, then prove the upgrade from it and its rollback in its own store."""
    installed = install_archive(
        release.archive,
        work / "previous" / release.version,
        mise=prepare_mise(ROOT),
        environment=environment,
        declaration=release.declaration,
    ).installed
    generations = tuple((installed / "ethos/runtime").iterdir())
    if len(generations) != 1:
        message = f"release_journey_previous_generation_ambiguous:v{release.version}"
        raise ValueError(message)
    store = work / "upgrade" / release.version
    return prove_upgrade(
        successor,
        require_installed_runtime(generations[0]),
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
        retained, openspec_config=ROOT / "openspec/config.yaml", run=_run, retained=True
    )
    return runtime_acceptance.prove_retained_upgrade(
        successor, retained, predecessor=predecessor, environment=environment
    )


def qualify(
    tag: str, *, work: Path, platform: str, changelog: str, previous: tuple[str, ...] = ()
) -> dict[str, object]:
    """Run every journey step on one published prerelease and return each step's result."""
    version = tag.removeprefix("v")
    skipped: tuple[str, ...] = ()
    if previous:
        predecessors = named_predecessors(changelog, version, previous, published=release_published)
    else:
        latest, skipped = previous_version(changelog, version, published=release_published)
        predecessors = (latest,)
    with observe_stage("published_assets"):
        subject = download_release(tag, work / "assets" / version, platform=platform, attested=True)
        earlier = [
            download_release(f"v{name}", work / "assets" / name, platform=platform, attested=False)
            for name in predecessors
        ]
    environment = independent_host_environment()[0]
    cold = work / "cold"
    # Installs through Mise, pins in the host store, binds repositories, reads status, uninstalls.
    shared = prove_shared_supply(
        subject.archive, cold, environment=environment, root=ROOT, declaration=subject.declaration
    )
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
        f"v{release.version}": upgrade_from(release, pinned, work, environment=environment)
        for release in earlier
    }
    return {
        "tag": tag,
        "previous": [f"v{name}" for name in predecessors],
        "previous_named": bool(previous),
        "skipped_unpublished": [f"v{name}" for name in skipped],
        "assets": {
            release.version: {"archive": release.archive.name, "sha256": release.sha256}
            for release in (subject, *earlier)
        },
        "attestation_verified": subject.archive.name,
        "steps": {
            "cold_install_pinning_binding_and_uninstall": shared,
            "full_proof_and_status": full,
            "upgrade_and_rollback": upgrades,
        },
    }


def run(
    session: nox.Session,
    *,
    tag: str,
    previous: tuple[str, ...] = (),
    evidence: Path | None = None,
    work: Path = WORK,
) -> None:
    """Qualify the tag on this host and keep its receipt and stage events, passing or not."""
    if _PRERELEASE.fullmatch(tag) is None:
        session.error(f"release journey needs a published prerelease tag, not {tag!r}")
    host = host_platform()
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
                    tag, work=work, platform=host, changelog=history, previous=previous
                )
                payload["state"] = "passed"
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
