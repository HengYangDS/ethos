from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

import pytest
import tomli_w

import ethos.adapters.mutation.lane_lifecycle.commitment_rebind as rebind
import ethos.adapters.mutation.lane_lifecycle.commitment_rebind_admission as rebind_admission
import ethos.adapters.mutation.lane_lifecycle.commitment_rebind_derivation as rebind_derivation
import ethos.adapters.mutation.lane_lifecycle.commitment_rebind_evidence as rebind_evidence
import ethos.adapters.repo.status.bindings as status_bindings
from ethos.adapters.admission.ref_intent import ref_intent_dir
from ethos.adapters.admission.transitions import work_lane_ref_transition_report
from ethos.adapters.openspec.start_effect import current_generation_scope
from ethos.adapters.repo.attestation_set import ATTESTATION_SET_REF
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.attestation_set import record_attestations
from ethos.adapters.repo.commitment import exact_commitment_fields
from ethos.adapters.repo.commitment import load_lease_bound_commitment
from ethos.adapters.repo.commitment import load_repository_commitment
from ethos.adapters.repo.dirty.change_provenance import working_overlay_sha256
from ethos.adapters.repo.hook_runtime import install_hook_launchers
from ethos.adapters.repo.status.bindings import leases_by_branch
from ethos.adapters.store.state.schema import state_database
from ethos.contracts.coordination import CommitmentRebindRequest
from tests.support.ethos_cli_runner import run_ethos
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.governed_repository import start_adopted_work_lane
from tests.support.lifecycle_cases import rebind_effect
from tests.support.lifecycle_cases import tamper_attestation
from tests.support.literal_cases import literal_case
from tests.support.semantic import commitment_v2


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

    def generation_scope(self) -> object:
        updated = leases_by_branch(self.worktree)[self.branch]
        return current_generation_scope(
            self.worktree,
            head=str(updated["expected_head"]),
            repository_id=load_repository_commitment(self.worktree).id,
            commitment=load_lease_bound_commitment(self.worktree, lease=updated),
            lease=updated,
            fallback_paths=("src/example.py",),
        )


def _case(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    carrier_mode: str = "stable",
    repair_identity: bool = False,
    semantic_rename: bool = False,
    earlier_change: bool = False,
) -> RebindCase:
    holder = "agent:test:case:commitment-rebind"
    fixture = start_adopted_work_lane(tmp_path, holder_ref=holder)
    worktree = fixture.worktree
    _install_hooks(fixture.repository, worktree)
    branch = git(worktree, "branch", "--show-current")
    lease = leases_by_branch(worktree)[branch]
    carrier = Path(str(lease["base_commitment_path"]))
    old_head = git(worktree, "rev-parse", "HEAD")
    if earlier_change:
        old_head = commit_fixture_file(
            worktree,
            "src/prior.py",
            "PRIOR = True\n",
            "feat: preserve prior generation scope",
        )
        lease = leases_by_branch(worktree)[branch]
    if repair_identity:
        commitment = worktree / carrier
        commitment.write_text(
            _identity_content(
                commitment.read_text(encoding="utf-8"),
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
    ("mode", "raw_gap"),
    literal_case(
        "lanes.lease.test_commitment_rebind:parametrize:test_rebind_owns_carrier_and_authority:0"
    ),
)
def test_rebind_owns_carrier_and_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
    raw_gap: str | None,
) -> None:
    case = _case(tmp_path, monkeypatch, carrier_mode=mode)
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


def test_ordinary_rebind_establishes_current_generation_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = _case(tmp_path, monkeypatch)

    report = case.execute()

    assert (report["verdict"], report["required_gaps"]) == ("pass", [])
    scope = case.generation_scope()
    assert scope.gaps == ()
    assert scope.start_authority["claim"]["operation"] == "commitment-rebind"


def test_ordinary_commit_preserves_rebind_generation_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = _case(tmp_path, monkeypatch)
    assert case.execute()["verdict"] == "pass"
    commit_fixture_file(
        case.worktree,
        "src/example.py",
        "VALUE = 1\n",
        "feat: advance rebound generation",
    )

    scope = case.generation_scope()

    assert scope.gaps == ()
    assert scope.start_authority["claim"]["operation"] == "commitment-rebind"


