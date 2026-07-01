from __future__ import annotations

from pathlib import Path

from ethos_repository import repository_audit as repository_audit_module


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
