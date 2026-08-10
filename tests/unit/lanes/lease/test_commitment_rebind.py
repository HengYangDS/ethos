from __future__ import annotations

import json
import os
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

import pytest

import ethos.adapters.mutation.lane_lifecycle.commitment_rebind as rebind
import ethos.adapters.mutation.lane_lifecycle.commitment_rebind_admission as rebind_admission
from ethos.adapters.admission.ref_intent import ref_intent_dir
from ethos.adapters.admission.transitions import work_lane_ref_transition_report
from ethos.adapters.repo.commit_identity import commit_trust_setup_action
from ethos.adapters.repo.commitment import exact_commitment_fields
from ethos.adapters.repo.dirty.change_provenance import working_overlay_sha256
from ethos.adapters.repo.hook_runtime import install_hook_launchers
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.coordination import CommitmentRebindRequest
from ethos.contracts.semantic import Commitment
from ethos.repository.openspec.identifiers import malformed_change_identity_repair_valid
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.governed_repository import git
from tests.support.governed_repository import start_adopted_work_lane
from tests.support.lifecycle_cases import rebind_attestation_path
from tests.support.lifecycle_cases import rebind_effect
from tests.support.lifecycle_cases import tamper_attestation
from tests.support.literal_cases import literal_case


def _replace_lease(worktree: Path, branch: str, **updates: object) -> None:
    with closing(sqlite3.connect(state_database(worktree))) as connection, connection:
        row = connection.execute(
            "select payload_json from leases where subject = ?", (branch,)
        ).fetchone()
        assert row
        payload = json.loads(row[0]) | updates
        connection.execute(
            "update leases set payload_json = ? where subject = ?",
            (json.dumps(payload, sort_keys=True, separators=(",", ":")), branch),
        )


def _install_hooks(repository: Path, worktree: Path) -> None:
    install_hook_launchers(repository)
    install_hook_launchers(worktree)
    exclude = Path(
        git(repository, "rev-parse", "--path-format=absolute", "--git-path", "info/exclude")
    )
    exclude.parent.mkdir(parents=True, exist_ok=True)
    exclude.write_text("tools/\n", encoding="utf-8")


def _identity_content(
    content: str, *, repair: bool, old: bool, semantic_rename: bool = False
) -> str:
    if not repair:
        return content
    if semantic_rename:
        return (
            content
            if old
            else content.replace(
                'id = "change:fixture-change"',
                'id = "change:declared-fixture"',
            ).replace(
                "Exercise the governed fixture lifecycle.",
                "Declare the renamed governed fixture lifecycle.",
            )
        )
    source, target = (
        ('id = "change:fixture-change"', 'id = "change:20260809-fixture-change"')
        if old
        else ('id = "change:20260809-fixture-change"', 'id = "change:fixture-change"')
    )
    return content.replace(source, target)


def _bind_fixture_commitment(
    worktree: Path, branch: str, carrier: Path, old_head: str
) -> tuple[str, dict[str, object]]:
    git(worktree, "add", carrier.as_posix())
    index = git(worktree, "write-tree")
    old_head = git(
        worktree, "commit-tree", index, "-p", old_head, "-m", "bind minimal fixture commitment"
    )
    git(worktree, "config", "--worktree", "--unset-all", "core.hooksPath")
    git(worktree, "update-ref", f"refs/heads/{branch}", old_head)
    git(worktree, "reset", "--hard", old_head)
    install_hook_launchers(worktree)
    binding = exact_commitment_fields(worktree, head=old_head, carrier=carrier.as_posix())
    _replace_lease(worktree, branch, **binding)
    return old_head, leases_by_branch(worktree)[branch]


