"""Immutable release artifact transition contracts."""

from __future__ import annotations

import hashlib
from datetime import UTC
from datetime import datetime
from functools import partial
from pathlib import Path

import pytest

import ethos.adapters.repo.runtime.materialization.dependency_supply as dependency_supply
import ethos.adapters.repo.runtime.transition as identity_transition
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.repository.release.admission import accepted_release_attestation
from ethos.repository.release.admission import accepted_release_identities
from ethos.repository.release.admission import accepted_release_identity
from ethos.repository.release.admission import checksum_bound_release
from ethos.repository.release.identity import BuildIdentity
from tests.support.governed_repository import init_git_repo

_BUILD_IDENTITY = BuildIdentity(
    "0.2.0-alpha.2",
    "0.2.0a2.dev0+gaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.tbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "a" * 40,
    "b" * 40,
)


def _wheel_case(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, content: bytes = b"wheel"):
    monkeypatch.setattr(identity_transition, "wheel_build_identity", lambda _wheel: _BUILD_IDENTITY)
    wheel = tmp_path / "ethos-test.whl"
    wheel.write_bytes(content)
    common = tmp_path / "repo.git"
    common.mkdir()
    monkeypatch.setattr(identity_transition, "git_common_dir", lambda _repo: common.as_posix())
    return tmp_path / "repo", wheel, common, hashlib.sha256(content).hexdigest()


