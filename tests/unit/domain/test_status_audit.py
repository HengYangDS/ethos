"""Status audit composition tests."""

from pathlib import Path

import pytest

import ethos.domain.status as status
from tests.support.governed_repository import init_git_repo


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

    assert status.product_audit(root) == {"verdict": "block"}
    assert "write_admission_gaps" not in received
    assert received["tracked_documents"] == tuple(tracked)


def _adopter(root: Path, *, registry: bool) -> Path:
    repo = init_git_repo(root)
    directory = repo / ".ethos"
    directory.mkdir()
    (directory / "profile.toml").write_text(
        'profile_id = "generic-repository"\n[openspec]\nmaterial_paths = ["**"]\n'
        + ('[proof]\ngate_registry = "gates.toml"\n' if registry else ""),
        encoding="utf-8",
    )
    (repo / "openspec/specs").mkdir(parents=True)
    (repo / "openspec/config.yaml").write_text("schema: spec-driven\n", encoding="utf-8")
    return repo


@pytest.mark.parametrize("registry", [False, True])
@pytest.mark.parametrize("condition", ["valid", "role", "release", "openspec", "commit"])
def test_common_adopter_audit_is_representation_independent(
    tmp_path: Path, condition: str, *, registry: bool
) -> None:
    """Real generic observations never inherit product layout or skip obligations."""
    repo = _adopter(tmp_path / "node", registry=registry)
    if condition in {"valid", "role", "release"}:
        source = (
            "[invalid"
            if condition == "release"
            else '[protected_refs]\nbranches = ["dev"]\n'
            if condition == "role"
            else '[protected_refs]\nbranches = ["dev", "main"]\n'
        )
        (repo / ".ethos/release.toml").write_text(source, encoding="utf-8")
    elif condition == "openspec":
        (repo / "openspec/config.yaml").write_text("[invalid", encoding="utf-8")
    else:
        (repo / ".ethos/workspace.toml").write_text(
            '[commit_policy]\nsubject_pattern = "["\n', encoding="utf-8"
        )
    report = status.audit_for_root(repo)
    assert report["verdict"] == ("pass" if condition == "valid" else "block"), report
    assert "docs" not in report
    assert "schemas" not in report
    if condition != "valid":
        fragment = {
            "role": "protected_branches_policy_missing",
            "release": "release_config_invalid",
            "openspec": "openspec_config_invalid",
            "commit": "commit_policy",
        }[condition]
        assert any(fragment in gap for gap in report["required_gaps"])


def test_common_audit_does_not_require_optional_product_capabilities(tmp_path: Path) -> None:
    """A binding-only repository has no invented release, schema or doc obligation."""
    repo = _adopter(tmp_path / "minimal", registry=False)
    (repo / ".ethos/profile.toml").write_text('profile_id = "minimal"\n', encoding="utf-8")
    report = status.audit_for_root(repo)
    assert report["verdict"] == "pass", report
    assert report["release_policy"]["protected_refs"] == {}
    assert report["openspec"]["state"] == "not_applicable"
