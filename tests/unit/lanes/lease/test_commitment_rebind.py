from __future__ import annotations

import json
import os
import shutil
import sqlite3
import sys
from contextlib import closing
from copy import deepcopy
from datetime import datetime
from pathlib import Path

import pytest

import ethos.adapters.mutation.lane_lifecycle.commitment_rebind as rebind
from ethos.adapters.admission.ref_intent import ref_intent_dir
from ethos.adapters.admission.transitions import work_lane_ref_transition_report
from ethos.adapters.mutation.lane_lifecycle.commitment_rebind import execute_commitment_rebind
from ethos.adapters.repo.commitment import exact_commitment_fields
from ethos.adapters.repo.dirty.change_provenance import working_overlay_sha256
from ethos.adapters.repo.git import git_common_dir
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
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hooks = repository / ".githooks"
    hooks.mkdir(parents=True, exist_ok=True)
    source = Path(__file__).resolve().parents[4] / ".githooks/reference-transaction"
    hook = Path(shutil.copy(source, hooks / "reference-transaction"))
    hook.chmod(0o755)
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
    runtime = invocation_root / "tools/ci/scripts/with-python-runtime.sh"
    runtime.parent.mkdir(parents=True, exist_ok=True)
    runtime.write_text('#!/bin/sh\n[ "$1" = "--" ] && shift\nexec "$@"\n', encoding="utf-8")
    runtime.chmod(0o755)
    git(repository, "config", "core.hooksPath", hooks.as_posix())
    monkeypatch.setenv("ETHOS_PYTHON", sys.executable)


def _case(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    relocate_carrier: bool = False,
    archive_to_active: bool = False,
    minimal_permissions: bool = False,
) -> dict[str, object]:
    holder = "agent:test:case:commitment-rebind"
    fixture = start_adopted_work_lane(tmp_path, holder_ref=holder)
    worktree = fixture.worktree
    _install_reference_transaction_hook(fixture.repository, worktree, monkeypatch)
    branch = git(worktree, "branch", "--show-current")
    lease = leases_by_branch(worktree)[branch]
    old_head = git(worktree, "rev-parse", "HEAD")
    carrier = Path(str(lease["base_commitment_path"]))
    commitment = worktree / carrier
    if archive_to_active:
        git(worktree, "config", "--unset-all", "core.hooksPath")
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
        git(worktree, "config", "core.hooksPath", (worktree / ".githooks").as_posix())
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
            'permissions = ["git.ref.compare-and-swap"]',
            'permissions = ["repository.read", "work-lane.write"]'
            if minimal_permissions
            else 'permissions = ["git.ref.compare-and-swap"]',
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
    return {
        "fixture": fixture,
        "worktree": worktree,
        "branch": branch,
        "lease": lease,
        "request": request,
        "target": target,
        "target_commit": target_commit,
        "tracked_overlay": tracked_overlay,
        "untracked_overlay": untracked_overlay,
        "overlay": overlay,
    }


def test_commitment_rebind_owns_one_exact_carrier_relocation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _case(tmp_path, monkeypatch, relocate_carrier=True)
    worktree = case["worktree"]
    request = case["request"]
    assert isinstance(worktree, Path)
    assert isinstance(request, CommitmentRebindRequest)

    raw_move = work_lane_ref_transition_report(
        root=worktree,
        phase="prepared",
        ref_name=f"refs/heads/{request.branch}",
        old_value=request.expect_head,
        new_value=request.target_commit,
    )
    report = execute_commitment_rebind(root=worktree, request=request)

    assert raw_move["required_gaps"] == ["lease_base_commitment_path_mismatch"]
    assert report["required_gaps"] == [], report
    assert report["verdict"] == "pass", report
    _assert_terminal(case, report)


