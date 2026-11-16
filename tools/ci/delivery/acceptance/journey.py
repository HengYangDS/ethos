"""Qualify one published prerelease on the declared adopter journey from its release assets alone.

The journey has two stages, and each runs in its own fresh environment. Acquisition is the only
stage that reaches the network: it verifies the prerelease and its predecessors, proves each
release's exact GitHub pin and writes the manifest of the archives it verified. Qualification
reads that manifest alone. It checks its environment before its first child, hashes each archive
again before Mise installs it offline, and on fresh host stores proves a cold install, host-store
pinning, hook binding, status and uninstall; a full proof in a fixture adopter whose status then
guides it to a ready repository; and an upgrade from the previous release with its rollback. A
dispatch may name several earlier published releases to upgrade from instead; each upgrade and
rollback then runs in its own host store. Each leg writes one receipt with the stage events
beside it, whether the journey passes or fails.
"""

from __future__ import annotations

import json
import os
from datetime import UTC
from datetime import datetime
from functools import partial
from pathlib import Path
from subprocess import SubprocessError
from typing import TYPE_CHECKING

import tools.ci.delivery.acceptance.adopter as adopter_fixture
import tools.ci.delivery.acceptance.runtime as runtime_acceptance
from ethos.adapters.repo.runtime.interpreter import PYTHON_FLAGS
from ethos.adapters.repo.runtime.materialization.effect import remove_generated_tree
from ethos.adapters.repo.runtime.selection import require_installed_runtime
from ethos.adapters.repo.runtime.selection import require_selected_runtime
from ethos.adapters.toolchain.mise import mise_version
from ethos.contracts.digest import file_sha256
from ethos.contracts.paradigm.declaration import load_repository_paradigm
from tools.ci.delivery.acceptance.acquisition import PRERELEASE
from tools.ci.delivery.acceptance.acquisition import acquire
from tools.ci.delivery.acceptance.acquisition import read_manifest
from tools.ci.delivery.acceptance.host_environment import hermetic_environment
from tools.ci.delivery.acceptance.host_environment import hermetic_gap
from tools.ci.delivery.acceptance.host_environment import host_supply
from tools.ci.delivery.acceptance.invocation import acceptance_observation
from tools.ci.delivery.acceptance.invocation import continuation
from tools.ci.delivery.acceptance.invocation import invoke
from tools.ci.delivery.acceptance.invocation import observe_stage
from tools.ci.delivery.acceptance.invocation import run_native
from tools.ci.delivery.distribution import install_archive
from tools.ci.delivery.distribution import prove_installed_supply
from tools.ci.toolchain.native import mise_target
from tools.ci.toolchain.native import prepare_mise

if TYPE_CHECKING:
    from collections.abc import Callable

    from ethos.adapters.repo.runtime.selection import SelectedRuntime
    from tools.ci.delivery.acceptance.acquisition import PublishedRelease
    from tools.ci.delivery.mise_tool import InstalledTool
    from tools.ci.session import Session

ROOT = Path(__file__).resolve().parents[4]
WORK = ROOT / "build/runtime/work/release-journey"
EVIDENCE = ROOT / "build/evidence/release-journey"
# The adopter whose lane command creates the fixture's candidate branch.
_ACTOR = "agent:test:journey:adopter"
# What a journey child finds on its path. Acquisition also finds what reaches the network: the
# forge's client, and the downloader that stages Mise where the host's tool supply lacks it.
_EXECUTABLES, _CLIENTS = ("git", "ssh-keygen"), ("gh", "curl")
# Where the host's tool supply is: acquisition's process holds these while it prepares Mise.
_SUPPLY = (
    "ETHOS_CI_TOOL_CACHE_DIR",
    "ETHOS_CI_PERSISTENT_TOOL_CACHE_DIR",
    "ETHOS_CI_SUPPLY_MANIFEST",
)
# A failed step, download or verification; anything else still writes the receipt and propagates.
_STEP_FAILURES = (LookupError, OSError, RuntimeError, SubprocessError, TypeError, ValueError)


def _native(environment: dict[str, str]) -> Callable[..., str]:
    """Run native commands in the journey's environment; left to inherit, they lose Git's own."""

    def run(*command: str, cwd: Path = ROOT, env: dict[str, str] | None = None) -> str:
        return run_native(*command, cwd=cwd, env=env or environment)

    return run


