"""Build and package-conformance effects for the locked project runtime."""

from __future__ import annotations

import argparse
import io
import shutil
import tarfile
import tempfile
from contextlib import contextmanager
from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import tools.ci.delivery.acceptance.effect as acceptance_effect
from ethos.adapters.mutation.proof import proof_for_repository_transition
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.release import accepted_release_source
from ethos.adapters.repo.runtime.source import build_input_identity
from ethos.adapters.repo.runtime.source import source_build_identity
from ethos.adapters.repo.runtime.transition import PackageArtifact
from ethos.adapters.repo.runtime.transition import materialize_package_wheel
from ethos.repository.release.identity import BuildIdentity
from ethos.repository.release.identity import build_identity
from ethos.repository.release.identity import build_identity_bytes

if TYPE_CHECKING:
    from collections.abc import Iterator

    import nox

    from tools.ci.toolchain.environment import ProjectRuntime


@dataclass(frozen=True, slots=True)
class DeliveryPipeline:
    """Own wheel materialization and its package-only acceptance sequence."""

    runtime: ProjectRuntime
    node_package_supply: Path

    @classmethod
    def from_runtime(cls, runtime: ProjectRuntime) -> DeliveryPipeline:
        """Bind delivery inputs only when a delivery operation is selected."""
        return cls(runtime, runtime.node_package_supply())

    def build(self, session: nox.Session, *, release_head: str = "") -> None:
        """Materialize exactly one offline wheel through Hatchling and uv."""
        work = self.runtime.root / "build/runtime/work"
        work.mkdir(parents=True, exist_ok=True)
        source = (
            release_build_source(self.runtime.root, work, head=release_head)
            if release_head
            else nullcontext(self.runtime.root)
        )
        with tempfile.TemporaryDirectory(prefix="ethos-wheel-build-", dir=work) as directory:
            staging = Path(directory)
            with source as prepared:
                expected = build_input_identity(prepared) if release_head else None
                session.run(
                    self.runtime.script("uv"),
                    "build",
                    "--offline",
                    "--no-build-isolation",
                    "--python",
                    str(self.runtime.python),
                    "--wheel",
                    "--out-dir",
                    str(staging),
                    "--no-create-gitignore",
                    *((str(prepared),) if release_head else ()),
                    env={"ETHOS_NODE_PACKAGE_SUPPLY": str(self.node_package_supply)},
                )
            if release_head:
                publish_built_wheel(
                    self.runtime.root,
                    staging,
                    self.runtime.root / "build/artifacts/release/python",
                    expected_build=expected,
                )
            else:
                publish_built_wheel(
                    self.runtime.root, staging, self.runtime.root / "build/artifacts/python"
                )

    def prove_install(self, session: nox.Session, *, release_head: str = "") -> None:
        """Exercise the explicitly selected candidate through the single package workload."""
        if release_head:
            artifact = prepare_release_candidate(self.runtime.root, release_head)
            acceptance_effect.run(
                session,
                artifact=artifact,
                evidence=self.runtime.root / "build/evidence/local-install/release-smoke.json",
            )
        else:
            acceptance_effect.run(session)

    def prove_host(self, session: nox.Session) -> None:
        """Run the complete package-only acceptance sequence on this host."""
        self.build(session)
        self.prove_install(session)
        session.run(
            str(self.runtime.python),
            "-m",
            "pytest",
            "-q",
            "tests/architecture/test_portable_toolchain.py",
        )


