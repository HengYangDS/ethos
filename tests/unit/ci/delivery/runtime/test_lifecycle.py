"""Installed acceptance observes and retires one complete runtime lifecycle."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.repository.release.identity import BuildIdentity
from tools.ci.delivery.acceptance import effect
from tools.ci.delivery.acceptance import receipt

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_one_acceptance_effect_observes_the_complete_runtime_lifecycle(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    bootstrap_environment = tmp_path / "bootstrap-environment"
    bootstrap_repository = tmp_path / "bootstrap-repository"
    repository = tmp_path / "adopter"
    for directory in (bootstrap_environment, bootstrap_repository, repository):
        directory.mkdir()
    (bootstrap_environment / "owned.txt").write_text("owned\n", encoding="utf-8")
    (bootstrap_repository / "owned.txt").write_text("owned\n", encoding="utf-8")

    events: list[str] = []
    bootstrap_python = tmp_path / "bootstrap-runtime/python/bin/python"
    runtime_python = tmp_path / "adopter-runtime/python/bin/python"
    bootstrap_report, successor_report = (
        {
            "runtime_digest": digit * 64,
            "wheel_sha256": "c" * 64,
            "source_commit": "a" * 40,
            "source_tree": "b" * 40,
        }
        for digit in ("1", "2")
    )
    successor_report["hooks_path"] = (tmp_path / "hooks").as_posix()

    def require_manifest(report, *_args, **_kwargs):
        stage = "bootstrap_manifest" if report is bootstrap_report else "successor_manifest"
        events.append(stage)
        return bootstrap_python if report is bootstrap_report else runtime_python

    monkeypatch.setattr(effect.runtime_acceptance, "require_manifest", require_manifest)
    declarations = (
        (effect.adopter_fixture, "materialize_bootstrap_repository", None),
        (effect.adopter_fixture, "prepare_acceptance_topology", tmp_path / "candidate"),
        (effect.runtime_acceptance, "activate_from_entrypoint", bootstrap_report),
        (effect.runtime_acceptance, "activate_from_runtime", successor_report),
        (effect.runtime_acceptance, "require_production_dependencies", {"state": "passed"}),
        (effect.runtime_acceptance, "require_version_identity", {"state": "passed"}),
        (effect.runtime_acceptance, "prove_repair", {"state": "passed"}),
        (effect.lane_acceptance, "prove_signature_repair", {"state": "passed"}),
        (
            effect.lane_acceptance,
            "prove_lifecycle",
            {
                stage: {"state": "passed"}
                for stage in ("lane_bootstrap", "retirement_recovery", "native_merge")
            },
        ),
    )
    for owner, method, result in declarations:
        monkeypatch.setattr(
            owner,
            method,
            lambda *_args, stage=method, result=result, **_kwargs: events.append(stage) or result,
        )

    lifecycle = effect.observe_runtime_lifecycle(
        installed_ethos=tmp_path / "wheel-environment/bin/ethos",
        bootstrap_environment=bootstrap_environment,
        bootstrap_repository=bootstrap_repository,
        repository=repository,
        build=BuildIdentity("0.2.0-alpha.3", "0.2.0a3.dev0+ga.ta", "a" * 40, "b" * 40),
        wheel_sha256="c" * 64,
        environment={},
    )

    expected = [method for _owner, method, _result in declarations]
    expected.insert(expected.index("activate_from_entrypoint") + 1, "bootstrap_manifest")
    expected.insert(expected.index("activate_from_runtime") + 1, "successor_manifest")
    assert events == expected
    assert set(lifecycle) == receipt.REQUIRED_LIFECYCLE_STAGES
    assert all(observation["state"] == "passed" for observation in lifecycle.values())
    assert not bootstrap_environment.exists()
    assert not bootstrap_repository.exists()
