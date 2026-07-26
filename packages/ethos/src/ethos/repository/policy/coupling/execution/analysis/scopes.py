"""Lexical analysis state and replay for executable coupling collection."""

from __future__ import annotations

import ast

from ethos.repository.policy.coupling.execution.aliases.core import SHADOWED_GETATTR_ALIAS
from ethos.repository.policy.coupling.execution.aliases.core import callable_reference
from ethos.repository.policy.coupling.execution.aliases.core import module_reference
from ethos.repository.policy.coupling.execution.aliases.keys import alias_key
from ethos.repository.policy.coupling.execution.analysis.replay import AliasState
from ethos.repository.policy.coupling.execution.analysis.replay import CallableNode
from ethos.repository.policy.coupling.execution.analysis.replay import ExecutionReplayState
from ethos.repository.policy.coupling.execution.analysis.replay import ReferencePair
from ethos.repository.policy.coupling.execution.analysis.replay import argument_names
from ethos.repository.policy.coupling.execution.analysis.replay import function_scope_bindings
from ethos.repository.policy.coupling.execution.analysis.replay import merge_aliases
from ethos.repository.policy.coupling.execution.analysis.replay import merge_instance_owners

AliasPair = tuple[dict[str, frozenset[str]], dict[str, frozenset[str]]]