def test_commitment_rebind_owns_one_archive_to_active_carrier_rollover(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _case(tmp_path, monkeypatch, archive_to_active=True)
    worktree = case["worktree"]
    request = case["request"]
    assert isinstance(worktree, Path)
    assert isinstance(request, CommitmentRebindRequest)

    report = execute_commitment_rebind(root=worktree, request=request)

    assert report["required_gaps"] == [], report
    assert report["verdict"] == "pass", report
    _assert_terminal(case, report)


def test_commitment_rebind_uses_exact_cas_bootstrap_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _case(tmp_path, monkeypatch, minimal_permissions=True)
    worktree = case["worktree"]
    request = case["request"]
    assert isinstance(worktree, Path)
    assert isinstance(request, CommitmentRebindRequest)

    report = execute_commitment_rebind(root=worktree, request=request)

    assert report["verdict"] == "pass", report
    _assert_terminal(case, report)


def _assert_terminal(case: dict[str, object], report: dict[str, object]) -> None:
    worktree = case["worktree"]
    branch = case["branch"]
    lease = case["lease"]
    target = case["target"]
    assert isinstance(worktree, Path)
    assert isinstance(branch, str)
    assert isinstance(lease, dict)
    assert isinstance(target, dict)
    updated = leases_by_branch(worktree)[branch]
    assert git(worktree, "rev-parse", "HEAD") == case["target_commit"]
    assert updated["epoch"] == int(lease["epoch"]) + 1
    assert {
        name: updated[name]
        for name in (
            "expected_head",
            "expected_tree",
            "base_commitment_path",
            "base_commitment_bytes_sha256",
            "base_commitment_digest",
        )
    } == target
    assert updated["holder_ref"] == lease["holder_ref"]
    assert updated["lease_id"] == lease["lease_id"]
    assert updated["lane_incarnation_id"] == lease["lane_incarnation_id"]
    assert updated["expires_at"] == lease["expires_at"]
    assert updated["path_scope"] == lease["path_scope"]
    attestation = report["attestation"]
    assert isinstance(attestation, dict)
    assert attestation["predicate"] == "effect:commitment-rebind"
    assert attestation["commitment_digest"] == lease["base_commitment_digest"]
    assert not list(ref_intent_dir(worktree).glob("*.json"))


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
    worktree = case["worktree"]
    request = case["request"]
    assert isinstance(worktree, Path)
    assert isinstance(request, CommitmentRebindRequest)
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
        case["untracked_overlay"].read_bytes(),
    )

    applied = execute_commitment_rebind(root=worktree, request=request)
    recognized = execute_commitment_rebind(root=worktree, request=request)

    _assert_terminal(case, applied)
    assert applied["state"] == "applied"
    assert recognized["state"] == "recognized"
    assert applied["attestation"] == recognized["attestation"]
    assert captured[0].inputs.commitment == case["lease"]["base_commitment_digest"]
    assert (
        git(worktree, "diff", "--binary"),
        git(worktree, "ls-files", "--others", "--exclude-standard"),
        case["untracked_overlay"].read_bytes(),
    ) == before
    assert case["tracked_overlay"].read_text(encoding="utf-8") == "# sample\n\nlocal overlay\n"
    assert os.environ["ETHOS_ACTOR"] == request.holder_ref


def test_commitment_rebind_recovers_after_git_cas_before_lease_cas(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _case(tmp_path, monkeypatch)
    worktree = case["worktree"]
    request = case["request"]
    assert isinstance(worktree, Path)
    assert isinstance(request, CommitmentRebindRequest)
    apply_lease = rebind.rebind_lease_commitment
    monkeypatch.setattr(
        rebind,
        "rebind_lease_commitment",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("injected_after_git_cas")),
    )

    interrupted = execute_commitment_rebind(root=worktree, request=request)

    assert interrupted["verdict"] == "block"
    assert git(worktree, "rev-parse", "HEAD") == case["target_commit"]
    assert leases_by_branch(worktree)[case["branch"]]["epoch"] == case["lease"]["epoch"]
    assert not list(ref_intent_dir(worktree).glob("*.json"))

    monkeypatch.setattr(rebind, "rebind_lease_commitment", apply_lease)
    recovered = execute_commitment_rebind(root=worktree, request=request)

    assert recovered["state"] == "recovered"
    _assert_terminal(case, recovered)


