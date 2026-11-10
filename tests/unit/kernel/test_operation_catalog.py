"""The catalog declares every command mode once, and every transport selects it alike."""

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

from ethos.adapters.admission.control.replacement import CONTROL_PREFIXES
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
from ethos.contracts.operations.catalog import GROUPS
from ethos.contracts.operations.catalog import select_argv
from ethos.contracts.operations.declaration import Command
from ethos.contracts.operations.declaration import CommandRequest
from ethos.contracts.operations.declaration import Operation
from ethos.surface.cli.application import app
from ethos.surface.cli.application import load_command_groups

# Assignments of a command's selectors that select no operation, pinned so a change is reviewed;
# a command not named here has none.
_UNMATCHED = {
    "prove": 6,
    "land": 8,
    "publish": 9,
    "adopt": 23,
    "lane candidate": 2,
    "lane redact private-addresses": 1,
}
# The one write without an authorization token, a named exemption that A8 retires.
_TOKENLESS = "hook.install"
_ROOT = Path(__file__).resolve().parents[3]
_ID = re.compile(r"[a-z]+(?:\.[a-z][a-z-]*)+")
_WRITES = frozenset({"local-write", "host-write", "remote-write", "opaque"})
_SDK = {
    "status": inspect_repository,
    "plan": plan_repository,
    "land": land_repository,
    "publish": publish_repository,
    "adopt": adopt_repository,
}


def test_each_operation_is_declared_once_with_its_effects_and_authority() -> None:
    """IDs are unique; a write needs an authorization kind and a verdict or process exit."""
    identities = [item.id for command in COMMANDS.values() for item in command.operations]
    assert len(identities) == len(set(identities)) == 102
    assert {name.rpartition(" ")[0] for name in COMMANDS} - {""} <= set(GROUPS)
    for command in COMMANDS.values():
        fields = command.request.model_fields
        assert set().union(*(item.accepted for item in command.operations)) == set(fields)
        assert all(info.kw_only and info.description for info in fields.values())
        assert {*command.positionals, *command.hyphen} <= set(fields)
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
            assert item.authorization != "none" or not writes or item.id == _TOKENLESS
            # A read authorizes nothing, unless its argv carries the Attestation that authorizes it.
            assert writes or item.authorization in {"none", "attestation"}
            assert item.exit != "observe" or not writes
            assert writes or not item.destructive
            assert "opaque" not in item.effects or item.authorization == "human"


@pytest.mark.parametrize("name", sorted(COMMANDS))
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
    assert unmatched == _UNMATCHED.get(name, 0)


def _value(command: Command, name: str) -> list[str]:
    """Return argv that sets one field to a value other than its default."""
    if not command.valued(name):
        return [command.flag(name)]
    annotation = command.request.model_fields[name].annotation
    literal = get_origin(annotation) is Literal
    return [command.flag(name), get_args(annotation)[-1] if literal else "1"]


def _required(command: Command) -> list[str]:
    """Return the command's path and argv that sets each field every request must set."""
    fields = command.request.model_fields
    required = sorted(name for name, info in fields.items() if info.is_required())
    return [*command.name.split(), *(token for name in required for token in _value(command, name))]


def _example(command: Command, item: Operation) -> list[str]:
    """Return the shortest argv that selects one operation."""
    argv = ["ethos", *_required(command)]
    for name, want in item.selectors:
        argv.extend(_value(command, name) if want in {"true", "set"} else ())
    return argv


def _parsed(command: Command, argv: list[str]) -> CommandRequest:
    """Return the request Cyclopts binds for one argv, which names the command's path."""
    bound = app.parse_args(argv, exit_on_error=False, print_error=False)[1]
    bound.apply_defaults()
    fields = command.request.model_fields
    return command.request(
        **{key: value for key, value in bound.arguments.items() if key in fields}
    )


def test_every_operation_parses_and_selects_alike_from_its_example() -> None:
    """The kernel's argv reading, Cyclopts' parse and the application selection agree."""
    load_command_groups([])
    for command in COMMANDS.values():
        required = command.present(_parsed(command, _required(command)))
        for name in command.request.model_fields.keys() - required:
            request = _parsed(command, [*_required(command), *_value(command, name)])
            assert command.present(request) == {name, *required}
        for item in command.operations:
            argv = _example(command, item)
            assert select_argv(argv) == (command, item)
            chosen = select_operation(command.name, _parsed(command, argv[1:]))
            assert isinstance(chosen, Selected)
            assert chosen.operation is item


@pytest.mark.parametrize(
    ("argv", "operation"),
    [
        ("land --apply=false", ""),
        ("land --no-apply", ""),
        ("land --expect-head", ""),
        ("land positional", ""),
        ("land --closeout --release", ""),
        ("land --release --candidate-head c", ""),
        ("host run --wait 5 -- git --root x", "host.run"),
        ("host run git -C x status --json", "host.run"),
        ("host run --command x y", ""),
        ("attestation record file.json --apply", "attestation.record.apply"),
        ("attestation query word", ""),
        ("hook commit-range refs/heads/main --remote origin", ""),
        ("attestation --apply", None),
    ],
)
def test_an_argv_selects_its_declared_form_and_nothing_else(argv: str, operation: str) -> None:
    """A path takes words and `--` for its positionals; any other form leaves it unselected."""
    chosen = select_argv(["ethos", *argv.split()])
    assert (chosen and (chosen[1].id if chosen[1] else "")) == operation


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
    """Every operation names one `(root, request)` function under `ethos.application`.

    A row is keyed by a command, serving each of its operations, or by an operation ID, which
    overrides its command's row and never repeats its body. The body of a group entry that writes
    or runs a caller's command lies under one of the control fence's prefixes, which all exist.
    """
    assert all((_ROOT / prefix).exists() for prefix in CONTROL_PREFIXES)
    commands = {item.id: name for name, command in COMMANDS.items() for item in command.operations}
    assert set(IMPLEMENTATIONS) <= commands.keys() | COMMANDS.keys()
    for name, command in COMMANDS.items():
        for item in command.operations:
            own, shared = IMPLEMENTATIONS.get(item.id), IMPLEMENTATIONS.get(name)
            assert own or shared
            assert own != shared
            module, _separator, function = (own or shared or "").partition(":")
            assert module.startswith("ethos.application.")
            implementation = getattr(import_module(module), function)
            parameters = list(inspect.signature(implementation).parameters)
            # `prove` postpones its annotations and imports `Path` for type checking only.
            hints = get_type_hints(implementation, localns={"Path": Path})
            assert (len(parameters), hints[parameters[1]]) == (2, command.request)
            assert "root" not in command.request.model_fields
            fenced = f"src/{module.replace('.', '/')}.py".startswith(CONTROL_PREFIXES)
            assert fenced or " " not in name or not _WRITES & set(item.effects)
