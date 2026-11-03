"""Qualify one published prerelease on the declared adopter journey from its release assets alone.

The journey downloads the release's Mise declaration, its checksums and its platform's archive,
checks the archive against both and against its build attestation, and lets Mise install the
declared URL as an adopter's repository does. On fresh host stores it then proves a cold install,
host-store pinning, hook binding, status and uninstall; a full proof and status in a fixture
adopter; and an upgrade from the previous release with its rollback. Each leg writes one receipt
with the stage events beside it, whether the journey passes or fails.
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
from tools.ci.delivery.acceptance.host_environment import independent_host_environment
from tools.ci.delivery.acceptance.invocation import acceptance_observation
from tools.ci.delivery.acceptance.invocation import command_label
from tools.ci.delivery.acceptance.invocation import invoke
from tools.ci.delivery.acceptance.invocation import observe_stage
from tools.ci.delivery.distribution import install_archive
from tools.ci.delivery.distribution import prove_shared_supply
from tools.ci.toolchain.native import prepare_mise

if TYPE_CHECKING:
    import nox

    from ethos.adapters.repo.runtime.selection import SelectedRuntime

ROOT = Path(__file__).resolve().parents[4]
WORK = ROOT / "build/runtime/work/release-journey"
EVIDENCE = ROOT / "build/evidence/release-journey"
REPOSITORY = "HengYangDS/ethos"
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


def previous_version(changelog: str, version: str) -> str:
    """Name the release whose changelog entry follows this prerelease's entry."""
    versions = _ENTRY.findall(changelog)
    if version not in versions:
        message = f"release_journey_entry_missing:{version}"
        raise ValueError(message)
    later = versions[versions.index(version) + 1 :]
    if not later:
        message = f"release_journey_previous_missing:{version}"
        raise ValueError(message)
    return later[0]


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
    """Bind a signed fixture adopter to the runtime, then prove its full floor and read status."""
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
    code, status, detail = invoke(
        repo, (*prefix, "status", "--root", str(repo), "--json"), environment=environment
    )
    data = status.get("data")
    selected = data.get("hook_runtime") if isinstance(data, dict) else None
    if code or not isinstance(selected, dict) or selected.get("current") is not True:
        message = f"release_journey_status_failed:{detail}"
        raise RuntimeError(message)
    return {
        "state": "passed",
        "head": head,
        "proof": {"verdict": proof["verdict"], "state": proof.get("state")},
        "status": {"verdict": status.get("verdict"), "state": status.get("state")},
    }


@observe_stage("published_upgrade")
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


def qualify(tag: str, *, work: Path, platform: str, changelog: str) -> dict[str, object]:
    """Run every journey step on one published prerelease and return each step's result."""
    version = tag.removeprefix("v")
    previous = previous_version(changelog, version)
    with observe_stage("published_assets"):
        subject = download_release(tag, work / "assets" / version, platform=platform, attested=True)
        earlier = download_release(
            f"v{previous}", work / "assets" / previous, platform=platform, attested=False
        )
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
    installed = install_archive(
        earlier.archive,
        work / "previous",
        mise=prepare_mise(ROOT),
        environment=environment,
        declaration=earlier.declaration,
    ).installed
    generations = tuple((installed / "ethos/runtime").iterdir())
    if len(generations) != 1:
        message = "release_journey_previous_generation_ambiguous"
        raise ValueError(message)
    upgrade = prove_upgrade(
        pinned,
        require_installed_runtime(generations[0]),
        work / "upgrade",
        environment={**environment, "XDG_DATA_HOME": str(work / "upgrade/host-data")},
    )
    return {
        "tag": tag,
        "previous": f"v{previous}",
        "assets": {
            release.version: {"archive": release.archive.name, "sha256": release.sha256}
            for release in (subject, earlier)
        },
        "attestation_verified": subject.archive.name,
        "steps": {
            "cold_install_pinning_binding_and_uninstall": shared,
            "full_proof_and_status": full,
            "upgrade_and_rollback": upgrade,
        },
    }


def run(session: nox.Session, *, tag: str, evidence: Path | None = None, work: Path = WORK) -> None:
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
                changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
                payload |= qualify(tag, work=work, platform=host, changelog=changelog)
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
