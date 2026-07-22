from __future__ import annotations

import importlib

import pytest

_FRAME_MODULE = "ethos_core.contracts.source_budget.measurement.worker.protocol.frame"


def test_worker_frame_module_is_importable() -> None:
    try:
        importlib.import_module(_FRAME_MODULE)
    except ModuleNotFoundError as exc:
        if exc.name == _FRAME_MODULE:
            pytest.fail(f"worker frame RED: missing module {_FRAME_MODULE}")
        raise