@dataclass
class RebindCase:
    worktree: Path
    branch: str
    lease: dict[str, object]
    request: CommitmentRebindRequest
    target: dict[str, object]
    tracked: Path
    untracked: Path

    def execute(self, **updates: object) -> dict[str, object]:
        request = self.request.model_copy(update=updates) if updates else self.request
        return rebind.execute_commitment_rebind(root=self.worktree, request=request)

    def replace_lease(self, **updates: object) -> None:
        _replace_lease(self.worktree, self.branch, **updates)

    def assert_terminal(self, report: dict[str, object]) -> None:
        updated = leases_by_branch(self.worktree)[self.branch]
        assert git(self.worktree, "rev-parse", "HEAD") == self.request.target_commit
        assert updated["epoch"] == int(self.lease["epoch"]) + 1
        assert {name: updated[name] for name in self.target} == self.target
        for name in (
            "holder_ref",
            "lease_id",
            "lane_incarnation_id",
            "issued_at",
            "renewed_at",
            "expires_at",
            "path_scope",
            "handoff",
        ):
            assert updated[name] == self.lease[name]
        attestation = report["attestation"]
        assert isinstance(attestation, dict)
        assert (attestation["predicate"], attestation["commitment_digest"]) == (
            "effect:commitment-rebind",
            self.lease["base_commitment_digest"],
        )
        assert not list(ref_intent_dir(self.worktree).glob("*.json"))


def _case(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    carrier_mode: str = "stable",
    old_permissions: tuple[str, ...] = ("git.ref.compare-and-swap",),
    repair_identity: bool = False,
    semantic_rename: bool = False,
) -> RebindCase:
    holder = "agent:test:case:commitment-rebind"
    fixture = start_adopted_work_lane(tmp_path, holder_ref=holder)
    worktree = fixture.worktree
    _install_hooks(fixture.repository, worktree)
    branch = git(worktree, "branch", "--show-current")
    lease = leases_by_branch(worktree)[branch]
    carrier = Path(str(lease["base_commitment_path"]))
    old_head = git(worktree, "rev-parse", "HEAD")
    if old_permissions != ("git.ref.compare-and-swap",) or repair_identity:
        commitment = worktree / carrier
        content = commitment.read_text(encoding="utf-8").replace(
            'permissions = ["git.ref.compare-and-swap"]',
            f"permissions = {json.dumps(old_permissions).replace(',', ', ')}",
        )
        commitment.write_text(
            _identity_content(
                content,
                repair=repair_identity,
                old=True,
                semantic_rename=semantic_rename,
            ),
            encoding="utf-8",
        )
        old_head, lease = _bind_fixture_commitment(worktree, branch, carrier, old_head)
    if carrier_mode == "archive-active":
        archived = Path("openspec/changes/archive/2026-08-06-fixture-change/commitment.toml")
        (worktree / archived).parent.mkdir(parents=True)
        git(worktree, "config", "--worktree", "--unset-all", "core.hooksPath")
        git(worktree, "mv", carrier.as_posix(), archived.as_posix())
        git(
            worktree,
            "commit",
            "-m",
            "archive fixture commitment",
        )
        old_head, carrier = git(worktree, "rev-parse", "HEAD"), archived
        binding = exact_commitment_fields(worktree, head=old_head, carrier=carrier.as_posix())
        _replace_lease(worktree, branch, **binding)
        lease = leases_by_branch(worktree)[branch]
        install_hook_launchers(worktree)
    target_carrier = {
        "stable": carrier,
        "relocated": Path("openspec/changes/rebound-fixture/commitment.toml"),
        "archive-active": Path("openspec/changes/fixture-change/commitment.toml"),
        "semantic-rename": Path("openspec/changes/declared-fixture/commitment.toml"),
    }[carrier_mode]
    if target_carrier != carrier:
        (worktree / target_carrier).parent.mkdir(parents=True, exist_ok=True)
        git(worktree, "mv", carrier.as_posix(), target_carrier.as_posix())
    commitment = worktree / target_carrier
    content = commitment.read_text(encoding="utf-8")
    content = _identity_content(
        content,
        repair=repair_identity,
        old=False,
        semantic_rename=semantic_rename,
    )
    if not repair_identity:
        content = content.replace(
            "Exercise the governed fixture lifecycle.",
            "Rebind one changed governed fixture intent.",
        )
    commitment.write_text(content, encoding="utf-8")
    git(worktree, "add", target_carrier.as_posix())
    index_tree = git(worktree, "write-tree")
    target_commit = git(
        worktree,
        "commit-tree",
        index_tree,
        "-p",
        old_head,
        "-m",
        "rebind fixture commitment",
    )
    target = exact_commitment_fields(
        worktree, head=target_commit, carrier=target_carrier.as_posix()
    )
    tracked, untracked = worktree / "README.md", worktree / "notes.txt"
    tracked.write_text("# sample\n\nlocal overlay\n", encoding="utf-8")
    untracked.write_bytes(b"untracked overlay\n")
    request = CommitmentRebindRequest(
        branch=branch,
        holder_ref=holder,
        lease_id=str(lease["lease_id"]),
        expected_lane_incarnation_id=str(lease["lane_incarnation_id"]),
        expected_epoch=int(lease["epoch"]),
        expected_issued_at=str(lease["issued_at"]),
        expected_renewed_at=str(lease["renewed_at"]),
        expected_expires_at=str(lease["expires_at"]),
        expected_path_scope=tuple(lease["path_scope"]),
        expected_payload_sha256=str(lease["payload_sha256"]),
        expect_head=old_head,
        expected_tree=str(lease["expected_tree"]),
        expected_commitment_path=str(lease["base_commitment_path"]),
        expected_commitment_bytes_sha256=str(lease["base_commitment_bytes_sha256"]),
        expected_commitment_digest=str(lease["base_commitment_digest"]),
        expect_index_tree=index_tree,
        expected_working_overlay_sha256=working_overlay_sha256(worktree),
        target_commit=target_commit,
        new_commitment_path=target["base_commitment_path"],
        new_commitment_bytes_sha256=target["base_commitment_bytes_sha256"],
        new_commitment_digest=target["base_commitment_digest"],
        repair_change_identity=repair_identity,
        apply=True,
    )
    monkeypatch.setenv("ETHOS_ACTOR", holder)
    return RebindCase(worktree, branch, lease, request, target, tracked, untracked)


