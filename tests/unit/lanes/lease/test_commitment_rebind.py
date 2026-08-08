from __future__ import annotations

import json
import os
import sqlite3
from contextlib import closing
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pytest

import ethos.adapters.mutation.lane_lifecycle.commitment_rebind as rebind
from ethos.adapters.admission.ref_intent import ref_intent_dir
from ethos.adapters.admission.transitions import work_lane_ref_transition_report
from ethos.adapters.mutation.lane_lifecycle.commitment_rebind import execute_commitment_rebind
from ethos.adapters.repo.commitment import exact_commitment_fields
from ethos.adapters.repo.commitment import load_lease_bound_commitment
from ethos.adapters.repo.dirty.change_provenance import working_overlay_sha256
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.git_effect_observation import compile_observed_git_effect
from ethos.adapters.repo.git_effects import execute_git_effect
from ethos.adapters.repo.hook_runtime import install_hook_launchers
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.coordination import CommitmentRebindRequest
from ethos.contracts.semantic import Attestation
from tests.support.ethos_cli_runner import run_ethos
from tests.support.governed_repository import git
from tests.support.governed_repository import start_adopted_work_lane


def _install_reference_transaction_hook(
    repository: Path,
    invocation_root: Path,
    _monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_hook_launchers(repository)
    if invocation_root != repository:
        install_hook_launchers(invocation_root)
    exclude = Path(
        git(
            repository,
            "rev-parse",
            "--path-format=absolute",
            "--git-path",
            "info/exclude",
        )
    )
    exclude.parent.mkdir(parents=True, exist_ok=True)
    exclude.write_text("tools/\n", encoding="utf-8")


def _bind_old_permissions(
    worktree: Path,
    branch: str,
    carrier: Path,
    permissions: tuple[str, ...],
) -> tuple[str, dict[str, object]]:
    """Commit and bind one old Commitment that cannot authorize its own rebind."""
    text = json.dumps(permissions, separators=(",", ":")).replace(",", ", ")
    commitment = worktree / carrier
    commitment.write_text(
        commitment.read_text(encoding="utf-8").replace(
            'permissions = ["git.ref.compare-and-swap"]',
            f"permissions = {text}",
        ),
        encoding="utf-8",
    )
    git(worktree, "add", carrier.as_posix())
    git(worktree, "config", "--worktree", "--unset-all", "core.hooksPath")
    git(
        worktree,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "bind minimal fixture commitment",
    )
    install_hook_launchers(worktree)
    old_head = git(worktree, "rev-parse", "HEAD")
    binding = exact_commitment_fields(worktree, head=old_head, carrier=carrier.as_posix())
    _replace_lease_payload(
        worktree,
        branch,
        expected_head=old_head,
        expected_tree=binding["expected_tree"],
        base_commitment_bytes_sha256=binding["base_commitment_bytes_sha256"],
        base_commitment_digest=binding["base_commitment_digest"],
    )
    return old_head, leases_by_branch(worktree)[branch]


@dataclass
class RebindCase:
    worktree: Path
    branch: str
    lease: dict[str, object]
    request: CommitmentRebindRequest
    target: dict[str, object]
    tracked_overlay: Path
    untracked_overlay: Path

    def execute(self, **request_updates: object) -> dict[str, object]:
        request = (
            self.request.model_copy(update=request_updates) if request_updates else self.request
        )
        return execute_commitment_rebind(root=self.worktree, request=request)

    def replace_lease(self, **updates: object) -> None:
        _replace_lease_payload(self.worktree, self.branch, **updates)

    def assert_terminal(self, report: dict[str, object]) -> None:
        updated = leases_by_branch(self.worktree)[self.branch]
        assert git(self.worktree, "rev-parse", "HEAD") == self.request.target_commit
        assert updated["epoch"] == int(self.lease["epoch"]) + 1
        assert {
            name: updated[name]
            for name in (
                "expected_head",
                "expected_tree",
                "base_commitment_path",
                "base_commitment_bytes_sha256",
                "base_commitment_digest",
            )
        } == self.target
        for name in (
            "holder_ref",
            "lease_id",
            "lane_incarnation_id",
            "expires_at",
            "path_scope",
        ):
            assert updated[name] == self.lease[name]
        attestation = report["attestation"]
        assert isinstance(attestation, dict)
        assert attestation["predicate"] == "effect:commitment-rebind"
        assert attestation["commitment_digest"] == self.lease["base_commitment_digest"]
        assert not list(ref_intent_dir(self.worktree).glob("*.json"))

    def cli_arguments(self) -> list[str]:
        arguments = ["lane", "rebind-commitment", "--root", self.worktree.as_posix()]
        for name, value in self.request.model_dump().items():
            option = "--" + name.replace("_", "-")
            if isinstance(value, bool):
                if value:
                    arguments.append(option)
            elif isinstance(value, tuple):
                for item in value:
                    arguments.extend((option, str(item)))
            else:
                arguments.extend((option, str(value)))
        return [*arguments, "--json"]


def _case(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    relocate_carrier: bool = False,
    archive_to_active: bool = False,
    old_permissions: tuple[str, ...] = ("git.ref.compare-and-swap",),
    new_permissions: tuple[str, ...] = ("git.ref.compare-and-swap",),
) -> RebindCase:
    holder = "agent:test:case:commitment-rebind"
    fixture = start_adopted_work_lane(tmp_path, holder_ref=holder)
    worktree = fixture.worktree
    _install_reference_transaction_hook(fixture.repository, worktree, monkeypatch)
    branch = git(worktree, "branch", "--show-current")
    lease = leases_by_branch(worktree)[branch]
    old_head = git(worktree, "rev-parse", "HEAD")
    carrier = Path(str(lease["base_commitment_path"]))
    commitment = worktree / carrier
    old_permission_text = json.dumps(old_permissions, separators=(",", ":"))
    old_permission_text = old_permission_text.replace(",", ", ")
    if old_permissions != ("git.ref.compare-and-swap",):
        old_head, lease = _bind_old_permissions(worktree, branch, carrier, old_permissions)
    if archive_to_active:
        git(worktree, "config", "--worktree", "--unset-all", "core.hooksPath")
        archived_carrier = Path(
            "openspec/changes/archive/2026-08-06-fixture-change/commitment.toml"
        )
        archived = worktree / archived_carrier
        archived.parent.mkdir(parents=True)
        git(worktree, "mv", carrier.as_posix(), archived_carrier.as_posix())
        git(
            worktree,
            "-c",
            "user.name=Test User",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-m",
            "archive fixture commitment",
        )
        head = git(worktree, "rev-parse", "HEAD")
        binding = exact_commitment_fields(worktree, head=head, carrier=archived_carrier.as_posix())
        _replace_lease_payload(
            worktree,
            branch,
            expected_head=head,
            expected_tree=binding["expected_tree"],
            base_commitment_path=binding["base_commitment_path"],
            base_commitment_bytes_sha256=binding["base_commitment_bytes_sha256"],
            base_commitment_digest=binding["base_commitment_digest"],
        )
        lease = leases_by_branch(worktree)[branch]
        old_head = head
        carrier = archived_carrier
        commitment = archived
        install_hook_launchers(worktree)
    target_carrier = (
        Path("openspec/changes/fixture-change/commitment.toml")
        if archive_to_active
        else Path("openspec/changes/rebound-fixture/commitment.toml")
        if relocate_carrier
        else carrier
    )
    if relocate_carrier or archive_to_active:
        (worktree / target_carrier).parent.mkdir(parents=True, exist_ok=True)
        git(worktree, "mv", carrier.as_posix(), target_carrier.as_posix())
        commitment = worktree / target_carrier
    commitment.write_text(
        commitment.read_text(encoding="utf-8")
        .replace(
            "Exercise the governed fixture lifecycle.",
            "Rebind one changed governed fixture intent.",
        )
        .replace(
            f"permissions = {old_permission_text}",
            f"permissions = {json.dumps(new_permissions).replace(': ', ':')}",
        ),
        encoding="utf-8",
    )
    git(worktree, "add", target_carrier.as_posix())
    index_tree = git(worktree, "write-tree")
    target_commit = git(
        worktree,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit-tree",
        index_tree,
        "-p",
        old_head,
        "-m",
        "rebind fixture commitment",
    )
    target = exact_commitment_fields(
        worktree,
        head=target_commit,
        carrier=target_carrier.as_posix(),
    )
    tracked_overlay = worktree / "README.md"
    tracked_overlay.write_text("# sample\n\nlocal overlay\n", encoding="utf-8")
    untracked_overlay = worktree / "notes.txt"
    untracked_overlay.write_bytes(b"untracked overlay\n")
    overlay = working_overlay_sha256(worktree)
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
        expected_working_overlay_sha256=overlay,
        target_commit=target_commit,
        new_commitment_path=target["base_commitment_path"],
        new_commitment_bytes_sha256=target["base_commitment_bytes_sha256"],
        new_commitment_digest=target["base_commitment_digest"],
        apply=True,
    )
    monkeypatch.setenv("ETHOS_ACTOR", holder)
    return RebindCase(
        worktree=worktree,
        branch=branch,
        lease=lease,
        request=request,
        target=target,
        tracked_overlay=tracked_overlay,
        untracked_overlay=untracked_overlay,
    )


