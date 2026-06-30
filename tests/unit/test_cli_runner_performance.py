from __future__ import annotations

from tests.support import ethos_cli_runner


def test_cli_json_runner_defaults_to_inprocess_execution(monkeypatch) -> None:
    def forbidden_subprocess(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("JSON CLI contract tests should not start a subprocess by default")

    monkeypatch.setattr(ethos_cli_runner, "_run_subprocess", forbidden_subprocess)

    payload = ethos_cli_runner.run_ethos("status", "--json")

    assert payload["ok"] is True
    assert payload["command"] == "status"
