"""Legacy role refs and proposal refs that stand at commits made before the adoption.

A repository adopted under a legacy branch-role table can hold refs at commits that carry no
repository profile. Their retirement and their rename read the accepted head's declarations and
shared history, never an identity that such a commit cannot have.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import ethos.adapters.mutation.lane_retirement.effects as effects
from ethos.adapters.admission.ref_move_policy import prepared_deletion_gaps
from ethos.adapters.repo.git_effect_observation import observe_git_effect
from ethos.adapters.repo.git_effect_observation import resolve_git_effect_repository
from ethos.adapters.repo.hook.activation import install_hook_launchers
from ethos.adapters.repo.profile import adoption_classification
from ethos.adapters.repo.profile import repository_identities
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.git_effect import plan
from tests.support.governed_repository import git
from tests.support.governed_repository import start_adopted_candidate
from tests.support.governed_repository import write_publication_topology
from tests.support.governed_repository import write_release_mirror
from tests.support.proof import seed_executed_proof
from tests.unit.cli.land.publication.support import accepted_release_fixture
from tests.unit.cli.land.publication.support import branch_publication_fixture

_TABLE = (
    "[branch_roles]\n"
    'release_branch = "master"\n'
    'accepted_branch = "dev"\n'
    'candidate_branch = "integration/dev"\n'
    'work_branch_prefix = "task/"\n'
    'proposal_branch_prefix = "submit/"\n'
)
_PLAIN = ("-c", "core.hooksPath=/dev/null")
_RETIRED_SCHEMA = '\n[retired]\nformat = "ruff-json"\n'
_REF = "submit/pre-adoption"
_ABANDON = (
    "lane",
    "retire",
    "abandon",
    "--branch",
    _REF,
    "--reason-code",
    "content-review",
    "--reason",
    "an equal patch is in the lane",
    "--review-content",
)
_ACTOR = "agent:test:case:agent-test"


def _run(root: Path, *words: str) -> dict[str, object]:
    done = run_ethos_raw(*words, "--json", cwd=root)
    return json.loads(done.stdout) | {"exit": done.returncode}


def _heads(repo: Path) -> dict[str, str]:
    rows = git(repo, "for-each-ref", "--format=%(refname:short) %(objectname)", "refs/heads")
    return dict(row.split() for row in rows.splitlines())


def _shape(tmp_path: Path, master_at: str = "before") -> tuple[Path, Path, str, dict[str, str]]:
    """The accepted head declares the legacy table and no release; legacy refs stand before it."""
    repo, candidate = start_adopted_candidate(tmp_path)
    first = git(repo, "rev-list", "--max-parents=0", "HEAD")
    adopted = git(repo, "rev-parse", "HEAD")
    places = {"before": first, "profile": adopted}
    if master_at == "retired-schema":
        profile = repo / ".ethos/profile.toml"
        current = profile.read_text(encoding="utf-8")
        profile.write_text(current + _RETIRED_SCHEMA, encoding="utf-8")
        git(repo, "commit", "-am", "chore: accept a profile of a retired schema")
        places["retired-schema"] = git(repo, "rev-parse", "HEAD")
        profile.write_text(current, encoding="utf-8")
        git(repo, "commit", "-am", "chore: migrate the profile schema")
    if master_at == "deleted":
        git(repo, "rm", "-q", ".ethos/profile.toml")
        git(repo, "commit", "-m", "chore: drop the profile")
        places["deleted"] = git(repo, "rev-parse", "HEAD")
        git(repo, "revert", "--no-edit", "HEAD")
    (repo / ".ethos/workspace.toml").write_text(_TABLE, encoding="utf-8")
    git(repo, "add", ".ethos/workspace.toml")
    if (repo / ".ethos/release.toml").exists():
        git(repo, "rm", "-q", ".ethos/release.toml")
    git(repo, "commit", "-m", "chore: declare legacy branch roles and no release declaration")
    head = git(repo, "rev-parse", "HEAD")
    git(candidate, "reset", "--hard", head)
    tree = git(repo, "rev-parse", f"{first}^{{tree}}")
    places["unrelated"] = git(repo, "commit-tree", tree, "-m", "chore: an unrelated root")
    git(repo, *_PLAIN, "update-ref", "refs/heads/master", places[master_at])
    old = git(repo, "commit-tree", tree, "-p", first, "-m", "fix: an old proposal")
    git(repo, *_PLAIN, "update-ref", f"refs/heads/{_REF}", old)
    git(repo, *_PLAIN, "worktree", "add", "-q", (tmp_path / "old-proposal").as_posix(), _REF)
    install_hook_launchers(repo)
    return repo, candidate, head, places


def _step(result: dict[str, object]) -> list[str]:
    """The words of a result's own next step, without the program name and the JSON flag."""
    step = result.get("next") if isinstance(result.get("next"), dict) else {}
    return [str(word) for word in step.get("argv") or [] if word != "--json"][1:]