def test_runtime_install_uses_a_durable_content_addressed_package_wheel(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo, volatile_wheel, common, wheel_sha256 = _wheel_case(tmp_path, monkeypatch)
    source = tmp_path / "source"
    (source / "a/b/c/d").mkdir(parents=True)
    (source / "pyproject.toml").write_text("[build-system]\n", encoding="utf-8")
    calls: list[tuple[str, tuple[str, ...], Path]] = []

    def record_runtime_tool(_source: Path, operation: str, *args: str, python: Path) -> None:
        calls.append((operation, args, python))

    monkeypatch.setattr(dependency_supply, "run_runtime_tool", record_runtime_tool)
    monkeypatch.setattr(dependency_supply, "project_dependency_supply", lambda *_args: None)
    materialize = partial(
        identity_transition.materialize_package_wheel,
        repo,
        volatile_wheel,
        expected_build=_BUILD_IDENTITY,
        collision="hook_runtime_wheel_digest_collision",
    )
    artifact = materialize()

    requirements = tmp_path / "work/locked-requirements.txt"
    requirements.parent.mkdir()
    requirements.write_text("locked\n", encoding="utf-8")
    dependency_supply.install_locked_runtime(
        source, tmp_path / "source-python", tmp_path / "python", artifact.path, requirements
    )
    durable = common / "ethos/packages" / wheel_sha256 / volatile_wheel.name
    assert calls[0][0] == "pip"
    assert {"sync", "--offline", "--break-system-packages", "--require-hashes"} < set(calls[0][1])
    assert Path(calls[0][1][-1]) == requirements
    assert calls[1][0] == "pip"
    assert {"install", "--offline", "--break-system-packages", "--no-deps"} < set(calls[1][1])
    assert Path(calls[1][1][-1]) == durable
    assert [python for _operation, _args, python in calls] == [
        tmp_path / "source-python",
        tmp_path / "source-python",
    ]
    assert durable.read_bytes() == b"wheel"
    durable.write_bytes(b"different")
    with pytest.raises(ValueError, match="hook_runtime_wheel_digest_collision"):
        materialize()
    durable.write_bytes(b"wheel")
    stale = _BUILD_IDENTITY._replace(source_commit="e" * 40)
    monkeypatch.setattr(
        identity_transition,
        "wheel_build_identity",
        lambda path: _BUILD_IDENTITY if path == volatile_wheel else stale,
    )
    with pytest.raises(ValueError, match="identity_transition_post_observation_mismatch"):
        materialize(collision="collision")
    monkeypatch.setattr(identity_transition, "wheel_build_identity", lambda _path: _BUILD_IDENTITY)
    with pytest.raises(ValueError, match="release_wheel_build_identity_stale"):
        materialize(expected_build=stale, collision="collision")
    volatile_wheel.unlink()


@pytest.mark.parametrize(
    "observation",
    ["match", "mismatch", "attestation", "raced", "rebound", "admission", "bound", "unlisted"],
)
def test_release_transition_attests_only_after_matching_post_observation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, observation: str
) -> None:
    build = _BUILD_IDENTITY._replace(distribution_version="0.2.0a2")
    release = accepted_release_identity(build, wheel_sha256=hashlib.sha256(b"wheel").hexdigest())
    wheel = tmp_path / "ethos-0.2.0a2-py3-none-any.whl"
    wheel.write_bytes(b"wheel")
    # Only these cases pass the release's checksum file, which lists the wheel or does not.
    bound = observation in {"bound", "rebound", "unlisted"}
    checksums = tmp_path / "SHA256SUMS" if bound else None
    if checksums:
        listed = "0" * 64 if observation == "unlisted" else release.wheel_sha256
        checksums.write_text(f"{listed}  {wheel.name}\n", encoding="ascii")
        if observation != "unlisted":
            release = checksum_bound_release(release, checksums.read_bytes(), published={})
    common = tmp_path / "repo.git"
    common.mkdir()
    events: list[str] = []
    monkeypatch.setattr(identity_transition, "wheel_build_identity", lambda _path: build)
    monkeypatch.setattr(identity_transition, "git_common_dir", lambda _repo: common.as_posix())
    prior = accepted_release_attestation(
        release._replace(build=build._replace(source_commit="e" * 40)),
        issued_at=datetime(2026, 8, 25, tzinfo=UTC),
    )
    monkeypatch.setattr(
        identity_transition,
        "read_attestation_set",
        lambda _repo: ("", (prior,) if observation == "admission" else ()),
    )
    monkeypatch.setattr(
        identity_transition,
        "_observe_release_wheel",
        lambda _path: (
            events.append("observe")
            or (
                release
                if observation != "mismatch"
                else release._replace(build=build._replace(source_commit="e" * 40))
            )
        ),
    )

    def write(path: Path, payload: bytes, **_kwargs: object) -> Path:
        events.append("effect")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        return path

    monkeypatch.setattr(identity_transition, "write_content_addressed", write)
    # In two cases another writer recorded this version first: with another wheel, or with
    # another checksum file.
    won = release
    if observation == "raced":
        won = release._replace(wheel_sha256="0" * 64)
    if observation == "rebound":
        other = f"{release.wheel_sha256}  other.whl\n".encode()
        won = checksum_bound_release(release, other, published={})
    attestation = accepted_release_attestation(won, issued_at=datetime(2026, 8, 25, tzinfo=UTC))
    monkeypatch.setattr(
        identity_transition,
        "record_attestation_once",
        lambda _repo, _attestation: (
            events.append("attest")
            or (
                attestation
                if observation != "attestation"
                else _attestation.model_copy(update={"predicate": "foreign"})
            )
        ),
    )

    transition = partial(
        identity_transition.materialize_explicit_release,
        tmp_path,
        wheel,
        expected_build=build,
        collision="wheel_collision",
        checksums=checksums,
    )
    if observation in {"match", "bound"}:
        assert transition() == release
        assert events == ["effect", "observe", "attest"]
    else:
        reason = {
            "attestation": "identity_transition_attestation_mismatch",
            "raced": "identity_transition_attestation_mismatch",
            "rebound": "identity_transition_attestation_mismatch",
            "admission": "accepted_version_source_conflict",
            "unlisted": "accepted_release_checksum_mismatch:ethos-0",
        }.get(observation, "identity_transition_post_observation_mismatch")
        with pytest.raises(ValueError, match=reason):
            transition()
        late = ["effect", "observe", "attest"]
        early = {"mismatch": ["effect", "observe"], "admission": [], "unlisted": []}
        assert events == early.get(observation, late)