@pytest.mark.parametrize(
    ("case_options", "raw_transition_gap"),
    [
        pytest.param(
            {"relocate_carrier": True},
            "lease_base_commitment_path_mismatch",
            id="active-carrier-relocation",
        ),
        pytest.param({"archive_to_active": True}, None, id="archive-to-active-rollover"),
        pytest.param(
            {"old_permissions": ("repository.read", "work-lane.write")},
            None,
            id="minimal-old-authority-bootstrap",
        ),
    ],
)
def test_commitment_rebind_owns_exact_carrier_and_authority_transitions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case_options: dict[str, object],
    raw_transition_gap: str | None,
) -> None:
    case = _case(tmp_path, monkeypatch, **case_options)
    if raw_transition_gap:
        raw_move = work_lane_ref_transition_report(
            root=case.worktree,
            phase="prepared",
            ref_name=f"refs/heads/{case.request.branch}",
            old_value=case.request.expect_head,
            new_value=case.request.target_commit,
        )
        assert raw_move["required_gaps"] == [raw_transition_gap]

    report = case.execute()
    assert report["verdict"] == "pass", report
    assert report["required_gaps"] == []
    case.assert_terminal(report)


def test_commitment_rebind_bootstrap_rejects_a_mismatched_target_digest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _case(
        tmp_path,
        monkeypatch,
        old_permissions=("repository.read", "work-lane.write"),
    )
    worktree = case.worktree
    request = case.request
    lease = case.lease
    effect = rebind.GitEffect(
        updates={
            f"refs/heads/{request.branch}": rebind.GitRefUpdate(
                expected=request.expect_head,
                desired=request.target_commit,
            )
        }
    )
    successor = rebind.old_generation(request) | {
        "epoch": request.expected_epoch + 1,
        "expected_head": request.target_commit,
        "expected_tree": request.expect_index_tree,
        "base_commitment_path": request.new_commitment_path,
        "base_commitment_bytes_sha256": request.new_commitment_bytes_sha256,
        "base_commitment_digest": request.new_commitment_digest,
    }
    successor = rebind.lease_generation(successor)
    successor.pop("payload_sha256")
    plan = compile_observed_git_effect(
        worktree,
        load_lease_bound_commitment(worktree, lease=lease),
        effect,
        head=request.expect_head,
        prior_attestations={},
        policy={
            "operation": "commitment.rebind",
            "old_commitment_digest": request.expected_commitment_digest,
            "new_commitment_digest": "0" * 64,
        },
        values={
            "lease_generation": rebind.lease_generation(lease),
            "lease_successor": successor,
            "index_tree": request.expect_index_tree,
            "working_overlay_sha256": request.expected_working_overlay_sha256,
            "new_commitment_path": request.new_commitment_path,
            "new_commitment_bytes_sha256": request.new_commitment_bytes_sha256,
            "new_commitment_digest": request.new_commitment_digest,
        },
    )

    with pytest.raises(ValueError, match="git_effect_permission_denied"):
        execute_git_effect(worktree, plan, issuer=request.holder_ref)