def _refusing(asked: list[tuple[str, str]], gap: str):
    """A deletion predicate that refuses with one gap and records what it was asked."""

    def ask(_root: Path, ref: str, head: str) -> list[str]:
        asked.append((ref, head))
        return [gap]

    return ask


def _abandon(repo: Path) -> dict[str, object]:
    preview = _run(repo, *_ABANDON)
    words = _step(preview)
    return _run(repo, *words) if words else preview


def _closeout(repo: Path, head: str, *extra: str) -> dict[str, object]:
    return _run(repo, "land", "--closeout", *extra, "--expect-head", head)


def test_a_pre_adoption_proposal_ref_is_abandoned_whole(tmp_path: Path) -> None:
    repo, _candidate, _head, _places = _shape(tmp_path)

    retired = _abandon(repo)

    assert (retired["verdict"], retired["state"]) == ("pass", "retired")
    assert _REF not in _heads(repo)
    assert not (tmp_path / "old-proposal").exists()


def test_a_refused_deletion_blocks_the_abandonment_before_any_effect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, _candidate, _head, _places = _shape(tmp_path)
    asked: list[tuple[str, str]] = []
    monkeypatch.setattr(
        effects, "prepared_deletion_gaps", _refusing(asked, "ref_move_policy_unavailable")
    )

    blocked = _run(repo, *_ABANDON)

    assert blocked["verdict"] == "block"
    assert "ref_move_policy_unavailable" in blocked["required_gaps"]
    assert not _step(blocked)
    assert asked == [(f"refs/heads/{_REF}", _heads(repo)[_REF])]
    assert (tmp_path / "old-proposal").exists()
    assert _REF in _heads(repo)


def test_a_half_done_abandonment_is_finished_by_its_own_step(tmp_path: Path) -> None:
    """The reported state: the worktree is gone and the ref stays; the same step ends it."""
    repo, _candidate, _head, _places = _shape(tmp_path)
    words = _step(_run(repo, *_ABANDON))
    assert words
    lock = Path(git(repo, "rev-parse", "--git-common-dir")) / f"refs/heads/{_REF}.lock"
    lock = lock if lock.is_absolute() else repo / lock
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_text("", encoding="utf-8")

    stopped = _run(repo, *words)
    half_done = not (tmp_path / "old-proposal").exists() and _REF in _heads(repo)
    lock.unlink()
    finished = _run(repo, *words)

    assert stopped["verdict"] == "block"
    assert half_done
    assert (finished["verdict"], finished["state"]) == ("pass", "retired")
    assert _REF not in _heads(repo)
    assert not (tmp_path / "old-proposal").exists()


@pytest.mark.parametrize("asking", ["the accepted root", "a root checked out before the table"])
def test_a_legacy_release_ref_is_protected_before_its_rename(tmp_path: Path, asking: str) -> None:
    """The accepted table protects the ref from every root, whatever that root has checked out."""
    repo, _candidate, _head, places = _shape(tmp_path)
    root = repo if asking == "the accepted root" else tmp_path / "old-proposal"

    gaps = prepared_deletion_gaps(root, "refs/heads/master", places["before"])

    assert gaps == ["legacy_role_ref_protected"]