def test_ordinary_rebind_preserves_the_existing_generation_base(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = _case(tmp_path, monkeypatch, earlier_change=True)
    generation_base = git(case.worktree, "rev-parse", "candidate/dev")

    assert case.execute()["verdict"] == "pass"

    scope = case.generation_scope()
    assert scope.start_authority["previous_head"] == generation_base
    assert "src/prior.py" in scope.paths


def test_relocated_rebind_preserves_the_carrier_origin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = _case(tmp_path, monkeypatch, carrier_mode="relocated")
    generation_base = git(case.worktree, "rev-parse", "candidate/dev")

    assert case.execute()["verdict"] == "pass"

    assert case.generation_scope().start_authority["previous_head"] == generation_base


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
    scope = case.generation_scope()
    assert scope.gaps == ()
    assert scope.start_authority["predicate"] == "effect:commitment-rebind"
    assert scope.start_authority["claim"]["operation"] == "commitment-rebind"


def test_ref_transition_does_not_scan_unrelated_lease_bindings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = _case(tmp_path, monkeypatch)
    monkeypatch.setattr(
        status_bindings,
        "lease_observations",
        lambda *_args, **_kwargs: pytest.fail("global Lease projection used"),
    )

    report = work_lane_ref_transition_report(
        root=case.worktree,
        phase="prepared",
        ref_name=f"refs/heads/{case.branch}",
        old_value=case.request.expect_head,
        new_value=case.request.target_commit,
    )

    assert report["required_gaps"] == ["commitment_rebind_required"]


@pytest.mark.parametrize(
    "checkpoint",
    ["git-cas", "prepared", "lease-cas"],
)
def test_rebind_checkpoint_matrix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, checkpoint: str
) -> None:
    case = _case(tmp_path, monkeypatch)
    epoch = int(case.lease["epoch"])
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


def test_rebind_rejects_unattested_partial_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
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

    report = case.execute()

    assert report["state"] == "repair_required"
    assert report["required_gaps"] == ["commitment_rebind_partial_git_attestation_missing"]


def _interrupted_partial_rebind(
    case: RebindCase, monkeypatch: pytest.MonkeyPatch
) -> tuple[object, ...]:
    """Persist one exact Git witness and project the corresponding partial Lease."""
    apply_rebind = rebind.rebind_lease_commitment
    monkeypatch.setattr(
        rebind,
        "rebind_lease_commitment",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("injected_after_git_effect")),
    )
    interrupted = case.execute()
    monkeypatch.setattr(rebind, "rebind_lease_commitment", apply_rebind)
    assert interrupted["required_gaps"] == ["injected_after_git_effect"]
    case.replace_lease(
        expected_head=case.request.target_commit,
        expected_tree=case.request.expect_index_tree,
    )
    return read_attestation_set(case.worktree)[1]


def test_partial_rebind_dry_run_and_apply_share_valid_historical_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = _case(tmp_path, monkeypatch)
    _interrupted_partial_rebind(case, monkeypatch)

    preview = case.execute(apply=False)
    applied = case.execute()

    assert (preview["verdict"], preview["state"], preview["required_gaps"]) == (
        "pass",
        "ready_to_recover",
        [],
    )
    assert (applied["verdict"], applied["state"], applied["required_gaps"]) == (
        "pass",
        "recovered",
        [],
    )


@pytest.mark.parametrize("mode", ["dry-run", "apply"])
def test_partial_rebind_rejects_historical_plan_collision_before_lease_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    case = _case(tmp_path, monkeypatch)
    selected = _interrupted_partial_rebind(case, monkeypatch)
    effect_digest = rebind_effect(case).digest()
    witness = next(
        item
        for item in selected
        if item.predicate == "effect:git-ref-update" and item.effect_digest == effect_digest
    )
    collision = tamper_attestation(
        witness.model_dump(mode="json"),
        location="attestation",
        field="verifier",
        replacement="agent:test:case:collision",
    )
    record_attestations(case.worktree, (collision,))
    epoch = leases_by_branch(case.worktree)[case.branch]["epoch"]

    report = case.execute(apply=mode == "apply")

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["git_effect_attestation_collision"]
    assert leases_by_branch(case.worktree)[case.branch]["epoch"] == epoch


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


