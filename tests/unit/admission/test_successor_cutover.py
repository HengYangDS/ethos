from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
from contextlib import closing
from contextlib import nullcontext
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.admission.successor_cutover as cutover
from ethos.adapters.admission.successor_cutover import apply_from_environment
from ethos.adapters.admission.successor_cutover import load_envelope
from ethos.adapters.admission.successor_cutover import replace_lease

if TYPE_CHECKING:
    from pathlib import Path


def test_evaluator_keeps_virtual_environment_interpreter_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    virtual_python = tmp_path / "venv" / "bin" / "python"
    virtual_python.parent.mkdir(parents=True)
    virtual_python.symlink_to(cutover.sys.executable)
    monkeypatch.setattr(cutover.sys, "executable", virtual_python.as_posix())
    monkeypatch.setenv("ETHOS_SUCCESSOR_ENVELOPE", "/tmp/envelope.json")
    monkeypatch.setenv("ETHOS_SUCCESSOR_ROOT", "/tmp/repository")
    monkeypatch.setattr(cutover, "validate_transition", lambda *_args: None)
    monkeypatch.setattr(
        cutover.subprocess,
        "Popen",
        lambda *_args, **_kwargs: SimpleNamespace(stdout=object(), wait=lambda: 0),
    )
    stream = SimpleNamespace(extractall=lambda *_args, **_kwargs: None)
    monkeypatch.setattr(cutover.tarfile, "open", lambda **_kwargs: nullcontext(stream))
    commands: list[tuple[list[str], dict[str, str]]] = []

    def run(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        commands.append((args, _kwargs["env"]))
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(cutover.subprocess, "run", run)

    cutover.evaluate_successor(
        tmp_path,
        {
            "successor_head": "a" * 40,
            "successor": {
                "carrier": ".ethos/commitment.toml",
                "digest": "b" * 64,
                "tests": ["tests/test_successor.py"],
            },
        },
    )

    assert [command[0][0] for command in commands] == [
        virtual_python.as_posix(),
        virtual_python.as_posix(),
    ]
    assert all(
        not any(key.startswith("ETHOS_SUCCESSOR_") for key in environment)
        for _, environment in commands
    )


def _write_envelope(path: Path, payload: dict[str, object]) -> str:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_envelope_requires_exact_external_digest(tmp_path: Path) -> None:
    path = tmp_path / "envelope.json"
    digest = _write_envelope(path, {"operation": "semantic-kernel-successor-cutover-v1"})

    assert load_envelope(path, digest)["operation"].endswith("-v1")
    with pytest.raises(ValueError, match="successor_envelope_digest_mismatch"):
        load_envelope(path, "0" * 64)


def test_envelope_rejects_group_writable_file(tmp_path: Path) -> None:
    path = tmp_path / "envelope.json"
    digest = _write_envelope(path, {"operation": "semantic-kernel-successor-cutover-v1"})
    path.chmod(0o660)

    with pytest.raises(ValueError, match="group_or_world_writable"):
        load_envelope(path, digest)


def test_lease_cutover_is_full_row_cas_and_single_use(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = tmp_path / "state.sqlite"
    before_payload = json.dumps({"wire": "before"}, sort_keys=True)
    after_payload = json.dumps({"wire": "after"}, sort_keys=True)
    with closing(sqlite3.connect(db)) as connection, connection:
        connection.execute(
            "create table leases (id text primary key, subject text, owner text, expires_at text, payload_json text)"
        )
        connection.execute(
            "insert into leases values (?, ?, ?, ?, ?)",
            ("lease:one", "work/one", "actor:one", "later", before_payload),
        )
    monkeypatch.setattr(
        "ethos.adapters.admission.successor_cutover.state_database", lambda _root: db
    )
    before = {
        "id": "lease:one",
        "subject": "work/one",
        "owner": "actor:one",
        "expires_at": "later",
        "payload_json": before_payload,
        "payload_sha256": hashlib.sha256(before_payload.encode()).hexdigest(),
    }
    after = {
        **before,
        "owner": "actor:two",
        "payload_json": after_payload,
        "payload_sha256": hashlib.sha256(after_payload.encode()).hexdigest(),
    }
    envelope = {"lease_before": before, "lease_after": after}

    replace_lease(tmp_path, envelope)
    with closing(sqlite3.connect(db)) as connection:
        assert connection.execute("select owner, payload_json from leases").fetchone() == (
            "actor:two",
            after_payload,
        )
    with pytest.raises(ValueError, match="successor_incumbent_lease_drift"):
        replace_lease(tmp_path, envelope)


def test_lease_cutover_rejects_identity_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "ethos.adapters.admission.successor_cutover.state_database",
        lambda _root: tmp_path / "unused.sqlite",
    )
    before = {
        "id": "lease:one",
        "subject": "work/one",
        "owner": "actor:one",
        "expires_at": "later",
        "payload_json": "{}",
        "payload_sha256": hashlib.sha256(b"{}").hexdigest(),
    }

    with pytest.raises(ValueError, match="successor_lease_identity_mismatch"):
        replace_lease(
            tmp_path,
            {"lease_before": before, "lease_after": {**before, "id": "lease:two"}},
        )


def test_lease_cutover_rejects_missing_incumbent_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = tmp_path / "state.sqlite"
    with closing(sqlite3.connect(db)) as connection, connection:
        connection.execute(
            "create table leases (id text primary key, subject text, owner text, expires_at text, payload_json text)"
        )
    monkeypatch.setattr(cutover, "state_database", lambda _root: db)
    before = {
        "id": "lease:one",
        "subject": "work/one",
        "owner": "actor:one",
        "expires_at": "later",
        "payload_json": "{}",
        "payload_sha256": hashlib.sha256(b"{}").hexdigest(),
    }

    with pytest.raises(ValueError, match="successor_incumbent_lease_drift"):
        replace_lease(tmp_path, {"lease_before": before, "lease_after": before})


def test_materialization_disables_prepare_reference_hook(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "work/test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    (repo / "value.txt").write_text("prepare\n", encoding="utf-8")
    subprocess.run(["git", "add", "value.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "prepare"], cwd=repo, check=True)
    prepare = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    (repo / "value.txt").write_text("successor\n", encoding="utf-8")
    subprocess.run(["git", "commit", "-qam", "successor"], cwd=repo, check=True)
    successor = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    tree = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=repo, text=True).strip()
    subprocess.run(
        ["git", "-c", "core.hooksPath=/dev/null", "update-ref", "refs/heads/work/test", prepare],
        cwd=repo,
        check=True,
    )
    subprocess.run(["git", "reset", "--hard", "-q", prepare], cwd=repo, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "core.hooksPath=/dev/null",
            "update-ref",
            "refs/heads/work/test",
            successor,
            prepare,
        ],
        cwd=repo,
        check=True,
    )
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    hook = hooks / "reference-transaction"
    hook.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    hook.chmod(0o755)
    subprocess.run(["git", "config", "core.hooksPath", str(hooks)], cwd=repo, check=True)

    cutover._materialize_successor(
        repo,
        {"successor_head": successor, "successor_tree": tree},
    )

    assert (repo / "value.txt").read_text(encoding="utf-8") == "successor\n"
    assert subprocess.check_output(["git", "status", "--porcelain"], cwd=repo, text=True) == ""


def test_apply_resumes_exact_successor_ref_and_lease(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    before = {
        "id": "lease:one",
        "subject": "work/one",
        "owner": "actor:one",
        "expires_at": "before",
        "payload_json": '{"wire":"before"}',
        "payload_sha256": hashlib.sha256(b'{"wire":"before"}').hexdigest(),
    }
    after = {
        **before,
        "expires_at": "after",
        "payload_json": '{"wire":"after"}',
        "payload_sha256": hashlib.sha256(b'{"wire":"after"}').hexdigest(),
    }
    envelope = {
        "prepare_head": "a" * 40,
        "successor_head": "b" * 40,
        "successor_tree": "c" * 40,
        "ref_name": "refs/heads/work/one",
        "lease_before": before,
        "lease_after": after,
    }
    calls: list[object] = []
    monkeypatch.setenv("ETHOS_SUCCESSOR_ROOT", str(tmp_path))
    monkeypatch.setattr(cutover, "_envelope_from_environment", lambda: (tmp_path, envelope))
    monkeypatch.setattr(cutover, "_git", lambda *_args: "b" * 40)
    monkeypatch.setattr(cutover, "_read_raw_lease", lambda *_args: after)
    monkeypatch.setattr(
        cutover,
        "evaluate_successor",
        lambda *_args, **kwargs: calls.append(kwargs) or {"state": "successor_evaluated"},
    )
    monkeypatch.setattr(
        cutover,
        "_materialize_successor",
        lambda *_args: calls.append("materialized"),
    )

    apply_from_environment()

    assert calls == [{"require_incumbent_lease": False}, "materialized"]
    assert json.loads(capsys.readouterr().out)["state"] == "successor_cutover_recovered"
