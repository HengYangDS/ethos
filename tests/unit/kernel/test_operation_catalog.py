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

import ethos.application.hook.installation as installation
from ethos.adapters.admission.control.replacement import CONTROL_PREFIXES
from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.repo.hook.rollback import RESTORE_ACTION
from ethos.adapters.repo.hook.rollback import RollbackRefusalError
from ethos.application.adoption import adopt_repository
from ethos.application.catalog import IMPLEMENTATIONS
from ethos.application.catalog import Selected
from ethos.application.catalog import invoke
from ethos.application.catalog import select_operation
from ethos.application.inspection import inspect_repository
from ethos.application.land.operation import land_repository
from ethos.application.plan import plan_repository
from ethos.application.proof.operation import prove_repository
from ethos.application.publication.operation import publish_repository
from ethos.contracts.admission import StepEffect
from ethos.contracts.operations.catalog import COMMANDS
from ethos.contracts.operations.catalog import GROUPS
from ethos.contracts.operations.catalog import select_argv
from ethos.contracts.operations.declaration import Command
from ethos.contracts.operations.declaration import CommandRequest
from ethos.contracts.operations.declaration import Operation
from ethos.result import EthosResult
from ethos.surface.cli.application import app
from ethos.surface.cli.catalog import register

# Assignments of a command's selectors that select no operation, pinned so a change is reviewed;
# a command not named here has none.
_UNMATCHED = {
    "prove": 6,
    "land": 8,
    "publish": 18,
    "adopt": 23,
    "lane candidate": 2,
    "lane redact private-addresses": 1,
    "lane repair-signature": 1,
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
# What hook activation hands `hook install`, by class: a binding, or the refusal it raises.
_BOUND = {"hooks_path": "hooks", "python": "python", "current": True, "required_gaps": []}
_GAPPED = _BOUND | {"required_gaps": ["hook_runtime_cleanup_deferred"]}
_ACTIVATIONS: dict[str, dict[str, object] | Exception] = {
    "current": _BOUND,
    "deferred": _GAPPED | {"generation_cleanup": {"state": "deferred"}},
    "deferred-ungapped": _BOUND | {"generation_cleanup": {"state": "deferred"}},
    "locator-retained": _GAPPED | {"legacy_runtime_locator": {"state": "retained"}},
    "io": OSError("readonly"),
    "worktrees": ValueError("hook_runtime_worktrees_unreadable"),
    "state-busy": ValueError("state_activation_failed:locked"),
    "reset-needed": ValueError("state_schema_migration_requires_reset"),
    "reset-unauthorized": ValueError("state_reset_authorization_required"),
    "supply": ValueError("hook_runtime_installed_supply_unavailable:/missing"),
    "rollback": RollbackRefusalError("runtime_rollback_declaration_repaired", RESTORE_ACTION),
    "process": ProcessExecutionError("failed", reason="exit", observation={"state": "unknown"}),
}
# Every form of the install request.
_INSTALLS: dict[str, dict[str, object]] = {
    "plain": {},
    "runtime": {"installed_runtime": "/runtime"},
    "reset": {"reset_state": True},
    "authorized-reset": {"reset_state": True, "authorize": True},
}


def test_each_operation_is_declared_once_with_its_effects_and_authority() -> None:
    """IDs are unique; a write needs an authorization kind and a verdict or process exit."""
    identities = [item.id for command in COMMANDS.values() for item in command.operations]
    assert len(identities) == len(set(identities)) == 108
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
            assert item.effects == tuple(e for e in get_args(StepEffect) if e in item.effects)
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
    register()
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
        ("host run --work render -- git status", "host.run"),
        ("host status --guest-cpus 8", "host.status"),
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


def _repeats(name: str, root: Path, fields: dict[str, object], result: EthosResult) -> bool:
    """Whether a result's next step runs the operation, root and request that produced it."""
    step, chosen = result.next, select_operation(name, fields)
    selected = select_argv(step.argv) if step.argv else None
    if selected is None or not isinstance(chosen, Selected) or selected[1] is not chosen.operation:
        return False
    request = _parsed(COMMANDS[name], list(step.argv[1:]))
    return (request, Path(str(step.binding.get("root", root)))) == (chosen.request, root)


@pytest.mark.parametrize("request_form", sorted(_INSTALLS))
@pytest.mark.parametrize("activation", sorted(_ACTIVATIONS))
def test_no_install_result_names_the_request_that_produced_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, activation: str, request_form: str
) -> None:
    """A `next` that repeats its producer's operation, root and request is a loop.

    The table reaches one builder through its stubbed adapter: each form of the install request
    against each class of activation outcome. It sees neither a builder that needs a repository,
    nor a cycle of two steps, nor prose or a non-`ethos` argv that asks for the same run.
    """
    outcome, fields = _ACTIVATIONS[activation], _INSTALLS[request_form]

    def activate(*_args: object, **_kwargs: object) -> dict[str, object]:
        if isinstance(outcome, Exception):
            raise outcome
        return dict(outcome)

    monkeypatch.setattr(installation, "install_hook_launchers", activate)
    monkeypatch.setattr(installation, "state_schema_report", lambda _root: {})
    register()
    result = invoke("hook install", tmp_path, fields)
    assert not _repeats("hook install", tmp_path, fields, result), result.next_action
    # The reading is not vacuous: the base's continuation for a plain request is seen as a loop.
    loop = result.model_copy(update={"next_action": f"ethos hook install --root {tmp_path} --json"})
    assert _repeats("hook install", tmp_path, {}, loop)