@pytest.mark.parametrize(
    ("mode", "permissions", "raw_gap"),
    literal_case(
        "lanes.lease.test_commitment_rebind:parametrize:test_rebind_owns_carrier_and_authority:0"
    ),
)
def test_rebind_owns_carrier_and_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
    permissions: tuple[str, ...],
    raw_gap: str | None,
) -> None:
    case = _case(tmp_path, monkeypatch, carrier_mode=mode, old_permissions=permissions)
    if raw_gap:
        raw = work_lane_ref_transition_report(
            root=case.worktree,
            phase="prepared",
            ref_name=f"refs/heads/{case.branch}",
            old_value=case.request.expect_head,
            new_value=case.request.target_commit,
        )
        assert raw["required_gaps"] == [raw_gap]
    report = case.execute()
    assert (report["verdict"], report["required_gaps"]) == ("pass", [])
    case.assert_terminal(report)


@pytest.mark.parametrize("trust_gaps", [("commit_signature_untrusted",), ()])
def test_change_identity_repair_requires_target_trust(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, trust_gaps: tuple[str, ...]
) -> None:
    case = _case(tmp_path, monkeypatch, repair_identity=True)
    monkeypatch.setattr(
        rebind_admission,
        "verify_commit_trust",
        lambda *_args: {"required_gaps": list(trust_gaps)},
    )
    report = case.execute()
    assert report["required_gaps"] == list(trust_gaps)
    if not trust_gaps:
        case.assert_terminal(report)


def test_change_identity_repair_accepts_one_exact_semantic_rename() -> None:
    old = Commitment(
        id="change:terminal-convergence",
        intent="Declare publication peers.",
        subjects=("repository:self",),
        scope=("src/**",),
    )
    renamed = old.model_copy(update={"id": "change:declared-publication-peers"})

    assert malformed_change_identity_repair_valid(
        carrier="openspec/changes/declared-publication-peers/commitment.toml",
        old_id=old.id,
        old_digest=old.digest(),
        new=renamed,
    )


