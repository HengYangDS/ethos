"""Status audit composition tests."""

from pathlib import Path

import ethos.domain.status as status


def test_product_source_audit_does_not_observe_local_hook_runtime(
    monkeypatch, tmp_path: Path
) -> None:
    """Source correctness is independent of local mutation-runtime activation."""
    root = tmp_path / "repo"
    root.mkdir()
    profile = root / ".ethos/profile.toml"
    profile.parent.mkdir()
    profile.write_text("", encoding="utf-8")
    tracked = ["README.md", "docs/concepts/kernel-model.md"]
    received: dict[str, object] = {}

    monkeypatch.setattr(status, "profile_gate_registry", lambda _root: ("gate",))
    monkeypatch.setattr(
        status,
        "hook_runtime_binding",
        lambda _root: (_ for _ in ()).throw(AssertionError("hook runtime must not be observed")),
        raising=False,
    )
    monkeypatch.setattr(status, "git_files", lambda _root, _pattern: tracked)

    def repository_audit(_root: Path, **kwargs: object) -> dict[str, object]:
        received.update(kwargs)
        return {"verdict": "block"}

    monkeypatch.setattr(status.repository_audit_module, "repository_audit", repository_audit)

    assert status.audit_for_root(root) == {"verdict": "block"}
    assert "write_admission_gaps" not in received
    assert received["tracked_documents"] == tuple(tracked)
