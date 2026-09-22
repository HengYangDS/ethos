"""Carry selected acceptance intent through candidate and publication effects."""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING

import ethos.adapters.mutation.publication.request as publication
from ethos.contracts.semantic import Commitment

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


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
