# ruff: noqa: I001 - compact source-budget projection preserves the exact test AST.
# fmt: off

from __future__ import annotations
import json
import sqlite3
import tarfile
from contextlib import closing
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any
import pytest
import ethos.adapters.store.state.maintenance as maintenance
from ethos.surface.cli.root import inspection as inspection_cli
from tests.support.contract_helpers import init_git_repo
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.local_state_maintenance import current_lease_payload
from tests.support.local_state_maintenance import insert_lease
OBSERVED_AT = datetime(2026, 7, 19, 0, 0, tzinfo=UTC)

def _repo(tmp_path: Path) -> Path:
    return init_git_repo(tmp_path / 'repo')

def _applied_recovery_fixture(tmp_path: Path) -> tuple[Path, Path, dict[str, Any], Path, Path]:
    repo = _repo(tmp_path)
    archive_root = tmp_path / 'archive'
    snapshots = repo / '.ethos' / 'state' / 'residue-snapshots'
    snapshots.mkdir(parents=True)
    (snapshots / 'dirty.patch').write_text('patch\n', encoding='utf-8')
    inventory = maintenance.local_state_maintenance_inventory(repo, archive_root, OBSERVED_AT)
    applied = maintenance.apply_local_state_maintenance(repo, archive_root, OBSERVED_AT, expect_inventory_digest=inventory['inventory_digest'], confirm_irreversible=True)
    manifest_path = Path(applied['archive']['manifest_path'])
    receipt_path = next(archive_root.glob('*.receipt.json'))
    return (repo, archive_root, applied, manifest_path, receipt_path)

