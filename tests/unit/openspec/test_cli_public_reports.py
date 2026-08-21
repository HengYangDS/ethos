"""Public OpenSpec CLI report boundaries."""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

import ethos.adapters.openspec.cli as cli


def _completed(*, stdout: str = "", stderr: str = "", returncode: int = 0):
    return subprocess.CompletedProcess((), returncode, stdout, stderr)


def test_run_json_reports_object_malformed_array_and_empty_stdout(monkeypatch, tmp_path):
    outputs = (
        (json.dumps({"state": "ready"}), {"state": "ready"}, ""),
        ("{", {}, "Expecting property name enclosed in double quotes: line 1 column 2 (char 1)"),
        ("[]", {}, "openspec_json_not_object"),
        ("", {}, ""),
    )
    observed = []

    def run_command(root, command, **kwargs):
        observed.append((root, command, kwargs))
        return _completed(stdout=outputs[len(observed) - 1][0])

    monkeypatch.setattr(cli, "run_command", run_command)
    reports = [cli.run_json(tmp_path, ("openspec",), ("doctor", "--json")) for _ in outputs]

    assert [(report["json"], report["parse_error"]) for report in reports] == [
        (payload, error) for _, payload, error in outputs
    ]
    assert all(item[0] == tmp_path for item in observed)
    assert all(item[1] == ("openspec", "doctor", "--json") for item in observed)
    assert all(item[2]["check"] is False and item[2]["capture_output"] is True for item in observed)


@pytest.mark.parametrize(
    ("stdout", "stderr", "expected_stdout", "expected_stderr"),
    [
        (b"partial", b"", "", "openspec command timed out after 60 seconds"),
        ("partial", "late stderr", "partial", "late stderr"),
    ],
)
def test_run_json_reports_timeout_without_claiming_payload(
    monkeypatch, tmp_path, stdout, stderr, expected_stdout, expected_stderr
):
    def timeout(*_args, **_kwargs):
        raise subprocess.TimeoutExpired(("openspec",), 60, output=stdout, stderr=stderr)

    monkeypatch.setattr(cli, "run_command", timeout)
    report = cli.run_json(tmp_path, ("openspec",), ("list", "--json"))

    assert report == {
        "command": ["openspec", "list", "--json"],
        "exit_code": 124,
        "stdout": expected_stdout,
        "stderr": expected_stderr,
        "json": {},
        "parse_error": "openspec_command_timeout",
    }


def test_run_json_rejects_hostile_inherited_shell_locations(tmp_path, monkeypatch):
    probe = tmp_path / "environment.py"
    probe.write_text(
        "import json, os\n"
        "print(json.dumps({key: os.environ.get(key) for key in ('PWD', 'OLDPWD', 'TZ')}))\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("PWD", "/hostile/pwd")
    monkeypatch.setenv("OLDPWD", "/hostile/oldpwd")

    report = cli.run_json(tmp_path, (sys.executable, probe.as_posix()), ())

    assert report["exit_code"] == 0
    assert report["json"] == {
        "PWD": tmp_path.as_posix(),
        "OLDPWD": tmp_path.as_posix(),
        "TZ": "UTC",
    }
    assert os.environ["PWD"] == "/hostile/pwd"
    assert os.environ["OLDPWD"] == "/hostile/oldpwd"


def test_official_cli_public_resolution_and_report_fail_closed(monkeypatch, tmp_path):
    entry = tmp_path / "openspec.js"
    entry.write_text("", encoding="utf-8")
    monkeypatch.setattr(cli, "_SOURCE_NODE", None)
    monkeypatch.setattr(cli, "_DISTRIBUTION_ENTRY", entry)
    monkeypatch.setattr(cli, "_packaged_node", lambda: "/node")
    verify = cli.verify_official_cli
    monkeypatch.setattr(cli, "verify_official_cli", lambda _command: {"verdict": "block"})
    assert cli.openspec_base_command() is None

    monkeypatch.setattr(cli, "_packaged_node", lambda: None)
    assert cli.openspec_base_command() is None

    report = verify(("node", "untrusted-entry.js"))
    assert (report["verdict"], report["required_gaps"]) == (
        "block",
        ["openspec_entry_mismatch"],
    )


def test_official_cli_reports_effective_version_mismatch(monkeypatch, tmp_path):
    package = tmp_path / "node_modules/@fission-ai/openspec/package.json"
    entry = package.parent / "bin/openspec.js"
    lock = tmp_path / "package-lock.json"
    package.parent.mkdir(parents=True)
    entry.parent.mkdir(parents=True)
    package.write_text(
        json.dumps({"name": cli.OFFICIAL_PACKAGE, "version": cli.OFFICIAL_VERSION}),
        encoding="utf-8",
    )
    entry.write_text("", encoding="utf-8")
    lock.write_text(
        json.dumps(
            {
                "packages": {
                    "": {"dependencies": {cli.OFFICIAL_PACKAGE: cli.OFFICIAL_VERSION}},
                    "node_modules/@fission-ai/openspec": {"version": cli.OFFICIAL_VERSION},
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "_ENTRY", entry)
    monkeypatch.setattr(cli, "_PACKAGE", package)
    monkeypatch.setattr(cli, "_LOCK", lock)
    command = ("node", entry.as_posix())
    monkeypatch.setattr(
        cli,
        "run_command",
        lambda *_args, **_kwargs: _completed(stdout="unexpected\n"),
    )

    report = cli.verify_official_cli(command)

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["openspec_effective_version_mismatch"]
    assert report["version"] == "unexpected"