def test_a_receipt_cannot_remove_a_worktree_for_a_deletion_that_now_refuses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A receipt derived while the deletion was admitted is asked again before any removal."""
    repo, _candidate, _head, _places = _shape(tmp_path)
    words = _step(_run(repo, *_ABANDON))
    assert words
    asked: list[tuple[str, str]] = []
    monkeypatch.setattr(
        effects, "prepared_deletion_gaps", _refusing(asked, "legacy_role_ref_protected")
    )

    refused = _run(repo, *words)

    assert refused["verdict"] == "block"
    assert "legacy_role_ref_protected" in refused["required_gaps"]
    assert (tmp_path / "old-proposal").exists()
    assert asked == [(f"refs/heads/{_REF}", _heads(repo)[_REF])]


@pytest.mark.parametrize("fault", ["no profile", "a release binding that cannot be honored"])
def test_a_deletion_stays_refused_without_a_policy_at_the_accepted_head(
    tmp_path: Path, fault: str
) -> None:
    """Only an accepted head with no release binding and a valid profile selects the default."""
    repo, _candidate, _head, _places = _shape(tmp_path)
    if fault == "no profile":
        git(repo, *_PLAIN, "rm", "-q", ".ethos/profile.toml")
    else:
        write_release_mirror(repo, "sideways")
        git(repo, "add", ".ethos/release.toml")
    git(repo, *_PLAIN, "commit", "-q", "-m", "chore: leave the accepted head without a policy")

    gaps = prepared_deletion_gaps(repo, f"refs/heads/{_REF}", _heads(repo)[_REF])

    assert gaps == ["ref_move_policy_unavailable"]


def test_an_unreadable_accepted_table_keeps_the_deleted_commit_s_protection(
    tmp_path: Path,
) -> None:
    """Each table is read on its own: one that cannot be read takes nothing from the other."""
    repo, _candidate, head, _places = _shape(tmp_path)
    git(repo, *_PLAIN, "update-ref", "refs/heads/master", head)
    (repo / ".ethos/workspace.toml").write_text("[branch_roles]\nrelease_branch = 5\n", "utf-8")
    git(repo, *_PLAIN, "commit", "-q", "-am", "chore: break the accepted table")

    assert prepared_deletion_gaps(repo, "refs/heads/master", head) == ["legacy_role_ref_protected"]


@pytest.mark.parametrize("master_at", ["before", "profile", "retired-schema"])
def test_closeout_renames_a_legacy_release_ref_that_predates_the_table(
    tmp_path: Path, master_at: str
) -> None:
    repo, _candidate, head, places = _shape(tmp_path, master_at)
    assert _abandon(repo)["state"] == "retired"

    preview = _closeout(repo, head)
    applied = _closeout(repo, head, "--apply", "--authorize")

    assert (preview["verdict"], preview["state"]) == ("pass", "ready_to_rename")
    assert (applied["verdict"], applied["state"]) == ("pass", "branch_roles_renamed")
    heads = _heads(repo)
    assert heads.get("main") == places[master_at]
    assert "master" not in heads
    assert _run(repo, "status")["state"] == "ready"


def test_closeout_renames_a_pre_adoption_release_ref_beside_a_legacy_accepted_name(
    tmp_path: Path,
) -> None:
    """The accepted root's own head is the source when the accepted ref has a legacy name too."""
    repo, candidate = start_adopted_candidate(tmp_path)
    first = git(repo, "rev-list", "--max-parents=0", "HEAD")
    (repo / ".ethos/workspace.toml").write_text(
        "[branch_roles]\n"
        'release_branch = "master"\n'
        'accepted_branch = "accepted/train"\n'
        'candidate_branch = "candidate/train"\n',
        encoding="utf-8",
    )
    git(repo, "add", ".ethos/workspace.toml")
    git(repo, "commit", "-m", "chore: declare legacy branch roles")
    git(repo, "branch", "-m", "dev", "accepted/train")
    git(repo, "branch", "-m", "candidate/dev", "candidate/train")
    head = git(repo, "rev-parse", "HEAD")
    git(candidate, "reset", "--hard", head)
    git(repo, *_PLAIN, "update-ref", "refs/heads/master", first)
    install_hook_launchers(repo)

    preview = _closeout(repo, head)
    applied = _closeout(repo, head, "--apply", "--authorize")

    assert (preview["verdict"], preview["state"]) == ("pass", "ready_to_rename")
    assert (applied["verdict"], applied["state"]) == ("pass", "branch_roles_renamed")
    heads = _heads(repo)
    assert (heads.get("dev"), heads.get("candidate/dev"), heads.get("main")) == (head, head, first)
    assert not {"master", "accepted/train", "candidate/train"} & set(heads)


@pytest.mark.parametrize(
    ("master_at", "gap"),
    [
        ("unrelated", "legacy_role_rename_history_unshared:master"),
        ("deleted", "repository_historical_identity_invalid:.ethos/profile.toml"),
    ],
)
def test_closeout_refuses_a_legacy_ref_outside_the_accepted_line(
    tmp_path: Path, master_at: str, gap: str
) -> None:
    """No shared history, or a profile that the line carried and then dropped, is not adopted."""
    repo, _candidate, head, places = _shape(tmp_path, master_at)
    assert _abandon(repo)["state"] == "retired"

    preview = _closeout(repo, head)
    applied = _closeout(repo, head, "--apply", "--authorize")

    assert preview["verdict"] == applied["verdict"] == "block"
    assert gap in preview["required_gaps"]
    assert gap in applied["required_gaps"]
    assert _heads(repo).get("master") == places[master_at]
    assert "main" not in _heads(repo)


