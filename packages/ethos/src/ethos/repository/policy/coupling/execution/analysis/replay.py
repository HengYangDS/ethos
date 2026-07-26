"""Replay direct user-callable candidates without losing branch state."""

from __future__ import annotations

import ast
from dataclasses import dataclass

from ethos.repository.policy.coupling.execution.aliases.catalog import alias_key

CallableNode = ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda
AliasMap = dict[str, frozenset[str]]
AliasState = tuple[AliasMap, AliasMap, dict[str, str]]
ReferencePair = tuple[frozenset[str], frozenset[str]]
CallableRegistry = dict[str, frozenset[CallableNode]]
CallableScopes = tuple[CallableRegistry, ...]
DeferredScopes = tuple[tuple[CallableNode, ...], ...]
ClassMethods = dict[tuple[str, str], frozenset[CallableNode]]
MethodEffects = dict[tuple[str, str], dict[str, ReferencePair]]


class ReplayStateError(ValueError):
    """Signal a violated replay-state invariant."""


@dataclass(frozen=True, slots=True)
class BranchState:
    """Own one copyable branch-local analysis state."""

    aliases: AliasState
    named_callables: CallableScopes
    deferred_callables: DeferredScopes
    class_module_aliases: AliasMap
    class_function_aliases: AliasMap
    class_callables: CallableRegistry
    class_methods: ClassMethods
    method_effects: MethodEffects
    global_module_aliases: AliasMap
    global_function_aliases: AliasMap

    @classmethod
    def merge(cls, states: tuple[BranchState, ...]) -> BranchState:
        """Merge every possible branch outcome without choosing traversal order."""
        if not states:
            raise ReplayStateError
        return cls(
            aliases=merge_alias_states(tuple(state.aliases for state in states)),
            named_callables=merge_callable_scopes(tuple(state.named_callables for state in states)),
            deferred_callables=merge_deferred_scopes(
                tuple(state.deferred_callables for state in states)
            ),
            class_module_aliases=merge_aliases(
                tuple(state.class_module_aliases for state in states)
            ),
            class_function_aliases=merge_aliases(
                tuple(state.class_function_aliases for state in states)
            ),
            class_callables=merge_callable_registries(
                tuple(state.class_callables for state in states)
            ),
            class_methods=merge_class_methods(tuple(state.class_methods for state in states)),
            method_effects=merge_method_effects(tuple(state.method_effects for state in states)),
            global_module_aliases=merge_aliases(
                tuple(state.global_module_aliases for state in states)
            ),
            global_function_aliases=merge_aliases(
                tuple(state.global_function_aliases for state in states)
            ),
        )


def copy_alias_map(aliases: AliasMap) -> AliasMap:
    """Copy immutable-reference aliases into a mutable map."""
    return aliases.copy()


def copy_alias_state(state: AliasState) -> AliasState:
    """Copy all current alias facts without retaining mutable branch state."""
    return (copy_alias_map(state[0]), copy_alias_map(state[1]), state[2].copy())


def copy_callable_registry(registry: CallableRegistry) -> CallableRegistry:
    """Copy exact-key user-callable candidates."""
    return registry.copy()


def copy_callable_scopes(scopes: list[CallableRegistry]) -> CallableScopes:
    """Copy user-callable candidates for every active lexical scope."""
    return tuple(copy_callable_registry(scope) for scope in scopes)


def copy_deferred_scopes(scopes: list[list[CallableNode]]) -> DeferredScopes:
    """Copy deferred replay candidates for every active lexical scope."""
    return tuple(tuple(scope) for scope in scopes)


def copy_class_methods(methods: ClassMethods) -> ClassMethods:
    """Copy class-method candidates keyed by owner and method name."""
    return methods.copy()


def copy_method_effects(effects: MethodEffects) -> MethodEffects:
    """Copy replayable instance-member effects."""
    return {method: values.copy() for method, values in effects.items()}


