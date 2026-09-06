from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.repo.git_signing as git_signing
from ethos.repository.policy.commit import CommitPolicy

if TYPE_CHECKING:
    from pathlib import Path


def test_commit_environment_rejects_missing_repository_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        git_signing,
        "run_git",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 1, "", ""),
    )

    with pytest.raises(ValueError, match="git_effect_signing_key_invalid"):
        git_signing.commit_environment(tmp_path, None)


def test_commit_environment_projects_the_required_signing_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    key = tmp_path / "signing-key.pub"
    key.write_text("ssh-ed25519 AAAATEST key\n", encoding="utf-8")
    monkeypatch.setattr(
        git_signing,
        "run_git",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, f"{key}\n", ""),
    )
    monkeypatch.setattr(git_signing, "_config", lambda *_args: "")

    assert git_signing.commit_environment(tmp_path, None) == {
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


def test_create_git_commit_uses_tracked_signing_when_ambient_git_disables_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[tuple[str, ...], dict[str, object]]] = []
    monkeypatch.setattr(
        git_signing,
        "load_commit_policy",
        lambda _root: CommitPolicy(
            subject_pattern=r"^fix: .+",
            signing_required=True,
            signing_format="ssh",
        ),
        raising=False,
    )
    monkeypatch.setattr(
        git_signing,
        "_config",
        lambda _root, name: "false" if name == "commit.gpgsign" else "",
    )
    monkeypatch.setattr(
        git_signing,
        "commit_environment",
        lambda _root, environment: dict(environment or {}) | {"POLICY_SIGNER": "1"},
    )
    monkeypatch.setattr(
        git_signing,
        "verify_commit_trust",
        lambda *_args: {"required_gaps": []},
    )

    def runner(_root: Path, *args: str, **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(args, 0, "c" * 40 + "\n", "")

    completed = git_signing.create_git_commit(
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
    monkeypatch.setattr(git_signing, "load_commit_policy", lambda _root: None, raising=False)
    monkeypatch.setattr(git_signing, "_config", lambda *_args: "true")
    monkeypatch.setattr(git_signing, "commit_environment", lambda *_args: {"IGNORED": "1"})

    def runner(_root: Path, *args: str, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, "c" * 40 + "\n", "")

    completed = git_signing.create_git_commit(
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
        git_signing,
        "load_commit_policy",
        lambda _root: CommitPolicy(
            subject_pattern=r"^fix: .+",
            signing_required=False,
            signing_format="ssh",
        ),
        raising=False,
    )

    with pytest.raises(ValueError, match="commit_subject_invalid:bootstrap Commitment v2"):
        git_signing.create_git_commit(
            tmp_path,
            tree="a" * 40,
            parent="b" * 40,
            message="bootstrap Commitment v2",
            runner=lambda *_args, **_kwargs: pytest.fail("Git must not run"),
        )


def test_validate_commits_checks_every_subject_and_required_signature(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    revisions = ("a" * 40, "b" * 40)
    subjects = dict(zip(revisions, ("fix: first", "fix(runtime): second"), strict=True))
    verified: list[str] = []

    def run_git(_root: Path, *args: str, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        revision = args[-1]
        return subprocess.CompletedProcess(args, 0, subjects[revision] + "\n", "")

    monkeypatch.setattr(git_signing, "run_git", run_git)
    monkeypatch.setattr(
        git_signing,
        "verify_commit_trust",
        lambda _root, revision: verified.append(revision) or {"required_gaps": []},
    )

    gaps = git_signing.validate_commits(
        tmp_path,
        revisions,
        policy=CommitPolicy(
            subject_pattern=r"^fix(\([a-z-]+\))?: .+",
            signing_required=True,
            signing_format="ssh",
        ),
    )

    assert gaps == []
    assert verified == list(revisions)


def test_validate_commits_stops_at_the_first_subject_violation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    revisions = ("a" * 40, "b" * 40)
    subjects = {revisions[0]: "fix: valid", revisions[1]: "invalid subject"}
    verified: list[str] = []

    def run_git(_root: Path, *args: str, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        revision = args[-1]
        return subprocess.CompletedProcess(args, 0, subjects[revision] + "\n", "")

    monkeypatch.setattr(git_signing, "run_git", run_git)
    monkeypatch.setattr(
        git_signing,
        "verify_commit_trust",
        lambda _root, revision: verified.append(revision) or {"required_gaps": []},
    )

    gaps = git_signing.validate_commits(
        tmp_path,
        revisions,
        policy=CommitPolicy(
            subject_pattern=r"^fix: .+",
            signing_required=True,
            signing_format="ssh",
        ),
    )

    assert gaps == [f"commit_subject_invalid:{revisions[1]}:invalid subject"]
    assert verified == [revisions[0]]