def test_commitment_rebind_recovers_after_hook_advanced_only_the_lease_head(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _case(tmp_path, monkeypatch)
    worktree = case["worktree"]
    branch = case["branch"]
    lease = case["lease"]
    request = case["request"]
    assert isinstance(worktree, Path)
    assert isinstance(branch, str)
    assert isinstance(lease, dict)
    assert isinstance(request, CommitmentRebindRequest)
    git(worktree, "config", "--unset-all", "core.hooksPath")
    git(worktree, "update-ref", f"refs/heads/{branch}", request.target_commit, request.expect_head)
    _replace_lease_payload(
        worktree,
        branch,
        expected_head=request.target_commit,
        expected_tree=request.expect_index_tree,
    )

    recovered = execute_commitment_rebind(root=worktree, request=request)

    assert recovered["state"] == "recovered"
    _assert_terminal(case, recovered)


def test_commitment_rebind_retries_prepared_intent_when_git_cas_never_ran(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _case(tmp_path, monkeypatch)
    worktree = case["worktree"]
    request = case["request"]
    assert isinstance(worktree, Path)
    assert isinstance(request, CommitmentRebindRequest)
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
            '#!/bin/sh\n[ "$1" = "aborted" ] && exit 0\n',
            1,
        )
        .replace(
            "done\nexit 0\n",
            'done\n[ "$phase" = "prepared" ] && exit 1\nexit 0\n',
            1,
        ),
        encoding="utf-8",
    )
    hook.chmod(0o755)
    git(worktree, "config", "core.hooksPath", injected_hooks.as_posix())

    interrupted = execute_commitment_rebind(root=worktree, request=request)

    assert interrupted["required_gaps"] == ["git_effect_cas_rejected"]
    assert git(worktree, "rev-parse", "HEAD") == request.expect_head
    assert not list(ref_intent_dir(worktree).glob("*.json"))
    git(worktree, "config", "core.hooksPath", original_hooks.as_posix())
    monkeypatch.setattr(rebind, "execute_git_effect", execute)

    applied = execute_commitment_rebind(root=worktree, request=request)

    assert applied["state"] == "applied"
    _assert_terminal(case, applied)


def test_commitment_rebind_attests_after_lease_cas_without_reapplying_effects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _case(tmp_path, monkeypatch)
    worktree = case["worktree"]
    request = case["request"]
    assert isinstance(worktree, Path)
    assert isinstance(request, CommitmentRebindRequest)
    persist = rebind.persist_rebind_attestation
    monkeypatch.setattr(
        rebind,
        "persist_rebind_attestation",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("injected_after_lease_cas")),
    )

    interrupted = execute_commitment_rebind(root=worktree, request=request)

    assert interrupted["verdict"] == "block"
    assert git(worktree, "rev-parse", "HEAD") == case["target_commit"]
    assert leases_by_branch(worktree)[case["branch"]]["epoch"] == int(case["lease"]["epoch"]) + 1
    assert not list(ref_intent_dir(worktree).glob("*.json"))

    monkeypatch.setattr(rebind, "persist_rebind_attestation", persist)
    attested = execute_commitment_rebind(root=worktree, request=request)

    assert attested["state"] == "attested"
    _assert_terminal(case, attested)


