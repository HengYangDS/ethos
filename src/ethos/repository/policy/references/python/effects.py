"""Effect contracts for proven Python callable identities and bounded residuals."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from dataclasses import replace
from typing import TYPE_CHECKING
from typing import Literal

from ethos.repository.policy.references.commands.invocation import command_executables
from ethos.repository.policy.references.python.bindings import BindingValue
from ethos.repository.policy.references.python.bindings import ImportReference
from ethos.repository.policy.references.python.bindings import MemberDemand
from ethos.repository.policy.references.python.bindings import ReceiverMethod
from ethos.repository.policy.references.python.bindings import ReferenceUncertainty
from ethos.repository.policy.references.python.functions.capabilities import escaped_capabilities
from ethos.repository.policy.references.python.functions.effects import EffectCall
from ethos.repository.policy.references.python.functions.effects import command_tokens
from ethos.repository.policy.references.python.functions.effects import project
from ethos.repository.policy.references.python.native.returns import native_return

if TYPE_CHECKING:
    import ast

    from ethos.repository.policy.references.python.bindings import BindingScope
    from ethos.repository.policy.references.python.functions.returns import PythonSourceReturns

_EXECUTABLE_CALLS = frozenset(
    f"subprocess.{name}"
    for name in (
        "run",
        "Popen",
        "call",
        "check_call",
        "check_output",
        "getoutput",
        "getstatusoutput",
    )
) | {"os.system", "os.execv"}
_VALUE_CALLS = frozenset({"os.getenv", "os.environ.get", "os.environ.__getitem__"})
_IMPORT_CALLS = frozenset({"importlib.import_module", "builtins.__import__"})


@dataclass(frozen=True, slots=True)
class ReceiverCall:
    """A native result and its effect disposition are separate observations."""

    returned: BindingValue | None = None
    disposition: Literal["read", "mutation", "unresolved"] = "unresolved"
    footprint: BindingValue = field(default_factory=BindingValue)
    argument_demand: int | None = None
    post_state: BindingValue | None = None


@dataclass(slots=True)
class PythonConsumption:
    """Consumed identities and unresolved sites, without any authorization claim."""

    path: str
    npm_scripts: dict[str, set[str]]
    sources: PythonSourceReturns | None = None
    imports: set[str] = field(default_factory=set)
    import_sites: list[ImportReference] = field(default_factory=list)
    executables: set[str] = field(default_factory=set)
    inputs: set[str] = field(default_factory=set)
    uncertainties: list[ReferenceUncertainty] = field(default_factory=list)

    def absorb(self, observation: PythonConsumption) -> None:
        """Retain native facts and their original uncertainty provenance once."""
        self.imports.update(observation.imports)
        self.executables.update(observation.executables)
        self.inputs.update(observation.inputs)
        self.uncertainties.extend(observation.uncertainties)
        if self.path == observation.path:
            self.import_sites.extend(observation.import_sites)

    def call(
        self,
        callee: BindingValue,
        args: tuple[BindingValue, ...],
        keywords: dict[str | None, BindingValue],
        node: ast.Call,
        scope: BindingScope,
    ) -> BindingValue:
        """Recognize effects only after binding resolution proves the callee."""
        native = replace(callee, methods=frozenset())
        has_native = bool(
            native.targets
            or native.selection
            or native.parameters
            or native.local
            or native.unknown
            or (native.deferred and not callee.methods)
        )
        if self.sources is not None:
            unresolved = frozenset(
                method
                for method in callee.methods
                if self.bound_method(
                    scope.resolve(method.receiver), method.name, args, keywords, scope
                ).disposition
                == "unresolved"
            )
            if has_native or unresolved:
                self.sources.invocations.note_call(
                    replace(callee, methods=unresolved), args, keywords, node, self.path, scope
                )
        receiver_scope = scope.fork() if callee.methods and has_native else scope
        returned = self.receiver_returns(callee.methods, args, keywords, node, receiver_scope)
        if has_native or not callee.methods:
            branch = scope.fork() if callee.methods else scope
            value = self.native_call(native, args, keywords, node, branch)
            returned = value if returned is None else returned.join(value)
            if callee.methods:
                scope.merge(receiver_scope, branch)
        return returned if returned is not None else BindingValue(unknown=True)

    def receiver_returns(
        self,
        methods: frozenset[ReceiverMethod],
        args: tuple[BindingValue, ...],
        keywords: dict[str | None, BindingValue],
        node: ast.Call,
        scope: BindingScope,
    ) -> BindingValue | None:
        """Demand only a qualified native input, then read its receiver's current heap."""
        returned: BindingValue | None = None
        for method in methods:
            native = self.bound_method(
                scope.resolve(method.receiver), method.name, args, keywords, scope
            )
            if native.argument_demand is not None and self.sources is not None:
                index = native.argument_demand
                demanded = self.sources.invocations.resolve(args[index], scope, self, deep=False)
                actual = (*args[:index], demanded, *args[index + 1 :])
                native = self.bound_method(
                    scope.resolve(method.receiver), method.name, actual, keywords, scope
                )
            if native.disposition != "read":
                if native.post_state is not None:
                    if self.sources is not None:
                        self.sources.invocations.note_mutation(scope, native.footprint)
                    for identity in native.footprint.aggregates:
                        updated = replace(native.post_state, aggregates=frozenset())
                        if (
                            len(methods) > 1
                            or len(native.footprint.aggregates) > 1
                            or identity in scope.summarized
                        ):
                            updated = scope.member(identity).join(updated)
                        scope.assign_member(identity, updated)
                else:
                    self.escape((*args, *keywords.values()), node, scope)
                    self.invalidate(scope, native.footprint, conditional=True)
            value = native.returned or BindingValue(unknown=True)
            returned = value if returned is None else returned.join(value)
        return returned

    def native_call(
        self,
        callee: BindingValue,
        args: tuple[BindingValue, ...],
        keywords: dict[str | None, BindingValue],
        node: ast.expr,
        scope: BindingScope,
    ) -> BindingValue:
        """Observe qualified native targets and retain their opaque alternatives."""
        dependencies = (callee, *args, *keywords.values())
        deferred = callee.deferred or bool(callee.parameters)
        generic = BindingValue(
            local=callee.local,
            deferred=deferred,
            unknown=any(value.unknown for value in dependencies) or not deferred,
            context_limited=any(value.context_limited for value in dependencies),
        )
        known = {
            target: native_return(self, target, args, keywords, scope) for target in callee.targets
        }
        if (
            callee.unknown
            or callee.local
            or not callee.targets
            or any(self.kind(target) is None and known[target] is None for target in callee.targets)
        ):
            self.escape(() if callee.parameters else (*args, *keywords.values()), node, scope)
            self.invalidate(scope, *args, *keywords.values(), conditional=True)
        returned: BindingValue | None = None
        for target in callee.targets:
            value_returned = known[target] or generic
            if (
                target in {"builtins.dict", "builtins.dict.fromkeys"}
                and value_returned.entries is not None
            ) or (
                target == "builtins.list"
                and (value_returned.items is not None or value_returned.element is not None)
            ):
                value_returned = scope.aggregate(value_returned, node)
            kind = self.kind(target)
            if kind is not None:
                value, executable = self.argument_roles(kind, target, args, keywords)
                self.consume(kind, value, node, scope, target, executable=executable)
                if kind == "import":
                    value_returned = self.imported(value, target, node)
                if callee.unknown:
                    self.residual(kind, "unknown", node, scope, target, "callee_not_closed")
            returned = value_returned if returned is None else returned.join(value_returned)
        for module in callee.selection:
            for kind in self.module_kinds(module):
                self.residual(kind, "unknown", node, scope, module, "dynamic_callee")
        if returned is not None and (callee.unknown or callee.local or callee.deferred):
            returned = returned.join(generic)
        return returned if returned is not None else generic

    def invalidate(
        self, scope: BindingScope, *values: BindingValue, conditional: bool = False
    ) -> None:
        """Invalidate reachable mutable and lazy return subjects through one boundary."""
        scope.invalidate_aggregates(*values)
        if self.sources is not None:
            self.sources.invocations.invalidate(scope, *values, conditional=conditional)

    @staticmethod
    def argument_roles(
        kind: Literal["import", "executable", "value"],
        target: str,
        args: tuple[BindingValue, ...],
        keywords: dict[str | None, BindingValue],
    ) -> tuple[BindingValue, BindingValue | None]:
        """Interpret native signature roles independently of process-visible argv labels."""
        key = {"executable": "args", "value": "key", "import": "name"}[kind]
        value = args[0] if args else keywords.get(key, BindingValue(unknown=True))
        executable = keywords.get("executable") if kind == "executable" else None
        if target == "os.execv":
            executable, value = (
                value,
                (args[1] if len(args) > 1 else keywords.get("argv", BindingValue(unknown=True))),
            )
        return value, executable

    def imported(self, value: BindingValue, target: str, node: ast.AST) -> BindingValue:
        """Retain the imported module result and its exact import sites together."""
        self.import_sites.extend(
            ImportReference(module, "", getattr(node, "lineno", 0), getattr(node, "col_offset", 0))
            for module in value.strings
        )
        return BindingValue(
            targets=frozenset(
                module.partition(".")[0] if target == "builtins.__import__" else module
                for module in value.strings
            ),
            unknown=value.unknown,
            deferred=value.deferred,
            context_limited=value.context_limited,
        )

    def bound_method(
        self,
        owner: BindingValue,
        name: str,
        args: tuple[BindingValue, ...],
        keywords: dict[str | None, BindingValue],
        scope: BindingScope,
    ) -> ReceiverCall:
        """Classify native receiver relationships without applying their effects."""
        disposition = "unresolved" if owner.unknown or owner.targets else "read"
        if owner.path and name in {"resolve", "absolute", "as_posix"}:
            return ReceiverCall(
                replace(owner, strings=frozenset(), path=name != "as_posix"), "read"
            )
        if (
            owner.aggregates
            and owner.native_kind == "list"
            and not (owner.unknown or owner.deferred or owner.view or owner.fields or owner.targets)
            and name == "append"
            and len(args) == 1
            and not (args[0].spread or keywords)
        ):
            return ReceiverCall(
                BindingValue(local=True),
                "mutation",
                owner,
                post_state=replace(
                    owner,
                    items=(*owner.items, args[0]) if owner.items is not None else None,
                    element=owner.iterated().join(args[0]) if owner.items is None else None,
                ),
            )
        if owner.aggregates and owner.entries is not None and name in {"keys", "values", "items"}:
            return ReceiverCall(
                scope.resolve(BindingValue(aggregates=owner.aggregates, view=name)),
                disposition,
                owner,
            )
        if owner.aggregates and owner.entries is not None and name == "get" and args:
            key = args[0]
            if key.projections:
                return ReceiverCall(disposition=disposition, footprint=owner, argument_demand=0)
            return ReceiverCall(
                project(
                    owner,
                    MemberDemand("get", selector=key, default=args[1] if len(args) > 1 else None),
                    scope,
                    self.sources,
                    self,
                ),
                disposition,
                owner,
            )
        return ReceiverCall(footprint=owner)

    def escape(self, values: tuple[BindingValue, ...], node: ast.AST, scope: BindingScope) -> None:
        """Opaque custody transfer may invoke a known capability before returning."""
        if self.sources is not None:
            for target in escaped_capabilities(self.sources, values, scope, self):
                kind = self.kind(target)
                for affected in (kind,) if kind is not None else self.module_kinds(target):
                    self.residual(
                        affected, "unknown", node, scope, target, "opaque_capability_escape"
                    )

    def call_escapes(
        self,
        callee: BindingValue,
        args: tuple[BindingValue, ...],
        keywords: dict[str | None, BindingValue],
        scope: BindingScope,
    ) -> bool:
        """Bind argument transfer to every source, native and unresolved callee alternative."""
        return (
            self.sources is not None
            and (
                callee.unknown
                or callee.local
                or bool(callee.parameters)
                or (callee.deferred and not callee.methods)
                or not (callee.targets or callee.methods)
                or any(
                    target not in self.sources.definitions
                    and self.kind(target) is None
                    and native_return(self, target, args, keywords, scope) is None
                    for target in callee.targets
                )
                or any(
                    self.bound_method(
                        scope.resolve(method.receiver), method.name, args, keywords, scope
                    ).disposition
                    == "unresolved"
                    for method in callee.methods
                )
            )
            and any(
                self.sources.invocations.custody.mutable(value, symbolic=True)
                for value in (*args, *keywords.values())
            )
        )

    @staticmethod
    def kind(target: str) -> Literal["import", "executable", "value"] | None:
        """Classify a closed contract, not the receiver's source spelling."""
        if target in _EXECUTABLE_CALLS:
            return "executable"
        if target in _VALUE_CALLS:
            return "value"
        if target in _IMPORT_CALLS:
            return "import"
        return None

    @staticmethod
    def module_kinds(module: str) -> tuple[Literal["import", "executable", "value"], ...]:
        """Unresolved members may affect every supported contract of their owner."""
        kinds: tuple[Literal["import", "executable", "value"], ...] = ()
        if module in {"os", "os.environ"}:
            kinds = ("value", "executable") if module == "os" else ("value",)
        elif module == "importlib":
            kinds = ("import",)
        elif module == "subprocess":
            kinds = ("executable",)
        return kinds

    def attribute(self, args: tuple[BindingValue, ...], scope: BindingScope) -> BindingValue:
        """Join source and native member alternatives through one lookup-time owner."""
        owner = scope.resolve(args[0])
        names = args[1] if len(args) > 1 else BindingValue(unknown=True)
        value = BindingValue(
            local=owner.local,
            deferred=owner.deferred or names.deferred,
            unknown=owner.unknown or names.unknown,
            context_limited=owner.context_limited or names.context_limited,
            parameters=frozenset(
                replace(
                    projection,
                    members=(*projection.members, MemberDemand("attribute", selector=names)),
                )
                for projection in owner.parameters
            ),
        )
        native_targets = frozenset(
            target
            for target in owner.targets
            if self.sources is None
            or (target not in self.sources.definitions and target not in self.sources.records)
        )
        native_owner = replace(owner, targets=native_targets)
        for name in names.strings:
            sourced = self.sources.attribute(owner, name, scope) if self.sources else None
            if sourced is not None:
                value = value.join(sourced)
            for target in native_targets:
                value = value.join(scope.member(f"{target}.{name}"))
            if owner.aggregates or owner.path:
                value = value.join(
                    BindingValue(methods=frozenset({ReceiverMethod(native_owner, name)}))
                )
        if not names.strings or names.unknown or names.deferred:
            value = value.join(
                BindingValue(
                    selection=frozenset(
                        target for target in owner.targets if self.module_kinds(target)
                    )
                )
            )
        if self.sources is not None and (owner.fields is not None or native_owner.targets):
            self.sources.invocations.note_member(
                owner, MemberDemand("attribute", selector=names), value, scope
            )
        return value

    def consume(
        self,
        kind: Literal["import", "executable", "value"],
        value: BindingValue,
        node: ast.expr,
        scope: BindingScope,
        target: str,
        *,
        executable: BindingValue | None = None,
    ) -> None:
        """Observe executable selection separately from process-visible arguments."""
        if self.sources is not None and self.sources.invocations.summarizing:
            summary = self.sources.invocations.summaries[self.sources.invocations.summarizing[-1]]
            summary.record(
                EffectCall(
                    BindingValue(targets=frozenset({target})),
                    (executable or BindingValue(unknown=True), value)
                    if target == "os.execv"
                    else (value,),
                    {"executable": executable}
                    if executable is not None and target != "os.execv"
                    else {},
                    node,
                    self.path,
                    scope.name,
                )
            )
        if self.sources is not None:
            value = self.sources.invocations.resolve(value, scope, self)
            if executable is not None:
                executable = self.sources.invocations.resolve(executable, scope, self)
        if kind == "executable":
            head = (
                executable if executable is not None else value.items[0] if value.items else value
            )
            if executable is None:
                head = replace(
                    head,
                    unknown=head.unknown or value.unknown,
                    deferred=head.deferred or value.deferred,
                )
            selected = replace(head, strings=head.strings | head.executable_origins)
            invocation = (
                replace(value, items=(selected, *value.items[1:]))
                if value.items is not None
                else selected
                if executable is not None
                else value
            )
            commands = command_tokens(invocation)
            for command in commands:
                self.executables.update(
                    command_executables(command, self.npm_scripts, module_imports=self.imports)
                )
            self.executables.update(head.executable_origins)
            known = bool(commands or head.executable_origins)
        else:
            (self.imports if kind == "import" else self.inputs).update(
                item.partition(".")[0] if kind == "import" else item for item in value.strings
            )
            known, head = bool(value.strings), value
        if head.unknown or (not known and not (head.deferred or head.parameters)):
            self.residual(kind, "unknown", node, scope, target, "value_not_resolved")
        elif head.deferred or head.parameters:
            self.residual(kind, "deferred", node, scope, target, "runtime_argument")

    def residual(
        self,
        kind: Literal["import", "executable", "value"],
        state: Literal["unknown", "deferred"],
        node: ast.AST,
        scope: BindingScope,
        target: str,
        reason: str,
    ) -> None:
        """Attach uncertainty to the affected program point and obligation."""
        self.uncertainties.append(
            ReferenceUncertainty(
                kind,
                state,
                self.path,
                scope.name,
                getattr(node, "lineno", 0),
                getattr(node, "col_offset", 0),
                target,
                reason,
            )
        )
