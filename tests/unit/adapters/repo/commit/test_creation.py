from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.repo.commit.creation as creation
from ethos.repository.policy.commit import CommitPolicy

if TYPE_CHECKING:
    from pathlib import Path


def test_commit_environment_rejects_missing_repository_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        creation,
        "run_git",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 1, "", ""),
    )

    with pytest.raises(ValueError, match="git_effect_signing_key_invalid"):
        creation.commit_environment(tmp_path, None)


def test_commit_environment_projects_the_required_signing_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    key = tmp_path / "signing-key.pub"
    key.write_text("ssh-ed25519 AAAATEST key\n", encoding="utf-8")
    monkeypatch.setattr(
        creation,
        "run_git",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, f"{key}\n", ""),
    )
    monkeypatch.setattr(creation, "_config", lambda *_args: "")

    assert creation.commit_environment(tmp_path, None) == {
        "GIT_CONFIG_COUNT": "3",
        "GIT_CONFIG_KEY_0": "commit.gpgSign",
        "GIT_CONFIG_VALUE_0": "true",
        "GIT_CONFIG_KEY_1": "gpg.format",
        "GIT_CONFIG_VALUE_1": "ssh",
        "GIT_CONFIG_KEY_2": "user.signingkey",
        "GIT_CONFIG_VALUE_2": "key::ssh-ed25519 AAAATEST key",
    }


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
        creation,
        "run_git",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, f"{key}\n", ""),
    )

    with pytest.raises(ValueError, match="git_effect_signing_key_invalid"):
        creation.commit_environment(tmp_path, None)


def test_commit_environment_rejects_invalid_signing_program(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    key = tmp_path / "signing-key.pub"
    key.write_text("ssh-ed25519 AAAATEST key\n", encoding="utf-8")
    monkeypatch.setattr(
        creation,
        "run_git",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, f"{key}\n", ""),
    )
    monkeypatch.setattr(
        creation,
        "_config",
        lambda *_args: "relative-signer",
    )

    with pytest.raises(ValueError, match="git_effect_signing_program_invalid"):
        creation.commit_environment(tmp_path, None)


def test_create_git_commit_uses_tracked_signing_when_ambient_git_disables_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[tuple[str, ...], dict[str, object]]] = []
    monkeypatch.setattr(
        creation,
        "load_commit_policy",
        lambda _root: CommitPolicy(
            subject_pattern=r"^fix: .+",
            signing_required=True,
            signing_format="ssh",
        ),
        raising=False,
    )
    monkeypatch.setattr(
        creation,
        "_config",
        lambda _root, name: "false" if name == "commit.gpgsign" else "",
    )
    monkeypatch.setattr(
        creation,
        "commit_environment",
        lambda _root, environment: dict(environment or {}) | {"POLICY_SIGNER": "1"},
    )
    monkeypatch.setattr(
        creation,
        "commit_policy_report",
        lambda *_args, **_kwargs: {"required_gaps": []},
    )

    def runner(_root: Path, *args: str, **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(args, 0, "c" * 40 + "\n", "")

    completed = creation.create_git_commit(
        tmp_path,
        tree="a" * 40,
        parent="b" * 40,
        message="fix: exact subject",
        runner=runner,
    )

    assert completed.returncode == 0
    assert "-S" in calls[0][0]
    assert calls[0][1]["env"] == {"POLICY_SIGNER": "1"}


def test_create_git_commit_does_not_promote_ambient_signing_to_policy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[str, ...]] = []
    monkeypatch.setattr(creation, "load_commit_policy", lambda _root: None, raising=False)
    monkeypatch.setattr(creation, "_config", lambda *_args: "true")
    monkeypatch.setattr(creation, "commit_environment", lambda *_args: {"IGNORED": "1"})

    def runner(_root: Path, *args: str, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, "c" * 40 + "\n", "")

    completed = creation.create_git_commit(
        tmp_path,
        tree="a" * 40,
        parent="b" * 40,
        message="unconstrained subject",
        runner=runner,
    )

    assert completed.returncode == 0
    assert "-S" not in calls[0]


def test_create_git_commit_rejects_subject_before_git_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        creation,
        "load_commit_policy",
        lambda _root: CommitPolicy(
            subject_pattern=r"^fix: .+",
            signing_required=False,
            signing_format="ssh",
        ),
        raising=False,
    )

    with pytest.raises(ValueError, match="commit_subject_invalid:bootstrap Commitment v2"):
        creation.create_git_commit(
            tmp_path,
            tree="a" * 40,
            parent="b" * 40,
            message="bootstrap Commitment v2",
            runner=lambda *_args, **_kwargs: pytest.fail("Git must not run"),
        )
