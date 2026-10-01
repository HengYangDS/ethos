"""Bind one finite source inventory through the existing lexical flow interpreter."""

from __future__ import annotations

import ast
import symtable
from collections import defaultdict
from collections import deque
from dataclasses import dataclass
from dataclasses import replace
from typing import TYPE_CHECKING

from ethos.repository.policy.references.python.binding import PythonFlow
from ethos.repository.policy.references.python.functions import FunctionObservation
from ethos.repository.policy.references.python.functions import call_arguments
from ethos.repository.policy.references.python.functions import local_call
from ethos.repository.policy.references.python.native import ENVIRONMENT_TARGETS
from ethos.repository.policy.references.python.native import PROCESS_TARGETS
from ethos.repository.policy.references.python.scope import Scope
from ethos.repository.policy.references.python.values import UNKNOWN
from ethos.repository.policy.references.python.values import BoundCall
from ethos.repository.policy.references.python.values import FormalInput
from ethos.repository.policy.references.python.values import Imported
from ethos.repository.policy.references.python.values import Literal
from ethos.repository.policy.references.python.values import LocalFunction
from ethos.repository.policy.references.python.values import MappingMethod
from ethos.repository.policy.references.python.values import Unknown
from ethos.repository.policy.references.python.values import Value
from ethos.repository.policy.references.python.values import attribute
from ethos.repository.policy.references.python.values import join
from ethos.repository.policy.references.python_syntax import complete_python_tree
from ethos.repository.policy.references.python_syntax import import_module
from ethos.repository.policy.references.python_syntax import module_name

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Mapping


@dataclass(frozen=True, slots=True)
class PythonBindings:
    """Calls retain their source owner even when another module supplies actual inputs."""

    imports: frozenset[str]
    calls: tuple[BoundCall, ...]
    compiler_valid: bool
    unresolved: frozenset[str] = frozenset()