def publish_built_wheel(
    repo: Path, staging: Path, artifacts: Path, *, expected_build: BuildIdentity | None = None
) -> Path:
    """Admit and project exactly one wheel built from the current source identity."""
    wheels = tuple(path for path in staging.glob("ethos-*.whl") if path.is_file())
    if len(wheels) != 1:
        message = "release_wheel_output_invalid"
        raise ValueError(message)
    wheel = wheels[0]
    durable = materialize_package_wheel(
        repo,
        wheel,
        expected_build=expected_build or source_build_identity(repo),
        collision="release_wheel_digest_collision",
    )
    artifacts = artifacts.resolve()
    artifacts.parent.mkdir(parents=True, exist_ok=True)
    replacement = artifacts.parent / f".{artifacts.name}-replacement"
    backup = artifacts.parent / f".{artifacts.name}-previous"
    if replacement.exists():
        shutil.rmtree(replacement)
    replacement.mkdir()
    shutil.copy2(durable.path, replacement / wheel.name)
    if backup.exists():
        shutil.rmtree(backup)
    if artifacts.exists():
        artifacts.rename(backup)
    try:
        replacement.rename(artifacts)
    except OSError:
        if backup.exists() and not artifacts.exists():
            backup.rename(artifacts)
        raise
    finally:
        shutil.rmtree(replacement, ignore_errors=True)
    shutil.rmtree(backup, ignore_errors=True)
    return artifacts / wheel.name


def prepare_release_candidate(repo: Path, head: str) -> PackageArtifact:
    """Select exact accepted-source release bytes without accepting or publishing a release."""
    expected = _release_source_identity(repo, head)
    wheels = tuple((repo / "build/artifacts/release/python").glob("ethos-*.whl"))
    if len(wheels) != 1 or wheels[0].is_symlink() or not wheels[0].is_file():
        message = "release_wheel_output_invalid"
        raise ValueError(message)
    return materialize_package_wheel(
        repo, wheels[0], expected_build=expected, collision="release_wheel_digest_collision"
    )


def release_build_head(arguments: tuple[str, ...]) -> str:
    """Parse explicit Nox build inputs without allowing ambient release promotion."""
    if not arguments:
        return ""
    parser = argparse.ArgumentParser(add_help=False, exit_on_error=False)
    parser.add_argument("--release", action="store_true")
    parser.add_argument("--expect-head")
    try:
        options, unknown = parser.parse_known_args(arguments)
    except argparse.ArgumentError as error:
        message = "release_build_arguments_invalid"
        raise ValueError(message) from error
    head = options.expect_head or ""
    if (
        unknown
        or not options.release
        or len(head) not in (40, 64)
        or set(head) - set("0123456789abcdef")
    ):
        message = "release_build_arguments_invalid"
        raise ValueError(message)

    return head


def _release_source_identity(repo: Path, head: str) -> BuildIdentity:
    """Require a clean exact accepted source and its applicable repository proof."""
    source = source_build_identity(repo)
    if source.source_commit != head:
        message = "release_build_source_stale"
        raise ValueError(message)
    if source != source_build_identity(repo, include_overlay=False):
        message = "release_build_source_dirty"
        raise ValueError(message)
    accepted_release_source(repo, head)
    proof, gaps = proof_for_repository_transition(repo, head)
    if proof is None or gaps:
        raise ValueError(gaps[0] if gaps else "release_source_not_proven")
    return build_identity(
        product=source.product_version,
        source_commit=head,
        source_tree=source.source_tree,
        release=True,
    )


@contextmanager
def release_build_source(repo: Path, work: Path, *, head: str) -> Iterator[Path]:
    """Project admitted Git bytes and release identity into one disposable build source."""
    identity = _release_source_identity(repo, head)
    work.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ethos-release-source-", dir=work) as directory:
        prepared = Path(directory)
        archive = run_git(repo, "archive", "--format=tar", head, text=False, timeout=30).stdout
        with tarfile.open(fileobj=io.BytesIO(archive)) as packed:
            packed.extractall(prepared, filter="data")
        carried = prepared / "src/ethos/data/build/identity.json"
        carried.parent.mkdir(parents=True, exist_ok=True)
        carried.write_bytes(build_identity_bytes(identity))
        yield prepared
        if _release_source_identity(repo, head) != identity:
            message = "release_build_source_changed"
            raise ValueError(message)