def merge_alias_states(states: tuple[AliasState, ...]) -> AliasState:
    """Merge aliases and retain only instance ownership shared by all paths."""
    return (
        merge_aliases(tuple(state[0] for state in states)),
        merge_aliases(tuple(state[1] for state in states)),
        merge_instance_owners(tuple(state[2] for state in states)),
    )


def merge_aliases(states: tuple[AliasMap, ...]) -> AliasMap:
    """Merge aliases from every possible control-flow path."""
    merged: AliasMap = {}
    for state in states:
        for name, references in state.items():
            merged[name] = merged.get(name, frozenset()).union(references)
    return merged


def merge_instance_owners(states: tuple[dict[str, str], ...]) -> dict[str, str]:
    """Retain instance owners that agree across every merged control-flow path."""
    if not states:
        return {}
    common = states[0].copy()
    for state in states[1:]:
        common = {name: owner for name, owner in common.items() if state.get(name) == owner}
    return common


def merge_callable_scopes(scopes: tuple[CallableScopes, ...]) -> CallableScopes:
    """Merge exact-key user-callable candidates at each lexical depth."""
    lengths = {len(scope) for scope in scopes}
    if len(lengths) != 1:
        raise ReplayStateError
    return tuple(
        merge_callable_registries(tuple(scope[index] for scope in scopes))
        for index in range(len(scopes[0]))
    )


def merge_callable_registries(registries: tuple[CallableRegistry, ...]) -> CallableRegistry:
    """Union user-callable candidates at each static key."""
    merged: CallableRegistry = {}
    for registry in registries:
        for key, candidates in registry.items():
            merged[key] = merged.get(key, frozenset()).union(candidates)
    return merged


def merge_deferred_scopes(scopes: tuple[DeferredScopes, ...]) -> DeferredScopes:
    """Merge deferred callable candidates once in source-discovery order."""
    lengths = {len(scope) for scope in scopes}
    if len(lengths) != 1:
        raise ReplayStateError
    return tuple(
        _merge_callable_nodes(tuple(scope[index] for scope in scopes))
        for index in range(len(scopes[0]))
    )


def merge_class_methods(methods: tuple[ClassMethods, ...]) -> ClassMethods:
    """Union class-method definitions across possible branch outcomes."""
    merged: ClassMethods = {}
    for registry in methods:
        for key, candidates in registry.items():
            merged[key] = merged.get(key, frozenset()).union(candidates)
    return merged


def merge_method_effects(effect_sets: tuple[MethodEffects, ...]) -> MethodEffects:
    """Union possible instance-member effects across branch outcomes."""
    merged: MethodEffects = {}
    for effects in effect_sets:
        for method, attributes in effects.items():
            destination = merged.setdefault(method, {})
            for attribute, (modules, functions) in attributes.items():
                previous_modules, previous_functions = destination.get(
                    attribute,
                    (frozenset(), frozenset()),
                )
                destination[attribute] = (
                    previous_modules.union(modules),
                    previous_functions.union(functions),
                )
    return merged


def _merge_callable_nodes(groups: tuple[tuple[CallableNode, ...], ...]) -> tuple[CallableNode, ...]:
    nodes: list[CallableNode] = []
    seen: set[int] = set()
    for group in groups:
        for node in group:
            if id(node) not in seen:
                seen.add(id(node))
                nodes.append(node)
    return tuple(nodes)