class PythonProgram:
    """Resolve current first-party modules without executing them or storing a graph."""

    def __init__(self, sources: Mapping[str, tuple[ast.AST, str]]) -> None:
        self.sources = sources
        self.modules: dict[str, tuple[str, ...]] = {}
        for path in sources:
            name = module_name(path)
            self.modules[name] = (*self.modules.get(name, ()), path)
        self.flows: dict[str, tuple[PythonFlow, Scope]] = {}
        self.invalid: set[str] = set()
        self.loading: set[str] = set()
        self.invocations = 0
        self.depth = 0
        self.observations: dict[tuple[LocalFunction, int], FunctionObservation] = {}
        self.observing: set[LocalFunction] = set()

    def bind(self, selected: Iterable[str] | None = None) -> dict[str, PythonBindings]:
        """Complete all source observations before freezing any consumer's view."""
        selected_paths = tuple(self.sources if selected is None else selected)
        for path in selected_paths:
            if path not in self.sources:
                continue
            self.load(path)
        completed = set()
        while pending := self.flows.keys() - completed:
            for path in sorted(pending):
                self.finish(self.flows[path][0])
                completed.add(path)
        impacts, names = self.consumer_dependencies()
        return {
            path: PythonBindings(
                imports=frozenset(name.partition(".")[0] for name in _import_origins(tree)),
                calls=tuple(
                    replace(
                        call,
                        targets=frozenset(
                            Unknown(
                                atom.origins
                                | frozenset(
                                    origin
                                    for name in atom.origins
                                    for origin in names.get(name, ())
                                )
                            )
                            if isinstance(atom, Unknown)
                            else atom
                            for atom in call.targets
                        ),
                    )
                    for call in dict.fromkeys(self.flows[path][0].calls)
                )
                if path in self.flows
                else (),
                compiler_valid=path not in self.invalid,
                unresolved=frozenset(
                    origin
                    for name in self.flows[path][0].unresolved
                    for origin in names.get(name, (name,))
                )
                | frozenset(
                    origin
                    for identity in self.flows[path][0].incomplete
                    for origin in impacts.get(identity, ())
                )
                if path in self.flows
                else frozenset(),
            )
            for path, (tree, _) in self.sources.items()
            if path in self.flows or path in self.invalid
        }

    def load(self, path: str) -> Scope | None:
        """Observe native import initialization, including bounded partial cyclic modules."""
        if path in self.flows:
            return self.flows[path][1]
        if path in self.invalid or len(self.loading) >= 32:
            return None
        tree, text = self.sources[path]
        try:
            table = symtable.symtable(text, path or "<reference-observation>", "exec")
        except (SyntaxError, ValueError):
            self.invalid.add(path)
            return None
        flow = PythonFlow(
            table,
            path=path,
            resolve=lambda name: self.resolve(path, name),
            normalize=self.normalize,
            invoke=lambda identity, call, caller: self.invoke(path, identity, call, caller),
            write_member=lambda name, value: self.write_member(path, name, value),
        )
        scope = Scope(table)
        self.flows[path] = flow, scope
        self.loading.add(path)
        try:
            flow.block(list(tree.body) if isinstance(tree, ast.Module) else [], scope)
        finally:
            self.loading.remove(path)
        return scope

    def write_member(self, source: str, name: str, value: Value) -> None:
        """Source-owned module writes invalidate reaching bindings, not prior call evidence."""
        if self.flows[source][0].definition_only:
            return
        module, _, member = name.rpartition(".")
        paths = self.modules.get(module, ())
        if len(paths) == 1 and (scope := self.load(paths[0])) is not None:
            scope.store(member, value)

    def resolve(self, source: str, name: str) -> Value:
        """A source-owned symbol uses its binding, never an imported spelling guess."""
        if name.startswith("."):
            level = len(name) - len(name.lstrip("."))
            tail = name[level:]
            package = import_module(source, ast.ImportFrom(module=None, names=[], level=level))
            if not package:
                return frozenset({Imported(name)})
            name = ".".join(filter(None, (package, tail)))
        parts = name.split(".")
        candidates = [
            module
            for end in range(len(parts), 0, -1)
            if (module := ".".join(parts[:end])) in self.modules
        ]
        if not candidates:
            return frozenset({Imported(name)})
        module = candidates[0]
        paths = self.modules[module]
        if len(paths) != 1:
            return frozenset({Unknown(frozenset({name}))})
        if (scope := self.load(paths[0])) is None:
            return frozenset({Unknown(frozenset({"unavailable_source", name}))})
        if name == module:
            return frozenset({Imported(name)})
        member, *attributes = name[len(module) + 1 :].split(".")
        value = scope.lookup(member)
        for part in attributes:
            value = attribute(value, part)
        if any(isinstance(atom, Unknown) for atom in value):
            value |= frozenset({Unknown(frozenset({name}))})
        return value

    def normalize(self, values: Value) -> Value:
        """Resolve native-produced imported callees; unknown impacts are derived once later."""
        return join(
            self.resolve("", atom.name) if isinstance(atom, Imported) else frozenset({atom})
            for atom in values
        )

    def invoke(
        self, source: str, identity: LocalFunction, call: BoundCall, caller: Scope | None
    ) -> Value:
        """Definition relations compose; actual calls retain fresh program-point effects."""
        if identity.path not in self.flows:
            self.flows[source][0].incomplete.add(identity)
            return UNKNOWN
        flow = self.flows[identity.path][0]
        if self.flows[source][0].definition_only:
            observation = self.definition(identity).bind(
                identity, call_arguments(flow.functions[identity][2], call)
            )
            self.flows[source][0].calls.extend(observation.calls)
            if caller is not None:
                caller.invalidate(observation.invalidated)
            return observation.result
        if self.depth == 0:
            self.invocations = 0
        if self.depth >= 32 or self.invocations >= 1024:
            self.flows[source][0].incomplete.add(identity)
            return UNKNOWN
        start = len(flow.calls)
        self.invocations += 1
        self.depth += 1
        try:
            return local_call(flow, identity, call, caller)
        finally:
            self.depth -= 1
            if source != identity.path:
                self.flows[source][0].calls.extend(flow.calls[start:])

    def definition(self, identity: LocalFunction) -> FunctionObservation:
        """Observe a body once in its lexical definition context, without an invocation."""
        flow = self.flows[identity.path][0]
        node, parent, signature = flow.functions[identity]
        key = identity, id(parent)
        if key in self.observations:
            return self.observations[key]
        if identity in self.observing or len(self.observing) >= 32:
            flow.incomplete.add(identity)
            return FunctionObservation(UNKNOWN, (), frozenset())
        self.observing.add(identity)
        scope = Scope(flow.tables[(node.name, node.lineno)], parent.snapshot())
        scope.values.update(
            {
                name: UNKNOWN
                if node.decorator_list or parent.table.get_type() == "class"
                else frozenset({FormalInput(identity.name, identity.line, name, identity.path)})
                for name in signature.parameters
            }
        )
        start = len(flow.calls)
        previous = flow.current, flow.definition_only
        flow.current, flow.definition_only = identity, True
        flow.returns.append([])
        try:
            falls_through = flow.block(node.body, scope)
            values = flow.returns[-1]
            if falls_through:
                values.append(frozenset({Literal(None)}))
            result = UNKNOWN if node.decorator_list else join(values) or UNKNOWN
            observation = FunctionObservation(result, tuple(flow.calls[start:]), scope.invalidated)
            self.observations[key] = observation
            return observation
        finally:
            del flow.calls[start:]
            flow.returns.pop()
            flow.current, flow.definition_only = previous
            self.observing.remove(identity)

    def function_groups(self) -> dict[str, set[LocalFunction]]:
        """Index actual source-owned definitions for ambiguous and dynamic relation queries."""
        groups: dict[str, set[LocalFunction]] = defaultdict(set)
        for path, (flow, _) in self.flows.items():
            module = module_name(path)
            for identity, (_, parent, _) in flow.functions.items():
                groups[module].add(identity)
                qualifier = (
                    f"{module}.{parent.table.get_name()}"
                    if parent.table.get_type() == "class"
                    else module
                )
                groups[f"{qualifier}.{identity.name}"].add(identity)
                if qualifier != module:
                    groups[qualifier].add(identity)
        return dict(groups)

    @staticmethod
    def consumer_transfer(
        call: BoundCall,
        groups: dict[str, set[LocalFunction]],
        impacts: dict[LocalFunction, set[str]],
        callers: dict[LocalFunction, set[LocalFunction]],
    ) -> None:
        """One bound call contributes native consumers or first-party dependency edges."""
        owner = call.owner
        if owner is None:
            return
        for target in call.targets:
            if isinstance(target, LocalFunction):
                callers[target].add(owner)
            elif isinstance(target, Imported) and target in PROCESS_TARGETS | ENVIRONMENT_TARGETS:
                impacts[owner].add(target.name)
            elif isinstance(target, MappingMethod) and target.owner.environment_entries:
                impacts[owner].add("os.environ")
            elif isinstance(target, Unknown):
                for name in target.origins:
                    if name in groups:
                        for callee in groups[name]:
                            callers[callee].add(owner)
                    else:
                        impacts[owner].add(name)

    def consumer_dependencies(
        self,
    ) -> tuple[dict[LocalFunction, set[str]], dict[str, frozenset[str]]]:
        """Derive actual callable-to-consumer reachability, not whole-module import effects."""
        groups = self.function_groups()
        impacts: dict[LocalFunction, set[str]] = defaultdict(set)
        callers: dict[LocalFunction, set[LocalFunction]] = defaultdict(set)
        for call in dict.fromkeys(call for flow, _ in self.flows.values() for call in flow.calls):
            if call.owner is not None:
                self.consumer_transfer(call, groups, impacts, callers)
        pending = deque(impacts)
        while pending:
            callee = pending.popleft()
            for caller in callers.get(callee, ()):
                added = impacts[callee] - impacts[caller]
                if added:
                    impacts[caller].update(added)
                    pending.append(caller)
        names = {
            name: frozenset(origin for identity in identities for origin in impacts[identity])
            for name, identities in groups.items()
        }
        return dict(impacts), names

    def finish(self, flow: PythonFlow) -> None:
        """Retain open definition obligations and defaults, never fabricate an execution."""
        while flow.deferred:
            node, scope = flow.deferred.popleft()
            identity = LocalFunction(
                "lambda" if isinstance(node, ast.Lambda) else node.name, node.lineno, flow.path
            )
            if isinstance(node, ast.Lambda):
                for symbol in scope.table.get_symbols():
                    if symbol.is_parameter():
                        scope.values[symbol.get_name()] = UNKNOWN
                previous = flow.current, flow.definition_only
                flow.current, flow.definition_only = identity, True
                try:
                    flow.expression(node.body, scope)
                finally:
                    flow.current, flow.definition_only = previous
                continue
            _, parent, signature = flow.functions[identity]
            values = {
                name: (
                    UNKNOWN
                    if node.decorator_list or parent.table.get_type() == "class"
                    else frozenset({FormalInput(identity.name, identity.line, name, flow.path)})
                )
                | (parameter.default if isinstance(parameter.default, frozenset) else frozenset())
                for name, parameter in signature.parameters.items()
            }
            flow.calls.extend(self.definition(identity).bind(identity, values).calls)


