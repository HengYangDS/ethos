"""Interpret native call results without executing repository expressions."""

from __future__ import annotations

from ethos.repository.policy.references.python.values import UNKNOWN
from ethos.repository.policy.references.python.values import BoundCall
from ethos.repository.policy.references.python.values import ExecutableLookup
from ethos.repository.policy.references.python.values import Imported
from ethos.repository.policy.references.python.values import Literal
from ethos.repository.policy.references.python.values import MappingMethod
from ethos.repository.policy.references.python.values import MappingValue
from ethos.repository.policy.references.python.values import PathMethod
from ethos.repository.policy.references.python.values import Unknown
from ethos.repository.policy.references.python.values import Value
from ethos.repository.policy.references.python.values import attribute
from ethos.repository.policy.references.python.values import join
from ethos.repository.policy.references.python.values import origins

PROCESS_TARGETS = frozenset(
    Imported(f"subprocess.{name}")
    for name in ("run", "Popen", "call", "check_call", "check_output")
)


def read_only_native_call(call: BoundCall) -> bool:
    """Only modeled native readers can preserve the mutable arguments they receive."""
    return bool(call.targets) and all(
        (isinstance(target, MappingMethod) and target.name in {"get", "copy", "__getitem__"})
        or target in PROCESS_TARGETS | {Imported("builtins.getattr"), Imported("shutil.which")}
        or target in {Imported("builtins.dict"), Imported("os.environ.copy")}
        for target in call.targets
    )


def native_call(call: BoundCall, *, site: tuple[int, int]) -> Value:
    """Retain only identities justified by the native callee's value contract."""
    values: list[Value] = []
    for target in call.targets:
        if isinstance(target, MappingMethod) and target.name == "get":
            values.append(target.owner.read(call.argument(0, "key"), call.argument(1, "default")))
        elif (
            isinstance(target, MappingMethod)
            and target.name == "copy"
            and not (call.args or call.keywords)
        ):
            values.append(MappingValue.construct(site, ((None, frozenset({target.owner})),)))
        elif target == Imported("os.environ.copy") and not (call.args or call.keywords):
            values.append(
                MappingValue.construct(site, ((None, frozenset({Imported("os.environ")})),))
            )
        elif target == Imported("builtins.dict") and len(call.args) <= 1:
            values.extend(
                MappingValue.construct(
                    site,
                    (((None, call.args[0]),) if call.args else ())
                    + tuple((frozenset({Literal(key)}), value) for key, value in keywords.items()),
                )
                if keywords is not None
                else UNKNOWN
                for keywords in call.keyword_bindings()
            )
        elif target == Imported("builtins.getattr"):
            owner, names = call.argument(0, "object"), call.argument(1, "name")
            values.extend(
                attribute(owner, name.value)
                if isinstance(name, Literal) and isinstance(name.value, str)
                else frozenset({Unknown(origins(owner))})
                for name in names
            )
        elif target == Imported("shutil.which"):
            values.extend(
                frozenset({ExecutableLookup(name.value)})
                if isinstance(name, Literal) and isinstance(name.value, str)
                else UNKNOWN
                for name in call.argument(0, "cmd")
            )
        elif target in {Imported("builtins.str"), Imported("pathlib.Path")}:
            values.extend(
                frozenset(
                    {ExecutableLookup(value.identity, is_path=target == Imported("pathlib.Path"))}
                )
                if isinstance(value, ExecutableLookup) and len(call.args) == 1 and not call.keywords
                else UNKNOWN
                for value in call.argument(0, "object")
            )
        elif isinstance(target, PathMethod):
            values.append(
                frozenset(
                    {
                        ExecutableLookup(
                            target.identity, is_path=target.name in {"resolve", "absolute"}
                        )
                    }
                )
            )
        else:
            values.append(UNKNOWN)
    return join(values)
