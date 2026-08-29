"""Immutable release artifact transition contracts."""

from __future__ import annotations

import hashlib
from datetime import UTC
from datetime import datetime
from pathlib import Path

import pytest

import ethos.adapters.repo.runtime.materialization.python_image as python_image
import ethos.adapters.repo.runtime.transition as identity_transition
from ethos.repository.release.admission import accepted_release_attestation
from ethos.repository.release.admission import accepted_release_identity
from ethos.repository.release.identity import BuildIdentity

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
    calls: list[tuple[str, tuple[str, ...]]] = []
    monkeypatch.setattr(
        python_image,
        "run_runtime_tool",
        lambda _source, operation, *args: calls.append((operation, args)),
    )
    artifact = identity_transition.materialize_package_wheel(
        repo,
        volatile_wheel,
        expected_build=_BUILD_IDENTITY,
        collision="hook_runtime_wheel_digest_collision",
    )

    requirements = tmp_path / "work/locked-requirements.txt"
    requirements.parent.mkdir()
    requirements.write_text("locked\n", encoding="utf-8")
    python_image.install_locked_runtime(
        source,
        tmp_path / "python",
        artifact.path,
        requirements,
    )
    durable = common / "ethos/packages" / wheel_sha256 / volatile_wheel.name
    assert calls[0][0] == "pip"
    assert {"sync", "--offline", "--break-system-packages", "--require-hashes"} < set(calls[0][1])
    assert Path(calls[0][1][-1]) == requirements
    assert calls[1][0] == "pip"
    assert {"install", "--offline", "--break-system-packages", "--no-deps"} < set(calls[1][1])
    assert Path(calls[1][1][-1]) == durable
    assert durable.read_bytes() == b"wheel"
    durable.write_bytes(b"different")
    with pytest.raises(ValueError, match="hook_runtime_wheel_digest_collision"):
        identity_transition.materialize_package_wheel(
            repo,
            volatile_wheel,
            expected_build=_BUILD_IDENTITY,
            collision="hook_runtime_wheel_digest_collision",
        )
    durable.write_bytes(b"wheel")
    stale = _BUILD_IDENTITY._replace(source_commit="e" * 40)
    monkeypatch.setattr(
        identity_transition,
        "wheel_build_identity",
        lambda path: _BUILD_IDENTITY if path == volatile_wheel else stale,
    )
    with pytest.raises(ValueError, match="identity_transition_post_observation_mismatch"):
        identity_transition.materialize_package_wheel(
            repo, volatile_wheel, expected_build=_BUILD_IDENTITY, collision="collision"
        )
    monkeypatch.setattr(identity_transition, "wheel_build_identity", lambda _path: _BUILD_IDENTITY)
    with pytest.raises(ValueError, match="release_wheel_build_identity_stale"):
        identity_transition.materialize_package_wheel(
            repo, volatile_wheel, expected_build=stale, collision="collision"
        )
    volatile_wheel.unlink()


@pytest.mark.parametrize("observation", ["match", "mismatch", "attestation", "admission"])
def test_release_transition_attests_only_after_matching_post_observation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    observation: str,
) -> None:
    build = _BUILD_IDENTITY._replace(distribution_version="0.2.0a2")
    release = accepted_release_identity(build, wheel_sha256=hashlib.sha256(b"wheel").hexdigest())
    wheel = tmp_path / "ethos-0.2.0a2-py3-none-any.whl"
    wheel.write_bytes(b"wheel")
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
                if observation in {"match", "attestation"}
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
    attestation = accepted_release_attestation(
        release,
        issued_at=datetime(2026, 8, 25, tzinfo=UTC),
    )
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

    if observation == "match":
        identity_transition.materialize_explicit_release(
            tmp_path, wheel, expected_build=build, collision="wheel_collision"
        )
        assert events == ["effect", "observe", "attest"]
    else:
        reason = {
            "attestation": "identity_transition_attestation_mismatch",
            "admission": "accepted_version_source_conflict",
        }.get(observation, "identity_transition_post_observation_mismatch")

        def transition() -> None:
            identity_transition.materialize_explicit_release(
                tmp_path, wheel, expected_build=build, collision="wheel_collision"
            )

        with pytest.raises(ValueError, match=reason):
            transition()
        expected = {"attestation": ["effect", "observe", "attest"], "admission": []}
        assert events == expected.get(observation, ["effect", "observe"])


def test_accepted_release_activation_requires_attestation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    release = accepted_release_identity(
        _BUILD_IDENTITY._replace(distribution_version="0.2.0a2"),
        wheel_sha256="c" * 64,
    )
    monkeypatch.setattr(identity_transition, "read_attestation_set", lambda _repo: ("", ()))
    identity_transition.require_release_identity_attested(Path(), None)
    with pytest.raises(ValueError, match="accepted_release_identity_unattested"):
        identity_transition.require_release_identity_attested(Path(), release)
