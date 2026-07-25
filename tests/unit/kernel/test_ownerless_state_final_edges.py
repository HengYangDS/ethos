from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from ethos.adapters.store.state import closeout
from ethos.adapters.store.state import schema
from ethos.adapters.store.state.lease.lifecycle.core import acquire_lease


def _fence_kwargs() -> dict[str, str]:
    return {
        "subject": "work/20260722-state-final",
        "expected_head": "a" * 40,
        "decision_id": "lane-decision:00000000-0000-4000-8000-000000000302",
        "executor_ref": "agent:codex:thread:state-final",
        "accepted_branch": "dev",
        "accepted_head": "b" * 40,
        "target_path": "/tmp/20260722-state-final",
        "lane_incarnation_id": "lane-incarnation:20260722-state-final",
        "observation_digest": "c" * 64,
        "decision_sha256": "d" * 64,
        "chronicle_digest": "e" * 64,
    }


def _replace_fence_payload(
    db_path: Path,
    *,
    fence: dict[str, object],
    payload: dict[str, object],
) -> None:
    binding = {
        field: fence[field]
        for field in (
            "subject",
            "expected_head",
            "decision_id",
            "executor_ref",
            "accepted_branch",
            "accepted_head",
        )
    }
    binding["payload"] = payload
    canonical_binding = json.dumps(
        binding,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    target_binding_digest = hashlib.sha256(canonical_binding.encode()).hexdigest()
    with closing(sqlite3.connect(db_path)) as connection, connection:
        connection.execute(
            """update closeout_fences
            set target_binding_digest = ?, payload_json = ? where subject = ?""",
            (
                target_binding_digest,
                json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False),
                _fence_kwargs()["subject"],
            ),
        )


def test_closeout_fence_rejects_same_decision_with_changed_binding(tmp_path: Path) -> None:
    db_path = tmp_path / "state.sqlite"
    closeout.acquire_closeout_fence(db_path, **_fence_kwargs())
    changed = _fence_kwargs()
    changed["accepted_head"] = "1" * 40

    with pytest.raises(ValueError, match="lane_closeout_fence_binding_mismatch"):
        closeout.acquire_closeout_fence(db_path, **changed)


