# ruff: noqa: I001, UP034 - compact source-budget projection preserves the exact test AST.
# fmt: off

from __future__ import annotations
import json
import os
import sqlite3
import subprocess
import sys
import tarfile
import textwrap
from contextlib import closing
from pathlib import Path
import pytest
import ethos.adapters.store.state.maintenance as maintenance
from ethos.adapters.store.state.maintenance import apply_local_state_maintenance
from ethos.adapters.store.state.maintenance import local_state_maintenance_inventory
from tests.support.contract_helpers import git
from tests.support.local_state_maintenance import OBSERVED_AT
from tests.support.local_state_maintenance import current_lease_payload
from tests.support.local_state_maintenance import insert_lease
from tests.support.local_state_maintenance import maintenance_repo
from tests.support.local_state_maintenance import unreachable_commit
from tests.support.local_state_maintenance import write_proof

def test_inventory_rejects_invalid_boundaries_and_git_failures(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = maintenance_repo(tmp_path)
    with pytest.raises(ValueError, match='maintenance_archive_root_must_be_absolute'):
        local_state_maintenance_inventory(repo, Path('relative'), OBSERVED_AT)
    with pytest.raises(ValueError, match='maintenance_archive_root_must_be_external'):
        local_state_maintenance_inventory(repo, repo / 'archive', OBSERVED_AT)
    for observed_at, message in (('not-a-time', 'maintenance_observed_at_invalid'), ('2026-07-19T00:00:00', 'maintenance_observed_at_timezone_required')):
        with pytest.raises(ValueError, match=message):
            local_state_maintenance_inventory(repo, tmp_path / 'archive', observed_at)
    monkeypatch.setattr(maintenance.subprocess, 'run', lambda *_args, **_kwargs: subprocess.CompletedProcess([], 1, '', ''))
    with pytest.raises(RuntimeError, match='maintenance_git_observation_failed:rev-parse'):
        local_state_maintenance_inventory(repo, tmp_path / 'archive', OBSERVED_AT)

def test_tree_inventory_rejects_links_and_special_entries(tmp_path: Path) -> None:
    repo = maintenance_repo(tmp_path)
    archive_root = tmp_path / 'archive'
    snapshots = repo / '.ethos' / 'state' / 'residue-snapshots'
    snapshots.mkdir(parents=True)
    link = snapshots / 'link'
    link.symlink_to(tmp_path / 'target')
    with pytest.raises(ValueError, match='maintenance_archive_symlink_unsupported:link'):
        local_state_maintenance_inventory(repo, archive_root, OBSERVED_AT)
    link.unlink()
    os.mkfifo(snapshots / 'pipe')
    with pytest.raises(ValueError, match='maintenance_archive_entry_unsupported:pipe'):
        local_state_maintenance_inventory(repo, archive_root, OBSERVED_AT)

def test_inventory_reports_an_unreadable_state_database(tmp_path: Path) -> None:
    repo = maintenance_repo(tmp_path)
    db_path = repo / '.ethos' / 'state' / 'state.sqlite'
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.write_bytes(b'not sqlite')
    inventory = local_state_maintenance_inventory(repo, tmp_path / 'archive', OBSERVED_AT)
    assert inventory['database']['error'] == 'DatabaseError'
    assert inventory['leases']['error'] == 'DatabaseError'

def test_inventory_prunes_only_expired_unobservable_current_contract_leases(tmp_path: Path) -> None:
    repo = maintenance_repo(tmp_path)
    archive_root = tmp_path / 'archive'
    missing_path = tmp_path / 'missing-worktree'
    existing_path = tmp_path / 'recorded-worktree'
    existing_path.mkdir()
    git(repo, 'branch', 'work/ref-present')
    linked_path = tmp_path / 'linked-worktree'
    git(repo, 'worktree', 'add', '-b', 'work/linked', linked_path.as_posix(), 'HEAD')
    linked_other = tmp_path / 'linked-worktree-other'
    git(repo, 'worktree', 'add', '-b', 'work/linked-other', linked_other.as_posix(), 'HEAD')
    expired = '2026-07-18T00:00:00+00:00'
    active = '2026-07-20T00:00:00+00:00'
    fixtures = (('lease:orphan', 'work/orphan', expired, current_lease_payload(path=missing_path.as_posix())), ('lease:active', 'work/active', active, current_lease_payload(path=missing_path.as_posix())), ('lease:ref', 'work/ref-present', expired, current_lease_payload(path=missing_path.as_posix())), ('lease:linked', 'work/linked', expired, current_lease_payload(path=missing_path.as_posix())), ('lease:linked-other', 'work/linked-other', expired, current_lease_payload(path=missing_path.as_posix())), ('lease:path', 'work/path', expired, current_lease_payload(path=existing_path.as_posix())), ('lease:bad-expiry', 'work/bad-expiry', 'not-a-time', current_lease_payload()), ('lease:naive-expiry', 'work/naive-expiry', '2026-07-18T00:00:00', current_lease_payload()), ('lease:bad-payload', 'work/bad-payload', expired, '[not-an-object]'), ('lease:legacy', 'work/legacy', expired, {}), ('lease:bad-path', 'work/bad-path', expired, {**current_lease_payload(), 'path': []}), ('lease:mismatched', 'work/mismatched', expired, {**current_lease_payload(), 'lease_id': 'lease:different'}), ('lease:bad-holder', 'work/bad-holder', expired, {**current_lease_payload(), 'holder_ref': 'not-canonical'}), ('lease:bad-subject', 'work/bad..subject', expired, current_lease_payload()), ('lease:empty-subject', '', expired, current_lease_payload()))
    for lease_id, subject, expires_at, payload in fixtures:
        insert_lease(repo, lease_id=lease_id, subject=subject, expires_at=expires_at, payload=payload)
    inventory = local_state_maintenance_inventory(repo, archive_root, OBSERVED_AT)
    assert [item['id'] for item in inventory['leases']['delete_candidates']] == ['lease:orphan']
    retained = {item['id']: item['reasons'] for item in inventory['leases']['retained']}
    assert 'unexpired' in retained['lease:active']
    assert 'branch_ref_present' in retained['lease:ref']
    assert 'linked_worktree_present' in retained['lease:linked']
    assert 'linked_worktree_present' in retained['lease:linked-other']
    assert 'recorded_path_present' in retained['lease:path']
    assert 'malformed_expiry' in retained['lease:bad-expiry']
    assert 'malformed_expiry' in retained['lease:naive-expiry']
    assert 'malformed_payload' in retained['lease:bad-payload']
    assert 'malformed_recorded_path' in retained['lease:bad-path']
    assert 'ambiguous_lease' in retained['lease:legacy']
    assert 'ambiguous_lease' in retained['lease:mismatched']
    assert 'ambiguous_lease' in retained['lease:bad-holder']
    assert 'malformed_subject' in retained['lease:bad-subject']
    assert 'malformed_subject' in retained['lease:empty-subject']

def test_inventory_protects_current_ref_worktree_and_live_lease_proofs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = maintenance_repo(tmp_path)
    archive_root = tmp_path / 'archive'
    current = git(repo, 'rev-parse', 'HEAD')
    (repo / 'next.txt').write_text('next\n', encoding='utf-8')
    git(repo, 'add', 'next.txt')
    git(repo, '-c', 'user.name=Test User', '-c', 'user.email=test@example.com', 'commit', '-m', 'next')
    ref_reachable = current
    current = git(repo, 'rev-parse', 'HEAD')
    worktree_head = 'c' * 40
    live_lease_head = 'd' * 40
    unreachable = 'e' * 40
    for head in (current, ref_reachable, worktree_head, live_lease_head, unreachable):
        write_proof(repo, head)
    insert_lease(repo, lease_id='lease:live', subject='work/live', expires_at='2026-07-20T00:00:00+00:00', payload=current_lease_payload(expected_head=live_lease_head))
    monkeypatch_heads = {current, worktree_head}
    monkeypatch.setattr(maintenance, '_git_worktree_heads', lambda _root: monkeypatch_heads)
    inventory = local_state_maintenance_inventory(repo, archive_root, OBSERVED_AT)
    assert [item['head'] for item in inventory['proofs']['delete_candidates']] == [unreachable]
    assert {item['head'] for item in inventory['proofs']['retained']} == {current, ref_reachable, worktree_head, live_lease_head}

def test_inventory_is_read_only_and_digest_changes_when_source_changes(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = maintenance_repo(tmp_path)
    archive_root = tmp_path / 'archive'
    snapshots = repo / '.ethos' / 'state' / 'residue-snapshots'
    snapshots.mkdir(parents=True)
    source = snapshots / 'dirty.patch'
    source.write_text('first\n', encoding='utf-8')
    first = local_state_maintenance_inventory(repo, archive_root, OBSERVED_AT)
    assert source.read_text(encoding='utf-8') == 'first\n'
    assert not archive_root.exists()
    source.write_text('second\n', encoding='utf-8')
    second = local_state_maintenance_inventory(repo, archive_root, OBSERVED_AT)
    assert first['inventory_digest'] != second['inventory_digest']
    monkeypatch.setattr(maintenance, 'local_state_maintenance_inventory', lambda *_args: first)
    with pytest.raises(ValueError, match='maintenance_recovery_snapshot_drift'):
        apply_local_state_maintenance(repo, archive_root, OBSERVED_AT, expect_inventory_digest=first['inventory_digest'], confirm_irreversible=True)

def test_inventory_reads_wal_through_read_only_uris_without_new_sidecars(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = maintenance_repo(tmp_path)
    archive_root = tmp_path / 'archive'
    insert_lease(repo, lease_id='lease:orphan', subject='work/orphan', expires_at='2026-07-18T00:00:00+00:00', payload=current_lease_payload(path=(tmp_path / 'gone').as_posix()))
    db_path = repo / '.ethos' / 'state' / 'state.sqlite'
    writer = sqlite3.connect(db_path)
    writer.execute('pragma journal_mode = wal')
    writer.execute('insert into leases(id, subject, owner, expires_at, payload_json) values (?, ?, ?, ?, ?)', ('lease:wal', 'work/wal', 'agent:test:case:owner', '2026-07-20T00:00:00+00:00', json.dumps(current_lease_payload(expected_head='a' * 40))))
    writer.commit()
    sidecars_before = {suffix: Path(f'{db_path}{suffix}').exists() for suffix in ('-wal', '-shm')}
    real_connect = sqlite3.connect
    connections: list[tuple[str, bool]] = []

    def recording_connect(database: object, *args: object, **kwargs: object) -> sqlite3.Connection:
        connections.append((str(database), kwargs.get('uri') is True))
        return real_connect(database, *args, **kwargs)
    monkeypatch.setattr(sqlite3, 'connect', recording_connect)
    try:
        inventory = local_state_maintenance_inventory(repo, archive_root, OBSERVED_AT)
        sidecars_after = {suffix: Path(f'{db_path}{suffix}').exists() for suffix in ('-wal', '-shm')}
    finally:
        writer.close()
    assert inventory['database']['exists'] is True
    assert any((item['id'] == 'lease:wal' for item in inventory['leases']['retained']))
    assert connections
    assert all((is_uri and 'mode=ro' in target and ('immutable=1' not in target) for target, is_uri in connections))
    assert sidecars_after == sidecars_before

def test_apply_requires_confirmation_and_exact_inventory_digest(tmp_path: Path) -> None:
    repo = maintenance_repo(tmp_path)
    archive_root = tmp_path / 'archive'
    inventory = local_state_maintenance_inventory(repo, archive_root, OBSERVED_AT)
    with pytest.raises(ValueError, match='maintenance_irreversible_confirmation_required'):
        apply_local_state_maintenance(repo, archive_root, OBSERVED_AT, expect_inventory_digest=inventory['inventory_digest'], confirm_irreversible=False)
    with pytest.raises(ValueError, match='maintenance_inventory_digest_mismatch'):
        apply_local_state_maintenance(repo, archive_root, OBSERVED_AT, expect_inventory_digest='0' * 64, confirm_irreversible=True)

def test_apply_archives_verifies_and_prunes_exact_inventory_idempotently(tmp_path: Path) -> None:
    repo = maintenance_repo(tmp_path)
    archive_root = tmp_path / 'archive'
    snapshots = repo / '.ethos' / 'state' / 'residue-snapshots'
    (snapshots / 'nested').mkdir(parents=True)
    (snapshots / 'dirty.patch').write_text('patch\n', encoding='utf-8')
    (snapshots / 'nested' / 'untracked.txt').write_text('recover\n', encoding='utf-8')
    insert_lease(repo, lease_id='lease:orphan', subject='work/orphan', expires_at='2026-07-18T00:00:00+00:00', payload=current_lease_payload(path=(tmp_path / 'gone').as_posix()))
    insert_lease(repo, lease_id='lease:active', subject='work/active', expires_at='2026-07-20T00:00:00+00:00', payload=current_lease_payload())
    unreachable = 'e' * 40
    proof = write_proof(repo, unreachable)
    inventory = local_state_maintenance_inventory(repo, archive_root, OBSERVED_AT)
    retained = {item['id']: item['reasons'] for item in inventory['leases']['retained']}
    assert 'unexpired' in retained['lease:active']
    applied = apply_local_state_maintenance(repo, archive_root, OBSERVED_AT, expect_inventory_digest=inventory['inventory_digest'], confirm_irreversible=True)
    assert applied['ok'] is True
    assert applied['state'] == 'applied'
    assert applied['deleted']['lease_ids'] == ['lease:orphan']
    assert applied['deleted']['proof_paths'] == [proof.relative_to(repo).as_posix()]
    assert applied['deleted']['recovery_snapshot'] is True
    assert not snapshots.exists()
    archive_path = Path(applied['archive']['path'])
    assert archive_path.is_file()
    assert applied['archive']['sha256']
    assert applied['archive']['entry_manifest_digest']
    manifest = json.loads(Path(applied['archive']['manifest_path']).read_text(encoding='utf-8'))
    assert manifest['archive'] == {'path': archive_path.as_posix(), 'sha256': applied['archive']['sha256'], 'size': applied['archive']['size']}
    assert manifest['bundle_verifications'] == []
    with tarfile.open(archive_path, 'r') as archive:
        names = set(archive.getnames())
    assert 'local-state/.ethos/state/residue-snapshots/dirty.patch' in names
    assert 'local-state/.ethos/state/residue-snapshots/nested/untracked.txt' in names
    replay = apply_local_state_maintenance(repo, archive_root, OBSERVED_AT, expect_inventory_digest=inventory['inventory_digest'], confirm_irreversible=True)
    assert replay['state'] == 'already_applied'
    assert replay['archive']['sha256'] == applied['archive']['sha256']

def test_receipt_replay_reobserves_deleted_postconditions(tmp_path: Path) -> None:
    repo = maintenance_repo(tmp_path)
    archive_root = tmp_path / 'archive'
    proof = write_proof(repo, 'e' * 40)
    inventory = local_state_maintenance_inventory(repo, archive_root, OBSERVED_AT)
    apply_local_state_maintenance(repo, archive_root, OBSERVED_AT, expect_inventory_digest=inventory['inventory_digest'], confirm_irreversible=True)
    proof.write_text(json.dumps({'schema_version': 3, 'head': 'e' * 40, 'state': 'proven'}), encoding='utf-8')
    with pytest.raises(ValueError, match='maintenance_existing_receipt_postcondition_failed'):
        apply_local_state_maintenance(repo, archive_root, OBSERVED_AT, expect_inventory_digest=inventory['inventory_digest'], confirm_irreversible=True)

def test_same_digest_concurrent_applies_serialize_and_replay(tmp_path: Path) -> None:
    repo = maintenance_repo(tmp_path)
    archive_root = tmp_path / 'archive'
    snapshots = repo / '.ethos' / 'state' / 'residue-snapshots'
    snapshots.mkdir(parents=True)
    (snapshots / 'dirty.patch').write_text('patch\n', encoding='utf-8')
    insert_lease(repo, lease_id='lease:orphan', subject='work/orphan', expires_at='2026-07-18T00:00:00+00:00', payload=current_lease_payload(path=(tmp_path / 'gone').as_posix()))
    proof = write_proof(repo, 'e' * 40)
    inventory = local_state_maintenance_inventory(repo, archive_root, OBSERVED_AT)
    project_root = Path(__file__).resolve().parents[3]
    gate = tmp_path / 'apply-gate'
    gate.mkdir()
    worker = tmp_path / 'apply-worker.py'
    worker.write_text(textwrap.dedent('\n            import json\n            import sys\n            import time\n            from datetime import datetime\n            from pathlib import Path\n\n            project_root = Path(sys.argv[1])\n            sys.path[:0] = [\n                project_root.as_posix(),\n                (project_root / "packages" / "ethos" / "src").as_posix(),\n                (project_root / "packages" / "ethos-core" / "src").as_posix(),\n            ]\n\n            import ethos.adapters.store.state.maintenance as maintenance\n\n            repo = Path(sys.argv[2])\n            archive_root = Path(sys.argv[3])\n            observed_at = datetime.fromisoformat(sys.argv[4])\n            inventory_digest = sys.argv[5]\n            gate = Path(sys.argv[6])\n            marker = gate / sys.argv[7]\n            result_path = Path(sys.argv[8])\n            original_stage = maintenance._stage_local_state\n\n            def synchronized_stage(root: Path, staging: Path) -> None:\n                original_stage(root, staging)\n                marker.write_text("ready\\n", encoding="utf-8")\n                deadline = time.monotonic() + 2\n                while len(list(gate.glob("ready-*"))) < 2 and time.monotonic() < deadline:\n                    time.sleep(0.01)\n\n            maintenance._stage_local_state = synchronized_stage\n            try:\n                result = maintenance.apply_local_state_maintenance(\n                    repo,\n                    archive_root,\n                    observed_at,\n                    expect_inventory_digest=inventory_digest,\n                    confirm_irreversible=True,\n                )\n            except Exception as exc:\n                outcome = ["error", f"{exc.__class__.__name__}:{exc}"]\n            else:\n                outcome = ["ok", result["state"]]\n            result_path.write_text(json.dumps(outcome), encoding="utf-8")\n            '), encoding='utf-8')
    result_paths = [tmp_path / f'result-{index}.json' for index in range(2)]
    processes = [subprocess.Popen([sys.executable, worker.as_posix(), project_root.as_posix(), repo.as_posix(), archive_root.as_posix(), OBSERVED_AT.isoformat(), inventory['inventory_digest'], gate.as_posix(), f'ready-{index}', result_paths[index].as_posix()], cwd=project_root, env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for index in range(2)]
    completed = [process.communicate(timeout=30) for process in processes]
    assert all((process.returncode == 0 for process in processes)), completed
    outcomes = [json.loads(path.read_text(encoding='utf-8')) for path in result_paths]
    assert sorted(outcomes) == [['ok', 'already_applied'], ['ok', 'applied']]
    assert not snapshots.exists()
    assert not proof.exists()

def test_maintenance_lock_is_scoped_to_repository_not_archive_root(tmp_path: Path) -> None:
    repo = maintenance_repo(tmp_path)
    archive_root = tmp_path / 'archive'
    with pytest.raises(ValueError, match='maintenance_inventory_digest_mismatch'):
        apply_local_state_maintenance(repo, archive_root, OBSERVED_AT, expect_inventory_digest='not-the-current-inventory', confirm_irreversible=True)
    assert (repo / '.ethos' / 'state' / 'local-state-maintenance.lock').is_file()
    assert not (archive_root / '.ethos-local-state-maintenance.lock').exists()

@pytest.mark.parametrize('late_protection', ['ref', 'worktree', 'live_lease'])
def test_apply_reobserves_proof_protection_immediately_before_deletion(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, late_protection: str) -> None:
    repo = maintenance_repo(tmp_path)
    archive_root = tmp_path / 'archive'
    candidate_head = unreachable_commit(repo)
    proof = write_proof(repo, candidate_head)
    inventory = local_state_maintenance_inventory(repo, archive_root, OBSERVED_AT)
    assert [item['head'] for item in inventory['proofs']['delete_candidates']] == [candidate_head]

    def verify_then_protect(_archive: Path, manifest: dict[str, list[object]], **_kwargs: object) -> dict[str, object]:
        if late_protection == 'ref':
            git(repo, 'branch', 'work/late-protected', candidate_head)
        elif late_protection == 'worktree':
            git(repo, 'worktree', 'add', '--detach', (tmp_path / 'late-worktree').as_posix(), candidate_head)
        else:
            insert_lease(repo, lease_id='lease:late-protected', subject='work/late-protected', expires_at='2026-07-20T00:00:00+00:00', payload=current_lease_payload(expected_head=candidate_head))
        return {'entry_count': len(manifest['entries']), 'bundle_verifications': []}
    monkeypatch.setattr(maintenance, 'verify_archive_extraction', verify_then_protect)
    with pytest.raises(ValueError, match='maintenance_proof_candidate_became_protected'):
        apply_local_state_maintenance(repo, archive_root, OBSERVED_AT, expect_inventory_digest=inventory['inventory_digest'], confirm_irreversible=True)
    assert proof.exists()

def test_apply_keeps_sources_when_bundle_verification_fails(tmp_path: Path) -> None:
    repo = maintenance_repo(tmp_path)
    archive_root = tmp_path / 'archive'
    snapshots = repo / '.ethos' / 'state' / 'residue-snapshots'
    snapshots.mkdir(parents=True)
    bundle = snapshots / 'recovery.bundle'
    bundle.write_text('not a git bundle\n', encoding='utf-8')
    inventory = local_state_maintenance_inventory(repo, archive_root, OBSERVED_AT)
    with pytest.raises(RuntimeError, match='maintenance_bundle_verify_failed'):
        apply_local_state_maintenance(repo, archive_root, OBSERVED_AT, expect_inventory_digest=inventory['inventory_digest'], confirm_irreversible=True)
    assert bundle.exists()

def test_apply_verifies_extracted_valid_git_bundle_against_repository(tmp_path: Path) -> None:
    repo = maintenance_repo(tmp_path)
    archive_root = tmp_path / 'archive'
    snapshots = repo / '.ethos' / 'state' / 'residue-snapshots'
    snapshots.mkdir(parents=True)
    bundle = snapshots / 'recovery.bundle'
    git(repo, 'bundle', 'create', bundle.as_posix(), '--all')
    inventory = local_state_maintenance_inventory(repo, archive_root, OBSERVED_AT)
    applied = apply_local_state_maintenance(repo, archive_root, OBSERVED_AT, expect_inventory_digest=inventory['inventory_digest'], confirm_irreversible=True)
    assert applied['archive']['bundle_verifications'] == [{'path': 'recovery.bundle', 'verified': True}]
    assert applied['archive']['extraction']['bundle_verifications'] == [{'path': 'recovery.bundle', 'verified': True}]

def test_apply_keeps_sources_when_archive_extraction_verification_fails(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = maintenance_repo(tmp_path)
    archive_root = tmp_path / 'archive'
    snapshots = repo / '.ethos' / 'state' / 'residue-snapshots'
    snapshots.mkdir(parents=True)
    source = snapshots / 'dirty.patch'
    source.write_text('patch\n', encoding='utf-8')
    inventory = local_state_maintenance_inventory(repo, archive_root, OBSERVED_AT)

    def fail_extraction(*_args: object, **_kwargs: object) -> dict[str, object]:
        message = 'maintenance_archive_extraction_failed'
        raise RuntimeError(message)
    monkeypatch.setattr(maintenance, 'verify_archive_extraction', fail_extraction)
    with pytest.raises(RuntimeError, match='maintenance_archive_extraction_failed'):
        apply_local_state_maintenance(repo, archive_root, OBSERVED_AT, expect_inventory_digest=inventory['inventory_digest'], confirm_irreversible=True)
    assert source.exists()

def test_apply_restores_sources_when_receipt_write_fails(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = maintenance_repo(tmp_path)
    archive_root = tmp_path / 'archive'
    snapshots = repo / '.ethos' / 'state' / 'residue-snapshots'
    snapshots.mkdir(parents=True)
    source = snapshots / 'dirty.patch'
    source.write_text('patch\n', encoding='utf-8')
    insert_lease(repo, lease_id='lease:orphan', subject='work/orphan', expires_at='2026-07-18T00:00:00+00:00', payload=current_lease_payload(path=(tmp_path / 'gone').as_posix()))
    proof = write_proof(repo, 'e' * 40)
    inventory = local_state_maintenance_inventory(repo, archive_root, OBSERVED_AT)
    path_type = type(repo)
    original_replace = path_type.replace

    def fail_receipt(source: Path, target: Path) -> Path:
        if target.name.endswith('.receipt.json'):
            msg = 'receipt write failed'
            raise OSError(msg)
        return original_replace(source, target)
    monkeypatch.setattr(path_type, 'replace', fail_receipt)
    with pytest.raises(OSError, match='receipt write failed'):
        apply_local_state_maintenance(repo, archive_root, OBSERVED_AT, expect_inventory_digest=inventory['inventory_digest'], confirm_irreversible=True)
    assert source.exists()
    assert proof.exists()
    restored = local_state_maintenance_inventory(repo, archive_root, OBSERVED_AT)
    assert [item['id'] for item in restored['leases']['delete_candidates']] == ['lease:orphan']

def test_failed_apply_preserves_database_writes_committed_after_staging(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = maintenance_repo(tmp_path)
    archive_root = tmp_path / 'archive'
    insert_lease(repo, lease_id='lease:orphan', subject='work/orphan', expires_at='2026-07-18T00:00:00+00:00', payload=current_lease_payload(path=(tmp_path / 'gone').as_posix()))
    db_path = repo / '.ethos' / 'state' / 'state.sqlite'
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute('create table concurrent_state (value text not null)')
        connection.commit()
    inventory = local_state_maintenance_inventory(repo, archive_root, OBSERVED_AT)
    path_type = type(repo)
    original_replace = path_type.replace

    def verify_then_write(_archive: Path, manifest: dict[str, list[object]], **_kwargs: object) -> dict[str, object]:
        with closing(sqlite3.connect(db_path)) as connection:
            connection.execute("insert into concurrent_state(value) values ('committed')")
            connection.commit()
        return {'entry_count': len(manifest['entries']), 'bundle_verifications': []}

    def fail_receipt(source: Path, target: Path) -> Path:
        if target.name.endswith('.receipt.json'):
            msg = 'receipt write failed'
            raise OSError(msg)
        return original_replace(source, target)
    monkeypatch.setattr(maintenance, 'verify_archive_extraction', verify_then_write)
    monkeypatch.setattr(path_type, 'replace', fail_receipt)
    with pytest.raises(OSError, match='receipt write failed'):
        apply_local_state_maintenance(repo, archive_root, OBSERVED_AT, expect_inventory_digest=inventory['inventory_digest'], confirm_irreversible=True)
    with closing(sqlite3.connect(db_path)) as connection:
        concurrent = connection.execute('select value from concurrent_state').fetchall()
        leases = connection.execute('select id from leases order by id').fetchall()
    assert concurrent == [('committed',)]
    assert leases == [('lease:orphan',)]

def test_failed_apply_restores_only_missing_recovery_paths(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = maintenance_repo(tmp_path)
    archive_root = tmp_path / 'archive'
    snapshots = repo / '.ethos' / 'state' / 'residue-snapshots'
    (snapshots / 'nested').mkdir(parents=True)
    retained = snapshots / 'retained.patch'
    missing = snapshots / 'nested' / 'missing.patch'
    replaced = snapshots / 'replaced.patch'
    retained.write_text('retained\n', encoding='utf-8')
    missing.write_text('missing\n', encoding='utf-8')
    replaced.write_text('staged\n', encoding='utf-8')
    inventory = local_state_maintenance_inventory(repo, archive_root, OBSERVED_AT)

    def partially_delete(_root: Path, _recovery: dict[str, object]) -> bool:
        missing.unlink()
        missing.parent.rmdir()
        replaced.unlink()
        replaced.write_text('concurrent\n', encoding='utf-8')
        msg = 'partial recovery deletion failed'
        raise OSError(msg)
    monkeypatch.setattr(maintenance, '_delete_recovery_snapshot', partially_delete)
    with pytest.raises(OSError, match='partial recovery deletion failed'):
        apply_local_state_maintenance(repo, archive_root, OBSERVED_AT, expect_inventory_digest=inventory['inventory_digest'], confirm_irreversible=True)
    assert retained.read_text(encoding='utf-8') == 'retained\n'
    assert missing.read_text(encoding='utf-8') == 'missing\n'
    assert replaced.read_text(encoding='utf-8') == 'concurrent\n'
