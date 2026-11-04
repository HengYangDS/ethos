"""An interrupted exit resumes from its receipt, and a later adoption starts afresh."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.repo.hook.exit as repository_exit
from ethos.adapters.repo.config_effects import config_values
from ethos.adapters.repo.hook.activation import install_hook_launchers
from ethos.adapters.repo.hook.observation import hook_runtime_binding
from ethos.adapters.repo.hook.preimage import ACTIVATION_KEYS
from ethos.adapters.repo.hook.preimage import read_hooks_preimage
from tests.support.repository_exit import Crash
from tests.support.repository_exit import adopted_with_own_hooks
from tests.support.repository_exit import apply_exit

if TYPE_CHECKING:
    from pathlib import Path


def _crash_after(patch: pytest.MonkeyPatch, step: str) -> None:
    """Stop the apply right after one step, as a killed process would."""

    def removed_then_crash(path: Path) -> None:
        path.unlink(missing_ok=True)
        if path.name == step:
            raise Crash(step)

    def crash(*_args: object, **_kwargs: object) -> None:
        raise Crash(step)

    steps = {
        "receipt": ("_remove", crash),
        "hooks-preimage.json": ("_remove", removed_then_crash),
        "config": ("_require_no_ethos_hooks", crash),
        "ROLLBACK": ("_remove", removed_then_crash),
        "CURRENT": ("_remove", removed_then_crash),
        "applied": ("_mark_applied", crash),
    }
    name, replacement = steps[step]
    patch.setattr(repository_exit, name, replacement)


@pytest.mark.parametrize(
    "step", ["receipt", "hooks-preimage.json", "config", "ROLLBACK", "CURRENT", "applied"]
)
def test_an_interrupted_exit_resumes_to_an_applied_exit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, step: str
) -> None:
    """Whichever step a crash follows, status names the exit incomplete and a re-run ends it."""
    repo, common, before = adopted_with_own_hooks(tmp_path, monkeypatch)
    runtime = common / "ethos/runtime"
    (runtime / "ROLLBACK").write_bytes((runtime / "CURRENT").read_bytes())
    with monkeypatch.context() as patch:
        _crash_after(patch, step)
        with pytest.raises(Crash):
            apply_exit(repo)

    assert hook_runtime_binding(repo)["exit"]["state"] == "incomplete"
    resumed = apply_exit(repo)

    assert resumed.state == "applied", resumed.to_json()
    assert config_values(repo, ACTIVATION_KEYS, scope="local") == before
    assert not (runtime / "CURRENT").exists()
    assert not (runtime / "ROLLBACK").exists()
    assert not (common / "ethos/hooks-preimage.json").exists()
    receipt = json.loads((common / "ethos/exit-receipt.json").read_text(encoding="utf-8"))
    assert receipt["state"] == "applied"


def test_a_readoption_after_an_exit_records_afresh_and_clears_the_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Adopting again replaces the exit with a new record of the configuration it replaces."""
    repo, common, _before = adopted_with_own_hooks(tmp_path, monkeypatch)
    runtime = next(path for path in (common / "ethos/runtime").iterdir() if len(path.name) == 64)
    (repo / ".venv").mkdir()
    (repo / ".venv/pyvenv.cfg").write_text(f"home = {runtime.as_posix()}\n", encoding="utf-8")
    assert apply_exit(repo).state == "applied"

    install_hook_launchers(repo)

    record = read_hooks_preimage(common)
    assert record is not None
    assert record["common"]["core.hooksPath"] == [".githooks"]
    assert not (common / "ethos/exit-receipt.json").exists()
    assert "exit" not in hook_runtime_binding(repo)