def test_change_identity_repair_accepts_a_semantic_change_during_rename() -> None:
    old = Commitment(
        id="change:terminal-convergence",
        intent="Declare publication peers.",
        subjects=("repository:self",),
        scope=("src/**",),
    )
    changed = old.model_copy(
        update={
            "id": "change:declared-publication-peers",
            "scope": ("src/**", "tests/**"),
        }
    )

    assert malformed_change_identity_repair_valid(
        carrier="openspec/changes/declared-publication-peers/commitment.toml",
        old_id=old.id,
        old_digest=old.digest(),
        new=changed,
    )


def test_change_identity_repair_applies_one_exact_semantic_rename(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = _case(
        tmp_path,
        monkeypatch,
        carrier_mode="semantic-rename",
        repair_identity=True,
        semantic_rename=True,
    )
    monkeypatch.setattr(
        rebind_admission,
        "verify_commit_trust",
        lambda *_args: {"required_gaps": []},
    )

    report = case.execute()

    assert (report["verdict"], report["required_gaps"]) == ("pass", [])
    case.assert_terminal(report)


def test_change_identity_repair_projects_trust_setup_action(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = _case(tmp_path, monkeypatch, repair_identity=True)
    monkeypatch.setattr(
        rebind_admission,
        "verify_commit_trust",
        lambda *_args: {"required_gaps": ["commit_signature_untrusted"]},
    )

    report = case.execute()

    assert report["next_action"] == commit_trust_setup_action(case.worktree, case.target)
    arguments = ["lane", "rebind-commitment", "--root", case.worktree.as_posix()]
    for name, value in case.request.model_dump().items():
        option = "--" + name.replace("_", "-")
        for item in value if isinstance(value, tuple) else (value,):
            arguments.extend(
                (option,) if item is True else () if item is False else (option, str(item))
            )
    result = run_ethos_blocked(*arguments, "--json", cwd=case.worktree)
    assert result["next_action"] == report["next_action"]


@pytest.mark.parametrize(
    "checkpoint",
    ["git-cas", "partial-ready", "partial-apply", "prepared", "lease-cas"],
)
def test_rebind_checkpoint_matrix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, checkpoint: str
) -> None:
    case = _case(tmp_path, monkeypatch)
    epoch = int(case.lease["epoch"])
    if checkpoint.startswith("partial"):
        git(case.worktree, "config", "--worktree", "--unset-all", "core.hooksPath")
        git(
            case.worktree,
            "update-ref",
            f"refs/heads/{case.branch}",
            case.request.target_commit,
            case.request.expect_head,
        )
        case.replace_lease(
            expected_head=case.request.target_commit,
            expected_tree=case.request.expect_index_tree,
        )
        apply = checkpoint == "partial-apply"
        report = case.execute(apply=apply)
        assert report["state"] == ("recovered" if apply else "ready_to_recover")
        assert leases_by_branch(case.worktree)[case.branch]["epoch"] == epoch + int(apply)
        if apply:
            case.assert_terminal(report)
        return
    if checkpoint == "prepared":
        original = Path(git(case.worktree, "config", "core.hooksPath"))
        hooks = tmp_path / "reject-prepared"
        hooks.mkdir()
        hook = hooks / "reference-transaction"
        hook.write_text(
            (original / hook.name)
            .read_text(encoding="utf-8")
            .replace("#!/bin/sh\n", '#!/bin/sh\n[ "$1" = "prepared" ] && exit 1\n', 1),
            encoding="utf-8",
        )
        hook.chmod(0o755)
        git(case.worktree, "config", "--worktree", "core.hooksPath", hooks.as_posix())
        interrupted = case.execute()
        assert interrupted["required_gaps"] == ["git_effect_cas_rejected"]
        assert git(case.worktree, "rev-parse", "HEAD") == case.request.expect_head
        git(case.worktree, "config", "--worktree", "core.hooksPath", original.as_posix())
        report = case.execute()
        assert report["state"] == "applied"
        case.assert_terminal(report)
        return
    attribute = (
        "rebind_lease_commitment" if checkpoint == "git-cas" else "persist_rebind_attestation"
    )
    original = getattr(rebind, attribute)
    message = f"injected_after_{checkpoint.replace('-', '_')}"
    error = ValueError if checkpoint == "git-cas" else OSError
    monkeypatch.setattr(
        rebind, attribute, lambda *_args, **_kwargs: (_ for _ in ()).throw(error(message))
    )
    interrupted = case.execute()
    assert interrupted["verdict"] == "block"
    assert git(case.worktree, "rev-parse", "HEAD") == case.request.target_commit
    assert leases_by_branch(case.worktree)[case.branch]["epoch"] == epoch + int(
        checkpoint == "lease-cas"
    )
    assert not list(ref_intent_dir(case.worktree).glob("*.json"))
    monkeypatch.setattr(rebind, attribute, original)
    report = case.execute()
    assert report["state"] == ("recovered" if checkpoint == "git-cas" else "attested")
    case.assert_terminal(report)


def test_rebind_preserves_overlay_and_recognizes_idempotently(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = _case(tmp_path, monkeypatch)
    captured = []
    execute = rebind.execute_git_effect

    def capture(*args, **kwargs):
        assert "intent" not in kwargs
        captured.append(args[1])
        return execute(*args, **kwargs)

    monkeypatch.setattr(rebind, "execute_git_effect", capture)
    before = (
        git(case.worktree, "diff", "--binary"),
        git(case.worktree, "ls-files", "--others", "--exclude-standard"),
        case.untracked.read_bytes(),
    )
    applied, repeated = case.execute(), case.execute()
    case.assert_terminal(applied)
    assert (applied["state"], repeated["state"]) == ("applied", "recognized")
    assert applied["attestation"] == repeated["attestation"]
    assert captured[0].inputs.commitment == case.lease["base_commitment_digest"]
    assert (
        git(case.worktree, "diff", "--binary"),
        git(case.worktree, "ls-files", "--others", "--exclude-standard"),
        case.untracked.read_bytes(),
    ) == before
    assert case.tracked.read_text(encoding="utf-8") == "# sample\n\nlocal overlay\n"
    assert os.environ["ETHOS_ACTOR"] == case.request.holder_ref


@pytest.mark.parametrize(
    "drift",
    ["issue-ref", "issue-lease", "recovery-lease", "dry-run", "actor", "overlay", "ref"],
)
def test_rebind_runtime_and_recovery_drift_matrix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, drift: str
) -> None:
    case = _case(tmp_path, monkeypatch)
    if drift == "recovery-lease":
        persist = rebind.persist_rebind_attestation
        monkeypatch.setattr(
            rebind,
            "persist_rebind_attestation",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("after lease cas")),
        )
        assert case.execute()["verdict"] == "block"
        case.replace_lease(path_scope=["other/**"])
        monkeypatch.setattr(rebind, "persist_rebind_attestation", persist)
        report = case.execute()
        assert (report["state"], report["required_gaps"]) == (
            "repair_required",
            ["commitment_rebind_state_inconsistent"],
        )
        return
    if drift.startswith("issue"):
        issue = rebind.issue_rebind_attestation

        def inject(*args, **kwargs):
            git(case.worktree, "config", "--worktree", "--unset-all", "core.hooksPath")
            if drift == "issue-ref":
                git(
                    case.worktree,
                    "update-ref",
                    f"refs/heads/{case.branch}",
                    case.request.expect_head,
                )
            else:
                case.replace_lease(path_scope=["drift/**"])
            return issue(*args, **kwargs)

        monkeypatch.setattr(rebind, "issue_rebind_attestation", inject)
        report = case.execute()
        expected = (
            "commitment_rebind_ref_stale"
            if drift == "issue-ref"
            else "commitment_rebind_lease_generation_stale"
        )
        assert report["required_gaps"] == [expected]
        return
    assert case.execute()["verdict"] == "pass"
    if drift == "dry-run":
        report, expected = case.execute(apply=False), "commitment_rebind_apply_required"
    elif drift == "actor":
        monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:other")
        report, expected = case.execute(), "lease_actor_mismatch"
    elif drift == "overlay":
        case.untracked.write_bytes(b"drifted overlay\n")
        report, expected = case.execute(), "commitment_rebind_overlay_changed"
    else:
        git(case.worktree, "config", "--worktree", "--unset-all", "core.hooksPath")
        git(case.worktree, "update-ref", f"refs/heads/{case.branch}", case.request.expect_head)
        report, expected = case.execute(), "commitment_rebind_terminal_mismatch"
        assert report["state"] == "blocked"
    assert report["required_gaps"] == [expected]