class ExecutionReplayState:
    """Provide replay mechanics to a lexical execution-analysis traversal."""

    _callable_default_bindings: dict[int, dict[str, tuple[frozenset[str], frozenset[str]]]]
    _class_callables: dict[str, frozenset[CallableNode]]
    _class_function_aliases: dict[str, frozenset[str]]
    _class_methods: dict[tuple[str, str], frozenset[CallableNode]]
    _class_module_aliases: dict[str, frozenset[str]]
    _deferred_callables: list[list[CallableNode]]
    _global_function_aliases: dict[str, frozenset[str]]
    _global_module_aliases: dict[str, frozenset[str]]
    _inline_lambdas: set[int]
    _instance_owners: dict[str, str]
    _method_context: list[tuple[str, str] | None]
    _method_effects: dict[
        tuple[str, str],
        dict[str, tuple[frozenset[str], frozenset[str]]],
    ]
    _method_owners: dict[int, tuple[str, str]]
    _named_callables: list[dict[str, frozenset[CallableNode]]]
    _propagating_scope_writes: list[bool]
    _replayed_callables: set[tuple[object, ...]]
    _scope_global_names: list[frozenset[str]]
    _scope_local_names: list[frozenset[str]]
    _scope_nonlocal_names: list[frozenset[str]]

    def _replay_direct_callable(self, node: ast.Call) -> None:
        key = alias_key(node.func)
        if key is None:
            return
        definitions = self._named_callable_definitions(key).union(
            self._class_callables.get(key, frozenset())
        )
        if not definitions:
            return
        snapshot = self._snapshot()
        entry = self._branch_snapshot()
        states = []
        for definition in _source_order(definitions):
            self._restore_branch(entry)
            replay_key = (
                id(definition),
                state_signature(snapshot),
                _alias_signature(self._global_module_aliases),
                _alias_signature(self._global_function_aliases),
            )
            if replay_key in self._replayed_callables:
                states.append(self._branch_snapshot())
                continue
            self._replayed_callables.add(replay_key)
            try:
                self._replay_callable(
                    definition,
                    snapshot,
                    propagate_scope_writes=True,
                )
            finally:
                self._replayed_callables.discard(replay_key)
            states.append(self._branch_snapshot())
        self._restore_branch(self._merged_branch_snapshot(tuple(states)))

    def _replay_inline_lambda(self, node: ast.Lambda) -> None:
        if id(node) in self._inline_lambdas:
            return
        self._inline_lambdas.add(id(node))
        self._prepare_lambda(node)
        self._replay_callable(node, self._snapshot())

    def _replay_callable(
        self,
        node: CallableNode,
        snapshot: AliasState | None = None,
        *,
        propagate_scope_writes: bool = False,
    ) -> None:
        current = self._snapshot()
        captured: AliasState | None = None
        if snapshot is not None:
            self._restore(snapshot)
        entry = self._snapshot()
        self._method_context.append(self._method_owners.get(id(node)))
        self._propagating_scope_writes.append(propagate_scope_writes)
        try:
            bindings = self._callable_default_bindings.get(id(node))
            if isinstance(node, ast.Lambda):
                self._visit_scoped_expression(
                    node.body,
                    node.args,
                    argument_bindings=bindings,
                )
            else:
                captured = self._visit_scoped_statements(
                    node.body,
                    node.args,
                    argument_bindings=bindings,
                    capture_state=propagate_scope_writes,
                )
        finally:
            self._method_context.pop()
            self._propagating_scope_writes.pop()
            self._restore(current)
        if captured is not None and isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            self._apply_callable_scope_writes(node.body, node.args, entry, captured)

    def _branch_snapshot(self) -> BranchState:
        return BranchState(
            aliases=copy_alias_state(self._snapshot()),
            named_callables=copy_callable_scopes(self._named_callables),
            deferred_callables=copy_deferred_scopes(self._deferred_callables),
            class_module_aliases=copy_alias_map(self._class_module_aliases),
            class_function_aliases=copy_alias_map(self._class_function_aliases),
            class_callables=copy_callable_registry(self._class_callables),
            class_methods=copy_class_methods(self._class_methods),
            method_effects=copy_method_effects(self._method_effects),
            global_module_aliases=copy_alias_map(self._global_module_aliases),
            global_function_aliases=copy_alias_map(self._global_function_aliases),
        )

    def _restore_branch(self, state: BranchState) -> None:
        self._restore(state.aliases)
        self._named_callables = [registry.copy() for registry in state.named_callables]
        self._deferred_callables = [list(scope) for scope in state.deferred_callables]
        self._class_module_aliases = state.class_module_aliases.copy()
        self._class_function_aliases = state.class_function_aliases.copy()
        self._class_callables = state.class_callables.copy()
        self._class_methods = state.class_methods.copy()
        self._method_effects = {
            method: attributes.copy() for method, attributes in state.method_effects.items()
        }
        self._global_module_aliases = state.global_module_aliases.copy()
        self._global_function_aliases = state.global_function_aliases.copy()

    def _merged_branch_snapshot(self, states: tuple[BranchState, ...]) -> BranchState:
        return BranchState.merge(states)

    def _set_named_callables(
        self,
        name: str,
        definitions: frozenset[CallableNode],
        *,
        clear_descendants: bool = False,
    ) -> None:
        scope_index = self._named_callable_scope_index(name)
        self._clear_named_callables(
            name,
            clear_descendants=clear_descendants,
            scope_index=scope_index,
        )
        if definitions:
            self._named_callables[scope_index][name] = definitions

    def _clear_named_callables(
        self,
        name: str,
        *,
        clear_descendants: bool = False,
        scope_index: int | None = None,
    ) -> None:
        index = self._named_callable_scope_index(name) if scope_index is None else scope_index
        registry = self._named_callables[index]
        keys = (name,)
        if clear_descendants:
            prefixes = (f"{name}.", f"{name}[")
            keys = tuple(key for key in registry if key == name or key.startswith(prefixes))
        for key in keys:
            registry.pop(key, None)

    def _named_callable_definitions(self, key: str) -> frozenset[CallableNode]:
        return self._named_callables[self._named_callable_scope_index(key)].get(
            key,
            frozenset(),
        )

    def _named_callable_scope_index(self, key: str) -> int:
        current = len(self._named_callables) - 1
        if not self._propagating_scope_writes or not self._propagating_scope_writes[-1]:
            return current
        name = _alias_root(key)
        while current > 0:
            if name in self._scope_global_names[current]:
                return 0
            if name in self._scope_nonlocal_names[current]:
                current -= 1
                continue
            if name in self._scope_local_names[current]:
                return current
            current -= 1
        return 0

    def _set_class_callables(
        self,
        name: str,
        definitions: frozenset[CallableNode],
    ) -> None:
        self._class_callables.pop(name, None)
        if definitions:
            self._class_callables[name] = definitions

    def _prepare_lambda(self, node: ast.Lambda) -> None:
        raise NotImplementedError

    def _apply_callable_scope_writes(
        self,
        statements: list[ast.stmt],
        arguments: ast.arguments,
        entry: AliasState,
        state: AliasState,
    ) -> None:
        local_names, global_names, _ = function_scope_bindings(statements)
        local_names = local_names.union(argument_names(arguments))
        for key in _changed_external_alias_keys(
            entry,
            state,
            local_names=local_names,
        ):
            name = _alias_root(key)
            if (
                (key == name and name in global_names)
                or len(self._scope_local_names) == 1
                or key in self._global_module_aliases
                or key in self._global_function_aliases
            ):
                self._set_global_alias_binding(
                    key,
                    state[0].get(key, frozenset()),
                    state[1].get(key, frozenset()),
                )
            else:
                self._set_current_alias_binding(key, state)

    def _snapshot(self) -> AliasState:
        raise NotImplementedError

    def _restore(self, snapshot: AliasState) -> None:
        raise NotImplementedError

    def _set_current_alias_binding(self, name: str, state: AliasState) -> None:
        raise NotImplementedError

    def _set_global_alias_binding(
        self,
        name: str,
        modules: frozenset[str],
        functions: frozenset[str],
    ) -> None:
        raise NotImplementedError

    def _visit_scoped_expression(
        self,
        expression: ast.expr,
        arguments: ast.arguments,
        *,
        argument_bindings: dict[str, tuple[frozenset[str], frozenset[str]]] | None = None,
    ) -> AliasState | None:
        raise NotImplementedError

    def _visit_scoped_statements(
        self,
        statements: list[ast.stmt],
        arguments: ast.arguments | None,
        *,
        argument_bindings: dict[str, tuple[frozenset[str], frozenset[str]]] | None = None,
        capture_state: bool = False,
    ) -> AliasState | None:
        raise NotImplementedError


