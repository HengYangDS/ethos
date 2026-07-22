from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from types import ModuleType

_PROTOCOL_MODULE = "ethos_core.contracts.source_budget.measurement.worker.protocol.core"
_PUBLIC_API = (
    "CHILD_WORKER_GAPS",
    "PARENT_WORKER_GAPS",
    "WorkerRequest",
    "WorkerResult",
    "WorkerSuccess",
    "replay_worker_result",
    "worker_protocol_json_schema",
)


def _protocol() -> ModuleType:
    return importlib.import_module(_PROTOCOL_MODULE)


def test_worker_protocol_exposes_final_public_api() -> None:
    module = _protocol()
    missing = tuple(name for name in _PUBLIC_API if not hasattr(module, name))

    if missing:
        pytest.fail(f"worker protocol RED: missing final public API {missing}")