@pytest.mark.parametrize("drift", ["ref", "lease"])
def test_commitment_rebind_rechecks_terminal_state_before_attestation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    drift: str,
) -> None:
    case = _case(tmp_path, monkeypatch)
    worktree = case["worktree"]
    request = case["request"]
    branch = case["branch"]
    assert isinstance(worktree, Path)
    assert isinstance(request, CommitmentRebindRequest)
    assert isinstance(branch, str)
    issue = rebind.issue_rebind_attestation

    def drift_before_issue(*args, **kwargs):
        git(worktree, "config", "--unset-all", "core.hooksPath")
        if drift == "ref":
            git(worktree, "update-ref", f"refs/heads/{branch}", request.expect_head)
        else:
            _replace_lease_payload(worktree, branch, path_scope=["drift/**"])
        return issue(*args, **kwargs)

    monkeypatch.setattr(rebind, "issue_rebind_attestation", drift_before_issue)

    report = execute_commitment_rebind(root=worktree, request=request)

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
    worktree = case["worktree"]
    branch = case["branch"]
    request = case["request"]
    assert isinstance(worktree, Path)
    assert isinstance(branch, str)
    assert isinstance(request, CommitmentRebindRequest)
    persist = rebind.persist_rebind_attestation
    monkeypatch.setattr(
        rebind,
        "persist_rebind_attestation",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("injected_after_lease_cas")),
    )
    interrupted = execute_commitment_rebind(root=worktree, request=request)
    assert interrupted["required_gaps"] == ["injected_after_lease_cas"]
    _replace_lease_payload(worktree, branch, path_scope=["other/**"])
    monkeypatch.setattr(rebind, "persist_rebind_attestation", persist)

    report = execute_commitment_rebind(root=worktree, request=request)

    assert report["state"] == "repair_required"
    assert report["required_gaps"] == ["commitment_rebind_state_inconsistent"]


def test_commitment_rebind_recognition_rechecks_apply_actor_and_overlay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _case(tmp_path, monkeypatch)
    worktree = case["worktree"]
    request = case["request"]
    assert isinstance(worktree, Path)
    assert isinstance(request, CommitmentRebindRequest)
    completed = execute_commitment_rebind(root=worktree, request=request)
    assert completed["verdict"] == "pass"

    dry_run = execute_commitment_rebind(
        root=worktree,
        request=request.model_copy(update={"apply": False}),
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:other")
    wrong_actor = execute_commitment_rebind(root=worktree, request=request)
    monkeypatch.setenv("ETHOS_ACTOR", request.holder_ref)
    Path(case["untracked_overlay"]).write_bytes(b"drifted overlay\n")
    drifted = execute_commitment_rebind(root=worktree, request=request)

    assert dry_run["required_gaps"] == ["commitment_rebind_apply_required"]
    assert wrong_actor["required_gaps"] == ["lease_actor_mismatch"]
    assert drifted["required_gaps"] == ["commitment_rebind_overlay_changed"]


def test_commitment_rebind_recognition_rejects_ref_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _case(tmp_path, monkeypatch)
    worktree = case["worktree"]
    request = case["request"]
    assert isinstance(worktree, Path)
    assert isinstance(request, CommitmentRebindRequest)
    completed = execute_commitment_rebind(root=worktree, request=request)
    assert completed["verdict"] == "pass"
    git(worktree, "config", "--unset-all", "core.hooksPath")
    git(worktree, "update-ref", f"refs/heads/{request.branch}", request.expect_head)

    recognized = execute_commitment_rebind(root=worktree, request=request)

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
    worktree = case["worktree"]
    request = case["request"]
    assert isinstance(worktree, Path)
    assert isinstance(request, CommitmentRebindRequest)
    completed = execute_commitment_rebind(root=worktree, request=request)
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
        assert isinstance(target, dict)
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

    recognized = execute_commitment_rebind(root=worktree, request=request)

    assert recognized["state"] == "repair_required"
    assert recognized["required_gaps"] == ["commitment_rebind_terminal_mismatch"]


def test_commitment_rebind_cli_projects_the_same_terminal_transaction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _case(tmp_path, monkeypatch)
    worktree = case["worktree"]
    request = case["request"]
    assert isinstance(worktree, Path)
    assert isinstance(request, CommitmentRebindRequest)
    arguments = ["lane", "rebind-commitment", "--root", worktree.as_posix()]
    for name, value in request.model_dump().items():
        option = "--" + name.replace("_", "-")
        if isinstance(value, bool):
            if value:
                arguments.append(option)
        elif isinstance(value, tuple):
            for item in value:
                arguments.extend((option, str(item)))
        else:
            arguments.extend((option, str(value)))
    arguments.append("--json")

    applied = run_ethos(*arguments, cwd=worktree)
    recognized = run_ethos(*arguments, cwd=worktree)

    assert applied["data"]["state"] == "applied"
    assert recognized["data"]["state"] == "recognized"
    assert applied["data"]["attestation"] == recognized["data"]["attestation"]


def test_commitment_rebind_cli_preserves_carrier_coordinates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _case(tmp_path, monkeypatch, relocate_carrier=True)
    worktree = case["worktree"]
    request = case["request"]
    assert isinstance(worktree, Path)
    assert isinstance(request, CommitmentRebindRequest)
    arguments = ["lane", "rebind-commitment", "--root", worktree.as_posix()]
    for name, value in request.model_dump().items():
        option = "--" + name.replace("_", "-")
        if isinstance(value, bool):
            if value:
                arguments.append(option)
        elif isinstance(value, tuple):
            for item in value:
                arguments.extend((option, str(item)))
        else:
            arguments.extend((option, str(value)))
    arguments.append("--json")

    applied = run_ethos(*arguments, cwd=worktree)

    assert applied["data"]["verdict"] == "pass"
    assert applied["data"]["lease"]["base_commitment_path"] == request.new_commitment_path


@pytest.mark.parametrize(
    ("lease_updates", "expected_gap"),
    [
        ({"lane_incarnation_id": "lane-incarnation:other"}, "lease_lane_incarnation_id_stale"),
        ({"expected_tree": "0" * 40}, "lease_expected_tree_stale"),
        (
            {"base_commitment_path": "openspec/changes/other/commitment.toml"},
            "lease_commitment_path_stale",
        ),
    ],
)
def test_commitment_rebind_rejects_stale_old_generation_coordinates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    lease_updates: dict[str, object],
    expected_gap: str,
) -> None:
    case = _case(tmp_path, monkeypatch)
    worktree = case["worktree"]
    branch = case["branch"]
    request = case["request"]
    assert isinstance(worktree, Path)
    assert isinstance(branch, str)
    assert isinstance(request, CommitmentRebindRequest)
    _replace_lease_payload(worktree, branch, **lease_updates)

    report = execute_commitment_rebind(root=worktree, request=request)

    assert report["required_gaps"] == [expected_gap]
    assert git(worktree, "rev-parse", "HEAD") == request.expect_head


