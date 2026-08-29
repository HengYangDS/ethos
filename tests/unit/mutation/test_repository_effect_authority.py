from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING

import ethos.adapters.mutation.landing as landing
import ethos.adapters.mutation.remote_publication as publication
from ethos.contracts.semantic import Commitment

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


class _Commitment:
    def digest(self) -> str:
        return "c" * 64


class _Proof:
    commitment_digest = "c" * 64

    def model_dump(self, **_kwargs: object) -> dict[str, str]:
        return {"predicate": "proof:execution", "verdict": "pass"}


def test_candidate_plan_compiles_active_openspec_acceptance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority = _Commitment()
    observed: dict[str, object] = {}
    head = "a" * 40
    candidate_head = "b" * 40
    policy = SimpleNamespace(candidate_branch="candidate/dev")
    monkeypatch.setattr(landing, "load_branch_role_policy", lambda _root: policy)
    monkeypatch.setattr(
        landing,
        "run_git",
        lambda *_args, **_kwargs: SimpleNamespace(stdout=f"{head}\n"),
    )
    monkeypatch.setattr(
        landing,
        "candidate_base_report",
        lambda **_kwargs: {
            "verdict": "pass",
            "path": (tmp_path / "candidate").as_posix(),
            "candidate_head": candidate_head,
        },
    )
    monkeypatch.setattr(landing, "proof_attestation", lambda *_args: _Proof())
    monkeypatch.setattr(
        landing,
        "workspace_status",
        lambda *_args, **_kwargs: {"branch": "work/change"},
    )
    monkeypatch.setattr(landing, "leases_by_branch", lambda _root: {"work/change": {}})

    def load_commitment(_root: Path, *, tree_ref: str) -> _Commitment:
        observed["tree_ref"] = tree_ref
        return authority

    def compile_transition(**kwargs: object) -> object:
        observed.update(kwargs)
        return SimpleNamespace(effect={"operation": "candidate.integrate"}, digest="d" * 64)

    monkeypatch.setattr(landing, "load_openspec_commitment", load_commitment)
    monkeypatch.setattr(landing, "_candidate_transition_plan", compile_transition)
    monkeypatch.setattr(landing, "admit_git_effect", lambda *_args: None)

    report = landing.candidate_transition_readiness(root=tmp_path)

    assert report["verdict"] == "pass"
    assert report["state"] == "candidate_transition_admitted"
    assert observed["tree_ref"] == head
    assert observed["authority"] is authority


def test_remote_publication_consumes_selected_proof_acceptance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authority = Commitment(
        schema_version=3,
        id="change:fixture",
        acceptance=("accepted",),
    )
    captured: dict[str, object] = {}
    source = SimpleNamespace(
        peeled_commit="a" * 40,
        tree_oid="b" * 40,
        model_dump=lambda **_kwargs: {"peeled_commit": "a" * 40},
    )
    update = SimpleNamespace(target_ref="refs/heads/dev")
    target = SimpleNamespace(
        remote="origin",
        updates=(update,),
        model_dump=lambda **_kwargs: {"remote": "origin"},
    )
    effect = SimpleNamespace(source=source, targets=(target,))
    monkeypatch.setattr(
        publication,
        "repository_identity",
        lambda _root, *, tree_ref: captured.update(identity_tree=tree_ref) or "repository:test",
    )

    def compile_plan(**kwargs: object) -> object:
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(publication, "compile_publication_plan", compile_plan)

    publication.compile_remote_publication_request(
        root=tmp_path,
        effect=effect,
        proof={
            "predicate": "proof:execution",
            "commitment": authority.identity_projection(),
            "commitment_digest": authority.digest(),
        },
    )

    assert captured["identity_tree"] == "a" * 40
    assert captured["commitment"].digest() == authority.digest()
    assert captured["facts"].repository == "repository:test"