@pytest.mark.parametrize("place", ["before", "unrelated"])
def test_an_effect_lends_the_accepted_identity_only_on_the_accepted_line(
    tmp_path: Path, place: str
) -> None:
    """Every Git effect resolves its identity here; only a pre-state the head descends from."""
    repo, _candidate, head, places = _shape(tmp_path, place)
    effect = GitEffect(
        updates={"refs/heads/master": GitRefUpdate(expected=places[place], desired=head)},
        assertions={"refs/heads/dev": head},
    )
    before = observe_git_effect(repo, effect)

    if place == "unrelated":
        with pytest.raises(ValueError, match="repository_historical_identity_invalid:"):
            resolve_git_effect_repository(repo, effect, before)
        return
    accepted = repository_identities(repo, (head,))[head]
    assert resolve_git_effect_repository(repo, effect, before) == accepted


@pytest.mark.parametrize("history", ["a merge that kept no profile", "a shallow clone"])
def test_a_history_that_may_have_carried_the_profile_is_not_adopted(
    tmp_path: Path, history: str
) -> None:
    """Only a complete history with no profile in it belongs to the adopted line."""
    repo, _candidate, head, places = _shape(tmp_path)
    first, old = places["before"], _heads(repo)[_REF]
    if history == "a shallow clone":
        root = tmp_path / "shallow"
        git(repo, "clone", "-q", "--depth", "1", "--branch", _REF, repo.as_uri(), root.as_posix())
        revision = accepted = old
    else:
        root, accepted = repo, head
        carried = git(repo, "commit-tree", f"{head}^{{tree}}", "-p", first, "-m", "feat: a side")
        bare = git(repo, "rev-parse", f"{first}^{{tree}}")
        revision = git(repo, "commit-tree", bare, "-p", first, "-p", carried, "-m", "merge: ours")

    assert adoption_classification(repo, old, accepted_head=head) == "unshared"
    assert adoption_classification(repo, first, accepted_head=head) == "adopted"
    assert adoption_classification(root, revision, accepted_head=accepted) == "dropped"


def test_the_accepted_table_protects_where_no_accepted_line_can_be_named(tmp_path: Path) -> None:
    """With no accepted ref, the asking root's own table keeps its protection."""
    repo, _candidate, _head, places = _shape(tmp_path)
    git(repo, *_PLAIN, "branch", "-m", "dev", "elsewhere")

    gaps = prepared_deletion_gaps(repo, "refs/heads/master", places["before"])

    assert gaps == ["legacy_role_ref_protected"]


def test_a_recorded_rename_is_read_without_today_s_accepted_head(tmp_path: Path) -> None:
    """A later identity of the accepted line does not unbind a rename recorded before it."""
    repo, _candidate, head, places = _shape(tmp_path)
    old, zero = places["before"], "0" * 40
    effect = GitEffect(
        updates={
            "refs/heads/master": GitRefUpdate(expected=old, desired=zero),
            "refs/heads/main": GitRefUpdate(expected=zero, desired=old),
        },
        assertions={"refs/heads/dev": head},
    )
    recorded, former = plan(repo, effect), repository_identities(repo, (head,))[head]
    profile = repo / ".ethos/profile.toml"
    text = profile.read_text(encoding="utf-8")
    profile.write_text(text.replace('profile_id = "', 'profile_id = "later-', 1), encoding="utf-8")
    git(repo, *_PLAIN, "commit", "-q", "-am", "chore: give the repository a later identity")
    later = git(repo, "rev-parse", "HEAD")
    assert repository_identities(repo, (later,))[later] != former

    resolved = resolve_git_effect_repository(
        repo, effect, {"head": head}, plan=recorded, historical_identity=True
    )

    assert resolved == former


