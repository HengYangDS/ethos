from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

from ethos.adapters.admission.control import replacement
from tests.support.contract_helpers import commit_fixture_file
from tests.support.contract_helpers import git
from tests.support.contract_helpers import init_git_repo
from tests.support.contract_helpers import init_repo_with_candidate

if TYPE_CHECKING:
    from pathlib import Path


def _write_json(path: Path, payload: object) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _native_proof_payload(head: str) -> dict[str, object]:
    return {
        "schema_version": 1,
        "command": "prove",
        "ok": True,
        "state": "proven",
        "summary": {"evidence_digest": "a" * 64},
        "data": {
            "executed": True,
            "evidence": {"head": head},
            "provenance": {"predicate": {"head": head}},
        },
    }


def _control_change(tmp_path: Path) -> tuple[Path, Path, str, str]:
    repo, candidate = init_repo_with_candidate(tmp_path)
    accepted_head = git(repo, "rev-parse", "HEAD")
    candidate_head = commit_fixture_file(candidate, "system/gates.toml", "version = 2\n", "floor")
    return repo, candidate, accepted_head, candidate_head


def _operator_receipt(
    tmp_path: Path,
    *,
    candidate_root: Path,
    accepted_head: str,
    candidate_head: str,
) -> tuple[Path, Path, Path, dict[str, object], dict[str, object]]:
    control_paths = ("system/gates.toml",)
    verifier = tmp_path / "operator-verifier.py"
    verifier.write_text("reviewed external verifier\n", encoding="utf-8")
    proof = _write_json(tmp_path / "candidate-proof.json", _native_proof_payload(candidate_head))
    verifier_digest = hashlib.sha256(verifier.read_bytes()).hexdigest()
    proof_digest = hashlib.sha256(proof.read_bytes()).hexdigest()
    decision_payload: dict[str, object] = {
        "schema_version": 1,
        "kind": "control-replacement-bootstrap-decision",
        "event_type": "decision",
        "decision": "bootstrap/control-replacement",
        "accepted_head": accepted_head,
        "candidate_head": candidate_head,
        "verifier_sha256": verifier_digest,
        "candidate_proof_digest": proof_digest,
        "evidence_ids": ["evidence:operator-review"],
        "mints_authority": False,
        "reusable_authorization": False,
    }
    decision = _write_json(tmp_path / "operator-decision.json", decision_payload)
    accepted_digest = replacement._control_digest(  # noqa: RUF100, SLF001 - fixture uses canonical digest
        candidate_root, accepted_head, control_paths
    )
    candidate_digest = replacement._control_digest(  # noqa: RUF100, SLF001 - fixture uses canonical digest
        candidate_root, candidate_head, control_paths
    )
    assert accepted_digest
    assert candidate_digest
    payload: dict[str, object] = {
        "schema_version": 1,
        "kind": "control-replacement-verifier",
        "provenance": "protected_external_bootstrap",
        "accepted_head": accepted_head,
        "candidate_head": candidate_head,
        "control_paths": list(control_paths),
        "accepted_control_digest": accepted_digest,
        "candidate_control_digest": candidate_digest,
        "verifier_path": verifier.as_posix(),
        "verifier_sha256": verifier_digest,
        "candidate_proof_path": proof.as_posix(),
        "candidate_proof_digest": proof_digest,
        "bootstrap_decision_path": decision.as_posix(),
        "bootstrap_decision_digest": hashlib.sha256(decision.read_bytes()).hexdigest(),
        "issued_at": "2026-07-19T00:00:00+00:00",
        "verdict": "allow",
        "mints_authority": False,
    }
    return (
        _write_json(tmp_path / "receipt.json", payload),
        proof,
        decision,
        payload,
        decision_payload,
    )


def _report(
    candidate: Path,
    accepted_head: str,
    candidate_head: str,
    receipt: Path,
) -> dict[str, object]:
    return replacement.control_replacement_report(
        candidate_root=candidate,
        accepted_head=accepted_head,
        candidate_head=candidate_head,
        external_receipt=receipt,
    )