@pytest.mark.parametrize(
    ("location", "field", "replacement"),
    [
        ("attestation", "facts_digest", "0" * 64),
        ("statement", "index_tree", "0" * 40),
        ("statement", "working_overlay_sha256", "0" * 64),
        ("statement", "observed_at", "2026-01-01T00:00:00+00:00"),
        ("freshness", "head", "0" * 40),
        ("old_lease_generation", "expected_tree", "0" * 40),
        ("new_lease_generation", "base_commitment_path", "other.toml"),
        ("new_commitment", "base_commitment_bytes_sha256", "0" * 64),
        ("result", "lease", "unchanged"),
    ],
)
def test_rebind_attestation_freshness_matrix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    location: str,
    field: str,
    replacement: str,
) -> None:
    case = _case(tmp_path, monkeypatch)
    completed = case.execute()
    attestation = completed["attestation"]
    assert completed["verdict"] == "pass"
    assert isinstance(attestation, dict)
    path = rebind_attestation_path(case.worktree, rebind_effect(case))
    path.write_text(
        tamper_attestation(
            attestation, location=location, field=field, replacement=replacement
        ).canonical_json(),
        encoding="utf-8",
    )
    report = case.execute()
    assert (report["state"], report["required_gaps"]) == (
        "repair_required",
        ["commitment_rebind_terminal_mismatch"],
    )


