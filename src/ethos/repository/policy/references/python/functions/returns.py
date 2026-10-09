"""Bind exact source invocations to bounded successful returns and native effects."""

from __future__ import annotations

import ast
import inspect
from dataclasses import dataclass
from dataclasses import field
from dataclasses import replace
from typing import TYPE_CHECKING

from ethos.repository.policy.references.python.bindings import BindingValue
from ethos.repository.policy.references.python.bindings import MemberDemand
from ethos.repository.policy.references.python.functions.classes import PythonClasses
from ethos.repository.policy.references.python.functions.invocation import PythonInvocations
from ethos.repository.policy.references.python.syntax import module_name

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Mapping

    from ethos.repository.policy.references.python.effects import PythonConsumption
    from ethos.repository.policy.references.python.flow import PythonReferenceFlow
    from ethos.repository.policy.references.python.scope import BindingScope


@dataclass(frozen=True, slots=True)
class FunctionDefinition:
    """The actual definition, evaluated defaults and lexical environment."""

    key: str
    node: ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda
    flow: PythonReferenceFlow
    parent: BindingScope
    signature: inspect.Signature
    receiver: str = ""
    binding: str = ""


@dataclass(frozen=True, slots=True)
class RecordDefinition:
    """A proven native generated constructor and its field-to-argument relation."""

    signature: inspect.Signature
    names: tuple[str, ...]
    positional: bool
    owner: BindingScope