def test_rebind_derive_emits_receipt_for_exact_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = _case(tmp_path, monkeypatch)

    report = rebind_derivation.derive_commitment_rebind(
        root=case.worktree,
        target_commit=case.request.target_commit,
        repair_change_identity=False,
    )

    assert (report["verdict"], report["state"]) == ("pass", "derived")
    assert "generation_authority" not in report["request"]
    expected = case.request.model_copy(update={"apply": False})
    assert report["request"] == expected.model_dump(mode="json")
    reference = report["receipt"]
    assert isinstance(reference, dict)
    receipt = rebind_derivation.load_commitment_rebind_receipt(
        case.worktree, str(reference["path"]), str(reference["sha256"])
    )
    assert receipt.request == expected
    assert len(receipt.digest) == 64
    assert report["next_action"] == (
        f"ethos lane rebind-commitment --receipt {reference['path']} --apply --json"
    )

    derived_cli = run_ethos(
        "lane",
        "rebind-commitment",
        "derive",
        "--root",
        case.worktree.as_posix(),
        "--target-commit",
        case.request.target_commit,
        "--json",
        cwd=case.worktree,
    )
    assert derived_cli["verdict"] == "pass"
    cli_receipt = derived_cli["data"]["receipt"]
    dry_run = run_ethos(
        "lane",
        "rebind-commitment",
        "--root",
        case.worktree.as_posix(),
        "--receipt",
        cli_receipt["path"],
        "--receipt-sha256",
        cli_receipt["sha256"],
        "--json",
        cwd=case.worktree,
    )
    assert (dry_run["verdict"], dry_run["state"]) == ("pass", "ready_to_apply")
    assert dry_run["data"]["request_receipt"] == {
        key: cli_receipt[key] for key in ("path", "sha256")
    }


def test_rebind_derive_constructs_the_exact_signed_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = _case(tmp_path, monkeypatch)
    signing_key = tmp_path / "derive-target-signing-key"
    subprocess.run(
        ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", signing_key.as_posix()],
        check=True,
    )
    git(case.worktree, "config", "gpg.format", "ssh")
    git(case.worktree, "config", "gpg.ssh.program", "/usr/bin/ssh-keygen")
    git(case.worktree, "config", "user.signingkey", f"{signing_key.as_posix()}.pub")
    git(
        case.worktree,
        "update-ref",
        "refs/heads/reachable-rebind-target",
        case.request.target_commit,
    )

    report = rebind_derivation.derive_commitment_rebind(
        root=case.worktree,
        target_commit="",
        repair_change_identity=False,
    )

    assert report["verdict"] == "pass", report["required_gaps"]
    target = report["request"]["target_commit"]
    assert target != case.request.target_commit
    assert git(case.worktree, "rev-parse", f"{target}^") == case.request.expect_head
    assert git(case.worktree, "rev-parse", f"{target}^{{tree}}") == case.request.expect_index_tree
    assert "gpgsig " in git(case.worktree, "cat-file", "commit", target)
    assert report["observed_targets"] == [target]

    projected = run_ethos(
        "lane",
        "rebind-commitment",
        "derive",
        "--root",
        case.worktree.as_posix(),
        "--json",
        cwd=case.worktree,
    )
    assert projected["verdict"] == "pass"
    projected_target = projected["data"]["request"]["target_commit"]
    assert projected["data"]["observed_targets"] == [projected_target]