class ExecutionScopeTraversal(ExecutionReplayState, ast.NodeVisitor):
    """Maintain lexical alias state while replaying deferred executable calls."""

    def __init__(self) -> None:
        self.module_aliases: dict[str, frozenset[str]] = {}
        self.function_aliases: dict[str, frozenset[str]] = {}
        self._class_module_aliases: dict[str, frozenset[str]] = {}
        self._class_function_aliases: dict[str, frozenset[str]] = {}
        self._instance_owners: dict[str, str] = {}
        self._method_owners: dict[int, tuple[str, str]] = {}
        self._method_effects: dict[tuple[str, str], dict[str, ReferencePair]] = {}
        self._class_callables: dict[str, frozenset[CallableNode]] = {}
        self._class_methods: dict[tuple[str, str], frozenset[CallableNode]] = {}
        self._callable_default_bindings: dict[int, dict[str, ReferencePair]] = {}
        self._method_context: list[tuple[str, str] | None] = [None]
        self._deferred_callables: list[list[CallableNode]] = [[]]
        self._class_scopes = [False]
        self._class_owners: list[str | None] = [None]
        self._named_callables: list[dict[str, frozenset[CallableNode]]] = [{}]
        self._scope_local_names: list[frozenset[str]] = [frozenset()]
        self._scope_global_names: list[frozenset[str]] = [frozenset()]
        self._scope_nonlocal_names: list[frozenset[str]] = [frozenset()]
        self._propagating_scope_writes: list[bool] = []
        self._global_module_aliases: dict[str, frozenset[str]] = {}
        self._global_function_aliases: dict[str, frozenset[str]] = {}
        self._replayed_callables: set[tuple[object, ...]] = set()
        self._inline_lambdas: set[int] = set()
        self.calls: list[tuple[ast.Call, str]] = []
        self._seen_call_ids: set[int] = set()

    def _visit_try(self, node: ast.Try | ast.TryStar) -> None:
        entry = self._branch_snapshot()
        self._visit_statements(node.body)
        normal = self._branch_snapshot()
        if node.orelse:
            self._visit_statements(node.orelse)
            normal = self._branch_snapshot()
        handler_entry = self._merged_branch_snapshot((entry, normal))
        states = [entry, normal]
        for handler in node.handlers:
            self._restore_branch(handler_entry)
            if handler.type is not None:
                self.visit(handler.type)
            if handler.name is not None:
                self._rebind(handler.name)
            self._visit_statements(handler.body)
            states.append(self._branch_snapshot())
        self._restore_branch(self._merged_branch_snapshot(tuple(states)))
        self._visit_statements(node.finalbody)

    def _visit_loop(
        self,
        iterable: ast.expr | None,
        target: ast.expr | None,
        body: list[ast.stmt],
        orelse: list[ast.stmt],
    ) -> None:
        if iterable is not None:
            self.visit(iterable)
        entry = self._branch_snapshot()
        if target is not None:
            self._bind_iterable_target(target, iterable)
        self._visit_statements(body)
        self._restore_branch(self._merged_branch_snapshot((entry, self._branch_snapshot())))
        self._visit_statements(orelse)

    def _visit_with(self, items: list[ast.withitem], body: list[ast.stmt]) -> None:
        for item in items:
            self.visit(item.context_expr)
            if item.optional_vars is not None:
                self._clear_target_aliases(item.optional_vars)
        self._visit_statements(body)

    def _bind_iterable_target(
        self,
        target: ast.expr,
        iterable: ast.expr | None,
    ) -> None:
        values = literal_iterable_values(iterable)
        if not values:
            self._clear_target_aliases(target)
            return
        key = alias_key(target)
        if key is None:
            self._clear_target_aliases(target)
            return
        source_modules, source_functions = self._resolution_aliases()
        modules = frozenset().union(
            *(module_reference(value, source_modules, source_functions) for value in values)
        )
        functions = frozenset().union(
            *(callable_reference(value, source_modules, source_functions) for value in values)
        )
        self._rebind(key, modules=modules, functions=functions)

    def _clear_target_aliases(self, target: ast.expr) -> None:
        key = alias_key(target)
        if key is not None:
            self._rebind(key)
        elif isinstance(target, (ast.List, ast.Tuple)):
            for element in target.elts:
                self._clear_target_aliases(element)

    def _visit_comprehension(
        self,
        generators: list[ast.comprehension],
        expressions: tuple[ast.expr, ...],
    ) -> None:
        snapshot = self._snapshot()
        try:
            for generator in generators:
                self.visit(generator.iter)
                self._bind_iterable_target(generator.target, generator.iter)
                for condition in generator.ifs:
                    self.visit(condition)
            for expression in expressions:
                self.visit(expression)
        finally:
            self._restore(snapshot)

    def _visit_branches(
        self,
        branches: tuple[list[ast.stmt], ...],
        *,
        include_entry: bool,
    ) -> None:
        entry = self._branch_snapshot()
        states = [entry] if include_entry else []
        for statements in branches:
            self._restore_branch(entry)
            self._visit_statements(statements)
            states.append(self._branch_snapshot())
        self._restore_branch(self._merged_branch_snapshot(tuple(states)))

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        for decorator in node.decorator_list:
            self.visit(decorator)
        self._visit_argument_defaults(node.args)
        self._visit_argument_annotations(node.args)
        if node.returns is not None:
            self.visit(node.returns)
        modules, functions = self._resolution_aliases()
        self._callable_default_bindings[id(node)] = default_argument_bindings(
            node.args,
            modules,
            functions,
        )
        self._rebind(node.name)
        if owner := self._class_owners[-1]:
            self._method_owners[id(node)] = (owner, node.name)
            self._class_methods[(owner, node.name)] = frozenset({node})
            self._class_callables[f"{owner}.{node.name}"] = frozenset({node})
        else:
            self._set_named_callables(node.name, frozenset({node}))
        self._defer_callable(node)

    def _visit_argument_defaults(self, arguments: ast.arguments) -> None:
        for default in (*arguments.defaults, *arguments.kw_defaults):
            if default is not None:
                self.visit(default)

    def _visit_argument_annotations(self, arguments: ast.arguments) -> None:
        for argument in (*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs):
            if argument.annotation is not None:
                self.visit(argument.annotation)
        for argument in (arguments.vararg, arguments.kwarg):
            if argument is not None and argument.annotation is not None:
                self.visit(argument.annotation)

    def _visit_scoped_statements(
        self,
        statements: list[ast.stmt],
        arguments: ast.arguments | None,
        *,
        class_owner: str | None = None,
        argument_bindings: dict[str, ReferencePair] | None = None,
        capture_state: bool = False,
    ) -> AliasState | None:
        local_names, global_names, nonlocal_names = (
            function_scope_bindings(statements) if class_owner is None else (frozenset(),) * 3
        )
        argument_local_names = argument_names(arguments)
        scope_local_names = local_names.union(argument_local_names)
        snapshot = self._enter_scope(
            arguments,
            class_owner=class_owner,
            argument_bindings=argument_bindings,
            local_names=scope_local_names,
            global_names=global_names,
        )
        self._scope_nonlocal_names[-1] = nonlocal_names
        captured: AliasState | None = None
        try:
            if class_owner is None:
                for name in local_names.difference(argument_local_names):
                    self._rebind(name)
            self._visit_statements(statements)
            self._replay_deferred_callables()
            if capture_state:
                captured = self._snapshot()
        finally:
            self._leave_scope(snapshot)
        return captured

    def _visit_scoped_expression(
        self,
        expression: ast.expr,
        arguments: ast.arguments,
        *,
        argument_bindings: dict[str, ReferencePair] | None = None,
    ) -> AliasState | None:
        snapshot = self._enter_scope(arguments, argument_bindings=argument_bindings)
        try:
            self.visit(expression)
            self._replay_deferred_callables()
            return self._snapshot()
        finally:
            self._leave_scope(snapshot)

    def _visit_statements(self, statements: list[ast.stmt]) -> None:
        for statement in statements:
            self.visit(statement)

    def _enter_scope(
        self,
        arguments: ast.arguments | None,
        *,
        class_owner: str | None = None,
        argument_bindings: dict[str, ReferencePair] | None = None,
        local_names: frozenset[str] = frozenset(),
        global_names: frozenset[str] = frozenset(),
    ) -> AliasState:
        snapshot = self._snapshot()
        self.module_aliases = self.module_aliases.copy()
        self.function_aliases = self.function_aliases.copy()
        self._deferred_callables.append([])
        self._class_scopes.append(class_owner is not None)
        self._class_owners.append(class_owner)
        self._named_callables.append({})
        self._scope_local_names.append(local_names)
        self._scope_global_names.append(global_names)
        self._scope_nonlocal_names.append(frozenset())
        if arguments is not None:
            for argument in (*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs):
                self._rebind(argument.arg)
            if arguments.vararg is not None:
                self._rebind(arguments.vararg.arg)
            if arguments.kwarg is not None:
                self._rebind(arguments.kwarg.arg)
        for name, (modules, functions) in (argument_bindings or {}).items():
            self._rebind(name, modules=modules, functions=functions)
        return snapshot

    def _leave_scope(self, snapshot: AliasState) -> None:
        self._deferred_callables.pop()
        self._class_scopes.pop()
        self._class_owners.pop()
        self._named_callables.pop()
        self._scope_local_names.pop()
        self._scope_global_names.pop()
        self._scope_nonlocal_names.pop()
        self._restore(snapshot)

    def _defer_callable(self, node: CallableNode) -> None:
        scope_index = len(self._class_scopes) - 1
        while self._class_scopes[scope_index]:
            scope_index -= 1
        self._deferred_callables[scope_index].append(node)

    def _replay_deferred_callables(self) -> None:
        for node in tuple(self._deferred_callables[-1]):
            self._replay_callable(node)

    def _prepare_lambda(self, node: ast.Lambda) -> None:
        self._visit_argument_defaults(node.args)
        modules, functions = self._resolution_aliases()
        self._callable_default_bindings[id(node)] = default_argument_bindings(
            node.args,
            modules,
            functions,
        )

    def _resolution_aliases(self) -> AliasPair:
        modules = self.module_aliases.copy()
        functions = self.function_aliases.copy()
        for name, aliases in self._global_module_aliases.items():
            if self._global_alias_visible(name):
                modules[name] = aliases
        for name, aliases in self._global_function_aliases.items():
            if self._global_alias_visible(name):
                functions[name] = aliases
        return (
            merge_aliases((self._class_module_aliases, modules)),
            merge_aliases((self._class_function_aliases, functions)),
        )

    def _record_call(self, node: ast.Call, function: str) -> None:
        if id(node) not in self._seen_call_ids:
            self._seen_call_ids.add(id(node))
            self.calls.append((node, function))

    def _rebind(
        self,
        name: str,
        *,
        modules: frozenset[str] = frozenset(),
        functions: frozenset[str] = frozenset(),
    ) -> None:
        self.module_aliases.pop(name, None)
        self.function_aliases.pop(name, None)
        self._class_module_aliases.pop(name, None)
        self._class_function_aliases.pop(name, None)
        self._instance_owners.pop(name, None)
        self._class_callables.pop(name, None)
        self._clear_named_callables(name)
        if modules:
            self.module_aliases[name] = modules
        if functions:
            self.function_aliases[name] = functions
        elif name == "getattr":
            self.function_aliases[name] = frozenset({SHADOWED_GETATTR_ALIAS})
        if len(self._scope_local_names) == 1:
            self._set_global_alias_binding(
                name,
                self.module_aliases.get(name, frozenset()),
                self.function_aliases.get(name, frozenset()),
            )

    def _erase(self, name: str) -> None:
        self.module_aliases.pop(name, None)
        self.function_aliases.pop(name, None)
        self._class_module_aliases.pop(name, None)
        self._class_function_aliases.pop(name, None)
        self._instance_owners.pop(name, None)
        self._class_callables.pop(name, None)
        self._clear_named_callables(name)
        if len(self._scope_local_names) == 1:
            self._global_module_aliases.pop(name, None)
            self._global_function_aliases.pop(name, None)

    def _snapshot(self) -> AliasState:
        return (
            self.module_aliases.copy(),
            self.function_aliases.copy(),
            self._instance_owners.copy(),
        )

    def _restore(self, snapshot: AliasState) -> None:
        self.module_aliases = snapshot[0].copy()
        self.function_aliases = snapshot[1].copy()
        self._instance_owners = snapshot[2].copy()

    def _merged_snapshot(self, states: tuple[AliasState, ...]) -> AliasState:
        return (
            merge_aliases(tuple(state[0] for state in states)),
            merge_aliases(tuple(state[1] for state in states)),
            merge_instance_owners(tuple(state[2] for state in states)),
        )

    def _set_current_alias_binding(self, name: str, state: AliasState) -> None:
        self.module_aliases.pop(name, None)
        self.function_aliases.pop(name, None)
        if modules := state[0].get(name):
            self.module_aliases[name] = modules
        if functions := state[1].get(name):
            self.function_aliases[name] = functions

    def _set_global_alias_binding(
        self,
        name: str,
        modules: frozenset[str],
        functions: frozenset[str],
    ) -> None:
        self._global_module_aliases.pop(name, None)
        self._global_function_aliases.pop(name, None)
        if modules:
            self._global_module_aliases[name] = modules
        if functions:
            self._global_function_aliases[name] = functions
        if len(self._scope_local_names) == 1:
            self.module_aliases.pop(name, None)
            self.function_aliases.pop(name, None)
            if modules:
                self.module_aliases[name] = modules
            if functions:
                self.function_aliases[name] = functions

    def _global_alias_visible(self, name: str) -> bool:
        for local_names, global_names in reversed(
            tuple(zip(self._scope_local_names, self._scope_global_names, strict=True))
        ):
            if name in global_names:
                return True
            if name in local_names:
                return False
        return True


