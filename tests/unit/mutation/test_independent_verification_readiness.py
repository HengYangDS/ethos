from __future__ import annotations

from typing import TYPE_CHECKING

import ethos.adapters.mutation.core as mutation_core

if TYPE_CHECKING:
    from pathlib import Path


def test_proof_readiness_projects_publish_verification_without_blocking_other_actions(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(mutation_core, "proof_gaps", lambda _root, _head: [])
    monkeypatch.setattr(
        mutation_core,
        "independent_verification_request",
        lambda **_kwargs: {"action": "publish"},
    )
    monkeypatch.setattr(
        mutation_core,
        "independent_verification_admission_report",
        lambda **_kwargs: {
            "ok": False,
            "state": "blocked",
            "evidence_class": "local_readiness",
            "required_gaps": ["independent_verification_receipt_required"],
        },
    )

    report = mutation_core.proof_readiness_report(tmp_path, "a" * 40)

    assert report["blocking"] is False
    assert report["local_readiness"] is True
    assert report["evidence_class"] == "local_readiness"
    assert report["independent_verification"]["state"] == "blocked"
    assert report["independent_verification"]["required_gaps"] == [
        "independent_verification_receipt_required"
    ]