def state_signature(state: AliasState) -> tuple[object, ...]:
    """Return a deterministic signature used to break one recursive replay cycle."""
    return (
        _alias_signature(state[0]),
        _alias_signature(state[1]),
        tuple(sorted(state[2].items())),
    )


def _alias_signature(aliases: dict[str, frozenset[str]]) -> tuple[tuple[str, tuple[str, ...]], ...]:
    return tuple(sorted((name, tuple(sorted(values))) for name, values in aliases.items()))


def _source_order(definitions: frozenset[CallableNode]) -> tuple[CallableNode, ...]:
    return tuple(sorted(definitions, key=lambda node: (node.lineno, node.col_offset, id(node))))


def _changed_external_alias_keys(
    entry: AliasState,
    state: AliasState,
    *,
    local_names: frozenset[str],
) -> tuple[str, ...]:
    keys = set(entry[0]).union(entry[1], state[0], state[1])
    return tuple(
        sorted(
            key
            for key in keys
            if _alias_root(key) not in local_names
            and (entry[0].get(key), entry[1].get(key)) != (state[0].get(key), state[1].get(key))
        )
    )


def _alias_root(key: str) -> str:
    return key.partition(".")[0].partition("[")[0]


def function_scope_bindings(
    statements: list[ast.stmt],
) -> tuple[frozenset[str], frozenset[str], frozenset[str]]:
    """Return immediate lexical declarations without traversing nested bodies."""
    visitor = _FunctionLocalBinderCollector()
    for statement in statements:
        visitor.visit(statement)
    return (
        frozenset(visitor.names.difference(visitor.global_names, visitor.nonlocal_names)),
        frozenset(visitor.global_names),
        frozenset(visitor.nonlocal_names),
    )


