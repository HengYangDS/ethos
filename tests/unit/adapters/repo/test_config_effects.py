"""Tests for the concrete semantic owner named by this module path."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.repo.config_effects as config_effects

if TYPE_CHECKING:
    from pathlib import Path


def test_config_effect_failures_report_the_exact_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    failure = subprocess.CompletedProcess([], 2, "", "config failed")
    monkeypatch.setattr(config_effects, "run_git", lambda *_args, **_kwargs: failure)
    with pytest.raises(ValueError, match="config failed"):
        config_effects.config_values(tmp_path, ("core.hooksPath",), scope="local")
    with pytest.raises(ValueError, match="config failed"):
        config_effects.replace_config_values(tmp_path, {"core.hooksPath": ()}, scope="local")


def test_local_config_uses_repository_identity_without_acceptance_commitment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, object] = {}
    monkeypatch.setattr(config_effects, "_values", lambda *_args, **_kwargs: {"key": "value"})
    monkeypatch.setattr(config_effects, "repository_identity", lambda _root: "repository:test")
    monkeypatch.setattr(
        config_effects,
        "issue_native_effect",
        lambda *_args, **kwargs: captured.update(kwargs) or object(),
    )

    config_effects.set_local_config(tmp_path, {"key": "value"})

    assert captured["commitment_digest"] is None
    assert captured["repository_id"] == "repository:test"
