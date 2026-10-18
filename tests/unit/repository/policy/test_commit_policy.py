"""Compile the commit policy once: the paradigm's grammar and SSH signature everywhere."""

from __future__ import annotations

from pathlib import Path

import pytest

import ethos.repository.policy.commit as commit_policy

ROOT = Path(__file__).resolve().parents[4]
_SHARED = ("feat(cli)!: drop the legacy flag", "fix: repair", "refactor(relay-core): split")
_FOREIGN = ("style: reformat", "spec(cli): add", "fix(Cli): repair", "fix:repair")


def _write_workspace(root: Path, text: str) -> None:
    path = root / ".ethos/workspace.toml"
    path.parent.mkdir(parents=True)
    path.write_text(text, encoding="utf-8")


def test_a_repository_without_a_commit_policy_gets_the_paradigm_policy(tmp_path: Path) -> None:
    """No declaration still applies the shared grammar and the SSH signature."""
    policy = commit_policy.load_commit_policy(tmp_path)

    assert policy == commit_policy.commit_policy_from_text("[commit_policy]\n")
    assert policy.signing_format == "ssh"
    assert all(policy.accepts_subject(subject) for subject in _SHARED)
    assert not any(policy.accepts_subject(subject) for subject in _FOREIGN)
    assert policy.projection() == {
        "subject_pattern": policy.subject_pattern,
        "signing_format": "ssh",
    }


def test_current_repository_commit_policy_compiles_through_the_unique_owner() -> None:
    policy = commit_policy.load_commit_policy(ROOT)

    assert policy.accepts_subject("fix(policy): close commit authority")


@pytest.mark.parametrize(
    "restated",
    [
        'signing_required = true\nsigning_format = "ssh"\n',
        'signing_required = false\nsigning_format = "openpgp"\n',
        'signing_required = "yes"\n',
    ],
    ids=["restated", "contradicting", "malformed"],
)
def test_a_restated_signature_does_not_change_the_policy(restated: str) -> None:
    """The paradigm fixes the signature; the paradigm report names any restated field."""
    policy = commit_policy.commit_policy_from_text(f"[commit_policy]\n{restated}")

    assert policy == commit_policy.commit_policy_from_text("")


def test_commit_policy_compiles_the_exact_supported_shape(tmp_path: Path) -> None:
    _write_workspace(
        tmp_path,
        r"""[commit_policy]
subject_pattern = "^(feat|fix)(\\([a-z-]+\\))?: .+"
""",
    )

    policy = commit_policy.load_commit_policy(tmp_path)

    assert policy.subject_pattern == r"^(feat|fix)(\([a-z-]+\))?: .+"
    assert policy.signing_format == "ssh"
    assert policy.accepts_subject("fix(runtime): bind signer") is True
    assert policy.accepts_subject("bootstrap Commitment v2") is False


def test_commit_policy_compiles_from_one_already_observed_snapshot() -> None:
    policy = commit_policy.commit_policy_from_text(
        '[commit_policy]\nsubject_pattern = "^fix: .+"\n'
    )

    assert policy.accepts_subject("fix: replay current intent")


@pytest.mark.parametrize(
    ("old", "new", "error"),
    [
        ("[commit_policy]", "[commit_policy", "commit_policy_toml_invalid"),
        ("all", 'commit_policy = "implicit"', "commit_policy_invalid:must_be_table"),
        ("", 'identity_mode = "external"', "commit_policy_unknown_fields:identity_mode"),
        ('"^fix: .+"', "1", "commit_policy_invalid:subject_pattern"),
        ('"^fix: .+"', '"["', "commit_policy_subject_pattern_invalid"),
        ("", 'scopes = ["cli"]', "commit_policy_invalid:scopes"),
        ('subject_pattern = "^fix: .+"', "scopes = []", "commit_policy_invalid:scopes"),
        ('subject_pattern = "^fix: .+"', 'scopes = ["Cli"]', "commit_policy_invalid:scopes"),
        ('subject_pattern = "^fix: .+"', 'scopes = ["cli", "cli"]', "commit_policy_invalid:scopes"),
        ('subject_pattern = "^fix: .+"', "scopes = [{}]", "commit_policy_invalid:scopes"),
    ],
)
def test_present_commit_policy_fails_closed(
    tmp_path: Path,
    old: str,
    new: str,
    error: str,
) -> None:
    valid = '[commit_policy]\nsubject_pattern = "^fix: .+"\n'
    text = new if old == "all" else valid.replace(old, new, 1) if old else valid + new
    assert text != valid
    _write_workspace(tmp_path, text)

    with pytest.raises((TypeError, ValueError), match=error):
        commit_policy.load_commit_policy(tmp_path)


@pytest.mark.parametrize(
    ("scopes", "accepted", "rejected"),
    [
        ("", _SHARED, _FOREIGN),
        (
            'scopes = ["cli", "relay"]\n',
            ("fix(cli): repair", "feat(relay)!: rename", "docs: explain"),
            ("fix(other): repair", "style(cli): reformat"),
        ),
    ],
    ids=["shared-grammar", "declared-scopes"],
)
def test_an_omitted_subject_pattern_applies_the_shared_grammar(
    scopes: str, accepted: tuple[str, ...], rejected: tuple[str, ...]
) -> None:
    """Without a declared pattern the paradigm's grammar applies, restricted to declared scopes."""
    policy = commit_policy.commit_policy_from_text(f"[commit_policy]\n{scopes}")

    assert all(policy.accepts_subject(subject) for subject in accepted)
    assert not any(policy.accepts_subject(subject) for subject in rejected)
    assert policy.projection().get("scopes", []) == list(policy.scopes)
