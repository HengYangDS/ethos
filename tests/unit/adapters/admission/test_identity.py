from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING

import ethos.adapters.admission.identity as identity

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_configured_identity_consumes_only_the_supplied_revisions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    revision = "a" * 40
    monkeypatch.setattr(identity, "_git", lambda *_args: SimpleNamespace(stdout="configured-user"))
    monkeypatch.setattr(
        identity,
        "observe_commit",
        lambda _root, _revision: (
            {
                role: {"name": "Other", "email": "other@example.invalid"}
                for role in ("author", "committer")
            }
            | {"required_gaps": []}
        ),
    )

    report = identity.push_identity_policy_report(tmp_path, (revision,))

    assert report["required_gaps"] == [
        f"pushed_commit_{role}_not_configured_identity:{revision}"
        for role in ("author", "committer")
    ]