@pytest.mark.parametrize(
    ("drift", "gap"),
    [
        ("head", "lease_head_stale"),
        ("overlay", "commitment_rebind_overlay_changed"),
        ("lease", "lease_epoch_stale"),
    ],
)
def test_rebind_receipt_apply_and_drift_matrix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    drift: str,
    gap: str,
) -> None:
    case = _case(tmp_path, monkeypatch)
    derived = rebind_derivation.derive_commitment_rebind(
        root=case.worktree,
        target_commit=case.request.target_commit,
        repair_change_identity=False,
    )
    receipt = str(derived["receipt"]["path"])
    digest = str(derived["receipt"]["sha256"])
    if drift == "head":
        case.replace_lease(expected_head="0" * 40)
    elif drift == "overlay":
        case.untracked.write_text("drifted\n", encoding="utf-8")
    else:
        case.replace_lease(epoch=int(case.lease["epoch"]) + 2)

    report = rebind.execute_commitment_rebind_receipt(
        root=case.worktree,
        receipt_path=receipt,
        receipt_sha256=digest,
        apply=True,
    )

    assert report["verdict"] == "block"
    assert report["required_gaps"] == [gap]


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
    derived = rebind_derivation.derive_commitment_rebind(
        root=case.worktree,
        target_commit=case.request.target_commit,
        repair_change_identity=False,
    )
    receipt = derived["receipt"]
    arguments = [
        "lane",
        "rebind-commitment",
        "--root",
        case.worktree.as_posix(),
        "--receipt",
        str(receipt["path"]),
        "--receipt-sha256",
        str(receipt["sha256"]),
        "--apply",
        "--json",
    ]
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


def _v1_commitment_text(
    *,
    identifier: str,
    intent: str,
    subjects: tuple[str, ...],
    scope: tuple[str, ...] = (),
) -> str:
    return tomli_w.dumps(
        {
            "schema_version": 1,
            "id": identifier,
            "intent": intent,
            "subjects": list(subjects),
            "scope": list(scope),
            "invariants": [],
            "acceptance": [],
            "authority_refs": [],
            "dependencies": [],
        }
    )