@pytest.mark.parametrize(
    "shape", ["rename", "rename and a second creation", "move onto it", "rewind onto it"]
)
def test_only_a_rename_puts_a_ref_on_a_pre_adoption_commit(tmp_path: Path, shape: str) -> None:
    """One creation for one deletion at a commit produces nothing; any further ref there does."""
    repo, _candidate, head, places = _shape(tmp_path)
    old, zero = places["before"], "0" * 40
    updates = {
        "rename": {
            "refs/heads/master": GitRefUpdate(expected=old, desired=zero),
            "refs/heads/main": GitRefUpdate(expected=zero, desired=old),
        },
        "rename and a second creation": {
            "refs/heads/master": GitRefUpdate(expected=old, desired=zero),
            "refs/heads/main": GitRefUpdate(expected=zero, desired=old),
            "refs/heads/extra": GitRefUpdate(expected=zero, desired=old),
        },
        "move onto it": {
            "refs/heads/master": GitRefUpdate(expected=old, desired=head),
            "refs/heads/other": GitRefUpdate(expected=head, desired=old),
        },
        "rewind onto it": {"refs/heads/dev": GitRefUpdate(expected=head, desired=old)},
    }[shape]
    effect = GitEffect(updates=updates, assertions={"refs/heads/candidate/dev": head})
    before = observe_git_effect(repo, effect)

    if shape == "rename":
        accepted = repository_identities(repo, (head,))[head]
        assert resolve_git_effect_repository(repo, effect, before) == accepted
        return
    with pytest.raises(ValueError, match="repository_profile_invalid"):
        resolve_git_effect_repository(repo, effect, before)


def test_the_release_mirror_advances_from_a_pre_adoption_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ETHOS_ACTOR", _ACTOR)
    repo, candidate, head, places = _shape(tmp_path)
    assert _abandon(repo)["state"] == "retired"
    assert _closeout(repo, head, "--apply", "--authorize")["state"] == "branch_roles_renamed"
    git(candidate, "rm", "-q", ".ethos/workspace.toml")
    write_release_mirror(candidate, "accepted_ff")
    write_publication_topology(candidate)
    git(candidate, "add", "-A")
    git(candidate, "commit", "-q", "-m", "chore: declare the release and drop the legacy table")
    landed = git(candidate, "rev-parse", "HEAD")
    seed_executed_proof(candidate, landed)
    accepted = _closeout(repo, head, "--apply", "--authorize", "--candidate-head", landed)
    assert accepted["verdict"] == "pass"
    assert _heads(repo)["main"] == places["before"]

    mirrored = _closeout(repo, landed, "--apply", "--authorize")

    assert (mirrored["verdict"], mirrored["state"]) == ("pass", "accepted_current")
    heads = _heads(repo)
    assert (heads["candidate/dev"], heads["dev"], heads["main"]) == (landed, landed, landed)


def test_a_release_advances_the_release_ref_from_a_pre_adoption_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ETHOS_ACTOR", _ACTOR)
    accepted, main, _old, head = accepted_release_fixture(tmp_path)
    base = git(accepted, "rev-list", "--max-parents=0", head)
    assert not git(accepted, "ls-tree", "-r", "--name-only", base, ".ethos")
    git(main, *_PLAIN, "reset", "-q", "--hard", base)
    release = (
        "land",
        "--release",
        "--expect-head",
        head,
        "--release-head",
        base,
        "--tag",
        "v1.2.3",
    )

    preview = _run(accepted, *release)
    applied = _run(accepted, *release, "--apply", "--authorize")

    assert (preview["verdict"], preview["state"]) == ("pass", "ready_to_release")
    assert (applied["verdict"], applied["state"]) == ("pass", "released")
    assert git(accepted, "rev-parse", "main") == head


@pytest.mark.parametrize("ref", ["refs/heads/master", f"refs/heads/{_REF}"])
def test_publication_retirement_still_refuses_a_peer_s_legacy_ref(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, ref: str
) -> None:
    """Unchanged by the repairs: a peer's legacy ref is no proposal, so a person deletes it."""
    monkeypatch.setenv("ETHOS_ACTOR", _ACTOR)
    repo, peers, _proposal = branch_publication_fixture(tmp_path, source_branch="dev", proof=False)
    policy = repo / ".ethos/release.toml"
    plain = policy.read_text(encoding="utf-8")
    for provider in ("gitlab", "github"):
        plain = plain.replace(f'provider = "{provider}"', 'provider = "git"')
    policy.write_text(plain, encoding="utf-8")
    git(repo, "add", ".ethos/release.toml")
    git(repo, "commit", "-m", "chore: declare plain Git peers")
    head = git(repo, "rev-parse", "HEAD")
    first = git(repo, "rev-list", "--max-parents=0", "HEAD")
    for remote in peers:
        git(repo, *_PLAIN, "push", "-q", remote, f"{head}:refs/heads/dev", f"{first}:{ref}")

    refused = _run(
        repo, "publish", "--retire", "--ref", ref, "--probe-remote", "--expect-head", head
    )

    assert refused["verdict"] == "block"
    assert {f"proposal_retirement_target_not_proposal:{remote}:{ref}" for remote in peers} <= set(
        refused["required_gaps"]
    )
    for peer in peers.values():
        assert git(peer, "rev-parse", ref) == first