def _replace_lease_payload(worktree: Path, branch: str, **updates: object) -> None:
    database = state_database(worktree)
    with closing(sqlite3.connect(database)) as connection, connection:
        row = connection.execute(
            "select payload_json from leases where subject = ?",
            (branch,),
        ).fetchone()
        assert row is not None
        payload = json.loads(row[0])
        payload.update(updates)
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        connection.execute(
            "update leases set payload_json = ? where subject = ?",
            (encoded, branch),
        )
        connection.commit()


def test_commitment_rebind_preserves_overlay_and_recognizes_the_terminal_attestation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _case(tmp_path, monkeypatch)
    worktree = case.worktree
    captured = []
    execute = rebind.execute_git_effect

    def execute_and_capture(*args, **kwargs):
        assert "intent" not in kwargs
        captured.append(args[1])
        return execute(*args, **kwargs)

    monkeypatch.setattr(rebind, "execute_git_effect", execute_and_capture)
    before = (
        git(worktree, "diff", "--binary"),
        git(worktree, "ls-files", "--others", "--exclude-standard"),
        case.untracked_overlay.read_bytes(),
    )

    applied = case.execute()
    recognized = case.execute()

    case.assert_terminal(applied)
    assert applied["state"] == "applied"
    assert recognized["state"] == "recognized"
    assert applied["attestation"] == recognized["attestation"]
    assert captured[0].inputs.commitment == case.lease["base_commitment_digest"]
    assert (
        git(worktree, "diff", "--binary"),
        git(worktree, "ls-files", "--others", "--exclude-standard"),
        case.untracked_overlay.read_bytes(),
    ) == before
    assert case.tracked_overlay.read_text(encoding="utf-8") == "# sample\n\nlocal overlay\n"
    assert os.environ["ETHOS_ACTOR"] == case.request.holder_ref