@observe_stage("published_full_proof")
def prove_full(
    runtime: SelectedRuntime, work: Path, *, environment: dict[str, str]
) -> dict[str, object]:
    """Prove a signed fixture adopter's full floor, then follow its status to a ready repository.

    A new adopter has no candidate branch; its status names the command that creates one, and the
    journey runs that command before it requires a passing status.
    """
    repo, run = work / "proof-adopter", _native(environment)
    adopter_fixture.materialize_adopter(
        repo, openspec_config=ROOT / "openspec/config.yaml", run=run
    )
    run("git", "add", *adopter_fixture.declare_trust_registry(repo), cwd=repo)
    run("git", "commit", "--quiet", "-m", "chore: declare the trust floor", cwd=repo)
    head = run("git", "rev-parse", "HEAD", cwd=repo)
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
        retained,
        openspec_config=ROOT / "openspec/config.yaml",
        run=_native(environment),
        retained=True,
    )
    return runtime_acceptance.prove_retained_upgrade(
        successor, retained, predecessor=predecessor, environment=environment
    )


def install_acquired(
    release: PublishedRelease, home: Path, *, mise: Path, environment: dict[str, str]
) -> InstalledTool:
    """Hash an acquired archive again, then let Mise install it offline in a fresh home.

    Mise is given the manifest's digest as the archive's checksum, so bytes that change after
    this check are refused by Mise itself.
    """
    if file_sha256(release.archive) != release.sha256:
        message = f"release_journey_archive_tampered:{release.archive.name}"
        raise ValueError(message)
    return install_archive(
        release.archive, home, mise=mise, environment=environment, sha256=release.sha256
    )


def qualify_offline(
    manifest: Path, work: Path, *, mise: Path, environment: dict[str, str]
) -> dict[str, object]:
    """Run every journey step on the acquired releases, and return each step's result.

    The manifest is the stage's only input: nothing here reaches the forge.
    """
    subject, *earlier = read_manifest(manifest)
    install = partial(install_acquired, mise=mise, environment=environment)
    cold = work / "cold"
    with observe_stage("shared_supply"):
        tool = install(subject, cold / "package-manager")
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
            release, pinned, work, install=install, environment=environment
        )
        for release in earlier
    }
    return {
        "cold_install_pinning_binding_and_uninstall": shared,
        "full_proof_and_status": full,
        "upgrade_and_rollback": upgrades,
    }


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
    """Acquire one published prerelease, then run every journey step on it offline.

    The receipt is filled as the journey goes, so a failed leg keeps what it had established.
    With `classes_only` the journey stops once each named release is verified by its class.
    Acquisition's path holds no Mise, so the journey runs the executable whose digest the
    repository binds, from the host's tool supply, and never a Mise the host installed. Only
    that preparation is shown where the supply is. The job's forge token leaves the
    environment before either stage: acquisition hands it to the forge's client and to Mise's
    forge calls, and to no other child.
    """
    receipt = {} if receipt is None else receipt
    mise, token = None, os.environ.get("GH_TOKEN", "")
    supply = {name: os.environ[name] for name in _SUPPLY if name in os.environ}
    acquired, qualified = work / "acquisition", work / "qualification"
    clients = (*_EXECUTABLES, *_CLIENTS)
    with hermetic_environment(acquired / "environment", clients) as environment:
        if not classes_only:
            with host_supply(supply):
                mise = prepare_mise(ROOT)
            receipt["mise"] = ".".join(map(str, mise_version(mise) or ()))
        manifest = acquire(
            tag,
            acquired,
            platform=platform,
            changelog=changelog,
            previous=previous,
            receipt=receipt,
            environment=environment,
            token=token,
            mise=mise,
        )
    if mise is None:
        return receipt
    with hermetic_environment(qualified / "environment", _EXECUTABLES) as environment:
        if gap := hermetic_gap(qualified / "environment", _EXECUTABLES):
            message = f"journey_environment_not_hermetic:{gap}"
            raise RuntimeError(message)
        receipt["steps"] = qualify_offline(manifest, qualified, mise=mise, environment=environment)
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
    if PRERELEASE.fullmatch(tag) is None:
        session.error(f"release journey needs a published prerelease tag, not {tag!r}")
    host = mise_target()
    output = evidence if evidence is not None else EVIDENCE / f"journey-{host}.json"
    events = output.with_suffix(".events.jsonl")
    # The venue is where this leg ran: under a forge's runner, or on a local host. Any value of
    # `CI` reads as a runner, as the product's other readers of that input read it.
    venue = "ci" if os.environ.get("CI") else "local"
    payload: dict[str, object] = {"tag": tag, "platform": host, "venue": venue, "state": "failed"}
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
