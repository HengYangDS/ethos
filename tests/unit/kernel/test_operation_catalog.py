"""The root catalog declares every root mode once, and every transport selects it alike."""

import inspect
import re
from importlib import import_module
from itertools import product
from pathlib import Path
from typing import Literal
from typing import get_args
from typing import get_origin
from typing import get_type_hints

import pytest

from ethos.application.adoption import adopt_repository
from ethos.application.catalog import IMPLEMENTATIONS
from ethos.application.catalog import Selected
from ethos.application.catalog import select_operation
from ethos.application.inspection import inspect_repository
from ethos.application.land.operation import land_repository
from ethos.application.plan import plan_repository
from ethos.application.proof.operation import prove_repository
from ethos.application.publication.operation import publish_repository
from ethos.contracts.admission import STEP_EFFECTS
from ethos.contracts.operations.catalog import COMMANDS
from ethos.contracts.operations.catalog import select_argv
from ethos.contracts.operations.declaration import Command
from ethos.contracts.operations.declaration import CommandRequest
from ethos.contracts.operations.declaration import Operation
from ethos.surface.cli.application import app
from ethos.surface.cli.application import load_command_groups

# Assignments of a command's selectors that select no operation, pinned so a change is reviewed.
_UNMATCHED = {"status": 0, "plan": 0, "prove": 6, "land": 8, "publish": 9, "adopt": 23}
_ID = re.compile(r"[a-z]+(?:\.[a-z][a-z-]*)+")
_WRITES = frozenset({"local-write", "host-write", "remote-write"})
_SDK = {
    "status": inspect_repository,
    "plan": plan_repository,
    "land": land_repository,
    "publish": publish_repository,
    "adopt": adopt_repository,
}


def test_each_operation_is_declared_once_with_its_effects_and_authority() -> None:
    """IDs are unique; a write needs an authorization kind and a verdict exit, and only a write."""
    identities = [item.id for command in COMMANDS.values() for item in command.operations]
    assert len(identities) == len(set(identities)) == 29
    for command in COMMANDS.values():
        fields = command.request.model_fields
        assert set().union(*(item.accepted for item in command.operations)) == set(fields)
        assert all(info.kw_only and info.description for info in fields.values())
        for item in command.operations:
            names = [name for name, _want in item.selectors]
            assert _ID.fullmatch(item.id)
            assert len(names) == len(set(names))
            assert not set(names) & item.request
            assert item.accepted <= set(fields)
            assert all(
                want in ({"set", "unset"} if command.valued(name) else {"true", "false"})
                for name, want in item.selectors
            )
            assert item.effects == tuple(e for e in STEP_EFFECTS if e in item.effects)
            writes = _WRITES & set(item.effects)
            assert (item.authorization != "none") is bool(writes)
            assert item.exit == "verdict" or not writes
            assert writes or not item.destructive


@pytest.mark.parametrize("name", sorted(_UNMATCHED))
def test_selectors_choose_at_most_one_operation_for_every_assignment(name: str) -> None:
    """Enumerating every selector assignment finds no overlap and the pinned unmatched count."""
    command = COMMANDS[name]
    selectors = sorted({field for item in command.operations for field, _ in item.selectors})
    unmatched = 0
    for values in product((False, True), repeat=len(selectors)):
        present = frozenset(field for field, value in zip(selectors, values, strict=True) if value)
        matched = [item for item in command.operations if not item.failed(present)]
        assert len(matched) <= 1, (name, present)
        unmatched += not matched
    assert unmatched == _UNMATCHED[name]


def _value(command: Command, name: str) -> list[str]:
    """Return argv that sets one field to a value other than its default."""
    if not command.valued(name):
        return [command.flag(name)]
    annotation = command.request.model_fields[name].annotation
    literal = get_origin(annotation) is Literal
    return [command.flag(name), get_args(annotation)[-1] if literal else "x"]


def _example(command: Command, item: Operation) -> list[str]:
    """Return the shortest argv that selects one operation."""
    argv = ["ethos", command.name]
    for name, want in item.selectors:
        argv.extend(_value(command, name) if want in {"true", "set"} else ())
    return argv


def _parsed(argv: list[str]) -> CommandRequest:
    """Return the request Cyclopts binds for one root argv."""
    bound = app.parse_args(argv, exit_on_error=False, print_error=False)[1]
    bound.apply_defaults()
    return bound.arguments["request"]


def test_every_operation_parses_and_selects_alike_from_its_example() -> None:
    """The kernel's argv reading, Cyclopts' parse and the application selection agree."""
    load_command_groups([])
    for command in COMMANDS.values():
        for name in command.request.model_fields:
            assert command.present(_parsed([command.name, *_value(command, name)])) == {name}
        for item in command.operations:
            argv = _example(command, item)
            assert select_argv(argv) == (command, item)
            chosen = select_operation(command.name, _parsed(argv[1:]))
            assert isinstance(chosen, Selected)
            assert chosen.operation is item


@pytest.mark.parametrize(
    "argv",
    [
        ("ethos", "land", "--apply=false"),
        ("ethos", "land", "--no-apply"),
        ("ethos", "land", "--expect-head"),
        ("ethos", "land", "positional"),
        ("ethos", "land", "--closeout", "--release"),
        ("ethos", "land", "--release", "--candidate-head", "c"),
    ],
)
def test_an_argv_outside_the_declared_forms_selects_nothing(argv: tuple[str, ...]) -> None:
    """A negated, valueless, positional, unmatched or refused form leaves the argv unselected."""
    assert select_argv(argv) == (COMMANDS["land"], None)


def test_each_root_operation_keeps_its_request_signature() -> None:
    """The SDK and MCP signatures take exactly the request fields with the same defaults."""
    for name, function in _SDK.items():
        parameters = dict(inspect.signature(function).parameters)
        parameters.pop("root")
        fields = COMMANDS[name].request.model_fields
        assert {key: item.default for key, item in parameters.items()} == {
            key: info.default for key, info in fields.items()
        }
        hints = get_type_hints(function, localns={"Path": Path})
        assert {key: hints[key] for key in parameters} == {
            key: info.annotation for key, info in fields.items()
        }
    proof = inspect.signature(prove_repository).parameters["request"]
    assert proof.default == COMMANDS["prove"].request()


def test_each_operation_maps_to_one_implementation_of_its_command() -> None:
    """Every operation names one `(root, request)` function under `ethos.application`."""
    commands = {item.id: name for name, command in COMMANDS.items() for item in command.operations}
    assert set(IMPLEMENTATIONS) == set(commands)
    for operation, target in IMPLEMENTATIONS.items():
        module, _separator, name = target.partition(":")
        assert module.startswith("ethos.application.")
        implementation = getattr(import_module(module), name)
        parameters = list(inspect.signature(implementation).parameters)
        request = COMMANDS[commands[operation]].request
        # `prove` postpones its annotations and imports `Path` for type checking only.
        hints = get_type_hints(implementation, localns={"Path": Path})
        assert (len(parameters), hints[parameters[1]]) == (2, request)
        assert "root" not in request.model_fields