@pytest.mark.parametrize(
    ("request_updates", "expected_gap"),
    [
        ({"expected_issued_at": "2026-01-01T00:00:00+00:00"}, "lease_issued_at_stale"),
        ({"expected_renewed_at": "2026-01-01T00:00:00+00:00"}, "lease_renewed_at_stale"),
        ({"expected_path_scope": ("other/**",)}, "lease_path_scope_stale"),
    ],
)
def test_commitment_rebind_rejects_inexact_old_generation_request(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    request_updates: dict[str, object],
    expected_gap: str,
) -> None:
    case = _case(tmp_path, monkeypatch)
    worktree = case["worktree"]
    request = case["request"]
    assert isinstance(worktree, Path)
    assert isinstance(request, CommitmentRebindRequest)

    report = execute_commitment_rebind(
        root=worktree,
        request=request.model_copy(update=request_updates),
    )

    assert report["required_gaps"] == [expected_gap]
    assert git(worktree, "rev-parse", "HEAD") == request.expect_head


def test_commitment_rebind_blocks_impossible_lease_ahead_of_ref(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _case(tmp_path, monkeypatch)
    worktree = case["worktree"]
    branch = case["branch"]
    lease = case["lease"]
    request = case["request"]
    target = case["target"]
    assert isinstance(worktree, Path)
    assert isinstance(branch, str)
    assert isinstance(lease, dict)
    assert isinstance(request, CommitmentRebindRequest)
    assert isinstance(target, dict)
    _replace_lease_payload(
        worktree,
        branch,
        epoch=int(lease["epoch"]) + 1,
        **target,
    )

    report = execute_commitment_rebind(root=worktree, request=request)

    assert report["state"] == "blocked"
    assert report["required_gaps"] == ["commitment_rebind_state_inconsistent"]
