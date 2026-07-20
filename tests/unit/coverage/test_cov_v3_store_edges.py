"""Compact store coverage closure."""

import ast
import sqlite3
import subprocess
from pathlib import Path

import pytest

import ethos.adapters.store.state.lease.lifecycle.core as lease
import ethos.adapters.store.state.lease.lifecycle.effects as effects
import ethos.adapters.store.state.lease.projection as projection
from ethos.adapters.store.retrieval import common
from ethos.adapters.store.retrieval import indexing
from ethos.adapters.store.retrieval import query
from ethos.adapters.store.retrieval import schema
from ethos.adapters.store.retrieval import sources
from ethos_core.contracts.context.projection import redact_secret_like


def _path(root, name):
    path = root / name
    path.mkdir()
    return path


def _git(root, *args):
    return subprocess.run(("git", *args), cwd=root, check=True, capture_output=True)


def _repo(root, name):
    root = _path(root, name)
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.name", "Test")
    _git(root, "config", "user.email", "test@example.com")
    return root


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def _commit(root):
    _git(root, "add", "-A")
    _git(root, "commit", "-m", "seed")


def test_store_edges(  # noqa: PLR0915, RUF100 - related store edge matrix
    tmp_path, monkeypatch
):
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/dev/null")
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", "/dev/null")
    plain = _path(tmp_path, "plain")
    assert sources.tracked_files(plain) == sources.dirty_allowed_sources(plain) == []
    assert sources.is_allowed_source_rel("packages/foo/README.md")
    target, link = plain / "real.md", plain / "link.md"
    _write(target, "x")
    link.symlink_to(target)
    assert sources.unsafe_source_reason(plain.resolve(), link) == "symlink_source"
    chunks = indexing.chunks_for("packages/x.py", "intro\n# Heading\nbody\n## Sub\nmore\n#\ntail\n")
    titles = [item["title"] for item in chunks]
    assert {"Heading", "Sub"} <= set(titles) and titles.count("packages/x.py") >= 2  # noqa: PT018 coverage closure keeps callback and branch shapes explicit  # fmt: skip
    assert indexing.signature_for(ast.parse("x=1").body[0]) == ""
    assert (indexing.kind_for("evidence/claims/c.md", Path("c.md")), indexing.kind_for("schemas/s.json", Path("s.json"))) == ("claim", "schema")  # fmt: skip
    candidate = {"path": ".ethos/state/x", "start_line": 1, "end_line": 1, "digest": "d", "file_digest": "f", "head": "h", "score": 1}  # fmt: skip
    assert query.verify_candidate(plain.resolve(), candidate)["verification"] == {"status": "unverified", "method": "tracked-path+head+line-span+sha256", "reason": "path_not_allowed_source"}  # fmt: skip
    redacted = redact_secret_like("api_key=ABCDEFGHIJKLMNOP")
    assert "<redacted-secret>" in redacted and "ABCDEFGHIJKLMNOP" not in redacted  # noqa: PT018 coverage closure keeps callback and branch shapes explicit  # fmt: skip
    repo = _repo(tmp_path, "rebuild")
    _write(repo / "README.md", "# Title\ncontent")
    _write(repo / "packages/demo/mod.py", "def alpha():\n return 1\n")
    _commit(repo)
    assert [indexing.rebuild_context_index(repo, apply=True, authorized=True)["state"] for _ in range(2)] == ["indexed"] * 2  # fmt: skip
    repo = _repo(tmp_path, "eval")
    _write(repo / "README.md", "# Title\nseed")
    _commit(repo)
    schema.initialize_context_index(common.default_retrieval_db_path(repo))
    report = query.context_eval_report(repo, suite="smoke")
    assert (report["ok"], report["required_gaps"], report["data"]["metrics"]["critical_stale_hits"]) == (False, ["context_eval_smoke_failed"], 1)  # fmt: skip
    repo = _repo(tmp_path, "digest")
    _write(repo / "README.md", "# Title\nactual body")
    _commit(repo)
    candidate = {"path": "README.md", "start_line": 1, "end_line": 1, "digest": "deadbeef", "file_digest": "deadbeef", "head": common.git_head(repo), "score": 1}  # fmt: skip
    verification = query.verify_candidate(repo, candidate)["verification"]
    assert verification["status"] == "stale"
    assert verification["reason"] == "digest_mismatch"
    assert lease.json_object("{") == {}
    assert indexing.rebuild_context_index(plain, apply=True, authorized=False)["required_gaps"] == ["context_index_requires_authorization"]  # fmt: skip
    assert query.query_candidates(plain / "missing", "!!!", limit=1) == []
    assert query.fts_query_str("!!!") == ""
    present = plain / "present"
    monkeypatch.setattr(projection, "lease_rows", lambda _: [("id", "lane", "owner", "bad", "{}")])
    assert projection.active_leases(present) == []
    present.touch()
    assert projection.active_leases(present) == []
    monkeypatch.setattr(projection, "lease_rows", lambda _: [("id", "lane", "owner", "x", "{")])
    assert not projection.lease_inventory_rows(present)[0]["payload_valid"]
    assert (projection.integer_value("7"), projection.integer_value("x"), effects.delete_exact_leases(plain / "absent", [])) == (7, 0, [])  # fmt: skip
    source = plain / "x.md"
    monkeypatch.setattr(query, "tracked_source_paths", lambda _: {"x.md"})
    monkeypatch.setattr(query, "allowed_sources", lambda _: [source])
    monkeypatch.setattr(query, "git_head", lambda _: "new")
    candidate = {"path": "x.md", "start_line": 1, "end_line": 1, "digest": "d", "file_digest": "f", "head": "old", "score": 1}  # fmt: skip
    assert query.verify_candidate(plain, candidate)["verification"]["reason"] == "head_mismatch"
    candidate["head"] = "new"
    assert query.verify_candidate(plain, candidate)["verification"]["reason"] == "missing_path"
    monkeypatch.setattr(projection, "_selectlease_rows", lambda _: [("id", "lane", "owner", "x", "{")])  # fmt: skip
    assert not projection.lease_inventory_rows_from_connection(object())[0]["payload_valid"]
    with pytest.raises(ValueError, match="holder_not_quiesced"):
        lease.accept_lease_handoff(plain / "db", subject="lane", target_holder_ref="agent:claude:session:second", offer_id="o", expected_lease_id="l", expected_epoch=1, expected_head="h", holder_quiesced=False)  # fmt: skip
    connection = sqlite3.connect(":memory:")
    connection.execute("create table leases(id,subject,owner,expires_at,payload_json)")
    with pytest.raises(ValueError, match="missing_lease"):
        lease._sole_subject_row(connection, "lane")  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch  # fmt: skip
    connection.execute("insert into leases values(?,?,?,?,?)", ("id", "lane", "h", "2000-01-01T00:00:00+00:00", '{"holder_ref":"h","epoch":1,"expected_head":"head"}'))  # fmt: skip
    with pytest.raises(ValueError, match="lease_expired"):
        lease.expected_current_lease(connection, subject="lane", holder_ref="h", expected_lease_id="id", expected_epoch=1, expected_head="head", require_expired=False)  # fmt: skip
    assert lease._is_expired("bad")  # noqa: RUF100, SLF001 - invalid expiry branch coverage
    assert lease._is_expired(  # noqa: RUF100, SLF001 - naive expiry branch coverage
        "2000-01-01T00:00:00"
    )
    with pytest.raises(ValueError, match="database_missing"):
        effects.delete_exact_leases(plain / "absent", [{"id": "x"}])
    database = plain / "empty.sqlite"
    database.touch()
    monkeypatch.setattr(effects, "delete_exact_leases_from_connection", lambda *_: ["x"])
    assert effects.delete_exact_leases(database, [{}]) == ["x"]
    connection.close()