def test_non_control_change_does_not_require_incumbent_verifier(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    candidate = tmp_path / "repo-candidate-dev"
    git(repo, "worktree", "add", "-b", "candidate/dev", candidate.as_posix(), "dev")
    (candidate / "README.md").write_text("# candidate\n", encoding="utf-8")
    git(candidate, "add", "README.md")
    git(
        candidate,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=t@example.com",
        "commit",
        "-m",
        "docs",
    )

    report = replacement.control_replacement_report(
        candidate_root=candidate,
        accepted_head=git(repo, "rev-parse", "HEAD"),
        candidate_head=git(candidate, "rev-parse", "HEAD"),
    )

    assert report["required"] is False
    assert report["verdict"] == "allow"
    assert report["required_gaps"] == []


def test_control_change_defers_without_incumbent_or_external_bootstrap(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    candidate = tmp_path / "repo-candidate-dev"
    git(repo, "worktree", "add", "-b", "candidate/dev", candidate.as_posix(), "dev")
    path = candidate / "packages" / "ethos" / "src" / "ethos" / "adapters" / "admission"
    path.mkdir(parents=True)
    (path / "core.py").write_text("CONTROL = 'candidate'\n", encoding="utf-8")
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

    report = replacement.control_replacement_report(
        candidate_root=candidate,
        accepted_head=git(repo, "rev-parse", "HEAD"),
        candidate_head=git(candidate, "rev-parse", "HEAD"),
    )

    assert report["required"] is True
    assert report["verdict"] == "defer"
    assert report["candidate_conformance"]["verifier_provenance"] == "candidate_runner"
    assert "incumbent_or_bootstrap_verifier_required" in report["required_gaps"]
    assert report["self_approval"] is False


def test_legacy_self_asserted_bootstrap_receipt_is_rejected(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    candidate = tmp_path / "repo-candidate-dev"
    git(repo, "worktree", "add", "-b", "candidate/dev", candidate.as_posix(), "dev")
    path = candidate / "system" / "gates.toml"
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
        "floor",
    )
    accepted_head = git(repo, "rev-parse", "HEAD")
    candidate_head = git(candidate, "rev-parse", "HEAD")
    receipt = tmp_path / "bootstrap.json"
    receipt.write_text(
        (
            '{"kind":"control-replacement-verifier","provenance":"protected_external_bootstrap",'
            f'"accepted_head":"{accepted_head}","candidate_head":"{candidate_head}",'
            '"verdict":"allow","mints_authority":false}\n'
        ),
        encoding="utf-8",
    )

    report = _report(candidate, accepted_head, candidate_head, receipt)

    assert report["verdict"] == "defer"
    assert report["required_gaps"] == ["control_replacement_receipt_invalid"]


def test_external_evidence_and_declarative_policy_changes_require_incumbent_verifier(
    tmp_path: Path,
) -> None:
    for relative_path in (
        ".ethos/workspace.toml",
        "packages/ethos-core/src/ethos_core/contracts/evidence/external.py",
        "packages/ethos/src/ethos/domain/land/core.py",
        "packages/ethos/src/ethos/surface/cli/root/lifecycle.py",
        "system/commands.toml",
        "system/evidence_boundaries.toml",
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

        report = replacement.control_replacement_report(
            candidate_root=candidate,
            accepted_head=git(repo, "rev-parse", "HEAD"),
            candidate_head=git(candidate, "rev-parse", "HEAD"),
        )

        assert report["required"] is True, relative_path


def test_control_path_rename_preserves_source_path_admission(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    accepted_head = commit_fixture_file(repo, "system/gates.toml", "version = 1\n", "control")
    candidate = tmp_path / "repo-candidate-dev"
    git(repo, "worktree", "add", "-b", "candidate/dev", candidate.as_posix(), "dev")
    git(candidate, "rm", "system/gates.toml")
    candidate_head = commit_fixture_file(candidate, "docs/gates.toml", "version = 1\n", "move")

    report = replacement.control_replacement_report(
        candidate_root=candidate,
        accepted_head=accepted_head,
        candidate_head=candidate_head,
    )

    assert report["required"] is True
    assert "system/gates.toml" in report["control_paths"]


def test_control_digest_binds_git_mode(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    control = repo / "system" / "gates.toml"
    control.parent.mkdir(parents=True)
    control.write_text("version = 1\n", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "control")
    accepted_head = git(repo, "rev-parse", "HEAD")
    control.chmod(0o755)
    git(repo, "add", ".")
    git(repo, "commit", "-m", "mode")
    candidate_head = git(repo, "rev-parse", "HEAD")
    receipt, _proof, _decision, receipt_payload, _decision_payload = _operator_receipt(
        tmp_path,
        candidate_root=repo,
        accepted_head=accepted_head,
        candidate_head=candidate_head,
    )

    assert receipt_payload["accepted_control_digest"] != receipt_payload["candidate_control_digest"]
    assert _report(repo, accepted_head, candidate_head, receipt)["verdict"] == "allow"


def test_native_proof_parser_rejects_handwritten_head_state_envelope() -> None:
    candidate_head = "a" * 40

    assert (
        replacement._native_executed_proof_head(  # noqa: RUF100, SLF001 - asserts receipt admission's fail-closed parser
            {"head": candidate_head, "state": "proven"}
        )
        == ""
    )


def test_operator_receipt_requires_native_executed_proof(
    tmp_path: Path,
) -> None:
    _repo, candidate, accepted_head, candidate_head = _control_change(tmp_path)
    receipt, proof, decision, receipt_payload, decision_payload = _operator_receipt(
        tmp_path,
        candidate_root=candidate,
        accepted_head=accepted_head,
        candidate_head=candidate_head,
    )

    report = _report(candidate, accepted_head, candidate_head, receipt)
    assert report["verdict"] == "allow"

    _write_json(proof, {"head": candidate_head, "state": "proven"})
    receipt_payload["candidate_proof_digest"] = hashlib.sha256(proof.read_bytes()).hexdigest()
    decision_payload["candidate_proof_digest"] = receipt_payload["candidate_proof_digest"]
    _write_json(decision, decision_payload)
    receipt_payload["bootstrap_decision_digest"] = hashlib.sha256(decision.read_bytes()).hexdigest()
    _write_json(receipt, receipt_payload)

    report = _report(candidate, accepted_head, candidate_head, receipt)
    assert report["verdict"] == "defer"
    assert report["required_gaps"] == ["control_replacement_candidate_proof_not_proven"]


def test_operator_receipt_rejects_forged_control_and_decision_bindings(
    tmp_path: Path,
) -> None:
    _repo, candidate, accepted_head, candidate_head = _control_change(tmp_path)
    receipt, _proof, decision, receipt_payload, decision_payload = _operator_receipt(
        tmp_path,
        candidate_root=candidate,
        accepted_head=accepted_head,
        candidate_head=candidate_head,
    )

    for key, forged, gap in (
        (
            "candidate_control_digest",
            "0" * 64,
            "control_replacement_candidate_control_digest_mismatch",
        ),
        (
            "control_paths",
            ["system/commands.toml"],
            "control_replacement_control_paths_mismatch",
        ),
    ):
        original = receipt_payload[key]
        receipt_payload[key] = forged
        _write_json(receipt, receipt_payload)
        assert gap in _report(candidate, accepted_head, candidate_head, receipt)["required_gaps"]
        receipt_payload[key] = original

    decision_payload["kind"] = "forged"
    _write_json(decision, decision_payload)
    receipt_payload["bootstrap_decision_digest"] = hashlib.sha256(decision.read_bytes()).hexdigest()
    _write_json(receipt, receipt_payload)
    assert (
        "control_replacement_bootstrap_decision_kind_invalid"
        in _report(candidate, accepted_head, candidate_head, receipt)["required_gaps"]
    )
