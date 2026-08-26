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
    product_version="0.2.0-alpha.1",
    distribution_version="0.2.0a1.dev0+gaaaaaaaaaaaa.tbbbbbbbbbbbb",
    source_commit="a" * 40,
    source_tree="b" * 40,
    channel="development",
    acceptance_state="unaccepted",
)


def _bind_build_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        identity_transition,
        "wheel_build_identity",
        lambda _wheel: _BUILD_IDENTITY,
    )


def test_runtime_install_uses_a_durable_content_addressed_release_wheel(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _bind_build_identity(monkeypatch)
    source = tmp_path / "source"
    (source / "a/b/c/d").mkdir(parents=True)
    (source / "pyproject.toml").write_text("[build-system]\n", encoding="utf-8")
    volatile_wheel = tmp_path / "volatile/ethos-test.whl"
    volatile_wheel.parent.mkdir()
    volatile_wheel.write_bytes(b"wheel")
    wheel_sha256 = hashlib.sha256(b"wheel").hexdigest()
    common = tmp_path / "repo.git"
    common.mkdir()
    calls: list[tuple[str, tuple[str, ...]]] = []
    monkeypatch.setattr(identity_transition, "git_common_dir", lambda _repo: common.as_posix())
    monkeypatch.setattr(
        python_image,
        "run_runtime_tool",
        lambda _source, operation, *args: calls.append((operation, args)),
    )
    artifact = identity_transition.materialize_release_wheel(
        tmp_path / "repo",
        volatile_wheel,
        expected_build=_BUILD_IDENTITY,
        collision="hook_runtime_wheel_digest_collision",
    )

    python_image.install_locked_runtime(
        source,
        tmp_path / "work",
        tmp_path / "python",
        artifact.path,
    )
    volatile_wheel.unlink()

    durable = common / "ethos/packages" / wheel_sha256 / volatile_wheel.name
    assert calls[0][1][:4] == ("--locked", "--offline", "--no-dev", "--no-emit-project")
    assert calls[1][0] == "pip"
    assert {"sync", "--offline", "--break-system-packages", "--require-hashes"} < set(calls[1][1])
    assert calls[2][0] == "pip"
    assert {"install", "--offline", "--break-system-packages", "--no-deps"} < set(calls[2][1])
    assert Path(calls[2][1][-1]) == durable
    assert durable.read_bytes() == b"wheel"


def test_runtime_install_rejects_a_durable_wheel_digest_collision(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _bind_build_identity(monkeypatch)
    wheel = tmp_path / "ethos-test.whl"
    wheel.write_bytes(b"wheel")
    wheel_sha256 = hashlib.sha256(b"wheel").hexdigest()
    common = tmp_path / "repo.git"
    durable = common / "ethos/packages" / wheel_sha256 / wheel.name
    durable.parent.mkdir(parents=True)
    durable.write_bytes(b"different")
    monkeypatch.setattr(identity_transition, "git_common_dir", lambda _repo: common.as_posix())

    with pytest.raises(ValueError, match="hook_runtime_wheel_digest_collision"):
        identity_transition.materialize_release_wheel(
            tmp_path / "repo",
            wheel,
            expected_build=_BUILD_IDENTITY,
            collision="hook_runtime_wheel_digest_collision",
        )


@pytest.mark.parametrize("observation", ["match", "mismatch"])
def test_release_transition_attests_only_after_matching_post_observation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    observation: str,
) -> None:
    build = _BUILD_IDENTITY._replace(
        distribution_version="0.2.0a1",
        channel="accepted",
        acceptance_state="accepted",
    )
    release = accepted_release_identity(build, wheel_sha256=hashlib.sha256(b"wheel").hexdigest())
    wheel = tmp_path / "ethos-0.2.0a1-py3-none-any.whl"
    wheel.write_bytes(b"wheel")
    common = tmp_path / "repo.git"
    common.mkdir()
    events: list[str] = []
    monkeypatch.setattr(identity_transition, "wheel_build_identity", lambda _path: build)
    monkeypatch.setattr(identity_transition, "git_common_dir", lambda _repo: common.as_posix())
    monkeypatch.setattr(identity_transition, "read_attestation_set", lambda _repo: ("", ()))
    monkeypatch.setattr(
        identity_transition,
        "_observe_release_wheel",
        lambda _path: (
            events.append("observe")
            or (
                release
                if observation == "match"
                else release._replace(build=build._replace(source_commit="e" * 40))
            )
        ),
    )
    monkeypatch.setattr(
        identity_transition,
        "write_content_addressed",
        lambda path, _payload, **_kwargs: events.append("effect") or path,
    )
    attestation = accepted_release_attestation(
        release,
        issued_at=datetime(2026, 8, 25, tzinfo=UTC),
    )
    monkeypatch.setattr(
        identity_transition,
        "record_attestation_once",
        lambda _repo, _attestation: events.append("attest") or attestation,
    )

    if observation == "match":
        identity_transition.materialize_release_wheel(
            tmp_path,
            wheel,
            expected_build=build,
            collision="wheel_collision",
        )
        assert events == ["effect", "observe", "attest"]
    else:
        with pytest.raises(ValueError, match="identity_transition_post_observation_mismatch"):
            identity_transition.materialize_release_wheel(
                tmp_path,
                wheel,
                expected_build=build,
                collision="wheel_collision",
            )
        assert events == ["effect", "observe"]
