"""Status audit composition tests."""

from pathlib import Path

from ethos.domain import status


def test_product_audit_receives_observed_hook_runtime_gaps(monkeypatch, tmp_path: Path) -> None:
    """The domain observes hook IO before invoking pure repository policy."""
    root = tmp_path / "repo"
    root.mkdir()
    profile = root / ".ethos/profile.toml"
    profile.parent.mkdir()
    profile.write_text("", encoding="utf-8")
    observed = ["write_admission_not_armed:pre-commit_launcher_missing"]
    tracked = ["README.md", "docs/concepts/kernel-model.md"]
    received: dict[str, object] = {}

    monkeypatch.setattr(status, "profile_gate_registry", lambda _root: ("gate",))
    monkeypatch.setattr(status, "hook_runtime_binding", lambda _root: {"required_gaps": observed})
    monkeypatch.setattr(status, "git_files", lambda _root, _pattern: tracked)

    def repository_audit(_root: Path, **kwargs: object) -> dict[str, object]:
        received.update(kwargs)
        return {"verdict": "block"}

    monkeypatch.setattr(status.repository_audit_module, "repository_audit", repository_audit)

    assert status.audit_for_root(root) == {"verdict": "block"}
    assert received["write_admission_gaps"] == observed
    assert received["tracked_documents"] == tuple(tracked)