@dataclass(slots=True)
class PythonSourceReturns:
    """One exact observation owns source lookup; calls neither execute nor authorize."""

    files: Mapping[str, str]
    trees: Mapping[str, ast.AST | None]
    factory: Callable[..., PythonReferenceFlow]
    definitions: dict[str, FunctionDefinition] = field(default_factory=dict)
    records: dict[str, RecordDefinition] = field(default_factory=dict)
    classes: PythonClasses = field(init=False)
    modules: dict[str, BindingScope] = field(default_factory=dict)
    module_paths: dict[str, str | None] = field(init=False)
    preparing: set[str] = field(default_factory=set)
    invocations: PythonInvocations = field(init=False)

    def __post_init__(self) -> None:
        """Resolve exact source modules once; collisions remain explicitly ambiguous."""
        self.classes = PythonClasses(self)
        self.invocations = PythonInvocations(self)
        self.module_paths = {}
        for path in self.trees:
            name = module_name(path)
            self.module_paths[name] = None if name in self.module_paths else path

    @staticmethod
    def signature(
        arguments: ast.arguments,
        defaults: tuple[BindingValue, ...],
        keyword_defaults: tuple[BindingValue | None, ...],
    ) -> inspect.Signature:
        """Use native Python binding without invoking source or trusting annotations."""
        parameters = []
        positional = (*arguments.posonlyargs, *arguments.args)
        defaults_at = len(positional) - len(defaults)
        for index, argument in enumerate(positional):
            kind = (
                inspect.Parameter.POSITIONAL_ONLY
                if index < len(arguments.posonlyargs)
                else inspect.Parameter.POSITIONAL_OR_KEYWORD
            )
            default = (
                defaults[index - defaults_at] if index >= defaults_at else inspect.Parameter.empty
            )
            parameters.append(inspect.Parameter(argument.arg, kind, default=default))
        if arguments.vararg:
            parameters.append(
                inspect.Parameter(arguments.vararg.arg, inspect.Parameter.VAR_POSITIONAL)
            )
        for argument, default in zip(arguments.kwonlyargs, keyword_defaults, strict=True):
            parameters.append(
                inspect.Parameter(
                    argument.arg,
                    inspect.Parameter.KEYWORD_ONLY,
                    default=default if default is not None else inspect.Parameter.empty,
                )
            )
        if arguments.kwarg:
            parameters.append(inspect.Parameter(arguments.kwarg.arg, inspect.Parameter.VAR_KEYWORD))
        return inspect.Signature(parameters)

    def definition(
        self,
        flow: PythonReferenceFlow,
        node: ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda,
        parent: BindingScope,
        defaults: tuple[BindingValue, ...],
        keyword_defaults: tuple[BindingValue | None, ...],
        *,
        receiver: str = "",
        binding: str = "",
    ) -> BindingValue:
        """Capture a distinct actual callable, including nested invocation closures."""
        name = "<lambda>" if isinstance(node, ast.Lambda) else node.name
        key = f"{flow.path}:{node.lineno}:{node.col_offset}:{name}:{len(self.definitions)}"
        self.definitions[key] = FunctionDefinition(
            key,
            node,
            flow,
            parent,
            self.signature(node.args, defaults, keyword_defaults),
            receiver,
            binding,
        )
        return BindingValue(targets=frozenset({key}))

    @staticmethod
    def record_kind(flow: PythonReferenceFlow, node: ast.ClassDef, parent: BindingScope) -> str:
        """Only exact native generators with modeled initialization establish fields."""
        if node.keywords:
            return ""
        if (
            len(node.bases) == 1
            and not node.decorator_list
            and flow.expression(node.bases[0], parent).targets == frozenset({"typing.NamedTuple"})
        ):
            return "named"
        if node.bases or len(node.decorator_list) != 1:
            return ""
        decorator = node.decorator_list[0]
        if not isinstance(decorator, ast.Call) or flow.expression(
            decorator.func, parent
        ).targets != frozenset({"dataclasses.dataclass"}):
            return ""
        options = {item.arg: item.value for item in decorator.keywords}
        frozen = options.get("frozen")
        if (
            not isinstance(frozen, ast.Constant)
            or frozen.value is not True
            or any(
                name
                not in {
                    "frozen",
                    "slots",
                    "eq",
                    "repr",
                    "order",
                    "unsafe_hash",
                    "match_args",
                }
                for name in options
            )
        ):
            return ""
        return "frozen"

    def record(
        self, flow: PythonReferenceFlow, node: ast.ClassDef, parent: BindingScope
    ) -> BindingValue:
        """Generated fields preserve values; names and field types grant no native trust."""
        kind = self.record_kind(flow, node, parent)
        forbidden = {
            "__new__",
            "__init__",
            "__getattribute__",
            "__getattr__",
            "__setattr__",
            "__delattr__",
            "__post_init__",
        }
        if not kind or any(
            isinstance(item, ast.FunctionDef) and item.name in forbidden for item in node.body
        ):
            return BindingValue(local=True)
        declarations = [
            item
            for item in node.body
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
        ]
        names = tuple(item.target.id for item in declarations if isinstance(item.target, ast.Name))
        if any(isinstance(item, ast.FunctionDef) and item.name in names for item in node.body):
            return BindingValue(local=True)
        parameters = [
            inspect.Parameter(
                item.target.id,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                default=flow.expression(item.value, parent)
                if item.value is not None
                else inspect.Parameter.empty,
            )
            for item in declarations
            if isinstance(item.target, ast.Name)
        ]
        try:
            signature = inspect.Signature(parameters)
        except ValueError:
            return BindingValue(unknown=True)
        key = f"{flow.path}:{node.lineno}:{node.col_offset}:{node.name}:{len(self.records)}"
        self.records[key] = RecordDefinition(signature, names, kind == "named", parent)
        for item in node.body:
            if not isinstance(item, ast.FunctionDef) or len(item.decorator_list) != 1:
                continue
            if flow.expression(item.decorator_list[0], parent).targets != frozenset(
                {"builtins.classmethod"}
            ):
                continue
            method = self.definition(
                flow,
                item,
                parent,
                tuple(flow.expression(value, parent) for value in item.args.defaults),
                tuple(
                    flow.expression(value, parent) if value is not None else None
                    for value in item.args.kw_defaults
                ),
                receiver=key,
            )
            member = f"{key}.{item.name}"
            parent.members[member] = parent.member_history[member] = method
        return BindingValue(targets=frozenset({key}))

    def imported(self, target: str) -> BindingValue | None:
        """Resolve actual selected exports; absent, cyclic and replaced values stay opaque."""
        parts = target.split(".")
        for length in range(len(parts) - 1, 0, -1):
            module = ".".join(parts[:length])
            if module not in self.module_paths:
                continue
            path = self.module_paths[module]
            if path is None or module in self.preparing:
                return BindingValue(unknown=True)
            if module not in self.modules:
                tree = self.trees[path]
                if not isinstance(tree, ast.Module):
                    return BindingValue(unknown=True)
                self.preparing.add(module)
                try:
                    flow = self.factory(path, {}, sources=self)
                    self.modules[module] = flow.initialize(tree, source=self.files[path])
                finally:
                    self.preparing.remove(module)
            value = self.modules[module].lookup(parts[length])
            for name in parts[length + 1 :]:
                value = self.attribute(value, name, self.modules[module]) or BindingValue(
                    unknown=True
                )
            return value
        return None

    def attribute(self, owner: BindingValue, name: str, scope: BindingScope) -> BindingValue | None:
        """Field projection follows reachable record state and the actual receiver identity."""
        owner = scope.resolve(owner)
        if owner.projections:
            return BindingValue(
                projections=frozenset(
                    replace(item, members=(*item.members, MemberDemand("attribute", key=name)))
                    for item in owner.projections
                ),
                unknown=owner.unknown,
                deferred=owner.deferred,
            )
        if owner.fields is not None:
            value = dict(owner.fields).get(name)
            if value is not None:
                if name in owner.optional_fields:
                    for target in owner.instance_types:
                        value = value.join(self.classes.member(target, name, owner, scope))
                if owner.instance_types and (
                    owner.unknown
                    or owner.local
                    or owner.deferred
                    or not self.classes.instance_storage(owner, name, scope)
                ):
                    return replace(
                        value,
                        unknown=True,
                        selection=value.selection | owner.instance_types,
                    )
                return replace(
                    value,
                    unknown=owner.unknown or value.unknown,
                    deferred=owner.deferred or value.deferred,
                )
        result = None
        for target in owner.instance_types:
            value = self.classes.member(target, name, owner, scope)
            result = value if result is None else result.join(value)
        for target in owner.targets:
            value = self.target_member(target, name, owner, scope)
            if value is not None:
                result = value if result is None else result.join(value)
        return (
            result.join(BindingValue(unknown=True))
            if result is not None and (owner.unknown or owner.local or owner.deferred)
            else result
        )

    def target_member(
        self, target: str, name: str, owner: BindingValue, scope: BindingScope
    ) -> BindingValue | None:
        """Resolve a native class, generated record or imported owner at its actual namespace."""
        if target in self.classes.definitions:
            return self.classes.member(target, name, owner, scope)
        if target in self.records:
            member = f"{target}.{name}"
            value = scope.member(member)
            return (
                self.records[target].owner.member(member)
                if value.targets == frozenset({member})
                else value
            )
        resolved = self.imported(target)
        return (
            self.attribute(resolved, name, scope)
            if resolved is not None and resolved != owner
            else None
        )

    def call(
        self,
        callee: BindingValue,
        args: tuple[BindingValue, ...],
        keywords: dict[str | None, BindingValue],
        node: ast.Call,
        scope: BindingScope,
        result: PythonConsumption,
    ) -> BindingValue | None:
        """Join alternative outgoing effects without dropping native or opaque branches."""
        selected = self.call_identity(callee)
        targets = selected.targets & (
            self.definitions.keys() | self.records.keys() | self.classes.definitions.keys()
        )
        methods = frozenset(
            method for method in selected.methods if method.name in self.definitions
        )
        if not targets and not methods:
            return None
        other = replace(
            selected, targets=selected.targets - targets, methods=selected.methods - methods
        )
        has_other = bool(
            other.targets
            or other.parameters
            or other.methods
            or other.unknown
            or other.local
            or other.deferred
            or other.selection
        )
        branches, returned = [], BindingValue()
        for target in targets:
            branch = scope.fork() if has_other or len(targets) + len(methods) > 1 else scope
            value = self.source_call(
                BindingValue(targets=frozenset({target})), args, keywords, node, branch, result
            )
            returned = returned.join(value)
            branches.append(branch)
        for method in methods:
            branch = scope.fork() if has_other or len(targets) + len(methods) > 1 else scope
            value = self.invocations.request(
                self.definitions[method.name],
                (method.receiver, *args),
                keywords,
                node,
                branch,
                result,
            )
            returned = returned.join(value)
            branches.append(branch)
        if has_other:
            branch = scope.fork()
            returned = returned.join(result.call(other, args, keywords, node, branch))
            branches.append(branch)
        if len(branches) > 1:
            scope.merge(*branches)
        return returned

    def call_identity(self, callee: BindingValue) -> BindingValue:
        """Resolve source exports while retaining every native and opaque alternative."""
        resolved = replace(callee, targets=frozenset())
        for target in callee.targets:
            value = (
                self.imported(target)
                if target not in self.definitions
                and target not in self.records
                and target not in self.classes.definitions
                else None
            )
            resolved = resolved.join(value or BindingValue(targets=frozenset({target})))
        return resolved

    def source_call(
        self,
        callee: BindingValue,
        args: tuple[BindingValue, ...],
        keywords: dict[str | None, BindingValue],
        node: ast.Call,
        scope: BindingScope,
        result: PythonConsumption,
    ) -> BindingValue:
        """Keep each possible definition and unknown alternative without selecting a winner."""
        returned = BindingValue(unknown=callee.unknown or callee.local or callee.deferred)
        for target in callee.targets:
            if target in self.records:
                value = self.construct(self.records[target], args, keywords, scope, node)
            elif target in self.classes.definitions:
                value = self.classes.construct(target, args, keywords, scope, node, result)
            elif target in self.definitions:
                definition = self.definitions[target]
                actual = (
                    (BindingValue(targets=frozenset({definition.receiver})), *args)
                    if definition.receiver
                    else args
                )
                value = self.invocations.request(definition, actual, keywords, node, scope, result)
            else:
                value = BindingValue(unknown=True)
            returned = returned.join(value)
        return returned

    @staticmethod
    def construct(
        record: RecordDefinition,
        args: tuple[BindingValue, ...],
        keywords: dict[str | None, BindingValue],
        scope: BindingScope,
        node: ast.Call,
    ) -> BindingValue:
        """A successful trailing expansion preserves only fields before its first unknown."""
        if None in keywords:
            return BindingValue(unknown=True)
        spread = next((index for index, value in enumerate(args) if value.spread), None)
        if spread is not None:
            values = tuple(
                (name, args[index] if index < spread else BindingValue(unknown=True))
                for index, name in enumerate(record.names)
            )
        else:
            try:
                bound = record.signature.bind(
                    *args, **{name: value for name, value in keywords.items() if name is not None}
                )
            except TypeError:
                return BindingValue(unknown=True)
            bound.apply_defaults()
            values = tuple((name, bound.arguments[name]) for name in record.names)
        value = BindingValue(
            fields=values,
            items=tuple(item for _, item in values) if record.positional else None,
            ordered=record.positional,
        )
        return scope.aggregate(value, node)
