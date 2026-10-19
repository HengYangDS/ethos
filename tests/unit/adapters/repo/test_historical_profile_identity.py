"""Historical identity replay keeps old evidence bound without accepting old policy."""

from __future__ import annotations

import cProfile
from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.repo.git_effect_attestation as attest
from ethos.adapters.repo.git_effect_observation import resolve_git_effect_repository
from ethos.adapters.repo.profile import historical_repository_identity
from ethos.adapters.repo.profile import repository_identities
from ethos.adapters.repo.profile import repository_identity
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from tests.support.git_effect import effect
from tests.support.git_effect import fixture
from tests.support.git_effect import plan
from tests.support.governed_repository import git
from tests.support.signature import signature_repository

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

ISSUER = "agent:test:case:one"


@pytest.mark.parametrize("historical", [False, True], ids=["current", "recorded"])
@pytest.mark.parametrize("count", [2, 3, 8], ids=["small-subject", "three-ref", "multi-ref"])
@pytest.mark.parametrize("allow_absent_prestate", [False, True], ids=["strict", "former-optional"])
def test_effect_profile_observation_batches_fresh_native_reads(
    tmp_path: Path, historical, count: int, *, allow_absent_prestate: bool
) -> None:
    """Optional former identity must not force required peers back to per-ref reads."""
    case = fixture(tmp_path)
    revisions = tuple(
        git(case.repo, "commit-tree", "HEAD^{tree}", "-p", case.old, "-m", f"peer-{index}")
        for index in range(count - 2)
    )
    value = GitEffect(
        updates={"refs/heads/dev": GitRefUpdate(expected=case.old, desired=case.new)},
        assertions={
            f"refs/heads/peer-{index}": revision for index, revision in enumerate(revisions)
        },
    )
    profile = cProfile.Profile()
    result = profile.runcall(
        resolve_git_effect_repository,
        case.repo,
        value,
        {"head": case.old},
        plan=plan(case.repo, value) if historical else None,
        historical_identity=historical,
        allow_absent_prestate=allow_absent_prestate,
    )

    assert result == "repository:repo"
    launches = sum(
        entry.callcount
        for entry in profile.getstats()
        if hasattr(entry.code, "co_name") and entry.code.co_name == "run_git"
    )
    assert launches == (min(count, 3) if allow_absent_prestate else 2)
    assert git(case.repo, "rev-parse", "HEAD") == case.old
    assert git(case.repo, "status", "--porcelain") == ""


@pytest.mark.parametrize("allow_absent_prestate", [False, True], ids=["strict", "former-optional"])
def test_effect_profile_batch_uses_the_selected_object_store_and_fresh_material(
    tmp_path: Path, *, allow_absent_prestate: bool
):
    """All profile reads share quarantine context and reject later object disappearance."""
    case = fixture(tmp_path / "target")
    source = fixture(tmp_path / "source", "repository:isolated")
    third = git(source.repo, "commit-tree", "HEAD^{tree}", "-p", source.new, "-m", "third")
    fourth = git(source.repo, "commit-tree", "HEAD^{tree}", "-p", source.new, "-m", "fourth")
    value = GitEffect(
        updates={"refs/heads/dev": GitRefUpdate(expected=source.old, desired=source.new)},
        assertions={"refs/heads/third": third, "refs/heads/fourth": fourth},
    )
    environment = {"GIT_ALTERNATE_OBJECT_DIRECTORIES": (source.repo / ".git/objects").as_posix()}
    before: dict[str, object] = {"head": source.old}
    assert (
        resolve_git_effect_repository(
            case.repo,
            value,
            before,
            environment=environment,
            allow_absent_prestate=allow_absent_prestate,
        )
        == "repository:isolated"
    )
    profile = git(source.repo, "rev-parse", "HEAD:.ethos/profile.toml")
    (source.repo / ".git/objects" / profile[:2] / profile[2:]).unlink()
    with pytest.raises(ValueError, match="invalid"):
        resolve_git_effect_repository(
            case.repo,
            value,
            before,
            environment=environment,
            allow_absent_prestate=allow_absent_prestate,
        )
    assert git(case.repo, "rev-parse", "HEAD") == case.old
    assert git(case.repo, "status", "--porcelain") == ""