def argument_names(arguments: ast.arguments | None) -> frozenset[str]:
    if arguments is None:
        return frozenset()
    names = {argument.arg for argument in (*arguments.posonlyargs, *arguments.args)}
    names.update(argument.arg for argument in arguments.kwonlyargs)
    if arguments.vararg is not None:
        names.add(arguments.vararg.arg)
    if arguments.kwarg is not None:
        names.add(arguments.kwarg.arg)
    return frozenset(names)


class _FunctionLocalBinderCollector(ast.NodeVisitor):
    def __init__(self) -> None:
        self.names: set[str] = set()
        self.global_names: set[str] = set()
        self.nonlocal_names: set[str] = set()

    def visit_Global(self, node: ast.Global) -> None:
        self.global_names.update(node.names)

    def visit_Nonlocal(self, node: ast.Nonlocal) -> None:
        self.nonlocal_names.update(node.names)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, (ast.Store, ast.Del)):
            self.names.add(node.id)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.names.add(alias.asname or alias.name.split(".", maxsplit=1)[0])

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            if alias.name != "*":
                self.names.add(alias.asname or alias.name)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.name is not None:
            self.names.add(node.name)
        self.generic_visit(node)

    def visit_MatchAs(self, node: ast.MatchAs) -> None:
        if node.name is not None:
            self.names.add(node.name)
        self.generic_visit(node)

    def visit_MatchStar(self, node: ast.MatchStar) -> None:
        if node.name is not None:
            self.names.add(node.name)

    def visit_MatchMapping(self, node: ast.MatchMapping) -> None:
        if node.rest is not None:
            self.names.add(node.rest)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.names.add(node.name)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.names.add(node.name)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.names.add(node.name)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        del node

    def visit_ListComp(self, node: ast.ListComp) -> None:
        del node

    def visit_SetComp(self, node: ast.SetComp) -> None:
        del node

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:
        del node

    def visit_DictComp(self, node: ast.DictComp) -> None:
        del node
