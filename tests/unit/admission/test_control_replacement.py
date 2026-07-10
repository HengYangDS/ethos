from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from ethos.adapters.admission.control_replacement import control_replacement_report
from tests.support.contract_helpers import git
from tests.support.contract_helpers import init_git_repo


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

    report = control_replacement_report(
        accepted_root=repo,
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
        candidate, "-c", "user.name=Test", "-c", "user.email=t@example.com", "commit", "-m", "floor"
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

    report = control_replacement_report(
        accepted_root=repo,
        candidate_root=candidate,
        accepted_head=accepted_head,
        candidate_head=candidate_head,
        external_receipt=receipt,
    )

    assert report["verdict"] == "defer"
    assert report["required_gaps"] == ["control_replacement_receipt_invalid"]


def test_external_evidence_and_declarative_policy_changes_require_incumbent_verifier(
    tmp_path: Path,
) -> None:
    for relative_path in (
        "packages/ethos-core/src/ethos_core/contracts/external_evidence.py",
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

        report = control_replacement_report(
            accepted_root=repo,
            candidate_root=candidate,
            accepted_head=git(repo, "rev-parse", "HEAD"),
            candidate_head=git(candidate, "rev-parse", "HEAD"),
        )

        assert report["required"] is True, relative_path


def test_protected_bootstrap_verifier_mints_exact_digest_bound_receipt(tmp_path: Path) -> None:
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
    proof = tmp_path / "candidate-proof.json"
    proof.write_text(
        json.dumps({"head": candidate_head, "state": "proven", "digest": "a" * 64}),
        encoding="utf-8",
    )
    receipt = tmp_path / "receipt.json"
    verifier_source = (
        Path(__file__).resolve().parents[3]
        / "tools"
        / "bootstrap"
        / "control-replacement-verifier.py"
    )
    verifier = tmp_path / "protected" / "control-replacement-verifier.py"
    verifier.parent.mkdir()
    verifier.write_bytes(verifier_source.read_bytes())
    verifier_digest = hashlib.sha256(verifier.read_bytes()).hexdigest()
    proof_digest = hashlib.sha256(proof.read_bytes()).hexdigest()
    chronicle = tmp_path / "bootstrap-chronicle.json"
    chronicle.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "kind": "control-replacement-bootstrap-decision",
                "id": "chronicle:bootstrap",
                "subject_id": "ethos:control-replacement",
                "event_type": "decision",
                "evidence_ids": ["evidence:bootstrap-review"],
                "decision": "bootstrap/control-replacement",
                "supersedes": [],
                "current_state_delta": "candidate-external verifier admitted for exact heads",
                "accepted_head": accepted_head,
                "candidate_head": candidate_head,
                "verifier_sha256": verifier_digest,
                "candidate_proof_digest": proof_digest,
                "mints_authority": False,
                "reusable_authorization": False,
            }
        ),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            verifier.as_posix(),
            "--accepted-root",
            repo.as_posix(),
            "--candidate-root",
            candidate.as_posix(),
            "--accepted-head",
            accepted_head,
            "--candidate-head",
            candidate_head,
            "--candidate-proof",
            proof.as_posix(),
            "--bootstrap-chronicle",
            chronicle.as_posix(),
            "--write-receipt",
            receipt.as_posix(),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert payload == json.loads(receipt.read_text(encoding="utf-8"))
    assert payload["accepted_head"] == accepted_head
    assert payload["candidate_head"] == candidate_head
    assert payload["accepted_control_digest"] != payload["candidate_control_digest"]
    assert payload["verifier_sha256"] == hashlib.sha256(verifier.read_bytes()).hexdigest()
    assert payload["candidate_proof_digest"] == hashlib.sha256(proof.read_bytes()).hexdigest()
    assert (
        payload["bootstrap_decision_digest"] == hashlib.sha256(chronicle.read_bytes()).hexdigest()
    )

    report = control_replacement_report(
        accepted_root=repo,
        candidate_root=candidate,
        accepted_head=accepted_head,
        candidate_head=candidate_head,
        external_receipt=receipt,
    )
    assert report["verdict"] == "allow"