@pytest.mark.parametrize("allow_absent_prestate", [False, True], ids=["strict", "former-optional"])
def test_effect_profile_observation_reads_current_bytes_after_ref_change(
    tmp_path: Path, *, allow_absent_prestate: bool
):
    """A second observation cannot authorize from a previous profile answer."""
    case = fixture(tmp_path)
    third = git(case.repo, "commit-tree", "HEAD^{tree}", "-p", case.old, "-m", "third")
    selected = ("HEAD", case.old, case.new, third)
    optional = frozenset({case.old}) if allow_absent_prestate else frozenset()
    assert repository_identities(case.repo, selected, optional=optional) == dict.fromkeys(
        selected, "repository:repo"
    )
    profile = case.repo / ".ethos/profile.toml"
    profile.write_text('profile_id = "changed"\n', encoding="utf-8")
    git(case.repo, "add", ".ethos/profile.toml")
    git(case.repo, "commit", "-m", "change current profile")
    assert repository_identities(case.repo, selected, optional=optional) == {
        "HEAD": "repository:changed",
        case.old: "repository:repo",
        case.new: "repository:repo",
        third: "repository:repo",
    }


def test_effect_profile_prestate_optional_scope_does_not_cover_new_refs(tmp_path: Path):
    """Deletion tolerance applies only to exact former revisions, never proposed ones."""
    case = fixture(tmp_path)
    profile = case.repo / ".ethos/profile.toml"
    profile.write_text("profile_id = 7\n", encoding="utf-8")
    git(case.repo, "add", ".ethos/profile.toml")
    git(case.repo, "commit", "-m", "malformed former profile")
    former = git(case.repo, "rev-parse", "HEAD")
    third = git(case.repo, "commit-tree", f"{case.old}^{{tree}}", "-p", case.old, "-m", "third")
    selected = (former, case.old, case.new, third)
    assert repository_identities(case.repo, selected, optional=frozenset({former})) == {
        case.old: "repository:repo",
        case.new: "repository:repo",
        third: "repository:repo",
    }
    with pytest.raises(ValueError, match="repository_profile_invalid"):
        repository_identities(case.repo, selected, optional=frozenset({case.old}))


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
    selected = ("HEAD", old, f"{old}~0")
    if expected_gap:
        with pytest.raises(ValueError, match=expected_gap):
            historical_repository_identity(repo, tree_ref=old)
        with pytest.raises(ValueError, match=expected_gap):
            repository_identities(repo, selected, historical=True)
    else:
        expected = (
            "repository:other"
            if historical_profile == 'profile_id = "other"\n'
            else "repository:signature-fixture"
        )
        assert historical_repository_identity(repo, tree_ref=old) == expected
        assert repository_identities(repo, selected, historical=True) == dict.fromkeys(
            selected, expected
        )
        if expected == "repository:signature-fixture":
            with pytest.raises(ValueError, match="repository_profile_invalid"):
                repository_identity(repo)


@pytest.mark.parametrize("former_id", ["repo", "other"])
@pytest.mark.parametrize("transition", ["commit.identity-replace", "candidate.accept"])
def test_recorded_effect_replay_uses_stable_historical_identity(
    tmp_path: Path, former_id: str, transition: str
) -> None:
    """Replay and current effects tolerate old pre-state fields, not changed identity."""
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
    before: dict[str, object] = {"head": former}
    carried = plan(
        case.repo,
        value,
        policy={
            "operation": "git.ref.compare-and-swap",
            "transition": transition,
            "effect_digest": value.digest(),
        },
    )
    for historical in (False, True):
        if former_id == "repo":
            assert (
                resolve_git_effect_repository(
                    case.repo, value, before, plan=carried, historical_identity=historical
                )
                == "repository:repo"
            )
        else:
            _reject(
                "git_effect_repository_identity_mismatch",
                lambda historical=historical: resolve_git_effect_repository(
                    case.repo, value, before, plan=carried, historical_identity=historical
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
            "git_effect_attestation_content_mismatch",
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
