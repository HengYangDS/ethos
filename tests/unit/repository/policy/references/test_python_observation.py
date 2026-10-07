"""Independent Python carriers preserve their own imported mutable state."""

from __future__ import annotations

import pytest

from ethos.repository.policy.references.observation import product_references_from_files
from ethos.repository.policy.references.observation import reference_consumer_sources_from_files


def _state_carriers(binding: str) -> dict[str, str]:
    state = (
        "command = 'before_probe'" if binding == "module" else "state = {'command': 'before_probe'}"
    )
    update = (
        "global command\n    command = value" if binding == "module" else "state['command'] = value"
    )
    selected = "command" if binding == "module" else "state['command']"
    return {
        "src/example/state.py": (
            f"import subprocess as sp\n{state}\n"
            f"def update(value):\n    {update}\n"
            f"def execute():\n    sp.run([{selected}])\n"
        ),
        "src/example/change.py": (
            "from example.state import update, execute\nupdate('changed_probe')\nexecute()\n"
        ),
        "src/example/read.py": "from example.state import execute\nexecute()\n",
    }


@pytest.mark.parametrize("binding", ["module", "heap"])
@pytest.mark.parametrize("reverse", [False, True])
def test_consumer_observation_keeps_mutation_in_its_own_carrier(
    binding: str, *, reverse: bool
) -> None:
    """One carrier's real effects survive without changing another carrier's initial state."""
    files = _state_carriers(binding)
    if reverse:
        files = dict(reversed(tuple(files.items())))

    observed = reference_consumer_sources_from_files(files)

    assert observed.unknown_paths == ()
    assert observed.sources["executable"] == {
        "before_probe": frozenset({"src/example/state.py", "src/example/read.py"}),
        "changed_probe": frozenset({"src/example/change.py"}),
    }


@pytest.mark.parametrize("binding", ["module", "heap"])
@pytest.mark.parametrize("reverse", [False, True])
def test_product_observation_uses_fresh_state_with_complete_source_context(
    binding: str, *, reverse: bool
) -> None:
    """Context supplies imported definitions, never another file's already-mutated heap."""
    files = _state_carriers(binding)
    context = {"src/example/state.py": files.pop("src/example/state.py")}
    if reverse:
        files = dict(reversed(tuple(files.items())))

    observed = product_references_from_files(files, context_files=context)

    assert observed.unknown_paths == ()
    assert observed.references["executable"] == {"before_probe", "changed_probe"}
