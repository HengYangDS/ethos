"""One owner reads the process actor, strips it, and supplies the local default."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from ethos.adapters.actor import ACTOR_VARIABLE
from ethos.adapters.actor import LOCAL_ISSUER
from ethos.adapters.actor import handoff_step
from ethos.adapters.actor import invocation_actor
from ethos.adapters.actor import process_actor
from ethos.adapters.actor import process_issuer
from ethos.adapters.process import run_command

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


@pytest.mark.parametrize(
    ("inherited", "given", "bound"),
    [
        ("agent:a:b:outer", " agent:a:b:inner ", "agent:a:b:inner"),
        (None, "agent:a:b:inner", "agent:a:b:inner"),
        ("agent:a:b:outer", None, "agent:a:b:outer"),
        ("agent:a:b:outer", "  ", "agent:a:b:outer"),
    ],
)
def test_an_explicit_actor_binds_one_invocation_and_its_children(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    inherited: str | None,
    given: str | None,
    bound: str,
) -> None:
    """A given actor wins over the fallback, reaches children and ends with its invocation."""
    if inherited is None:
        monkeypatch.delenv(ACTOR_VARIABLE, raising=False)
    else:
        monkeypatch.setenv(ACTOR_VARIABLE, inherited)
    probe = (sys.executable, "-c", "import os; print(os.environ['ETHOS_ACTOR'])")
    seen: list[str] = []

    def failed_invocation() -> None:
        with invocation_actor(given):
            seen.extend((process_actor(), run_command(tmp_path, probe, check=True).stdout.strip()))
            raise LookupError

    with pytest.raises(LookupError):
        failed_invocation()
    assert seen == [bound, bound]
    assert process_actor() == (inherited or "")


def test_no_other_product_module_reads_the_actor_variable() -> None:
    """Every product read goes through the owner, so normalization and the default stay one."""
    owner = ROOT / "src/ethos/adapters/actor.py"
    readers = [
        path.relative_to(ROOT).as_posix()
        for path in sorted((ROOT / "src/ethos").rglob("*.py"))
        if path != owner and '"ETHOS_ACTOR"' in path.read_text(encoding="utf-8")
    ]
    assert readers == []


@pytest.mark.parametrize(
    "missing",
    [{"generation": None}, {"generation": 0}, {"expires_at": None}, {"holder_ref": "  "}],
)
def test_a_lease_without_its_coordinates_renders_no_handoff(missing: dict[str, object]) -> None:
    """A preview that reads `--generation None` cannot be followed, so the caller gets none."""
    lease = {"holder_ref": "agent:a:b:c", "generation": 1, "expires_at": "2099-01-01T00:00:00Z"}
    assert handoff_step(ROOT, "work/example", lease | missing, "agent:a:b:d") == ""