def _release_case(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[BuildIdentity, Path, Path, Path]:
    """Build a repository, the release wheel a transition is to accept, and its checksum file."""
    build = _BUILD_IDENTITY._replace(distribution_version="0.2.0a2")
    wheel = tmp_path / "ethos-0.2.0a2-py3-none-any.whl"
    wheel.write_bytes(b"wheel")
    checksums = tmp_path / "SHA256SUMS"
    checksums.write_text(
        f"{hashlib.sha256(b'wheel').hexdigest()}  {wheel.name}\n", encoding="ascii"
    )
    monkeypatch.setattr(identity_transition, "wheel_build_identity", lambda _path: build)
    return build, init_git_repo(tmp_path / "repo"), wheel, checksums


@pytest.mark.parametrize("first", ["unbound", "bound"])
def test_a_version_accepted_again_with_or_without_its_checksum_file_keeps_its_record(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, first: str
) -> None:
    """Admission accepts a candidate that differs only in the binding, so the transition ends."""
    build, repo, wheel, checksums = _release_case(tmp_path, monkeypatch)
    accept = partial(
        identity_transition.materialize_explicit_release,
        repo,
        wheel,
        expected_build=build,
        collision="wheel_collision",
    )
    earlier, later = (None, checksums) if first == "unbound" else (checksums, None)
    recorded = accept(checksums=earlier)
    members = read_attestation_set(repo)[1]

    # Admission names that record before any effect, and says that the set holds it.
    admit = partial(identity_transition.admit_explicit_release, repo, wheel, expected_build=build)
    assert admit(checksums=later) == (recorded, True)
    # The version's one Attestation stands, and the transition returns the identity it records.
    assert accept(checksums=later) == recorded
    assert bool(recorded.checksums_sha256) is (first == "bound")
    assert read_attestation_set(repo)[1] == members
    assert accepted_release_identities(members) == (recorded,)


def test_a_record_that_another_writer_made_without_the_binding_refuses_the_transition(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The transition attests the identity it admitted, or it refuses: no record stands in."""
    build, repo, wheel, checksums = _release_case(tmp_path, monkeypatch)
    bare = accepted_release_identity(build, wheel_sha256=hashlib.sha256(b"wheel").hexdigest())
    won = accepted_release_attestation(bare, issued_at=datetime(2026, 8, 25, tzinfo=UTC))
    monkeypatch.setattr(identity_transition, "record_attestation_once", lambda *_args: won)
    with pytest.raises(ValueError, match="identity_transition_attestation_mismatch"):
        identity_transition.materialize_explicit_release(
            repo, wheel, expected_build=build, collision="wheel_collision", checksums=checksums
        )


def test_the_transition_stores_the_bytes_that_admission_hashed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A wheel that changes after it was hashed does not reach the store under that digest."""
    build, repo, wheel, _checksums = _release_case(tmp_path, monkeypatch)
    read = identity_transition.read_attestation_set
    # Admission reads the set after it hashed the wheel; the wheel changes at that moment.
    monkeypatch.setattr(
        identity_transition,
        "read_attestation_set",
        lambda root: (wheel.write_bytes(b"other"), read(root))[1],
    )
    recorded = identity_transition.materialize_explicit_release(
        repo, wheel, expected_build=build, collision="wheel_collision"
    )
    stored = repo / ".git/ethos/packages" / recorded.wheel_sha256 / wheel.name
    assert recorded.wheel_sha256 == hashlib.sha256(b"wheel").hexdigest()
    assert stored.read_bytes() == b"wheel"


def test_a_second_checksum_file_of_a_recorded_version_refuses_the_transition(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Two checksum files are two releases of one version: refused, and nothing is recorded."""
    build, repo, wheel, checksums = _release_case(tmp_path, monkeypatch)
    accept = partial(
        identity_transition.materialize_explicit_release,
        repo,
        wheel,
        expected_build=build,
        collision="wheel_collision",
    )
    accept(checksums=checksums)
    members = read_attestation_set(repo)[1]
    other = tmp_path / "OTHER"
    listed = checksums.read_text(encoding="ascii") + f"{'f' * 64}  extra.whl\n"
    other.write_text(listed, encoding="ascii")
    with pytest.raises(ValueError, match="accepted_version_artifact_conflict"):
        accept(checksums=other)
    assert read_attestation_set(repo)[1] == members