def test_closeout_fence_probe_rejects_a_database_without_current_schema(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "plain.sqlite"
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute("create table unrelated(value text)")

    assert closeout.probe_closeout_fence(db_path, subject="work/20260722-state-final") == (
        "unverifiable",
        None,
    )


def test_closeout_fence_probe_maps_corrupt_database_to_unverifiable(tmp_path: Path) -> None:
    db_path = tmp_path / "corrupt.sqlite"
    db_path.write_bytes(b"not-a-sqlite-database")

    assert closeout.probe_closeout_fence(db_path, subject="work/20260722-state-final") == (
        "unverifiable",
        None,
    )


def test_closeout_fence_probe_maps_malformed_schema_to_unverifiable(tmp_path: Path) -> None:
    db_path = tmp_path / "malformed.sqlite"
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute("create table closeout_fences(subject text not null)")

    assert closeout.probe_closeout_fence(db_path, subject="work/20260722-state-final") == (
        "unverifiable",
        None,
    )


def test_closeout_fence_rejects_provider_field_with_rebound_digest(tmp_path: Path) -> None:
    db_path = tmp_path / "provider-field.sqlite"
    fence = closeout.acquire_closeout_fence(db_path, **_fence_kwargs())
    payload = dict(fence["payload"])
    payload["provider_binding_digest"] = "f" * 64
    _replace_fence_payload(db_path, fence=fence, payload=payload)

    with pytest.raises(ValueError, match="lane_closeout_fence_binding_invalid"):
        closeout.acquire_closeout_fence(db_path, **_fence_kwargs())


def test_closeout_fence_probe_maps_provider_prefixed_payload_to_unverifiable(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "provider_binding_digest.sqlite"
    fence = closeout.acquire_closeout_fence(db_path, **_fence_kwargs())
    payload = dict(fence["payload"])
    payload["provider_binding_digest"] = "f" * 64
    _replace_fence_payload(db_path, fence=fence, payload=payload)

    assert closeout.probe_closeout_fence(db_path, subject=_fence_kwargs()["subject"]) == (
        "unverifiable",
        None,
    )


@pytest.mark.parametrize(
    ("case", "expected_gap"),
    [
        ("table", "state_schema_closeout_fence_table_definition_mismatch"),
        ("index", "state_schema_closeout_fence_subject_unique_missing"),
        ("trigger", "state_schema_closeout_fence_trigger_present"),
    ],
)
def test_closeout_fence_schema_rejects_noncanonical_objects(
    case: str,
    expected_gap: str,
) -> None:
    with closing(sqlite3.connect(":memory:")) as connection:
        if case == "table":
            connection.execute("create table closeout_fences(subject text not null)")
        else:
            connection.execute(schema.CLOSEOUT_FENCE_SCHEMA[0])
            if case == "trigger":
                connection.execute(schema.CLOSEOUT_FENCE_SCHEMA[1])
                connection.execute(
                    "create trigger closeout_fences_extra after insert on closeout_fences "
                    "begin select 1; end"
                )

        with pytest.raises(RuntimeError, match=expected_gap):
            schema.validate_current_closeout_fence_schema(connection)


def test_closeout_fence_schema_initialization_requires_a_writer_transaction() -> None:
    with (
        closing(sqlite3.connect(":memory:")) as connection,
        pytest.raises(RuntimeError, match="state_schema_transaction_required"),
    ):
        schema.initialize_closeout_fence_connection(connection)


def _replace_lease_payload(db_path: Path, *, subject: str, field: str, value: object) -> None:
    with closing(sqlite3.connect(db_path)) as connection, connection:
        raw = connection.execute(
            "select payload_json from leases where subject = ?", (subject,)
        ).fetchone()[0]
        payload = json.loads(raw)
        payload[field] = value
        connection.execute(
            "update leases set payload_json = ? where subject = ?",
            (json.dumps(payload, sort_keys=True), subject),
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("holder_ref", False),
        ("epoch", True),
        ("epoch", "1"),
        ("issued_at", 1),
        ("renewed_at", False),
        ("expected_head", 7),
        ("claim_id", False),
        ("path_scope", "README.md"),
        ("path_scope", [1]),
        ("mints_authority", "false"),
        ("mints_authority", True),
        ("filesystem_fence", 0),
        ("distributed_lock", None),
    ],
)
def test_ownerless_state_rejects_every_raw_lease_coercion(
    tmp_path: Path, field: str, value: object
) -> None:
    db_path = tmp_path / "state.sqlite"
    subject = "work/raw-state"
    acquire_lease(
        db_path,
        subject=subject,
        holder_ref="agent:test:case:raw-state",
        ttl_seconds=-1,
    )
    _replace_lease_payload(db_path, subject=subject, field=field, value=value)

    with pytest.raises(closeout.OwnerlessCloseoutStateError) as raised:
        closeout.observe_ownerless_closeout_state(db_path, subject=subject)

    assert raised.value.kind == "state_unverifiable"
    assert raised.value.detail == "lease"


def test_raw_holder_type_is_rejected_before_holder_ref_parsing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "state.sqlite"
    subject = "work/raw-holder"
    acquire_lease(
        db_path,
        subject=subject,
        holder_ref="agent:test:case:raw-holder",
        ttl_seconds=-1,
    )
    _replace_lease_payload(db_path, subject=subject, field="holder_ref", value=False)

    def forbidden_parse(cls: type[object], value: object) -> object:
        del cls, value
        raise AssertionError(forbidden_parse.__name__)

    monkeypatch.setattr(closeout.HolderRef, "parse", classmethod(forbidden_parse))

    with pytest.raises(closeout.OwnerlessCloseoutStateError):
        closeout.observe_ownerless_closeout_state(db_path, subject=subject)


def test_raw_epoch_type_is_rejected_before_strict_lane_lease_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "state.sqlite"
    subject = "work/raw-epoch"
    acquire_lease(
        db_path,
        subject=subject,
        holder_ref="agent:test:case:raw-epoch",
        ttl_seconds=-1,
    )
    _replace_lease_payload(db_path, subject=subject, field="epoch", value=True)

    def forbidden_validate(cls: type[object], value: object, **kwargs: object) -> object:
        del cls, value, kwargs
        raise AssertionError(forbidden_validate.__name__)

    monkeypatch.setattr(
        closeout.LaneLease,
        "model_validate",
        classmethod(forbidden_validate),
    )

    with pytest.raises(closeout.OwnerlessCloseoutStateError):
        closeout.observe_ownerless_closeout_state(db_path, subject=subject)


@pytest.mark.parametrize("suffix", ["-wal", "-shm"])
def test_ownerless_state_rejects_sidecar_without_database(tmp_path: Path, suffix: str) -> None:
    db_path = tmp_path / "state.sqlite"
    Path(f"{db_path}{suffix}").write_bytes(b"orphan sidecar")

    with pytest.raises(closeout.OwnerlessCloseoutStateError) as raised:
        closeout.observe_ownerless_closeout_state(db_path, subject="work/sidecar")

    assert raised.value.kind == "state_unverifiable"
    assert raised.value.detail == "sidecar"


def test_ownerless_state_rejects_raw_fence_tuple_coercion(tmp_path: Path) -> None:
    db_path = tmp_path / "state.sqlite"
    schema.initialize_state(db_path)

    with pytest.raises(closeout.OwnerlessCloseoutStateError) as raised:
        closeout.observe_ownerless_closeout_state(
            db_path,
            subject="work/fence",
            observed_fence=("present", {"subject": False}),
        )

    assert raised.value.kind == "fence_unverifiable"


def test_closeout_fence_internal_scalar_and_payload_validation_edges() -> None:
    with pytest.raises(ValueError, match="lane_closeout_fence_binding_invalid:unknown"):
        closeout._record(("incomplete",))  # noqa: SLF001, RUF100

    malformed_payload = {
        "acquisition_id": "00000000-0000-4000-8000-000000000001",
        "target_path": 1,
        "lane_incarnation_id": "lane-incarnation:edge",
        "observation_digest": "a" * 64,
        "decision_sha256": "b" * 64,
        "chronicle_digest": "c" * 64,
    }
    row = (
        "work/edge",
        "d" * 40,
        "lane-decision:00000000-0000-4000-8000-000000000303",
        "agent:codex:thread:edge",
        "dev",
        "e" * 40,
        "f" * 64,
        json.dumps(malformed_payload),
    )
    with pytest.raises(ValueError, match="lane_closeout_fence_binding_invalid:work/edge"):
        closeout._record(row)  # noqa: SLF001, RUF100

    class StringSubclass(str):
        __slots__ = ()

    with pytest.raises(ValueError, match="lane_closeout_fence_binding_invalid:work/edge"):
        closeout._canonical_holder(StringSubclass("agent:codex:thread:edge"), "work/edge")  # noqa: SLF001, RUF100
    with pytest.raises(ValueError, match="lane_closeout_fence_binding_invalid:work/edge"):
        closeout._canonical_holder("not-a-holder", "work/edge")  # noqa: SLF001, RUF100

    for value in (
        False,
        StringSubclass("00000000-0000-4000-8000-000000000001"),
        "not-a-uuid",
        "00000000-0000-4000-8000-0000000000AA",
    ):
        with pytest.raises(ValueError, match="lane_closeout_fence_binding_invalid:work/edge"):
            closeout._validated_acquisition_id(value, "work/edge")  # noqa: SLF001, RUF100


def test_ownerless_state_snapshot_and_fence_observation_fail_closed_edges(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_directory = tmp_path / "state-directory"
    database_directory.mkdir()
    with pytest.raises(closeout.OwnerlessCloseoutStateError) as directory_error:
        closeout.observe_ownerless_closeout_state(database_directory, subject="work/edge")
    assert (directory_error.value.kind, directory_error.value.detail) == (
        "state_unverifiable",
        "database",
    )

    plain = tmp_path / "plain.sqlite"
    with closing(sqlite3.connect(plain)) as connection:
        connection.execute("create table unrelated(value text)")
    with pytest.raises(closeout.OwnerlessCloseoutStateError) as schema_error:
        closeout.observe_ownerless_closeout_state(plain, subject="work/edge")
    assert (schema_error.value.kind, schema_error.value.detail) == (
        "state_unverifiable",
        "database",
    )

    broken = tmp_path / "broken.sqlite"
    broken.touch()
    with monkeypatch.context() as scoped:
        scoped.setattr(
            closeout,
            "validate_current_lease_schema",
            lambda _connection: (_ for _ in ()).throw(RuntimeError("broken schema")),
        )
        with pytest.raises(closeout.OwnerlessCloseoutStateError) as broken_error:
            closeout.observe_ownerless_closeout_state(broken, subject="work/edge")
    assert (broken_error.value.kind, broken_error.value.detail) == (
        "state_unverifiable",
        "database",
    )

    with monkeypatch.context() as scoped:
        scoped.setattr(closeout, "_closeout_state_snapshot", lambda _path: ([], True))
        scoped.setattr(
            closeout, "probe_closeout_fence", lambda *_args, **_kwargs: ("unverifiable", None)
        )
        with pytest.raises(closeout.OwnerlessCloseoutStateError) as fence_error:
            closeout.observe_ownerless_closeout_state(
                tmp_path / "state.sqlite", subject="work/edge"
            )
    assert (fence_error.value.kind, fence_error.value.detail) == ("fence_unverifiable", "state")

    with pytest.raises(closeout.OwnerlessCloseoutStateError) as tuple_error:
        closeout._validated_observed_fence(("absent", None, None))  # noqa: SLF001, RUF100
    assert (tuple_error.value.kind, tuple_error.value.detail) == ("fence_unverifiable", "state")
    assert closeout._validated_observed_fence(("absent", None)) == ("absent", None)  # noqa: SLF001, RUF100

    with pytest.raises(closeout.OwnerlessCloseoutStateError) as shape_error:
        closeout._validated_observed_fence(("present", {"subject": "work/edge"}))  # noqa: SLF001, RUF100
    assert (shape_error.value.kind, shape_error.value.detail) == ("fence_unverifiable", "state")

    invalid_fence = {
        "subject": "work/edge",
        "expected_head": "a" * 40,
        "decision_id": "lane-decision:00000000-0000-4000-8000-000000000303",
        "executor_ref": False,
        "accepted_branch": "dev",
        "accepted_head": "b" * 40,
        "payload": {},
        "target_binding_digest": "c" * 64,
    }
    with pytest.raises(closeout.OwnerlessCloseoutStateError) as invalid_error:
        closeout._validated_observed_fence(("present", invalid_fence))  # noqa: SLF001, RUF100
    assert (invalid_error.value.kind, invalid_error.value.detail) == ("fence_unverifiable", "state")


def test_validated_lease_rejects_raw_rows_and_invalid_bound_head() -> None:
    with pytest.raises(ValueError, match="lease_invalid"):
        closeout._validated_lease(("incomplete",))  # noqa: SLF001, RUF100
    with pytest.raises(TypeError, match="lease_invalid"):
        closeout._validated_lease(  # noqa: SLF001, RUF100
            (
                "lease:edge",
                "work/edge",
                "agent:codex:thread:edge",
                "2026-07-25T00:00:00+00:00",
                "[]",
            )
        )

    payload = {
        "lane_incarnation_id": "lane-incarnation:edge",
        "lease_id": "lease:edge",
        "lane_ref": "work/edge",
        "holder_ref": "agent:codex:thread:edge",
        "epoch": 1,
        "issued_at": "2026-07-25T00:00:00+00:00",
        "renewed_at": "2026-07-25T00:00:00+00:00",
        "expected_head": "not-a-git-oid",
        "claim_id": "",
        "coordination_scope": "git_common_directory",
        "path_scope": [],
        "mints_authority": False,
        "filesystem_fence": False,
        "distributed_lock": False,
    }
    with pytest.raises(ValueError, match="lease_invalid"):
        closeout._validated_lease(  # noqa: SLF001, RUF100
            (
                payload["lease_id"],
                payload["lane_ref"],
                payload["holder_ref"],
                "2026-07-25T01:00:00+00:00",
                json.dumps(payload),
            )
        )
