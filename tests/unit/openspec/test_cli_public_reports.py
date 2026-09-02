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


def test_official_version_is_the_repository_locked_stable_release() -> None:
    assert cli.OFFICIAL_VERSION == "1.11.0"


def test_source_cli_consumes_the_single_resolved_node_package_supply(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    source = tmp_path / "source"
    supply = tmp_path / "prepared/node_modules"
    package = supply / "@fission-ai/openspec/package.json"
    entry = package.parent / "bin/openspec.js"
    source.mkdir()
    entry.parent.mkdir(parents=True)
    (source / "package.json").write_text("{}\n", encoding="utf-8")
    (source / "package-lock.json").write_text(
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
    package.write_text(
        json.dumps({"name": cli.OFFICIAL_PACKAGE, "version": cli.OFFICIAL_VERSION}),
        encoding="utf-8",
    )
    entry.write_text("", encoding="utf-8")
    observed = []

    def resolve(root):
        observed.append(root)
        return supply

    monkeypatch.setattr(cli, "_SOURCE_ROOT", source)
    monkeypatch.setattr(cli, "_SOURCE_DECLARATION", source / "package.json")
    monkeypatch.setattr(cli, "_LOCK", source / "package-lock.json")
    monkeypatch.setattr(cli, "resolve_node_package_supply", resolve, raising=False)
    monkeypatch.setattr(cli, "_SOURCE_NODE", "/node")
    monkeypatch.setattr(
        cli,
        "run_command",
        lambda *_args, **_kwargs: _completed(stdout=f"{cli.OFFICIAL_VERSION}\n"),
    )

    assert cli.openspec_base_command() == ("/node", entry.as_posix())
    assert observed == [source]


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
    assert all(item[2]["check"] is False for item in observed)
    assert all(item[2]["remove_env_prefixes"] == ("GIT_",) for item in observed)


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
    monkeypatch.setattr(
        cli,
        "verify_official_cli",
        lambda _command, **_kwargs: {"verdict": "block"},
    )
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
    monkeypatch.setattr(cli, "_LOCK", lock)
    monkeypatch.setattr(cli, "_source_runtime", lambda: (package, entry))
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


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({}, ["openspec_status_artifact_graph_missing"]),
        ({"artifacts": []}, ["openspec_status_artifact_graph_missing"]),
        ({"artifacts": [{"id": "proposal"}]}, ["openspec_status_artifact_graph_invalid"]),
        (
            {"artifacts": [{"id": "proposal", "status": "done", "requires": []}]},
            [],
        ),
    ],
)
def test_status_contract_requires_the_official_artifact_graph(payload, expected):
    assert cli.status_contract_gaps(payload) == expected


@pytest.mark.parametrize(
    ("operation", "payload", "expected"),
    [
        ("archive", {}, ["openspec_archive_instructions_invalid"]),
        ("archive", {"changeName": "x", "root": {}}, []),
        ("apply", {"changeName": "x", "root": {}}, ["openspec_apply_instructions_invalid"]),
        (
            "apply",
            {
                "changeName": "x",
                "root": {},
                "state": "ready",
                "progress": {},
                "tasks": [],
                "instruction": "continue",
            },
            [],
        ),
    ],
)
def test_instruction_contracts_are_operation_specific(operation, payload, expected):
    assert cli.instructions_contract_gaps(operation, payload) == expected


def test_config_contract_rejects_machine_global_store_selection():
    assert cli.config_contract_gaps({"defaultStore": "/tmp/global"}) == [
        "openspec_default_store_forbidden"
    ]
    assert cli.config_contract_gaps({}) == []


@pytest.mark.parametrize(
    ("metadata", "expected"),
    [
        ("schema: spec-driven\n", ("openspec", "archive", "change", "--yes", "--json")),
        (
            "schema: spec-driven\nskip_specs: true\n",
            ("openspec", "archive", "change", "--yes", "--skip-specs", "--json"),
        ),
        ("invalid: [", ("openspec", "archive", "change", "--yes", "--json")),
    ],
)
def test_archive_command_uses_only_the_official_change_declaration(tmp_path, metadata, expected):
    marker = tmp_path / "openspec/changes/change/.openspec.yaml"
    marker.parent.mkdir(parents=True)
    marker.write_text(metadata, encoding="utf-8")

    assert cli.archive_command(tmp_path, "change") == expected


@pytest.mark.parametrize(
    ("result", "expected_gaps", "expected_path"),
    [
        (
            {
                "exit_code": 0,
                "parse_error": "",
                "json": {
                    "archive": {
                        "change": "change",
                        "path": "openspec/changes/archive/2026-08-29-change",
                    }
                },
            },
            [],
            "openspec/changes/archive/2026-08-29-change",
        ),
        ({"exit_code": 1, "parse_error": "", "json": {}}, ["openspec_archive_result_invalid"], ""),
        (
            {
                "exit_code": 0,
                "parse_error": "",
                "json": {"archive": {"change": "other", "path": "/outside"}},
            },
            ["openspec_archive_result_invalid"],
            "",
        ),
    ],
)
def test_archive_result_accepts_only_the_exact_repository_archive(
    tmp_path, result, expected_gaps, expected_path
):
    path = result.get("json", {}).get("archive", {}).get("path")
    if isinstance(path, str) and path.startswith("openspec/"):
        result["json"]["archive"]["path"] = (tmp_path / path).as_posix()

    assert cli.archive_result(tmp_path, "change", result) == (expected_gaps, expected_path)