def _bootstrap_case(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[RebindCase, dict[str, object], dict[str, object], str, str]:
    case = _case(tmp_path, monkeypatch)
    repository_carrier = case.worktree / ".ethos/commitment.toml"
    lane_carrier = case.worktree / str(case.lease["base_commitment_path"])
    repository_carrier.write_text(
        _v1_commitment_text(
            identifier="repository:test",
            intent="Legacy repository authority.",
            subjects=("repository:test",),
        ),
        encoding="utf-8",
    )
    lane_carrier.write_text(
        _v1_commitment_text(
            identifier="change:fixture-change",
            intent="Legacy lane authority.",
            subjects=("repository:test",),
            scope=("**",),
        ),
        encoding="utf-8",
    )
    git(case.worktree, "add", repository_carrier.as_posix(), lane_carrier.as_posix())
    old_head = git(
        case.worktree,
        "commit-tree",
        git(case.worktree, "write-tree"),
        "-p",
        case.request.expect_head,
        "-m",
        "bind opaque v1 carriers",
    )
    git(case.worktree, "config", "--worktree", "--unset-all", "core.hooksPath")
    git(case.worktree, "update-ref", f"refs/heads/{case.branch}", old_head)
    git(case.worktree, "reset", "--hard", old_head)
    install_hook_launchers(case.worktree)
    repository_hash = hashlib.sha256(repository_carrier.read_bytes()).hexdigest()
    lane_hash = hashlib.sha256(lane_carrier.read_bytes()).hexdigest()
    _replace_lease(
        case.worktree,
        case.branch,
        expected_head=old_head,
        expected_tree=git(case.worktree, "rev-parse", f"{old_head}^{{tree}}"),
        base_commitment_bytes_sha256=lane_hash,
        base_commitment_digest="1" * 64,
    )
    repository_carrier.write_text(
        tomli_w.dumps(
            commitment_v2(
                id="repository:test",
                intent="Terminal repository authority.",
                subjects=("repository:test",),
            ).model_dump(mode="python")
        ),
        encoding="utf-8",
    )
    lane_carrier.write_text(
        tomli_w.dumps(
            commitment_v2(
                id="change:fixture-change",
                intent="Terminal lane authority.",
                subjects=("repository:test",),
                scope=("**",),
            ).model_dump(mode="python")
        ),
        encoding="utf-8",
    )
    git(case.worktree, "add", repository_carrier.as_posix(), lane_carrier.as_posix())
    signing_key = tmp_path / "bootstrap-signing-key"
    subprocess.run(
        ("ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", signing_key.as_posix()),
        check=True,
    )
    git(case.worktree, "config", "gpg.format", "ssh")
    git(case.worktree, "config", "gpg.ssh.program", "/usr/bin/ssh-keygen")
    git(case.worktree, "config", "user.signingkey", f"{signing_key.as_posix()}.pub")
    before_lease = leases_by_branch(case.worktree)[case.branch]
    before_set = git(case.worktree, "rev-parse", "--verify", ATTESTATION_SET_REF)
    report = rebind_derivation.derive_commitment_rebind(
        root=case.worktree,
        target_commit="",
        repair_change_identity=False,
        operation="v1-to-v2-bootstrap",
    )
    return case, report, before_lease, before_set, repository_hash


def test_v1_to_v2_bootstrap_derive_owns_target_and_keeps_old_bytes_opaque(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case, report, before_lease, before_set, repository_hash = _bootstrap_case(tmp_path, monkeypatch)
    before_ref = git(case.worktree, "rev-parse", f"refs/heads/{case.branch}")

    assert report["verdict"] == "pass", report["required_gaps"]
    request = report["request"]
    index_tree = git(case.worktree, "write-tree")
    assert request["operation"] == "v1-to-v2-bootstrap"
    assert request["expect_head"] == before_ref
    assert request["expect_index_tree"] == index_tree
    assert request["old_repository_commitment_bytes_sha256"] == repository_hash
    assert request["old_repository_id"] == "repository:test"
    assert (
        request["new_repository_commitment_digest"]
        == load_repository_commitment(case.worktree).digest()
    )
    assert request["target_commit"] != before_ref
    assert git(case.worktree, "rev-parse", f"{request['target_commit']}^") == before_ref
    assert git(case.worktree, "rev-parse", f"{request['target_commit']}^{{tree}}") == index_tree
    assert "gpgsig " in git(case.worktree, "cat-file", "commit", request["target_commit"])
    assert git(case.worktree, "rev-parse", f"refs/heads/{case.branch}") == before_ref
    assert leases_by_branch(case.worktree)[case.branch] == before_lease
    assert git(case.worktree, "rev-parse", "--verify", ATTESTATION_SET_REF) == before_set

    applied = rebind.execute_commitment_rebind_receipt(
        root=case.worktree,
        receipt_path=str(report["receipt"]["path"]),
        receipt_sha256=str(report["receipt"]["sha256"]),
        apply=True,
    )

    assert (applied["verdict"], applied["required_gaps"]) == (
        "pass",
        [],
    ), applied["required_gaps"]
    assert applied["state"] == "applied"
    assert git(case.worktree, "rev-parse", f"refs/heads/{case.branch}") == request["target_commit"]
    updated = leases_by_branch(case.worktree)[case.branch]
    assert updated["epoch"] == int(before_lease["epoch"]) + 1
    assert updated["base_commitment_digest"] == request["new_commitment_digest"]
    assert updated["expected_head"] == request["target_commit"]
    set_root, attestations = read_attestation_set(case.worktree)
    assert set_root != before_set
    bootstrap = next(
        item
        for item in attestations
        if item.predicate == "effect:commitment-rebind"
        and item.payload.body["claim"]["operation"] == "v1-to-v2-bootstrap"
    )
    lane_commitment = load_lease_bound_commitment(
        case.worktree,
        lease=updated,
        change_id="fixture-change",
    )
    repository = load_repository_commitment(case.worktree)
    scope = current_generation_scope(
        case.worktree,
        head=str(updated["expected_head"]),
        repository_id=repository.id,
        commitment=lane_commitment,
        lease=updated,
        fallback_paths=(),
    )

    assert scope.gaps == ()
    assert scope.start_authority["predicate"] == "effect:commitment-rebind"
    assert scope.start_authority["claim"]["operation"] == "v1-to-v2-bootstrap"
    assert {item.source for item in scope.attributions if item.state == "authorized"} == {
        "rebind_generation",
        "dirty_overlay",
    }
    forged = tamper_attestation(
        bootstrap.model_dump(mode="json"),
        location="new_lease_generation",
        field="lease_id",
        replacement="lease:forged",
    )
    assert (
        rebind_evidence.rebind_generation_authority(
            case.worktree,
            forged,
            repository_id=repository.id,
            commitment_digest=lane_commitment.digest(),
            lease=updated,
        )
        == {}
    )
