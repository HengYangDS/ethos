from __future__ import annotations

from pathlib import Path

from ethos_governance import self_audit as self_audit_module


def test_self_audit_can_skip_deep_openspec_cli(monkeypatch) -> None:
    def forbidden_openspec(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise AssertionError("shallow self-audit should not run the official OpenSpec CLI")

    monkeypatch.setattr(
        self_audit_module,
        "openspec_self_governance_report",
        forbidden_openspec,
    )

    report = self_audit_module.self_audit(Path.cwd(), openspec_mode="shape")

    assert report["ok"] is True
    assert report["openspec"]["mode"] == "shape"


def test_quality_release_avoids_full_self_audit(monkeypatch) -> None:
    from tests.support import ethos_cli_runner

    def forbidden_self_audit(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise AssertionError("release file readiness should not run full self-audit")

    monkeypatch.setattr(self_audit_module, "self_audit", forbidden_self_audit)

    payload = ethos_cli_runner.run_ethos("quality", "release", "--json")

    assert payload["ok"] is True
    assert payload["command"] == "quality release"


def test_default_prove_uses_shallow_self_audit(monkeypatch) -> None:
    from tests.support import ethos_cli_runner

    def forbidden_openspec(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise AssertionError("default proof readiness should not run deep OpenSpec validation")

    monkeypatch.setattr(
        self_audit_module,
        "openspec_self_governance_report",
        forbidden_openspec,
    )

    payload = ethos_cli_runner.run_ethos("prove", "--json")

    assert payload["ok"] is True
    assert payload["data"]["self_audit"]["openspec"]["mode"] == "shape"


def test_report_uses_shallow_self_audit(monkeypatch) -> None:
    from tests.support import ethos_cli_runner

    def forbidden_openspec(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise AssertionError("scorecard report should not run deep OpenSpec validation")

    monkeypatch.setattr(
        self_audit_module,
        "openspec_self_governance_report",
        forbidden_openspec,
    )

    payload = ethos_cli_runner.run_ethos("report", "--json")

    assert payload["ok"] is True
    assert payload["data"]["self_audit"]["openspec"]["mode"] == "shape"