def single_reference(reference: str | None) -> frozenset[str]:
    """Wrap a present reference in the collector's immutable alias representation."""
    return frozenset({reference}) if reference is not None else frozenset()


def default_argument_bindings(
    arguments: ast.arguments,
    module_aliases: dict[str, frozenset[str]],
    function_aliases: dict[str, frozenset[str]],
) -> dict[str, ReferencePair]:
    """Resolve lexical aliases captured by default argument expressions."""
    bindings: dict[str, ReferencePair] = {}
    positional = (*arguments.posonlyargs, *arguments.args)
    offset = len(positional) - len(arguments.defaults)
    for argument, value in zip(positional[offset:], arguments.defaults, strict=True):
        bindings[argument.arg] = (
            module_reference(value, module_aliases, function_aliases),
            callable_reference(value, module_aliases, function_aliases),
        )
    for argument, value in zip(arguments.kwonlyargs, arguments.kw_defaults, strict=True):
        if value is not None:
            bindings[argument.arg] = (
                module_reference(value, module_aliases, function_aliases),
                callable_reference(value, module_aliases, function_aliases),
            )
    return bindings


def literal_iterable_values(iterable: ast.expr | None) -> tuple[ast.expr, ...]:
    """Return statically enumerated iterable values, if the iterable is literal."""
    return tuple(iterable.elts) if isinstance(iterable, (ast.List, ast.Set, ast.Tuple)) else ()


def pattern_capture_names(pattern: ast.pattern) -> frozenset[str]:
    """Return names bound by a match pattern before the case body executes."""
    names: set[str] = set()
    for node in ast.walk(pattern):
        if isinstance(node, (ast.MatchAs, ast.MatchStar)) and node.name is not None:
            names.add(node.name)
        elif isinstance(node, ast.MatchMapping) and node.rest is not None:
            names.add(node.rest)
    return frozenset(names)
