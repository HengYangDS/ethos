from __future__ import annotations

import hashlib
import json
import shlex
import shutil
import subprocess
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any
from typing import cast

import pytest

import ethos.adapters.admission.control.replacement as replacement
from ethos.adapters.admission.control.replacement import control_replacement_report
from tests.support.contract_helpers import git
from tests.support.contract_helpers import init_git_repo

_CONTROL_PATH = "system/gates.toml"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _control_digest(root: Path, head: str, paths: list[str]) -> str:
    records = []
    for path in paths:
        completed = subprocess.run(
            ["git", "show", f"{head}:{path}"], cwd=root, check=False, capture_output=True
        )
        records.append(
            {
                "path": path,
                "present": completed.returncode == 0,
                "sha256": hashlib.sha256(completed.stdout).hexdigest()
                if completed.returncode == 0
                else "",
            }
        )
    encoded = json.dumps(records, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _control_change(tmp_path: Path) -> tuple[Path, Path, str, str]:
    repo = init_git_repo(tmp_path / "repo")
    candidate = tmp_path / "repo-candidate-dev"
    git(repo, "worktree", "add", "-b", "candidate/dev", candidate.as_posix(), "dev")
    path = candidate / _CONTROL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("version = 2\n", encoding="utf-8")
    git(candidate, "add", ".")
    git(
        candidate,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=t@example.com",
        "commit",
        "-m",
        "control",
    )
    return repo, candidate, git(repo, "rev-parse", "HEAD"), git(candidate, "rev-parse", "HEAD")


def _bundle(
    tmp_path: Path,
    candidate: Path,
    accepted_head: str,
    candidate_head: str,
) -> dict[str, Any]:
    verifier = tmp_path / "protected" / "operator-verifier"
    verifier.parent.mkdir(exist_ok=True)
    verifier.write_text("operator supplied\n", encoding="utf-8")
    proof = tmp_path / "candidate-proof.json"
    decision = tmp_path / "bootstrap-decision.json"
    receipt = tmp_path / "receipt.json"
    bundle: dict[str, Any] = {
        "verifier": verifier,
        "proof": proof,
        "decision": decision,
        "receipt": receipt,
        "proof_payload": {
            "schema_version": 1,
            "command": "prove",
            "ok": True,
            "state": "proven",
            "summary": {"evidence_digest": "a" * 64},
            "data": {
                "executed": True,
                "evidence": {"head": candidate_head},
                "provenance": {"predicate": {"head": candidate_head}},
            },
        },
        "decision_payload": {
            "schema_version": 1,
            "kind": "control-replacement-bootstrap-decision",
            "id": "chronicle:bootstrap",
            "subject_id": "ethos:control-replacement",
            "event_type": "decision",
            "evidence_ids": ["evidence:bootstrap-review"],
            "decision": "bootstrap/control-replacement",
            "supersedes": [],
            "current_state_delta": "operator verifier admitted for exact heads",
            "accepted_head": accepted_head,
            "candidate_head": candidate_head,
            "verifier_sha256": "",
            "candidate_proof_digest": "",
            "mints_authority": False,
            "reusable_authorization": False,
        },
        "receipt_payload": {
            "schema_version": 1,
            "kind": "control-replacement-verifier",
            "provenance": "protected_external_bootstrap",
            "accepted_head": accepted_head,
            "candidate_head": candidate_head,
            "control_paths": [_CONTROL_PATH],
            "accepted_control_digest": _control_digest(candidate, accepted_head, [_CONTROL_PATH]),
            "candidate_control_digest": _control_digest(candidate, candidate_head, [_CONTROL_PATH]),
            "verifier_path": verifier.as_posix(),
            "verifier_sha256": "",
            "candidate_proof_path": proof.as_posix(),
            "candidate_proof_digest": "",
            "bootstrap_decision_path": decision.as_posix(),
            "bootstrap_decision_digest": "",
            "issued_at": datetime.now(UTC).isoformat(),
            "verdict": "allow",
            "mints_authority": False,
        },
    }
    _write_bundle(bundle)
    return bundle


def _write_bundle(bundle: dict[str, Any]) -> None:
    proof = cast("Path", bundle["proof"])
    decision = cast("Path", bundle["decision"])
    receipt = cast("Path", bundle["receipt"])
    proof.write_text(json.dumps(bundle["proof_payload"]), encoding="utf-8")
    proof_digest = _sha256(proof)
    bundle["decision_payload"].update(
        verifier_sha256=_sha256(bundle["verifier"]), candidate_proof_digest=proof_digest
    )
    decision.write_text(json.dumps(bundle["decision_payload"]), encoding="utf-8")
    bundle["receipt_payload"].update(
        verifier_sha256=_sha256(bundle["verifier"]),
        candidate_proof_digest=proof_digest,
        bootstrap_decision_digest=_sha256(decision),
    )
    receipt.write_text(json.dumps(bundle["receipt_payload"]), encoding="utf-8")


def _report(repo: Path, candidate: Path, accepted: str, head: str, receipt: Path):
    return control_replacement_report(
        accepted_root=repo,
        candidate_root=candidate,
        accepted_head=accepted,
        candidate_head=head,
        external_receipt=receipt,
    )


def _set_nested(payload: dict[str, Any], path: tuple[str, ...], value: object) -> None:
    target = payload
    for key in path[:-1]:
        target = cast("dict[str, Any]", target[key])
    target[path[-1]] = value


def test_non_control_change_does_not_require_incumbent_verifier(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    candidate = tmp_path / "repo-candidate-dev"
    git(repo, "worktree", "add", "-b", "candidate/dev", candidate.as_posix(), "dev")
    (candidate / "README.md").write_text("# candidate\n", encoding="utf-8")
    git(candidate, "add", "README.md")
    git(candidate, "-c", "user.name=Test", "-c", "user.email=t@example.com", "commit", "-m", "docs")

    report = control_replacement_report(
        accepted_root=repo,
        candidate_root=candidate,
        accepted_head=git(repo, "rev-parse", "HEAD"),
        candidate_head=git(candidate, "rev-parse", "HEAD"),
    )

    assert report["required"] is False
    assert report["verdict"] == "allow"
    assert report["required_gaps"] == []


def test_control_change_defers_without_incumbent_or_external_bootstrap(tmp_path: Path) -> None:
    repo, candidate, accepted, head = _control_change(tmp_path)
    report = control_replacement_report(
        accepted_root=repo,
        candidate_root=candidate,
        accepted_head=accepted,
        candidate_head=head,
    )
    assert report["required"] is True
    assert report["verdict"] == "defer"
    assert report["candidate_conformance"]["verifier_provenance"] == "candidate_runner"
    assert "incumbent_or_bootstrap_verifier_required" in report["required_gaps"]
    assert report["self_approval"] is False


def test_legacy_self_asserted_bootstrap_receipt_is_rejected(tmp_path: Path) -> None:
    repo, candidate, accepted, head = _control_change(tmp_path)
    receipt = tmp_path / "bootstrap.json"
    receipt.write_text(
        '{"kind":"control-replacement-verifier","provenance":"protected_external_bootstrap",'
        f'"accepted_head":"{accepted}","candidate_head":"{head}",'
        '"verdict":"allow","mints_authority":false}\n',
        encoding="utf-8",
    )
    report = _report(repo, candidate, accepted, head, receipt)
    assert report["verdict"] == "defer"
    assert report["required_gaps"] == ["control_replacement_receipt_invalid"]


def test_external_evidence_and_declarative_policy_changes_require_incumbent_verifier(
    tmp_path: Path,
) -> None:
    for relative_path in (
        "packages/ethos-core/src/ethos_core/contracts/evidence/external.py",
        "system/evidence_boundaries.toml",
        "system/commands.toml",
        "system/policies/generated-artifact-topology.toml",
        "system/workflows.toml",
    ):
        repo = init_git_repo(tmp_path / relative_path.replace("/", "-"))
        candidate = repo.with_name(f"{repo.name}-candidate-dev")
        git(repo, "worktree", "add", "-b", "candidate/dev", candidate.as_posix(), "dev")
        path = candidate / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("candidate control\n", encoding="utf-8")
        git(candidate, "add", ".")
        git(
            candidate,
            "-c",
            "user.name=Test",
            "-c",
            "user.email=t@example.com",
            "commit",
            "-m",
            "control",
        )
        report = control_replacement_report(
            accepted_root=repo,
            candidate_root=candidate,
            accepted_head=git(repo, "rev-parse", "HEAD"),
            candidate_head=git(candidate, "rev-parse", "HEAD"),
        )
        assert report["required"] is True, relative_path


def test_operator_supplied_bootstrap_receipt_is_admitted(tmp_path: Path) -> None:
    repo, candidate, accepted, head = _control_change(tmp_path)
    bundle = _bundle(tmp_path, candidate, accepted, head)
    report = _report(repo, candidate, accepted, head, bundle["receipt"])
    assert report["verdict"] == "allow"
    assert report["required_gaps"] == []


@pytest.mark.parametrize(
    ("path", "value", "gap"),
    [
        (("command",), "status", "candidate_proof_not_proven"),
        (("ok",), False, "candidate_proof_not_proven"),
        (("state",), "ready", "candidate_proof_not_proven"),
        (("data", "executed"), False, "candidate_proof_not_proven"),
        (("data", "evidence"), [], "candidate_proof_not_proven"),
        (("data", "evidence", "head"), "f" * 40, "candidate_proof_head_mismatch"),
        (("data", "provenance", "predicate", "head"), "f" * 40, "candidate_proof_head_mismatch"),
    ],
)
def test_candidate_proof_must_be_native_executed_prove(
    tmp_path: Path, path: tuple[str, ...], value: object, gap: str
) -> None:
    repo, candidate, accepted, head = _control_change(tmp_path)
    bundle = _bundle(tmp_path, candidate, accepted, head)
    _set_nested(bundle["proof_payload"], path, value)
    _write_bundle(bundle)
    report = _report(repo, candidate, accepted, head, bundle["receipt"])
    assert report["verdict"] == "defer"
    assert gap in report["required_gaps"]


@pytest.mark.parametrize(
    ("field", "value", "gap"),
    [
        ("schema_version", 2, "bootstrap_decision_schema_invalid"),
        ("kind", "wrong", "bootstrap_decision_kind_invalid"),
        ("event_type", "observation", "bootstrap_chronicle_event_invalid"),
        ("decision", "bootstrap/wrong", "bootstrap_decision_value_invalid"),
        ("accepted_head", "f" * 40, "bootstrap_accepted_head_mismatch"),
        ("candidate_head", "f" * 40, "bootstrap_candidate_head_mismatch"),
        ("verifier_sha256", "f" * 64, "bootstrap_verifier_digest_mismatch"),
        ("candidate_proof_digest", "f" * 64, "bootstrap_candidate_proof_digest_mismatch"),
        ("evidence_ids", [], "bootstrap_evidence_required"),
        ("mints_authority", True, "bootstrap_authority_invalid"),
        ("reusable_authorization", True, "bootstrap_reusable_authorization_invalid"),
    ],
)
def test_bootstrap_decision_is_revalidated(
    tmp_path: Path, field: str, value: object, gap: str
) -> None:
    repo, candidate, accepted, head = _control_change(tmp_path)
    bundle = _bundle(tmp_path, candidate, accepted, head)
    bundle["decision_payload"][field] = value
    bundle["decision"].write_text(json.dumps(bundle["decision_payload"]), encoding="utf-8")
    bundle["receipt_payload"]["bootstrap_decision_digest"] = _sha256(bundle["decision"])
    bundle["receipt"].write_text(json.dumps(bundle["receipt_payload"]), encoding="utf-8")
    report = _report(repo, candidate, accepted, head, bundle["receipt"])
    assert report["verdict"] == "defer"
    assert gap in report["required_gaps"]


@pytest.mark.parametrize(
    ("field", "value", "gap"),
    [
        ("control_paths", ["system/tools.toml"], "control_replacement_control_paths_mismatch"),
        (
            "accepted_control_digest",
            "f" * 64,
            "control_replacement_accepted_control_digest_mismatch",
        ),
        (
            "candidate_control_digest",
            "f" * 64,
            "control_replacement_candidate_control_digest_mismatch",
        ),
    ],
)
def test_receipt_must_match_recomputed_control_scope(
    tmp_path: Path, field: str, value: object, gap: str
) -> None:
    repo, candidate, accepted, head = _control_change(tmp_path)
    bundle = _bundle(tmp_path, candidate, accepted, head)
    bundle["receipt_payload"][field] = value
    bundle["receipt"].write_text(json.dumps(bundle["receipt_payload"]), encoding="utf-8")
    report = _report(repo, candidate, accepted, head, bundle["receipt"])
    assert report["verdict"] == "defer"
    assert gap in report["required_gaps"]


def test_checkout_heads_are_revalidated_before_receipt_admission(tmp_path: Path) -> None:
    repo, candidate, accepted, head = _control_change(tmp_path)
    bundle = _bundle(tmp_path, candidate, accepted, head)
    (repo / "accepted.txt").write_text("advanced\n", encoding="utf-8")
    git(repo, "add", "accepted.txt")
    git(
        repo,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=t@example.com",
        "commit",
        "-m",
        "accepted advance",
    )
    report = _report(repo, candidate, accepted, head, bundle["receipt"])
    assert report["verdict"] == "defer"
    assert "control_replacement_accepted_checkout_head_mismatch" in report["required_gaps"]


def test_candidate_checkout_head_is_revalidated_before_receipt_admission(tmp_path: Path) -> None:
    repo, candidate, accepted, head = _control_change(tmp_path)
    bundle = _bundle(tmp_path, candidate, accepted, head)
    (candidate / "candidate.txt").write_text("advanced\n", encoding="utf-8")
    git(candidate, "add", "candidate.txt")
    git(
        candidate,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=t@example.com",
        "commit",
        "-m",
        "candidate advance",
    )
    report = _report(repo, candidate, accepted, head, bundle["receipt"])
    assert report["verdict"] == "defer"
    assert "control_replacement_candidate_checkout_head_mismatch" in report["required_gaps"]


def test_candidate_must_descend_from_current_accepted_head(tmp_path: Path) -> None:
    repo, candidate, _accepted, head = _control_change(tmp_path)
    (repo / "accepted.txt").write_text("diverged\n", encoding="utf-8")
    git(repo, "add", "accepted.txt")
    git(
        repo,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=t@example.com",
        "commit",
        "-m",
        "accepted diverged",
    )
    accepted = git(repo, "rev-parse", "HEAD")
    bundle = _bundle(tmp_path, candidate, accepted, head)
    report = _report(repo, candidate, accepted, head, bundle["receipt"])
    assert report["verdict"] == "defer"
    assert "control_replacement_candidate_not_descendant" in report["required_gaps"]


def test_git_diff_failure_defers_instead_of_looking_like_no_control_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, candidate, accepted, head = _control_change(tmp_path)
    real_git = shutil.which("git")
    assert real_git
    shim = tmp_path / "bin" / "git"
    shim.parent.mkdir()
    shim.write_text(
        f'#!/bin/sh\nif [ "$1" = "diff" ]; then exit 42; fi\nexec {shlex.quote(real_git)} "$@"\n',
        encoding="utf-8",
    )
    shim.chmod(0o755)
    monkeypatch.setenv("PATH", f"{shim.parent}:{Path(real_git).parent}")
    report = control_replacement_report(
        accepted_root=repo,
        candidate_root=candidate,
        accepted_head=accepted,
        candidate_head=head,
    )
    assert report["verdict"] == "defer"
    assert "control_replacement_diff_unreadable" in report["required_gaps"]


def test_unreadable_checkout_and_receipt_fail_closed(tmp_path: Path) -> None:
    repo, candidate, accepted, head = _control_change(tmp_path)
    unreadable = control_replacement_report(
        accepted_root=tmp_path / "not-a-repository",
        candidate_root=candidate,
        accepted_head=accepted,
        candidate_head=head,
    )
    assert "control_replacement_accepted_checkout_head_unreadable" in unreadable["required_gaps"]

    inside = candidate / "receipt.json"
    inside.write_text("{}", encoding="utf-8")
    inside_report = _report(repo, candidate, accepted, head, inside)
    assert "bootstrap_verifier_inside_candidate_tree" in inside_report["required_gaps"]

    invalid = tmp_path / "invalid-receipt.json"
    invalid.write_text("not-json", encoding="utf-8")
    invalid_report = _report(repo, candidate, accepted, head, invalid)
    assert invalid_report["required_gaps"] == ["control_replacement_receipt_invalid"]


@pytest.mark.parametrize(
    ("mutation", "gap"),
    [
        ("verifier_inside", "bootstrap_verifier_inside_candidate_tree"),
        ("decision_missing", "bootstrap_decision_missing"),
        ("proof_digest", "control_replacement_candidate_proof_digest_mismatch"),
    ],
)
def test_operator_artifacts_are_revalidated(tmp_path: Path, mutation: str, gap: str) -> None:
    repo, candidate, accepted, head = _control_change(tmp_path)
    bundle = _bundle(tmp_path, candidate, accepted, head)
    if mutation == "verifier_inside":
        verifier = candidate / "operator-verifier"
        verifier.write_text("inside candidate\n", encoding="utf-8")
        bundle["receipt_payload"].update(
            verifier_path=verifier.as_posix(), verifier_sha256=_sha256(verifier)
        )
    elif mutation == "decision_missing":
        bundle["receipt_payload"].update(
            bootstrap_decision_path=(tmp_path / "missing-decision").as_posix(),
            bootstrap_decision_digest="f" * 64,
        )
    else:
        bundle["receipt_payload"]["candidate_proof_digest"] = "f" * 64
    bundle["receipt"].write_text(json.dumps(bundle["receipt_payload"]), encoding="utf-8")
    report = _report(repo, candidate, accepted, head, bundle["receipt"])
    assert report["verdict"] == "defer"
    assert gap in report["required_gaps"]


def test_invalid_decision_and_unreadable_control_digest_defer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, candidate, accepted, head = _control_change(tmp_path)
    bundle = _bundle(tmp_path, candidate, accepted, head)
    bundle["decision"].write_text("not-json", encoding="utf-8")
    bundle["receipt_payload"]["bootstrap_decision_digest"] = _sha256(bundle["decision"])
    bundle["receipt"].write_text(json.dumps(bundle["receipt_payload"]), encoding="utf-8")
    invalid = _report(repo, candidate, accepted, head, bundle["receipt"])
    assert "bootstrap_decision_invalid" in invalid["required_gaps"]

    monkeypatch.setattr(replacement, "_control_digest", lambda *_args: None)
    unreadable = _report(repo, candidate, accepted, head, bundle["receipt"])
    assert "control_replacement_control_digest_unreadable" in unreadable["required_gaps"]


def test_low_level_git_and_digest_failures_are_bounded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert replacement._control_digest(tmp_path, "f" * 40, (_CONTROL_PATH,)) is None

    def fail(*_args, **_kwargs):
        message = "git unavailable"
        raise OSError(message)

    monkeypatch.setattr(replacement.subprocess, "run", fail)
    assert replacement._git_text(tmp_path, "status").returncode == 127
    assert replacement._git_bytes(tmp_path, "show", "HEAD:file").returncode == 127


def test_control_digest_git_read_error_defers_instead_of_claiming_absence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, candidate, accepted, head = _control_change(tmp_path)
    bundle = _bundle(tmp_path, candidate, accepted, head)
    real_git = shutil.which("git")
    assert real_git
    shim = tmp_path / "git-error-bin" / "git"
    shim.parent.mkdir()
    shim.write_text(
        f"""#!/bin/sh
case "$1" in
  show|ls-tree) exit 42 ;;
  cat-file) case "$3" in *:*) exit 42 ;; esac ;;
esac
exec {shlex.quote(real_git)} "$@"
""",
        encoding="utf-8",
    )
    shim.chmod(0o755)
    monkeypatch.setenv("PATH", f"{shim.parent}:{Path(real_git).parent}")
    report = _report(repo, candidate, accepted, head, bundle["receipt"])
    assert report["verdict"] == "defer"
    assert "control_replacement_control_digest_unreadable" in report["required_gaps"]


def test_candidate_cannot_weaken_control_replacement_receipt_schema(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "schema-repo")
    source = Path(__file__).resolve().parents[3] / "system" / "schemas" / "kernel"
    target = repo / "system" / "schemas" / "kernel"
    shutil.copytree(source, target)
    git(repo, "add", "system/schemas/kernel")
    git(
        repo,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=t@example.com",
        "commit",
        "-m",
        "accepted receipt schemas",
    )
    candidate = tmp_path / "schema-repo-candidate-dev"
    git(repo, "worktree", "add", "-b", "candidate/schema", candidate.as_posix(), "dev")
    relative = "system/schemas/kernel/control-replacement-verifier-receipt.schema.json"
    (candidate / relative).write_text('{"type":"object"}\n', encoding="utf-8")
    git(candidate, "add", relative)
    git(
        candidate,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=t@example.com",
        "commit",
        "-m",
        "weaken candidate receipt schema",
    )
    accepted, head = git(repo, "rev-parse", "HEAD"), git(candidate, "rev-parse", "HEAD")
    bundle = _bundle(tmp_path, candidate, accepted, head)
    bundle["receipt_payload"].update(
        control_paths=[relative],
        accepted_control_digest=_control_digest(candidate, accepted, [relative]),
        candidate_control_digest=_control_digest(candidate, head, [relative]),
    )
    bundle["receipt_payload"].pop("schema_version")
    bundle["receipt_payload"].pop("issued_at")
    _write_bundle(bundle)
    report = _report(repo, candidate, accepted, head, bundle["receipt"])
    assert report["verdict"] == "defer"
    assert "control_replacement_receipt_invalid" in report["required_gaps"]