def test_commitment_rebind_recovers_after_git_cas_before_lease_cas(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _case(tmp_path, monkeypatch)
    worktree = case.worktree
    apply_lease = rebind.rebind_lease_commitment
    monkeypatch.setattr(
        rebind,
        "rebind_lease_commitment",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("injected_after_git_cas")),
    )

    interrupted = case.execute()

    assert interrupted["verdict"] == "block"
    assert git(worktree, "rev-parse", "HEAD") == case.request.target_commit
    assert leases_by_branch(worktree)[case.branch]["epoch"] == case.lease["epoch"]
    assert not list(ref_intent_dir(worktree).glob("*.json"))

    monkeypatch.setattr(rebind, "rebind_lease_commitment", apply_lease)
    recovered = case.execute()

    assert recovered["state"] == "recovered"
    case.assert_terminal(recovered)


@pytest.mark.parametrize("apply_mode", [False, True], ids=["readiness", "apply"])
def test_commitment_rebind_recovers_hook_advanced_partial_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    apply_mode: bool,
) -> None:
    case = _case(tmp_path, monkeypatch)
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

    report = case.execute(apply=apply_mode)
    assert report["verdict"] == "pass"
    assert report["state"] == ("recovered" if apply_mode else "ready_to_recover")
    if apply_mode:
        case.assert_terminal(report)
    else:
        assert report["required_gaps"] == []
        assert report["lease"]["epoch"] == case.request.expected_epoch
        assert leases_by_branch(case.worktree)[case.branch]["epoch"] == case.request.expected_epoch


def test_commitment_rebind_retries_prepared_intent_when_git_cas_never_ran(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _case(tmp_path, monkeypatch)
    worktree = case.worktree
    execute = rebind.execute_git_effect
    original_hooks = Path(git(worktree, "config", "core.hooksPath"))
    injected_hooks = tmp_path / "prepared-without-cas-hooks"
    injected_hooks.mkdir()
    hook = injected_hooks / "reference-transaction"
    hook.write_text(
        (original_hooks / "reference-transaction")
        .read_text(encoding="utf-8")
        .replace(
            "#!/bin/sh\n",
            '#!/bin/sh\n[ "$1" = "prepared" ] && exit 1\n[ "$1" = "aborted" ] && exit 0\n',
            1,
        ),
        encoding="utf-8",
    )
    hook.chmod(0o755)
    git(worktree, "config", "--worktree", "core.hooksPath", injected_hooks.as_posix())

    interrupted = case.execute()

    assert interrupted["required_gaps"] == ["git_effect_cas_rejected"]
    assert git(worktree, "rev-parse", "HEAD") == case.request.expect_head
    assert not list(ref_intent_dir(worktree).glob("*.json"))
    git(worktree, "config", "--worktree", "core.hooksPath", original_hooks.as_posix())
    monkeypatch.setattr(rebind, "execute_git_effect", execute)

    applied = case.execute()

    assert applied["state"] == "applied"
    case.assert_terminal(applied)


def test_commitment_rebind_attests_after_lease_cas_without_reapplying_effects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _case(tmp_path, monkeypatch)
    worktree = case.worktree
    persist = rebind.persist_rebind_attestation
    monkeypatch.setattr(
        rebind,
        "persist_rebind_attestation",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("injected_after_lease_cas")),
    )

    interrupted = case.execute()

    assert interrupted["verdict"] == "block"
    assert git(worktree, "rev-parse", "HEAD") == case.request.target_commit
    assert leases_by_branch(worktree)[case.branch]["epoch"] == int(case.lease["epoch"]) + 1
    assert not list(ref_intent_dir(worktree).glob("*.json"))

    monkeypatch.setattr(rebind, "persist_rebind_attestation", persist)
    attested = case.execute()

    assert attested["state"] == "attested"
    case.assert_terminal(attested)


