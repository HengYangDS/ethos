from __future__ import annotations

import json
import sys

import ethos.surface.cli.version as version_module
from tests.support.ethos_cli_runner import run_ethos_raw


def test_version_json_is_one_utf8_result_not_double_encoded() -> None:
    completed = run_ethos_raw("--version", "--json")

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert isinstance(payload, dict)
    assert payload["command"] == "version"
    assert payload["verdict"] == "pass"
    identity = payload["data"]["identity"]
    assert identity["product_version"] == "0.2.0-alpha.1"
    assert identity["distribution_version"].startswith("0.2.0a1.dev0+")
    assert len(identity["source_commit"]) == 40
    assert len(identity["source_tree"]) == 40
    assert identity["channel"] == "development"
    assert identity["acceptance_state"] == "unaccepted"
    assert "\\u" not in completed.stdout


def test_version_human_output_is_concise(tmp_path, monkeypatch) -> None:
    completed = run_ethos_raw("--version")

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.startswith("ethos 0.2.0-alpha.1 ")
    assert "0.2.0a1.dev0+" in completed.stdout
    assert "{" not in completed.stdout
    monkeypatch.setattr(sys, "prefix", (tmp_path / "runtime" / ("a" * 64) / "python").as_posix())
    monkeypatch.setattr(
        version_module, "require_selected_runtime", lambda _root: (_ for _ in ()).throw(ValueError)
    )
    assert version_module.version_text().startswith("ethos 0.2.0-alpha.1 ")
