from __future__ import annotations

import sqlite3
from contextlib import closing
from shutil import copytree
from shutil import rmtree
from typing import TYPE_CHECKING
from typing import Any

import pytest

import ethos.adapters.mutation.local_state as ls
import ethos.adapters.store.state.schema as ss
import ethos.surface.cli.root.proof as proof
import tests.support.ethos_cli_runner as cli
import tests.support.governed_repository as gr
from ethos.adapters.admission.transitions import work_lane_ref_transition_report
from ethos.adapters.repo.status.bindings import leases_by_branch

if TYPE_CHECKING:
    from pathlib import Path

# Original named claim -> row, in the order reported before mutation.
CORE = ["move", "drift", "compensate", "absent"]
COMPAT = ["plan", "read", "guard", "ref", "prove", "land"]
MERGE = ["merge", "table", "lease-conflict", "file-conflict"]


def _db(path: Path, *leases: tuple[str, str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as con:
        con.execute("begin immediate")
        ss.initialize_state_connection(con)
        sql = "insert into leases(id,subject,owner,expires_at,payload_json) values(?,?,?,?,?)"
        con.executemany(sql, [(*row, "2030-01-01T00:00:00Z", "{}") for row in leases])
        con.commit()


def _file(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _expect(
    result: dict[str, Any], verdict: str, state: str = "", gaps: list[str] | None = None
) -> None:
    assert result["verdict"] == verdict
    if state:
        assert result["state"] == state
    if gaps is not None:
        assert result["required_gaps"] == gaps


def _apply(repo: Path, digest: object = "") -> dict[str, Any]:
    plan = ls.local_state_migration(repo, apply=False)
    digest = digest or plan["plan_digest"]
    return ls.local_state_migration(repo, apply=True, expect_plan_digest=str(digest))


def _run(repo: Path, *args: str, fail: bool = False) -> dict[str, Any]:
    return (cli.run_ethos_blocked if fail else cli.run_ethos)(*args, "--json", cwd=repo)


def _legacy_lane(tmp: Path, *, empty: bool) -> tuple[Path, Path, Path, str]:
    repo, _candidate = gr.init_repo_with_candidate(tmp)
    lane = gr.create_change_source_lane(
        repo, tmp / "repo-work-source", branch="work/source", holder_ref="agent:test:case:source"
    )
    current, legacy = ss.state_database(repo), repo / ".ethos/state/state.sqlite"
    legacy.parent.mkdir(parents=True, exist_ok=True)
    current.replace(legacy)
    if empty:
        current.touch()
    return repo, lane, legacy, gr.git(lane, "rev-parse", "HEAD")


def _migration_block(result: dict[str, Any], lane: Path, head: str) -> None:
    assert result["required_gaps"] == ["local_state_migration_required"]
    prefix = f"ethos migrate-local-state --root {lane} --apply --authorize --expect-head {head} "
    assert str(result["next_action"]).startswith(prefix + "--expect-plan-digest ")


@pytest.mark.parametrize("case", CORE)
def test_local_state_migration_core_matrix(
    case: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, legacy = gr.init_git_repo(tmp_path / "repo"), tmp_path / "repo/.ethos/state"
    source, target = legacy / "state.sqlite", ss.state_database(repo)
    if case == "absent":
        for path in sorted(legacy.rglob("*"), reverse=True):
            path.unlink() if path.is_file() else path.rmdir()
        legacy.rmdir()
        _expect(ls.local_state_migration(repo, apply=False), "pass", "current", [])
        return
    _db(source)
    proof_file = _file(legacy / "attestations/proof.json", '{"proof": true}\n')
    if case == "move":
        artifact = _file(legacy / "attestations/artifacts/artifact.json", '{"artifact": true}\n')
        expected_proof, expected_artifact = proof_file.read_text(), artifact.read_text()
        plan = ls.local_state_migration(repo, apply=False)
        _expect(plan, "pass", "ready")
        assert (plan["source"], plan["target"]) == (legacy.as_posix(), target.parent.as_posix())
        assert (source.exists(), target.exists()) == (True, False)
        result = _apply(repo)
        _expect(result, "pass", "migrated")
        assert [item["path"] for item in result["manifest"]] == [
            "attestations/artifacts/artifact.json",
            "attestations/proof.json",
        ]
        files = [
            path.relative_to(legacy).as_posix() for path in legacy.rglob("*") if path.is_file()
        ]
        assert sorted(files) == [".gitignore"]
        assert (target.parent / "attestations/proof.json").read_text() == expected_proof
        assert (
            target.parent / "attestations/artifacts/artifact.json"
        ).read_text() == expected_artifact
        with closing(sqlite3.connect(target)) as con:
            assert con.execute("select count(*) from leases").fetchone() == (0,)
    elif case == "drift":
        foreign = _file(target.parent / "foreign", "occupied\n")
        _expect(_apply(repo), "pass", "migrated")
        assert foreign.read_text() == "occupied\n"
        _db(source)
        result = _apply(repo, "0" * 64)
        _expect(result, "block", gaps=["local_state_migration_plan_digest_mismatch"])
        assert source.exists()
    else:
        plan = ls.local_state_migration(repo, apply=False)
        monkeypatch.setattr(
            ls,
            "_verify_migration",
            lambda *_args: (_ for _ in ()).throw(ValueError("local_state_migration_source_drift")),
        )
        result = ls.local_state_migration(
            repo, apply=True, expect_plan_digest=str(plan["plan_digest"])
        )
        _expect(result, "block", gaps=["local_state_migration_source_drift"])
        assert source.exists()
        assert proof_file.read_text() == '{"proof": true}\n'
        assert not target.parent.exists()
        assert not list(target.parent.parent.glob(".ethos.migrate-*"))


@pytest.mark.parametrize("case", COMPAT)
def test_state_migration_reference_transaction_compatibility_matrix(
    case: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _repo, lane, legacy, head = _legacy_lane(tmp_path, empty=case != "plan")
    if case == "plan":
        result = ls.local_state_migration(lane, apply=False)
        _expect(result, "pass", "ready")
        assert result["source"] == legacy.parent.as_posix()
        return
    if case == "read":
        lease = leases_by_branch(lane)["work/source"]
        assert ss.observed_state_database(lane) == legacy
        assert (lease["lease_state"], lease["holder_ref"]) == ("valid", "agent:test:case:source")
        return
    if case == "guard":
        result = ls.local_state_mutation_guard(lane)
        _migration_block(result, lane, head)
        assert result["next_action"].endswith(f"{result['plan_digest']} --json")
        return
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:source")
    if case == "ref":
        tree = gr.git(lane, "rev-parse", "HEAD^{tree}")
        target = gr.git(lane, "commit-tree", tree, "-p", head, "-m", "target")
        result = work_lane_ref_transition_report(
            root=lane,
            phase="prepared",
            ref_name="refs/heads/work/source",
            old_value=head,
            new_value=target,
        )
    elif case == "prove":
        monkeypatch.setattr(
            proof,
            "run_plan_checks",
            lambda **_kwargs: (_ for _ in ()).throw(AssertionError("gate runner reached")),
        )
        result = _run(lane, "prove", "--execute", "--expect-head", head, fail=True)
    else:
        result = _run(lane, "land", "--apply", "--authorize", "--expect-head", head, fail=True)
    _migration_block(result, lane, head)
    if case in {"ref", "land"}:
        assert gr.git(lane, "rev-parse", "work/source" if case == "ref" else "HEAD") == head


@pytest.mark.parametrize("case", MERGE)
def test_local_state_migration_merge_conflict_matrix(case: str, tmp_path: Path) -> None:
    repo = gr.init_git_repo(tmp_path / "repo")
    source, target = repo / ".ethos/state/state.sqlite", ss.state_database(repo)
    _db(source, *(("source", "work/source", "agent:test"),) if case == "merge" else ())
    _db(target, *(("target", "work/target", "agent:test"),) if case == "merge" else ())
    if case == "merge":
        proof_file = _file(source.parent / "attestations/proof.json", '{"proof": true}\n')
        effect = _file(target.parent / "git-effects/effect.json", '{"effect": true}\n')
        expected_proof, expected_effect = proof_file.read_text(), effect.read_text()
    elif case == "table":
        with closing(sqlite3.connect(source)) as con:
            con.executescript(
                "create table legacy_events(id integer primary key,payload text);"
                "insert into legacy_events(payload) values('preserve me')"
            )
            con.commit()
        _db(target, ("target", "work/target", "agent:test"))
    elif case == "lease-conflict":
        _db(source, ("source", "work/conflict", "agent:test"))
        _db(target, ("target", "work/conflict", "agent:other"))
    else:
        _file(source.parent / "attestations/same.json", "source\n")
        _file(target.parent / "attestations/same.json", "target\n")
    if case.endswith("conflict"):
        gap = (
            "lease_conflict:work/conflict"
            if case[0] == "l"
            else "file_conflict:attestations/same.json"
        )
        _expect(ls.local_state_migration(repo, apply=False), "block", gaps=[f"local_state_{gap}"])
        return
    _expect(_apply(repo), "pass", "migrated")
    with closing(sqlite3.connect(target)) as con:
        if case == "merge":
            assert (expected_proof, expected_effect) == ('{"proof": true}\n', '{"effect": true}\n')
            assert con.execute("select subject from leases order by subject").fetchall() == [
                ("work/source",),
                ("work/target",),
            ]
        else:
            assert con.execute("select payload from legacy_events").fetchall() == [("preserve me",)]
            assert con.execute("select subject from leases").fetchall() == [("work/target",)]


@pytest.mark.parametrize("case", ["public", "lane-start"])
def test_public_migration_and_clean_lane_start_matrix(case: str, tmp_path: Path) -> None:
    if case == "public":
        repo = gr.init_git_repo(tmp_path / "repo")
        _db(repo / ".ethos/state/state.sqlite")
        head = gr.git(repo, "rev-parse", "HEAD")
        plan = _run(repo, "migrate-local-state", "--root", repo.as_posix())
        missing = _run(repo, "migrate-local-state", "--root", repo.as_posix(), "--apply", fail=True)
        result = _run(
            repo,
            "migrate-local-state",
            "--root",
            repo.as_posix(),
            "--apply",
            "--authorize",
            "--expect-head",
            head,
            "--expect-plan-digest",
            plan["data"]["plan_digest"],
        )
        _expect(plan, "pass", "ready")
        _expect(missing, "block", gaps=["authorization_required", "expect_head_required"])
        _expect(result, "pass", "migrated")
        assert ss.state_database(repo).exists()
        assert gr.git(repo, "rev-parse", "HEAD") == head
        return
    repo, candidate = gr.init_repo_with_candidate(tmp_path)
    _file(repo / ".gitignore", "")
    gr.git(repo, "rm", ".ethos/state/.gitignore")
    gr.git(repo, "add", ".gitignore")
    gr.git(repo, "commit", "-m", "do not ignore misplaced state")
    gr.git(candidate, "reset", "--hard", "dev")
    source = gr.create_change_source_lane(
        repo,
        tmp_path / "repo-work-source-next",
        branch="work/source-next",
        holder_ref="agent:test:case:source",
    )
    current, legacy = ss.state_database(repo).parent, repo / ".ethos/state"
    copytree(current, legacy, dirs_exist_ok=True)
    rmtree(current)
    assert gr.git(repo, "status", "--short")
    plan = _run(repo, "migrate-local-state", "--root", repo.as_posix())
    migrated = _run(
        repo,
        "migrate-local-state",
        "--root",
        repo.as_posix(),
        "--apply",
        "--authorize",
        "--expect-head",
        gr.git(repo, "rev-parse", "HEAD"),
        "--expect-plan-digest",
        plan["data"]["plan_digest"],
    )
    lane = tmp_path / "repo-work-next"
    started = _run(
        repo,
        "lane",
        "start",
        "next",
        "--root",
        repo.as_posix(),
        "--path",
        lane.as_posix(),
        "--source-root",
        source.as_posix(),
        "--holder-ref",
        "agent:test:case:next",
        "--apply",
    )
    _expect(migrated, "pass", "migrated")
    _expect(started, "pass", "started")
    assert (gr.git(repo, "status", "--short"), lane.is_dir()) == ("", True)
