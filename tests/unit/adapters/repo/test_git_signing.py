from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.repo.git_signing as git_signing

if TYPE_CHECKING:
    from pathlib import Path


def test_commit_environment_has_no_projection_without_repository_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        git_signing,
        "run_git",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 1, "", ""),
    )

    assert git_signing.commit_environment(tmp_path, None) is None
    assert git_signing.commit_environment(tmp_path, {"LANG": "C"}) == {"LANG": "C"}


@pytest.mark.parametrize("key_text", [None, "not-an-ssh-key\n"])
def test_commit_environment_rejects_invalid_repository_key(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    key_text: str | None,
) -> None:
    key = tmp_path / "signing-key.pub"
    if key_text is not None:
        key.write_text(key_text, encoding="utf-8")
    monkeypatch.setattr(
        git_signing,
        "run_git",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, f"{key}\n", ""),
    )

    with pytest.raises(ValueError, match="git_effect_signing_key_invalid"):
        git_signing.commit_environment(tmp_path, None)


def test_commit_environment_rejects_invalid_signing_program(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    key = tmp_path / "signing-key.pub"
    key.write_text("ssh-ed25519 AAAATEST key\n", encoding="utf-8")
    monkeypatch.setattr(
        git_signing,
        "run_git",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, f"{key}\n", ""),
    )
    monkeypatch.setattr(
        git_signing,
        "_config",
        lambda *_args: "relative-signer",
    )

    with pytest.raises(ValueError, match="git_effect_signing_program_invalid"):
        git_signing.commit_environment(tmp_path, None)


def test_create_git_commit_rejects_unknown_signing_policy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        git_signing,
        "_config",
        lambda *_args: "sometimes",
    )

    with pytest.raises(ValueError, match="git_effect_commit_signing_policy_invalid"):
        git_signing.create_git_commit(
            tmp_path,
            tree="a" * 40,
            parent="b" * 40,
            message="test: exact subject",
        )