@pytest.mark.parametrize("drift", ["ref", "lease"])
def test_commitment_rebind_rechecks_terminal_state_before_attestation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    drift: str,
) -> None:
    case = _case(tmp_path, monkeypatch)
    worktree = case.worktree
    request = case.request
    branch = case.branch
    issue = rebind.issue_rebind_attestation

    def drift_before_issue(*args, **kwargs):
        git(worktree, "config", "--worktree", "--unset-all", "core.hooksPath")
        if drift == "ref":
            git(worktree, "update-ref", f"refs/heads/{branch}", request.expect_head)
        else:
            case.replace_lease(path_scope=["drift/**"])
        return issue(*args, **kwargs)

    monkeypatch.setattr(rebind, "issue_rebind_attestation", drift_before_issue)

    report = case.execute()

    assert report["verdict"] == "block"
    assert report["required_gaps"] == [
        "commitment_rebind_ref_stale"
        if drift == "ref"
        else "commitment_rebind_lease_generation_stale"
    ]


def test_commitment_rebind_recovery_rejects_complete_target_lease_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _case(tmp_path, monkeypatch)
    persist = rebind.persist_rebind_attestation
    monkeypatch.setattr(
        rebind,
        "persist_rebind_attestation",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("injected_after_lease_cas")),
    )
    interrupted = case.execute()
    assert interrupted["required_gaps"] == ["injected_after_lease_cas"]
    case.replace_lease(path_scope=["other/**"])
    monkeypatch.setattr(rebind, "persist_rebind_attestation", persist)

    report = case.execute()

    assert report["state"] == "repair_required"
    assert report["required_gaps"] == ["commitment_rebind_state_inconsistent"]


def test_commitment_rebind_recognition_rechecks_apply_actor_and_overlay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _case(tmp_path, monkeypatch)
    request = case.request
    completed = case.execute()
    assert completed["verdict"] == "pass"

    dry_run = case.execute(apply=False)
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:other")
    wrong_actor = case.execute()
    monkeypatch.setenv("ETHOS_ACTOR", request.holder_ref)
    Path(case.untracked_overlay).write_bytes(b"drifted overlay\n")
    drifted = case.execute()

    assert dry_run["required_gaps"] == ["commitment_rebind_apply_required"]
    assert wrong_actor["required_gaps"] == ["lease_actor_mismatch"]
    assert drifted["required_gaps"] == ["commitment_rebind_overlay_changed"]


