"""Interpret native call results without executing repository expressions."""

from __future__ import annotations

from ethos.repository.policy.references.python.values import UNKNOWN
from ethos.repository.policy.references.python.values import BoundCall
from ethos.repository.policy.references.python.values import ExecutableLookup
from ethos.repository.policy.references.python.values import Imported
from ethos.repository.policy.references.python.values import Literal
from ethos.repository.policy.references.python.values import PathMethod
from ethos.repository.policy.references.python.values import Unknown
from ethos.repository.policy.references.python.values import Value
from ethos.repository.policy.references.python.values import attribute
from ethos.repository.policy.references.python.values import join
from ethos.repository.policy.references.python.values import origins


def native_call(call: BoundCall) -> Value:
    """Retain only identities justified by the native callee's value contract."""
    values: list[Value] = []
    for target in call.targets:
        if target == Imported("builtins.getattr"):
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
