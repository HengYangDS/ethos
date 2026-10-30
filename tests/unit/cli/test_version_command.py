"""Return one native version result without loading unrelated command machinery."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from packaging.version import Version

import ethos.surface.cli.version as version_module
from ethos.repository.release.identity import product_version
from tests.support.ethos_cli_runner import run_ethos_raw

_PRODUCT = product_version(Path(__file__).resolve().parents[3])
_DEVELOPMENT = f"{Version(_PRODUCT)}.dev0+"


def test_version_json_is_one_utf8_result_not_double_encoded() -> None:
    completed = run_ethos_raw("--version", "--json")

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert isinstance(payload, dict)
    assert payload["command"] == "version"
    assert payload["verdict"] == "pass"
    identity = payload["data"]["identity"]
    assert identity["product_version"] == _PRODUCT
    assert identity["distribution_version"].startswith(_DEVELOPMENT)
    assert payload["data"]["openspec_version"] == version_module.OFFICIAL_VERSION
    assert len(identity["source_commit"]) == 40
    assert len(identity["source_tree"]) == 40
    assert "channel" not in identity
    assert "acceptance_state" not in identity
    assert "\\u" not in completed.stdout


def test_version_human_output_is_concise(tmp_path, monkeypatch) -> None:
    completed = run_ethos_raw("--version")

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.startswith(f"ethos {_PRODUCT} ")
    assert _DEVELOPMENT in completed.stdout
    assert f"OpenSpec {version_module.OFFICIAL_VERSION}" in completed.stdout
    assert "{" not in completed.stdout
    monkeypatch.setattr(sys, "prefix", (tmp_path / "runtime" / ("a" * 64) / "python").as_posix())
    monkeypatch.setattr(
        version_module, "require_selected_runtime", lambda _root: (_ for _ in ()).throw(ValueError)
    )
    assert version_module.version_text().startswith(f"ethos {_PRODUCT} ")


def test_version_observation_does_not_create_an_undeclared_subcommand() -> None:
    """The global version flag must not make an unknown command silently succeed."""
    completed = run_ethos_raw("version")
    assert completed.returncode != 0
    assert f"ethos {_PRODUCT} " not in completed.stdout


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
        assert result.stdout.startswith(f"ethos {_PRODUCT} ")