def test_commitment_rebind_recognition_rejects_ref_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _case(tmp_path, monkeypatch)
    worktree = case.worktree
    request = case.request
    completed = case.execute()
    assert completed["verdict"] == "pass"
    git(worktree, "config", "--worktree", "--unset-all", "core.hooksPath")
    git(worktree, "update-ref", f"refs/heads/{request.branch}", request.expect_head)

    recognized = case.execute()

    assert recognized["state"] == "blocked"
    assert recognized["required_gaps"] == ["commitment_rebind_terminal_mismatch"]


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
def test_commitment_rebind_recognition_rejects_attestation_freshness_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    location: str,
    field: str,
    replacement: str,
) -> None:
    case = _case(tmp_path, monkeypatch)
    worktree = case.worktree
    request = case.request
    completed = case.execute()
    assert completed["verdict"] == "pass"
    effect = rebind.GitEffect(
        updates={
            f"refs/heads/{request.branch}": rebind.GitRefUpdate(
                expected=request.expect_head,
                desired=request.target_commit,
            )
        }
    )
    path = (
        Path(git_common_dir(worktree))
        / "ethos"
        / "attestations"
        / "commitment-rebind"
        / f"{effect.digest()}.json"
    )
    payload = deepcopy(completed["attestation"])
    assert isinstance(payload, dict)
    if location == "attestation":
        payload[field] = replacement
    else:
        statement = payload["statement"]
        assert isinstance(statement, dict)
        target = statement if location == "statement" else statement[location]
        target[field] = replacement
    payload["statement_digest"] = "0" * 64
    payload["id"] = "0" * 64
    payload["issued_at"] = datetime.fromisoformat(str(payload["issued_at"]))
    payload["valid_from"] = datetime.fromisoformat(str(payload["valid_from"]))
    payload["advisories"] = tuple(payload["advisories"])
    payload["evidence_refs"] = tuple(payload["evidence_refs"])
    tampered = Attestation.issue(
        {
            name: value
            for name, value in payload.items()
            if name not in {"schema_version", "id", "statement_digest"}
        }
    )
    path.write_text(tampered.canonical_json(), encoding="utf-8")

    recognized = case.execute()

    assert recognized["state"] == "repair_required"
    assert recognized["required_gaps"] == ["commitment_rebind_terminal_mismatch"]


@pytest.mark.parametrize(
    "carrier_mode",
    ["stable", "relocated"],
    ids=["stable-carrier", "relocated"],
)
def test_commitment_rebind_cli_projects_terminal_transaction_and_carrier(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    carrier_mode: str,
) -> None:
    relocate_carrier = carrier_mode == "relocated"
    case = _case(tmp_path, monkeypatch, relocate_carrier=relocate_carrier)
    arguments = case.cli_arguments()

    applied = run_ethos(*arguments, cwd=case.worktree)
    assert applied["data"]["verdict"] == "pass"
    assert applied["data"]["lease"]["base_commitment_path"] == case.request.new_commitment_path

    if not relocate_carrier:
        recognized = run_ethos(*arguments, cwd=case.worktree)
        assert (applied["data"]["state"], recognized["data"]["state"]) == (
            "applied",
            "recognized",
        )
        assert applied["data"]["attestation"] == recognized["data"]["attestation"]


@pytest.mark.parametrize(
    ("mutation", "updates", "expected_gap"),
    [
        (
            "lease",
            {"lane_incarnation_id": "lane-incarnation:other"},
            "lease_lane_incarnation_id_stale",
        ),
        ("lease", {"expected_tree": "0" * 40}, "lease_expected_tree_stale"),
        (
            "lease",
            {"base_commitment_path": "openspec/changes/other/commitment.toml"},
            "lease_commitment_path_stale",
        ),
        ("request", {"expected_issued_at": "2026-01-01T00:00:00+00:00"}, "lease_issued_at_stale"),
        ("request", {"expected_renewed_at": "2026-01-01T00:00:00+00:00"}, "lease_renewed_at_stale"),
        ("request", {"expected_path_scope": ("other/**",)}, "lease_path_scope_stale"),
    ],
)
def test_commitment_rebind_rejects_inexact_old_generation_coordinates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
    updates: dict[str, object],
    expected_gap: str,
) -> None:
    case = _case(tmp_path, monkeypatch)
    if mutation == "lease":
        case.replace_lease(**updates)
        report = case.execute()
    else:
        report = case.execute(**updates)

    assert report["required_gaps"] == [expected_gap]
    assert git(case.worktree, "rev-parse", "HEAD") == case.request.expect_head


def test_commitment_rebind_blocks_impossible_lease_ahead_of_ref(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _case(tmp_path, monkeypatch)
    worktree = case.worktree
    branch = case.branch
    lease = case.lease
    target = case.target
    _replace_lease_payload(
        worktree,
        branch,
        epoch=int(lease["epoch"]) + 1,
        **target,
    )

    report = case.execute()

    assert report["state"] == "blocked"
    assert report["required_gaps"] == ["commitment_rebind_state_inconsistent"]
