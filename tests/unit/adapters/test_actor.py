"""One owner reads the process actor, strips it, and supplies the local default."""

from __future__ import annotations

from pathlib import Path

import pytest

from ethos.adapters.actor import ACTOR_VARIABLE
from ethos.adapters.actor import LOCAL_ISSUER
from ethos.adapters.actor import process_actor
from ethos.adapters.actor import process_issuer

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize(
    ("declared", "actor", "issuer"),
    [
        ("  agent:codex:thread:1  ", "agent:codex:thread:1", "agent:codex:thread:1"),
        ("   ", "", LOCAL_ISSUER),
        (None, "", LOCAL_ISSUER),
    ],
)
def test_the_process_actor_is_stripped_and_defaults_only_for_issuers(
    monkeypatch: pytest.MonkeyPatch, declared: str | None, actor: str, issuer: str
) -> None:
    """An undeclared or blank actor is empty for checks and the local process for records."""
    if declared is None:
        monkeypatch.delenv(ACTOR_VARIABLE, raising=False)
    else:
        monkeypatch.setenv(ACTOR_VARIABLE, declared)
    assert (process_actor(), process_issuer()) == (actor, issuer)


def test_no_other_product_module_reads_the_actor_variable() -> None:
    """Every product read goes through the owner, so normalization and the default stay one."""
    owner = ROOT / "src/ethos/adapters/actor.py"
    readers = [
        path.relative_to(ROOT).as_posix()
        for path in sorted((ROOT / "src/ethos").rglob("*.py"))
        if path != owner and '"ETHOS_ACTOR"' in path.read_text(encoding="utf-8")
    ]
    assert readers == []