@pytest.mark.parametrize("mode", ["stable", "relocated", "lease-ahead"])
def test_rebind_cli_and_impossible_state_matrix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    case = _case(
        tmp_path, monkeypatch, carrier_mode="relocated" if mode == "relocated" else "stable"
    )
    if mode == "lease-ahead":
        case.replace_lease(epoch=int(case.lease["epoch"]) + 1, **case.target)
        report = case.execute()
        assert (report["state"], report["required_gaps"]) == (
            "blocked",
            ["commitment_rebind_state_inconsistent"],
        )
        return
    arguments = ["lane", "rebind-commitment", "--root", case.worktree.as_posix()]
    for name, value in case.request.model_dump().items():
        option = "--" + name.replace("_", "-")
        for item in value if isinstance(value, tuple) else (value,):
            arguments.extend(
                (option,) if item is True else () if item is False else (option, str(item))
            )
    arguments.append("--json")
    applied = run_ethos(*arguments, cwd=case.worktree)["data"]
    assert applied["verdict"] == "pass"
    assert applied["lease"]["base_commitment_path"] == case.request.new_commitment_path
    if mode == "stable":
        repeated = run_ethos(*arguments, cwd=case.worktree)["data"]
        assert (applied["state"], repeated["state"]) == ("applied", "recognized")
        assert applied["attestation"] == repeated["attestation"]


@pytest.mark.parametrize(
    ("location", "updates", "gap"),
    literal_case(
        "lanes.lease.test_commitment_rebind:parametrize:test_rebind_exact_old_generation_matrix:derived"
    ),
)
def test_rebind_exact_old_generation_matrix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    location: str,
    updates: dict[str, object],
    gap: str,
) -> None:
    case = _case(tmp_path, monkeypatch)
    if location == "lease":
        case.replace_lease(**updates)
        report = case.execute()
    else:
        report = case.execute(**updates)
    assert report["required_gaps"] == [gap]
    assert git(case.worktree, "rev-parse", "HEAD") == case.request.expect_head
