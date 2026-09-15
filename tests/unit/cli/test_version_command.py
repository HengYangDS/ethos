from __future__ import annotations

import json
import subprocess
import sys

import pytest

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
    assert identity["product_version"] == "0.2.0-alpha.5"
    assert identity["distribution_version"].startswith("0.2.0a5.dev0+")
    assert payload["data"]["openspec_version"] == "1.13.0"
    assert len(identity["source_commit"]) == 40
    assert len(identity["source_tree"]) == 40
    assert "channel" not in identity
    assert "acceptance_state" not in identity
    assert "\\u" not in completed.stdout


def test_version_human_output_is_concise(tmp_path, monkeypatch) -> None:
    completed = run_ethos_raw("--version")

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.startswith("ethos 0.2.0-alpha.5 ")
    assert "0.2.0a5.dev0+" in completed.stdout
    assert "OpenSpec 1.13.0" in completed.stdout
    assert "{" not in completed.stdout
    monkeypatch.setattr(sys, "prefix", (tmp_path / "runtime" / ("a" * 64) / "python").as_posix())
    monkeypatch.setattr(
        version_module, "require_selected_runtime", lambda _root: (_ for _ in ()).throw(ValueError)
    )
    assert version_module.version_text().startswith("ethos 0.2.0-alpha.5 ")


def test_version_observation_does_not_create_an_undeclared_subcommand() -> None:
    """The global version flag must not make an unknown command silently succeed."""
    completed = run_ethos_raw("version")
    assert completed.returncode != 0
    assert "ethos 0.2.0-alpha.5 " not in completed.stdout


@pytest.mark.parametrize("json_output", [False, True])
def test_native_version_does_not_require_the_command_framework(*, json_output: bool) -> None:
    """Loading Cyclopts for identity-only inspection adds an unrelated dependency."""
    program = (
        "import importlib.abc, runpy, sys\n"
        "class UnavailableFramework(importlib.abc.MetaPathFinder):\n"
        "    def find_spec(self, fullname, path=None, target=None):\n"
        "        if fullname == 'cyclopts' or fullname.startswith('cyclopts.'):\n"
        "            raise ImportError('command framework must not load for version')\n"
        "sys.meta_path.insert(0, UnavailableFramework())\n"
        f"sys.argv = {['ethos', '--version', *(['--json'] if json_output else [])]!r}\n"
        "runpy.run_module('ethos.cli', run_name='__main__')\n"
    )
    result = subprocess.run(
        [sys.executable, "-B", "-I", "-c", program],
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    if json_output:
        assert json.loads(result.stdout)["command"] == "version"
    else:
        assert result.stdout.startswith("ethos 0.2.0-alpha.5 ")
