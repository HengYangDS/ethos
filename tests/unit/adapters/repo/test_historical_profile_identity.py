"""Historical identity replay keeps old evidence bound without accepting old policy."""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.repo.git_effect_attestation as attest
from ethos.adapters.repo.git_effect_observation import resolve_git_effect_repository
from ethos.adapters.repo.profile import historical_repository_identity
from ethos.adapters.repo.profile import repository_identity
from tests.support.git_effect import effect
from tests.support.git_effect import fixture
from tests.support.git_effect import plan
from tests.support.governed_repository import git
from tests.support.signature import signature_repository

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

ISSUER = "agent:test:case:one"


def _reject(error: str, call: Callable[[], object]) -> None:
    with pytest.raises(ValueError, match=error):
        call()


@pytest.mark.parametrize(
    ("historical_profile", "expected_gap"),
    [
        ('profile_id = "signature-fixture"\n\n[roots]\nopenspec = "openspec"\n', ""),
        (None, "repository_historical_identity_invalid"),
        (b"\xff", "repository_historical_identity_invalid"),
        ('profile_id = "signature-fixture"\n[roots\n', "repository_historical_identity_invalid"),
        ("profile_id = 7\n", "repository_historical_identity_invalid"),
        ('profile_id = ""\n', "repository_historical_identity_invalid"),
        ('profile_id = "other"\n', ""),
    ],
    ids=["retired-field", "absent", "non-utf8", "malformed", "non-string", "empty", "mismatch"],
)
def test_exact_historical_profile_reader_keeps_only_stable_identity(
    tmp_path, historical_profile, expected_gap
):
    """Old operational schema drift cannot erase or invent repair identity."""
    repo, _old, _candidate = signature_repository(tmp_path, coupled=True)
    profile = repo / ".ethos/profile.toml"
    if historical_profile is None:
        profile.unlink()
    elif isinstance(historical_profile, bytes):
        profile.write_bytes(historical_profile)
    else:
        profile.write_text(historical_profile)
    git(repo, "add", "-A", ".ethos/profile.toml")
    git(repo, "commit", "-m", "fix: change former profile")
    old = git(repo, "rev-parse", "HEAD")
    if expected_gap:
        with pytest.raises(ValueError, match=expected_gap):
            historical_repository_identity(repo, tree_ref=old)
    else:
        expected = (
            "repository:other"
            if historical_profile == 'profile_id = "other"\n'
            else "repository:signature-fixture"
        )
        assert historical_repository_identity(repo, tree_ref=old) == expected
        if expected == "repository:signature-fixture":
            with pytest.raises(ValueError, match="repository_profile_invalid"):
                repository_identity(repo)


@pytest.mark.parametrize("former_id", ["repo", "other"])
@pytest.mark.parametrize("transition", ["commit.identity-replace", "candidate.accept"])
def test_recorded_effect_replay_uses_stable_historical_identity(
    tmp_path: Path, former_id: str, transition: str
) -> None:
    """Recorded effect replay tolerates old fields, not changed identity."""
    case = fixture(tmp_path)
    profile = case.repo / ".ethos/profile.toml"
    profile.write_text(f'profile_id = "{former_id}"\n\n[roots]\nopenspec = "openspec"\n')
    git(case.repo, "add", ".ethos/profile.toml")
    former = git(
        case.repo,
        "commit-tree",
        git(case.repo, "write-tree"),
        "-p",
        case.old,
        "-m",
        "former profile",
    )
    git(case.repo, "reset", "--hard", case.old)
    replacement = git(
        case.repo,
        "commit-tree",
        f"{case.old}^{{tree}}",
        "-p",
        former,
        "-m",
        "current profile",
    )
    value = effect(former, replacement)
    before = {"head": former}
    carried = plan(
        case.repo,
        value,
        policy={
            "operation": "git.ref.compare-and-swap",
            "transition": transition,
            "effect_digest": value.digest(),
        },
    )
    _reject(
        "repository_profile_invalid",
        lambda: resolve_git_effect_repository(case.repo, value, before, plan=carried),
    )
    if former_id == "repo":
        assert (
            resolve_git_effect_repository(
                case.repo, value, before, plan=carried, historical_identity=True
            )
            == "repository:repo"
        )
    else:
        _reject(
            "git_effect_repository_identity_mismatch",
            lambda: resolve_git_effect_repository(
                case.repo, value, before, plan=carried, historical_identity=True
            ),
        )
    observed_at = datetime.now(UTC).isoformat()
    record = attest.issue(
        value,
        plan=carried,
        issuer=ISSUER,
        evidence=(
            "repository:repo",
            "applied",
            {
                "observed_at": observed_at,
                "head": former,
                "tree": git(case.repo, "rev-parse", f"{former}^{{tree}}"),
                "refs": {"refs/heads/dev": former},
                "assertions": {},
            },
            {
                "observed_at": observed_at,
                "head": replacement,
                "tree": git(case.repo, "rev-parse", f"{replacement}^{{tree}}"),
                "refs": {"refs/heads/dev": replacement},
            },
        ),
    )

    def replay() -> None:
        attest.validate(
            case.repo,
            value,
            record,
            issuer=ISSUER,
            plan=carried,
            current_postconditions=False,
        )

    if former_id == "repo":
        replay()
        _reject(
            "repository_profile_invalid",
            lambda: attest.validate(case.repo, value, record, issuer=ISSUER, plan=carried),
        )
    else:
        _reject("git_effect_repository_identity_mismatch", replay)
    _reject(
        "git_effect_historical_identity_plan_required",
        lambda: resolve_git_effect_repository(
            case.repo,
            value,
            before,
            historical_identity=True,
        ),
    )
