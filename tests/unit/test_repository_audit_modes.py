from __future__ import annotations

from pathlib import Path

from ethos.repository import repository_audit as repository_audit_module


def test_repository_audit_can_skip_deep_openspec_cli() -> None:
    def forbidden_openspec(_root: Path) -> dict[str, object]:
        raise AssertionError("shallow repository-audit should not run the official OpenSpec CLI")

    report = repository_audit_module.repository_audit(
        Path.cwd(),
        openspec_mode="shape",
        openspec_reporter=forbidden_openspec,
    )

    assert report["ok"] is True
    assert report["openspec"]["mode"] == "shape"


def test_deep_repository_audit_requires_injected_openspec_provider() -> None:
    report = repository_audit_module.repository_audit(Path.cwd(), openspec_mode="deep")

    assert report["ok"] is False
    assert report["openspec"]["required_gaps"] == ["openspec_reporter_not_configured"]


def test_deep_repository_audit_uses_injected_openspec_provider() -> None:
    def fake_openspec(_root: Path) -> dict[str, object]:
        return {"ok": True, "mode": "deep", "required_gaps": []}

    report = repository_audit_module.repository_audit(
        Path.cwd(),
        openspec_mode="deep",
        openspec_reporter=fake_openspec,
    )

    assert report["ok"] is True
    assert report["openspec"]["mode"] == "deep"


def test_quality_release_avoids_full_repository_audit(monkeypatch) -> None:
    from tests.support import ethos_cli_runner

    def forbidden_repository_audit(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise AssertionError("release file readiness should not run full repository-audit")

    monkeypatch.setattr(repository_audit_module, "repository_audit", forbidden_repository_audit)

    payload = ethos_cli_runner.run_ethos("quality", "release", "--json")

    assert payload["ok"] is True
    assert payload["command"] == "quality release"


def test_default_prove_uses_shallow_repository_audit(monkeypatch) -> None:
    import ethos.cli as cli_module
    from tests.support import ethos_cli_runner

    def forbidden_openspec(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise AssertionError("default proof readiness should not run deep OpenSpec validation")

    monkeypatch.setattr(
        cli_module,
        "openspec_governance_report",
        forbidden_openspec,
    )

    payload = ethos_cli_runner.run_ethos("prove", "--json")

    assert payload["ok"] is True
    assert payload["data"]["repository_audit"]["openspec"]["mode"] == "shape"


def test_report_uses_shallow_repository_audit(monkeypatch) -> None:
    import ethos.cli as cli_module
    from tests.support import ethos_cli_runner

    def forbidden_openspec(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise AssertionError("scorecard report should not run deep OpenSpec validation")

    monkeypatch.setattr(
        cli_module,
        "openspec_governance_report",
        forbidden_openspec,
    )

    payload = ethos_cli_runner.run_ethos("report", "--json")

    assert payload["ok"] is True
    assert payload["data"]["repository_audit"]["openspec"]["mode"] == "shape"


def test_openspec_shape_flags_completed_but_unarchived_change(tmp_path: Path) -> None:
    """A change whose tasks are all complete but which is still in changes/ (not
    archived) is a carrier masquerading as active — the always-run shape audit must
    flag it from ETHOS's own tasks-complete signal, not only at land --closeout."""
    from ethos.repository.repository_audit import _openspec_shape_report

    openspec = tmp_path / "openspec"
    (openspec / "specs").mkdir(parents=True)
    (openspec / "config.yaml").write_text("version: 1\n", encoding="utf-8")
    change = openspec / "changes" / "done-change"
    change.mkdir(parents=True)
    (change / "tasks.md").write_text("## 1\n\n- [x] a\n- [x] b\n", encoding="utf-8")

    report = _openspec_shape_report(tmp_path)

    assert report["ok"] is False
    assert "openspec_completed_change_unarchived:done-change" in report["required_gaps"]


def test_openspec_shape_allows_in_progress_and_archived_changes(tmp_path: Path) -> None:
    from ethos.repository.repository_audit import _openspec_shape_report

    openspec = tmp_path / "openspec"
    (openspec / "specs").mkdir(parents=True)
    (openspec / "config.yaml").write_text("version: 1\n", encoding="utf-8")
    # in-progress change (a box unchecked) is legitimately active
    active = openspec / "changes" / "wip"
    active.mkdir(parents=True)
    (active / "tasks.md").write_text("- [x] a\n- [ ] b\n", encoding="utf-8")
    # archived completed change is fine
    archived = openspec / "changes" / "archive" / "2026-01-01-old"
    archived.mkdir(parents=True)
    (archived / "tasks.md").write_text("- [x] a\n", encoding="utf-8")

    report = _openspec_shape_report(tmp_path)

    assert not any("unarchived" in gap for gap in report["required_gaps"])
