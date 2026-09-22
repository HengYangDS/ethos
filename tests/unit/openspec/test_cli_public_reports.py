"""Public OpenSpec CLI report boundaries."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from unittest.mock import Mock

import pytest

import ethos.adapters.openspec.cli as cli
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_active_commitment
from tests.support.subprocesses import completed


@pytest.mark.parametrize("reported", [cli.OFFICIAL_VERSION, "unexpected"])
def test_source_cli_consumes_the_single_resolved_node_package_supply(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    reported,
) -> None:
    source = tmp_path
    supply = tmp_path / "prepared/node_modules"
    package = supply / "@fission-ai/openspec/package.json"
    entry = package.parent / "bin/openspec.js"
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
    resolve = Mock(return_value=supply)

    monkeypatch.setattr(cli, "_SOURCE_ROOT", source)
    monkeypatch.setattr(cli, "_SOURCE_DECLARATION", source / "package.json")
    monkeypatch.setattr(cli, "_LOCK", source / "package-lock.json")
    monkeypatch.setattr(cli, "resolve_node_package_supply", resolve, raising=False)
    monkeypatch.setattr(cli, "_SOURCE_NODE", "/node")
    monkeypatch.setattr(
        cli,
        "run_command",
        lambda *_args, **_kwargs: completed(stdout=f"{reported}\n"),
    )
    command = ("/node", entry.as_posix())
    report = cli.verify_official_cli(command)
    assert report["version"] == reported
    assert report["required_gaps"] == (
        [] if reported == cli.OFFICIAL_VERSION else ["openspec_effective_version_mismatch"]
    )
    if reported == cli.OFFICIAL_VERSION:
        assert cli.openspec_base_command() == command
    assert [call.args for call in resolve.call_args_list] == [(source,)] * (
        2 if reported == cli.OFFICIAL_VERSION else 1
    )


@pytest.mark.parametrize(
    ("stdout", "payload", "error"),
    [
        (json.dumps({"state": "ready"}), {"state": "ready"}, ""),
        ("{", {}, "Expecting property name enclosed in double quotes: line 1 column 2 (char 1)"),
        ("[]", {}, "openspec_json_not_object"),
        ("", {}, ""),
    ],
)
def test_run_json_reports_object_malformed_array_and_empty_stdout(
    monkeypatch, tmp_path, stdout, payload, error
):
    def run_command(root, command, **kwargs):
        assert root == tmp_path
        assert command == ("openspec", "doctor", "--json")
        assert (kwargs["check"], kwargs["remove_env_prefixes"]) == (False, ("GIT_",))
        return completed(stdout=stdout)

    monkeypatch.setattr(cli, "run_command", run_command)
    report = cli.run_json(tmp_path, ("openspec",), ("doctor", "--json"))
    assert (report["json"], report["parse_error"]) == (payload, error)


@pytest.mark.parametrize("seconds", [20, 60, 0, 61, float("inf"), float("nan")])
@pytest.mark.parametrize("binary", [False, True])
def test_run_json_reports_timeout_without_claiming_payload(monkeypatch, tmp_path, seconds, binary):
    body = '{"state":"done"}'

    def timeout(*_args, **kwargs):
        assert kwargs["timeout"] == seconds
        raise subprocess.TimeoutExpired(
            ("openspec",),
            seconds,
            output=body.encode() if binary else body,
            stderr=b"" if binary else "late stderr",
        )

    monkeypatch.setattr(cli, "run_command", timeout)
    if not 0 < seconds <= 60:
        with pytest.raises(ValueError, match="openspec_command_timeout_invalid"):
            cli.run_json(tmp_path, ("openspec",), ("list", "--json"), timeout=seconds)
        return
    report = cli.run_json(tmp_path, ("openspec",), ("list", "--json"), timeout=seconds)
    assert report == {
        "command": ["openspec", "list", "--json"],
        "exit_code": 124,
        "stdout": body,
        "stderr": f"openspec command timed out after {seconds:g} seconds"
        if binary
        else "late stderr",
        "json": {},
        "parse_error": "openspec_command_timeout",
    }


def test_run_json_rejects_hostile_inherited_shell_locations(tmp_path, monkeypatch):
    hostile = {
        "PWD": "/hostile/pwd",
        "OLDPWD": "/hostile/oldpwd",
        "OPENSPEC_TELEMETRY": "1",
        "OPENSPEC_NO_UPDATE_CHECK": "0",
    }
    program = (
        "import json, os; "
        f"print(json.dumps({{key: os.environ.get(key) for key in {(*hostile, 'TZ')!r}}}))"
    )
    for name, value in hostile.items():
        monkeypatch.setenv(name, value)
    report = cli.run_json(tmp_path, (sys.executable, "-c", program), ())
    assert report["exit_code"] == 0
    assert report["json"] == {
        "PWD": tmp_path.as_posix(),
        "OLDPWD": tmp_path.as_posix(),
        "TZ": "UTC",
        "OPENSPEC_TELEMETRY": "0",
        "OPENSPEC_NO_UPDATE_CHECK": "1",
    }
    assert {name: os.environ[name] for name in hostile} == hostile


def test_official_cli_public_resolution_and_report_fail_closed(monkeypatch, tmp_path):
    entry = tmp_path / "openspec.js"
    entry.write_text("", encoding="utf-8")
    monkeypatch.setattr(cli, "_SOURCE_NODE", None)
    monkeypatch.setattr(cli, "_DISTRIBUTION_ENTRY", entry)
    monkeypatch.setattr(cli, "_packaged_node", lambda: "/node")
    assert cli.openspec_base_command() is None

    monkeypatch.setattr(cli, "_packaged_node", lambda: None)
    assert cli.openspec_base_command() is None
    with pytest.raises(ValueError, match="openspec_official_cli_missing"):
        cli.run_json_batch(tmp_path, None, (("list", "--json"),))

    report = cli.verify_official_cli(("node", "untrusted-entry.js"))
    assert (report["verdict"], report["required_gaps"]) == (
        "block",
        ["openspec_entry_mismatch"],
    )


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
    ("path", "change", "exit_code", "parse_error", "bound", "alias"),
    [
        ("openspec/changes/archive/2026-08-29-change", "change", 0, "", True, False),
        ("openspec/changes/archive/2026-08-29-change", "change", 1, "", True, False),
        ("openspec/changes/archive/2026-08-29-change", "change", 0, "truncated", True, False),
        ("openspec/changes/archive/2026-08-29-change", "other", 0, "", False, False),
        ("openspec/changes/archive/2026-08-29-other-change", "change", 0, "", False, False),
        ("openspec/changes/archive/2026-08-29-change/nested-change", "change", 0, "", False, False),
        ("openspec/changes/archive/2026-02-30-change", "change", 0, "", False, False),
        ("openspec/changes/archive/invalid-change", "change", 0, "", False, False),
        ("openspec/changes/archive", "change", 0, "", False, False),
        (".", "change", 0, "", False, False),
        ("unrelated", "change", 0, "", False, False),
        ("/outside", "other", 0, "", False, False),
        ("", "change", 0, "", False, False),
        (None, "change", 1, "", False, False),
        ("alias", "change", 0, "", False, True),
        ("openspec/changes/archive/2026-08-30-change", "change", 0, "", False, True),
    ],
)
def test_archive_result_accepts_only_the_exact_repository_archive(
    tmp_path, path, change, exit_code, parse_error, bound, alias
):
    target = tmp_path / "openspec/changes/archive/2026-08-28-change"
    target.mkdir(parents=True)
    marker = target / "proposal.md"
    marker.write_text("preserve unrelated archive\n")
    if alias:
        (tmp_path / path).symlink_to(target, target_is_directory=True)
    result = {
        "exit_code": exit_code,
        "parse_error": parse_error,
        "json": {"archive": {"change": change, "path": str(tmp_path / path) if path else path}}
        if path is not None
        else {},
    }
    gaps = (
        [] if bound and exit_code == 0 and not parse_error else ["openspec_archive_result_invalid"]
    )
    assert cli.archive_result(tmp_path, "change", result) == (gaps, path if bound else "")
    assert marker.read_text() == "preserve unrelated archive\n"


@pytest.mark.parametrize("task_count", [1, 10_000])
def test_official_batch_preserves_native_output_order_failure_and_unexecuted_tail(
    tmp_path, task_count, monkeypatch
):
    """The transport invokes the official program, not a second command parser."""
    root = init_git_repo(tmp_path / "repo")
    write_active_commitment(root)
    tasks = root / "openspec/changes/fixture-change/tasks.md"
    tasks.write_text(
        "## Tasks\n\n" + "".join(f"- [ ] {i}. " + "x" * 128 + "\n" for i in range(task_count))
    )
    base = cli.openspec_base_command()
    assert base is not None
    commands = (
        ("list", "--json"),
        ("status", "--change", "fixture-change", "--json"),
        ("instructions", "apply", "--change", "fixture-change", "--json"),
        ("instructions", "archive", "--change", "fixture-change", "--json"),
        ("show", "fixture-change", "--type", "change", "--json"),
        ("status", "--change", "missing-native-change", "--json"),
        ("list", "--json"),
    )
    expected = [cli.run_json(root, base, args) for args in commands[:-1]]
    native = Mock(wraps=cli.run_command)
    monkeypatch.setattr(cli, "run_command", native)
    actual = cli.run_json_batch(root, None, commands)
    assert native.call_count == 1
    if task_count > 1 and os.name == "posix":
        transport = list(actual[0]["transport"]["command"])
        transport[3] = "0.5"
        with subprocess.Popen(
            transport,
            cwd=root,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ) as child:
            try:
                child.stdin.write(json.dumps([commands[2]]).encode())
                child.stdin.close()
                child.wait(timeout=5)
            finally:
                if child.poll() is None:
                    child.kill()
                    child.wait(timeout=5)
            assert child.returncode != 0
            assert b"openspec_batch_write_timeout" in child.stderr.read()
            assert child.stdout.read().count(b'{"index":') == 1
    for index, (old, new) in enumerate(zip(expected, actual[:-1], strict=True)):
        assert {key: new[key] for key in old} == old
        assert new["transport"]["input_index"] == index
    assert actual[-1]["parse_error"] == "openspec_batch_interrupted"
    assert actual[-1]["json"] == {}
    monkeypatch.setattr(cli, "OFFICIAL_VERSION", "mismatched")
    with pytest.raises(ValueError, match="openspec_effective_version_mismatch"):
        cli.run_json_batch(root, base, commands[:1])
    assert cli.run_json_batch(root, base, ()) == ()
    for invalid in ((), ("openspec",)):
        with pytest.raises(ValueError, match="openspec_batch_entry_invalid"):
            cli.run_json_batch(root, invalid, commands)
    with pytest.raises(ValueError, match="openspec_batch_read_only_required"):
        cli.run_json_batch(root, base, (("archive", "fixture-change", "--yes", "--json"),))


@pytest.mark.parametrize(
    "fault",
    [
        "shape",
        "ordinal",
        "arguments",
        "code",
        "stdout",
        "truncated",
        "extra",
        "missing",
        "exit",
        "stderr",
        "timeout",
    ],
)
def test_official_batch_rejects_unbound_output_and_preserves_failure_evidence(
    tmp_path, monkeypatch, fault
):
    """Only complete ordered native results may become observed JSON facts."""
    args = ("list", "--json")
    row = {
        "index": 0,
        "args": list(args),
        "exit_code": 0,
        "stdout": '{"changes": []}',
        "stderr": "",
    }
    changed = {
        "shape": [],
        "ordinal": row | {"index": True},
        "arguments": row | {"args": ["doctor"]},
        "code": row | {"exit_code": False},
        "stdout": row | {"stdout": {}},
    }.get(fault, row)
    output = json.dumps(changed) + "\n"
    output = {"truncated": output[:-3], "extra": output * 2, "missing": ""}.get(fault, output)
    error = "native error" if fault in {"stderr", "timeout"} else ""

    def native(*_args, **kwargs):
        assert kwargs["timeout"] == cli.OPENSPEC_COMMAND_TIMEOUT_SECONDS
        assert json.loads(kwargs["stdin"]) == [list(args)]
        if fault == "timeout":
            raise subprocess.TimeoutExpired((), 60, output=output.encode(), stderr=error.encode())
        return completed(stdout=output, stderr=error, returncode=int(fault == "exit"))

    monkeypatch.setattr(cli, "run_command", native)
    (report,) = cli.run_json_batch(tmp_path, ("node", "/selected/openspec.js"), (args,))
    assert report["json"] == {}
    assert report["parse_error"] == (
        "openspec_command_timeout" if fault == "timeout" else "openspec_batch_invalid"
    )
    assert report["transport"]["stdout"] == output
    assert report["transport"]["stderr"] == error