def test_inventory_lease_deletion_fails_closed_on_missing_database_and_drift(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    inventory_reader = maintenance.local_state_maintenance_inventory
    missing_repo = _repo(tmp_path / 'missing')
    missing_archive = tmp_path / 'missing-archive'
    insert_lease(missing_repo, lease_id='lease:missing', subject='work/missing', expires_at='2026-07-18T00:00:00+00:00', payload=current_lease_payload(path=(tmp_path / 'gone').as_posix()))
    missing_inventory = inventory_reader(missing_repo, missing_archive, OBSERVED_AT)
    missing_db = missing_repo / '.ethos' / 'state' / 'state.sqlite'

    def inventory_after_database_removal(*_args: object, **_kwargs: object) -> dict[str, object]:
        missing_db.unlink()
        return missing_inventory
    monkeypatch.setattr(maintenance, 'local_state_maintenance_inventory', inventory_after_database_removal)
    with pytest.raises(ValueError, match='lease_maintenance_database_missing'):
        maintenance.apply_local_state_maintenance(missing_repo, missing_archive, OBSERVED_AT, expect_inventory_digest=missing_inventory['inventory_digest'], confirm_irreversible=True)
    repo = _repo(tmp_path / 'drift')
    archive_root = tmp_path / 'drift-archive'
    for suffix in ('a', 'b'):
        insert_lease(repo, lease_id=f'lease:{suffix}', subject=f'work/{suffix}', expires_at='2026-07-18T00:00:00+00:00', payload=current_lease_payload(path=(tmp_path / 'gone').as_posix()))
    inventory = inventory_reader(repo, archive_root, OBSERVED_AT)
    db_path = repo / '.ethos' / 'state' / 'state.sqlite'

    def inventory_after_owner_drift(*_args: object, **_kwargs: object) -> dict[str, object]:
        with closing(sqlite3.connect(db_path)) as connection:
            connection.execute("update leases set owner = 'agent:test:case:forged' where id = 'lease:b'")
            connection.commit()
        return inventory
    monkeypatch.setattr(maintenance, 'local_state_maintenance_inventory', inventory_after_owner_drift)
    with pytest.raises(ValueError, match='lease_maintenance_candidate_drift:lease:b'):
        maintenance.apply_local_state_maintenance(repo, archive_root, OBSERVED_AT, expect_inventory_digest=inventory['inventory_digest'], confirm_irreversible=True)
    with closing(sqlite3.connect(db_path)) as connection:
        assert connection.execute('select id from leases order by id').fetchall() == [('lease:a',), ('lease:b',)]

def test_doctor_cli_keeps_maintenance_flags_flat(tmp_path: Path) -> None:
    help_result = run_ethos_raw('doctor', '--help')
    assert help_result.returncode == 0
    assert 'Usage: ethos doctor [OPTIONS]\n' in help_result.stdout
    assert '[ARGS]' not in help_result.stdout
    for flag in ('--maintenance', '--apply-maintenance', '--archive-root', '--observed-at', '--expect-inventory-digest', '--confirm-irreversible'):
        assert flag in help_result.stdout
    repo = _repo(tmp_path)
    archive_root = tmp_path / 'archive'
    snapshots = repo / '.ethos' / 'state' / 'residue-snapshots'
    snapshots.mkdir(parents=True)
    source = snapshots / 'dirty.patch'
    source.write_text('patch\n', encoding='utf-8')
    payload = run_ethos('doctor', '--root', repo.as_posix(), '--maintenance', '--archive-root', archive_root.as_posix(), '--observed-at', OBSERVED_AT.isoformat(), '--json', cwd=repo)
    report = payload['data']['maintenance']
    assert report['inventory_digest']
    assert source.exists()
    assert not archive_root.exists()

def test_archive_extraction_rejects_invalid_and_mismatched_payloads(tmp_path: Path) -> None:
    invalid = tmp_path / 'invalid.tar'
    invalid.write_text('not a tar\n', encoding='utf-8')
    with pytest.raises(RuntimeError, match='maintenance_archive_extraction_failed'):
        maintenance.verify_archive_extraction(invalid, {'entries': []}, repository_root=tmp_path)
    payload = tmp_path / 'payload' / 'local-state'
    payload.mkdir(parents=True)
    (payload / 'state.txt').write_text('state\n', encoding='utf-8')
    archive = tmp_path / 'mismatched.tar'
    with tarfile.open(archive, 'w') as stream:
        stream.add(payload, arcname='local-state')
    with pytest.raises(RuntimeError, match='maintenance_archive_entry_verification_failed'):
        maintenance.verify_archive_extraction(archive, {'entries': []}, repository_root=tmp_path)

def test_replay_validation_rejects_drift_and_malformed_receipts(tmp_path: Path) -> None:
    repo, archive_root, applied, manifest_path, receipt_path = _applied_recovery_fixture(tmp_path)
    digest = applied['inventory_digest']
    receipt_text = receipt_path.read_text(encoding='utf-8')
    manifest_text = manifest_path.read_text(encoding='utf-8')
    receipt_path.write_text('{', encoding='utf-8')
    with pytest.raises(ValueError, match='maintenance_existing_receipt_invalid'):
        maintenance.apply_local_state_maintenance(repo, archive_root, OBSERVED_AT, expect_inventory_digest=digest, confirm_irreversible=True)
    receipt_path.write_text(receipt_text, encoding='utf-8')
    manifest_path.write_text('{}', encoding='utf-8')
    with pytest.raises(ValueError, match='maintenance_existing_receipt_invalid'):
        maintenance.apply_local_state_maintenance(repo, archive_root, OBSERVED_AT, expect_inventory_digest=digest, confirm_irreversible=True)
    manifest_path.write_text(manifest_text, encoding='utf-8')
    receipt = json.loads(receipt_text)
    for deleted in ([], {'proof_paths': ['../escape']}):
        receipt_path.write_text(json.dumps({**receipt, 'deleted': deleted}), encoding='utf-8')
        with pytest.raises(ValueError, match='maintenance_existing_receipt_invalid'):
            maintenance.apply_local_state_maintenance(repo, archive_root, OBSERVED_AT, expect_inventory_digest=digest, confirm_irreversible=True)
    receipt_path.write_text(receipt_text, encoding='utf-8')
    snapshots = repo / '.ethos' / 'state' / 'residue-snapshots'
    snapshots.mkdir(parents=True)
    (snapshots / 'dirty.patch').write_text('reappeared\n', encoding='utf-8')
    with pytest.raises(ValueError, match='maintenance_existing_receipt_postcondition_failed'):
        maintenance.apply_local_state_maintenance(repo, archive_root, OBSERVED_AT, expect_inventory_digest=digest, confirm_irreversible=True)

def test_doctor_default_is_read_only_and_explicit_maintenance_emits_inventory(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    archive_root = tmp_path / 'archive'
    snapshots = repo / '.ethos' / 'state' / 'residue-snapshots'
    snapshots.mkdir(parents=True)
    source = snapshots / 'dirty.patch'
    source.write_text('patch\n', encoding='utf-8')
    emitted = []
    monkeypatch.setattr(inspection_cli, 'emit', lambda result, **_kwargs: emitted.append(result))
    inspection_cli.doctor(root=repo, json_output=True)
    assert emitted[-1].data['maintenance'] == {}
    assert source.exists()
    inspection_cli.doctor(options=inspection_cli.DoctorMaintenanceOptions(maintenance=True, archive_root=archive_root, observed_at=OBSERVED_AT.isoformat()), root=repo, json_output=True)
    report = emitted[-1].data['maintenance']
    assert report['inventory_digest']
    assert report['recovery']['source_exists'] is True
    assert source.exists()
    assert not archive_root.exists()

def test_doctor_maintenance_reports_stable_boundary_gaps(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    emitted = []
    monkeypatch.setattr(inspection_cli, 'emit', lambda result, **_kwargs: emitted.append(result))
    inspection_cli.doctor(options=inspection_cli.DoctorMaintenanceOptions(maintenance=True), root=repo, json_output=True)
    assert emitted[-1].required_gaps == ('maintenance_archive_root_required', 'maintenance_observed_at_required')
    for error, gap in ((RuntimeError('maintenance_archive_extraction_failed'), 'maintenance_archive_extraction_failed'), (ValueError('invalid'), 'maintenance_operation_failed'), (OSError(), 'maintenance_operation_failed')):

        def fail_inventory(*_args: object, _error: Exception=error) -> dict[str, object]:
            raise _error
        monkeypatch.setattr(inspection_cli, 'local_state_maintenance_inventory', fail_inventory)
        inspection_cli.doctor(options=inspection_cli.DoctorMaintenanceOptions(maintenance=True, archive_root=tmp_path / 'archive', observed_at=OBSERVED_AT.isoformat()), root=repo, json_output=True)
        assert emitted[-1].required_gaps == (gap,)
    archive_root = tmp_path / 'archive'

    def apply(*args: object, **kwargs: object) -> dict[str, object]:
        assert args == (repo, archive_root, OBSERVED_AT.isoformat())
        assert kwargs == {'expect_inventory_digest': 'digest', 'confirm_irreversible': True}
        return {'state': 'applied'}
    monkeypatch.setattr(inspection_cli, 'apply_local_state_maintenance', apply)
    inspection_cli.doctor(options=inspection_cli.DoctorMaintenanceOptions(apply_maintenance=True, archive_root=archive_root, observed_at=OBSERVED_AT.isoformat(), expect_inventory_digest='digest', confirm_irreversible=True), root=repo, json_output=True)
    assert emitted[-1].summary['maintenance_state'] == 'applied'
