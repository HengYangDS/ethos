"""Compact CLI parity rejection coverage."""

import pytest

import ethos.adapters.shadow.core as shadow_core
import ethos.surface.cli.parity.core as parity_cli


@pytest.mark.parametrize(
    ("execute", "ok", "expected"),
    [
        (False, True, "parity_evidence_write_requires_execute"),
        (True, False, "parity_evidence_write_blocked:demo"),
    ],
)
def test_parity_write_rejection(execute, ok, expected, monkeypatch, tmp_path):
    report = {"ok": ok, "state": "matched", "required_gaps": []}
    monkeypatch.setattr(parity_cli, "resolve_root", lambda _root: tmp_path)
    monkeypatch.setattr(parity_cli, "shadow_parity_report", lambda **_kwargs: report)
    monkeypatch.setattr(shadow_core, "run_shadow_parity", lambda **_kwargs: report)
    emitted = []
    monkeypatch.setattr(parity_cli, "emit", lambda result, **_kwargs: emitted.append(result))
    parity_cli.parity_shadow(
        target=tmp_path,
        adopter="demo",
        execute=execute,
        write_evidence=True,
        json_output=True,
    )
    assert expected in emitted[-1].required_gaps
