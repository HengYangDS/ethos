"""Reject escaping patch preimages and expose materialization failures."""

from __future__ import annotations

import difflib
from typing import TYPE_CHECKING

import pytest
import tomli_w

import ethos.adapters.admission.patch_admission as admission
from ethos.adapters.admission.patch_admission import patch_admission
from ethos.contracts.gates import Gate
from ethos.contracts.gates import GateProofSets
from ethos.contracts.gates import GateRegistryDeclaration
from ethos.repository.profile import ProofPolicy
from ethos.repository.profile import RepositoryProfileDeclaration
from ethos.repository.profile import render_repository_profile
from tests.support.governed_repository import commit_active_change
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path


def _repository(tmp_path: Path) -> tuple[Path, str]:
    repo = init_git_repo(tmp_path / "repo")
    (repo / "safe.txt").write_text("old\n", encoding="utf-8")
    commit_active_change(repo)
    return repo, git(repo, "rev-parse", "HEAD")


def _patch(old: str, new: str, body: str = "+value\n") -> str:
    return f"diff --git a/{old} b/{new}\n--- a/{old}\n+++ b/{new}\n@@ -0,0 +1 @@\n{body}"


def _change_patch() -> str:
    return (
        "diff --git a/safe.txt b/safe.txt\n"
        "--- a/safe.txt\n"
        "+++ b/safe.txt\n"
        "@@ -1 +1,2 @@\n"
        " old\n"
        "+value\n"
    )


@pytest.mark.parametrize("old", ["/absolute", "../escape"])
def test_patch_admission_rejects_absolute_and_escaping_preimages(tmp_path: Path, old: str) -> None:
    repo, head = _repository(tmp_path)

    report = patch_admission(
        root=repo,
        requested_paths=("safe.txt",),
        baseline_head=head,
        patch=_patch(old, "safe.txt"),
    )

    assert report["verdict"] == "block"
    assert report["reason"] == "prewrite_patch_preimage_mismatch"


def test_patch_admission_rejects_missing_preimage(tmp_path: Path) -> None:
    repo, head = _repository(tmp_path)

    report = patch_admission(
        root=repo,
        requested_paths=("safe.txt",),
        baseline_head=head,
        patch=_patch("missing.txt", "safe.txt"),
    )

    assert report["verdict"] == "block"
    assert report["reason"] == "prewrite_patch_preimage_mismatch"


def test_patch_admission_rejects_escaping_postimage(tmp_path: Path) -> None:
    repo, head = _repository(tmp_path)

    report = patch_admission(
        root=repo,
        requested_paths=("../escape",),
        baseline_head=head,
        patch=_patch("safe.txt", "../escape"),
    )

    assert report["verdict"] == "block"
    assert report["reason"] == "prewrite_patch_preimage_mismatch"


def test_patch_admission_reports_failed_postimage_apply(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, head = _repository(tmp_path)
    calls = 0

    real_run = admission.run_git

    def fail_second_apply(root: Path, *args: str, **kwargs):
        nonlocal calls
        completed = real_run(root, *args, **kwargs)
        if args[:1] != ("apply",):
            return completed
        calls += 1
        return completed if calls == 1 else completed.__class__(completed.args, 1, "", "")

    monkeypatch.setattr(admission, "run_git", fail_second_apply)

    report = patch_admission(
        root=repo,
        requested_paths=("safe.txt",),
        baseline_head=head,
        patch=_change_patch(),
    )

    assert report["verdict"] == "block"
    assert report["reason"] == "prewrite_patch_postimage_failed"


@pytest.mark.parametrize("owner", ["profile", "registry", "undeclared"])
def test_native_proof_gate_owner_binds_immutable_document_admission(
    tmp_path: Path, owner: str
) -> None:
    """Both native gate carriers close references against only their selected baseline."""
    gate = Gate(id="quality", kind="check", command=("mise", "exec", "--", "python", "--version"))
    registry = GateRegistryDeclaration(
        id="native-quality",
        proof_sets=GateProofSets(default=("quality",), full=("quality",)),
        gates=(gate,),
    )
    inline = ProofPolicy(
        code_correctness_gates=("quality",),
        gates=(gate,),
        code_correctness_map={"behavior": "quality", "static-analysis": "quality"},
    )
    proof = (
        ProofPolicy(gate_registry=".config/quality/gates.toml")
        if owner == "registry"
        else inline
        if owner == "profile"
        else ProofPolicy()
    )
    profile = render_repository_profile(
        RepositoryProfileDeclaration(profile_id="native-reference", proof=proof)
    )
    repo = tmp_path / "native-docs"
    repo.mkdir()
    git(repo, "init", "-b", "dev")
    binding = repo / ".ethos/profile.toml"
    binding.parent.mkdir()
    binding.write_text(profile, encoding="utf-8")
    if owner == "registry":
        declaration = repo / ".config/quality/gates.toml"
        declaration.parent.mkdir(parents=True)
        declaration.write_text(
            tomli_w.dumps(registry.model_dump(mode="json", exclude_defaults=True)), encoding="utf-8"
        )
    path = "docs/README.md"
    document = repo / path
    document.parent.mkdir()
    before = "# Native checks\n\n```sh\nmise exec -- python --version\n```\n"
    after = (
        "---\nsubject: native:checks\nrole: reference\nstate: canonical\nrelations: {}\n---\n\n"
        + before
    )
    document.write_text(before, encoding="utf-8")
    git(repo, "add", ".")
    baseline = git(repo, "write-tree")
    # Mutable profile edits cannot create or withdraw baseline command ownership.
    binding.write_text(
        render_repository_profile(RepositoryProfileDeclaration.bootstrap("native-reference"))
        if owner != "undeclared"
        else render_repository_profile(
            RepositoryProfileDeclaration(profile_id="native-reference", proof=inline)
        ),
        encoding="utf-8",
    )
    patch = f"diff --git a/{path} b/{path}\n" + "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
        )
    )

    report = patch_admission(
        root=repo, requested_paths=(path,), baseline_head=baseline, patch=patch
    )

    assert report["references"] == {"executable": ["mise"]}
    assert report["verdict"] == ("block" if owner == "undeclared" else "pass"), report
    assert report["reason"] == (
        "product_reference_not_admitted_at_baseline:executable:mise"
        if owner == "undeclared"
        else "baseline_product_closure_matched"
    )
    assert document.read_text(encoding="utf-8") == before
    assert git(repo, "show", f"{baseline}:.ethos/profile.toml") == profile.strip()
