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
    stream = SimpleNamespace(extractall=lambda *_args, **_kwargs: None)
    monkeypatch.setattr(cutover.tarfile, "open", lambda **_kwargs: nullcontext(stream))
    commands: list[tuple[list[str], dict[str, str]]] = []

    def run(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        environment = _kwargs.get("env")
        if isinstance(environment, dict):
            commands.append((args, environment))
            return subprocess.CompletedProcess(args, 0, "", "")
        return subprocess.CompletedProcess(args, 0, b"archive", b"")

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


def _materialization_case(tmp_path: Path) -> tuple[Path, dict[str, str]]:
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
    successor_tree = subprocess.check_output(
        ["git", "rev-parse", "HEAD^{tree}"], cwd=repo, text=True
    ).strip()
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
    return repo, {
        "prepare_head": prepare,
        "prepare_tree": subprocess.check_output(
            ["git", "rev-parse", f"{prepare}^{{tree}}"], cwd=repo, text=True
        ).strip(),
        "successor_head": successor,
        "successor_tree": successor_tree,
        "ref_name": "refs/heads/work/test",
    }


def test_materialization_disables_prepare_reference_hook(tmp_path: Path) -> None:
    repo, envelope = _materialization_case(tmp_path)
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    hook = hooks / "reference-transaction"
    hook.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    hook.chmod(0o755)
    subprocess.run(["git", "config", "core.hooksPath", str(hooks)], cwd=repo, check=True)

    cutover._materialize_successor(repo, envelope)
    cutover._materialize_successor(repo, envelope)

    assert (repo / "value.txt").read_text(encoding="utf-8") == "successor\n"
    assert subprocess.check_output(["git", "status", "--porcelain"], cwd=repo, text=True) == ""


def test_materialization_refuses_dirty_prepare_without_deleting_bytes(tmp_path: Path) -> None:
    repo, envelope = _materialization_case(tmp_path)
    (repo / "value.txt").write_text("valuable dirty bytes\n", encoding="utf-8")

    with pytest.raises(ValueError, match="successor_worktree_not_exact_prepare"):
        cutover._materialize_successor(repo, envelope)

    assert (repo / "value.txt").read_text(encoding="utf-8") == "valuable dirty bytes\n"


def test_materialization_refuses_raced_tree_without_deleting_bytes(tmp_path: Path) -> None:
    repo, envelope = _materialization_case(tmp_path)
    original_run = cutover._run
    observations = 0

    def race_after_clean_check(
        root: Path, *args: str, input_text: str | None = None
    ) -> subprocess.CompletedProcess[str]:
        nonlocal observations
        result = original_run(root, *args, input_text=input_text)
        if args == ("git", "diff-files", "--quiet", "--"):
            observations += 1
            if observations == 1:
                (repo / "value.txt").write_text("valuable raced bytes\n", encoding="utf-8")
        return result

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(cutover, "_run", race_after_clean_check)
        with pytest.raises(ValueError, match="successor_worktree_materialization_failed"):
            cutover._materialize_successor(repo, envelope)

    assert (repo / "value.txt").read_text(encoding="utf-8") == "valuable raced bytes\n"


def test_materialization_holds_successor_lease_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = tmp_path / "state.sqlite"
    payload = '{"wire":"after"}'
    after = {
        "id": "lease:one",
        "subject": "work/one",
        "owner": "actor:one",
        "expires_at": "after",
        "payload_json": payload,
        "payload_sha256": hashlib.sha256(payload.encode()).hexdigest(),
    }
    with closing(sqlite3.connect(db)) as connection, connection:
        connection.execute(
            "create table leases (id text primary key, subject text, owner text, expires_at text, payload_json text)"
        )
        connection.execute(
            "insert into leases values (?, ?, ?, ?, ?)",
            tuple(after[key] for key in ("id", "subject", "owner", "expires_at", "payload_json")),
        )
    monkeypatch.setattr(cutover, "state_database", lambda _root: db)

    def materialize(_root: Path, _envelope: dict[str, object]) -> None:
        with (
            closing(sqlite3.connect(db, timeout=0)) as contender,
            pytest.raises(sqlite3.OperationalError, match="locked"),
        ):
            contender.execute(
                "update leases set payload_json = ? where subject = ?",
                ('{"wire":"drift"}', "work/one"),
            )

    monkeypatch.setattr(cutover, "_materialize_successor", materialize)
    monkeypatch.setattr(cutover, "_git", lambda *_args: "b" * 40)

    cutover._materialize_successor_with_lease_lock(
        tmp_path,
        {
            "successor_head": "b" * 40,
            "ref_name": "refs/heads/work/one",
            "lease_after": after,
        },
    )


def test_materialization_rereads_successor_lease_after_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = tmp_path / "state.sqlite"
    payload = '{"wire":"after"}'
    after = {
        "id": "lease:one",
        "subject": "work/one",
        "owner": "actor:one",
        "expires_at": "after",
        "payload_json": payload,
        "payload_sha256": hashlib.sha256(payload.encode()).hexdigest(),
    }
    with closing(sqlite3.connect(db)) as connection, connection:
        connection.execute(
            "create table leases (id text primary key, subject text, owner text, expires_at text, payload_json text)"
        )
        connection.execute(
            "insert into leases values (?, ?, ?, ?, ?)",
            tuple(after[key] for key in ("id", "subject", "owner", "expires_at", "payload_json")),
        )
    original_lease_rows = cutover._lease_rows

    def drift_after_initial_read(
        root: Path, subject: str
    ) -> tuple[sqlite3.Connection, sqlite3.Row | None]:
        connection, row = original_lease_rows(root, subject)
        with closing(sqlite3.connect(db)) as drifter, drifter:
            drifter.execute(
                "update leases set payload_json = ? where subject = ?",
                ('{"wire":"drift"}', subject),
            )
        return connection, row

    monkeypatch.setattr(cutover, "state_database", lambda _root: db)
    monkeypatch.setattr(cutover, "_lease_rows", drift_after_initial_read)
    monkeypatch.setattr(
        cutover,
        "_materialize_successor",
        lambda *_args: pytest.fail("stale Lease reached materialization"),
    )

    with pytest.raises(ValueError, match="successor_successor_lease_drift"):
        cutover._materialize_successor_with_lease_lock(
            tmp_path,
            {
                "successor_head": "b" * 40,
                "ref_name": "refs/heads/work/one",
                "lease_after": after,
            },
        )


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
    monkeypatch.setattr(cutover, "_validate_static_transition", lambda *_args: None)
    states = iter(("successor_after", "successor_after"))
    monkeypatch.setattr(cutover, "_transition_state", lambda *_args: next(states))
    monkeypatch.setattr(
        cutover,
        "evaluate_successor",
        lambda *_args, **kwargs: calls.append(kwargs) or {"state": "successor_evaluated"},
    )
    monkeypatch.setattr(
        cutover,
        "_materialize_successor_with_lease_lock",
        lambda *_args: calls.append("materialized"),
    )

    apply_from_environment()

    assert calls == [{"require_incumbent_lease": False}, "materialized"]
    assert json.loads(capsys.readouterr().out)["state"] == "successor_cutover_recovered"


def test_apply_rechecks_successor_state_after_evaluation_before_materialization(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    envelope = {
        "prepare_head": "a" * 40,
        "successor_head": "b" * 40,
        "ref_name": "refs/heads/work/one",
        "lease_before": {"subject": "work/one"},
        "lease_after": {"subject": "work/one"},
    }
    states = iter(("successor_after", "successor_before"))
    calls: list[str] = []
    monkeypatch.setenv("ETHOS_SUCCESSOR_ROOT", str(tmp_path))
    monkeypatch.setattr(cutover, "_envelope_from_environment", lambda: (tmp_path, envelope))
    monkeypatch.setattr(cutover, "_validate_static_transition", lambda *_args: None)
    monkeypatch.setattr(cutover, "_transition_state", lambda *_args: next(states))
    monkeypatch.setattr(
        cutover,
        "evaluate_successor",
        lambda *_args, **_kwargs: calls.append("evaluated") or {},
    )
    monkeypatch.setattr(
        cutover,
        "replace_lease",
        lambda *_args: (_ for _ in ()).throw(ValueError("lease_drift_after_evaluation")),
    )
    monkeypatch.setattr(
        cutover,
        "_materialize_successor_with_lease_lock",
        lambda *_args: calls.append("materialized"),
    )

    with pytest.raises(ValueError, match="lease_drift_after_evaluation"):
        apply_from_environment()

    assert calls == ["evaluated"]


def test_apply_rejects_unknown_successor_lease_without_ref_rollback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    envelope = {
        "prepare_head": "a" * 40,
        "successor_head": "b" * 40,
        "ref_name": "refs/heads/work/one",
        "lease_before": {"subject": "work/one"},
        "lease_after": {"subject": "work/one"},
    }
    monkeypatch.setenv("ETHOS_SUCCESSOR_ROOT", str(tmp_path))
    monkeypatch.setattr(cutover, "_envelope_from_environment", lambda: (tmp_path, envelope))
    monkeypatch.setattr(cutover, "_validate_static_transition", lambda *_args: None)
    monkeypatch.setattr(
        cutover,
        "_transition_state",
        lambda *_args: (_ for _ in ()).throw(ValueError("successor_successor_lease_drift")),
    )
    calls: list[object] = []
    monkeypatch.setattr(cutover.subprocess, "run", lambda *_args, **_kwargs: calls.append(_args))

    with pytest.raises(ValueError, match="successor_successor_lease_drift"):
        apply_from_environment()

    assert calls == []