def _import_origins(tree: ast.AST) -> frozenset[str]:
    """Import syntax establishes dependencies, not a resolved effect or callee."""
    return frozenset(
        name
        for node in ast.walk(tree)
        for name in (
            tuple(alias.name for alias in node.names)
            if isinstance(node, ast.Import)
            else (node.module,)
            if isinstance(node, ast.ImportFrom) and node.module
            else ()
        )
    )


def bind_python(tree: ast.AST, text: str) -> PythonBindings:
    """Bind an isolated syntax carrier through the same current-source interpreter."""
    return PythonProgram({"": (tree, text)}).bind()[""]


def bind_repository_python(
    files: Mapping[str, str],
    *,
    parsed_files: Mapping[str, ast.AST | None] | None = None,
    selected: Iterable[str] | None = None,
) -> dict[str, PythonBindings]:
    """Share exact source inputs; failed source binding stays attributable to its callers."""
    sources = {}
    invalid = set()
    for path, text in files.items():
        if path.endswith(".py"):
            tree = (
                parsed_files.get(path) if parsed_files is not None else complete_python_tree(text)
            )
            if tree is not None:
                sources[path] = tree, text
            else:
                sources[path] = ast.Module(body=[], type_ignores=[]), text
                invalid.add(path)
    program = PythonProgram(sources)
    program.invalid.update(invalid)
    return program.bind(selected)
