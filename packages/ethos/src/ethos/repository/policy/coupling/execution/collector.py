"""Bounded lexical collector for known external execution calls."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING
from typing import override

from ethos.repository.policy.coupling.execution.aliases.catalog import alias_key
from ethos.repository.policy.coupling.execution.aliases.catalog import literal_subscript_key
from ethos.repository.policy.coupling.execution.aliases.catalog import static_mapping_entries
from ethos.repository.policy.coupling.execution.aliases.core import callable_reference
from ethos.repository.policy.coupling.execution.aliases.core import canonical_execution_function
from ethos.repository.policy.coupling.execution.aliases.core import execution_function
from ethos.repository.policy.coupling.execution.aliases.core import imported_callable_alias
from ethos.repository.policy.coupling.execution.aliases.core import imported_execution_functions
from ethos.repository.policy.coupling.execution.aliases.core import imported_execution_module
from ethos.repository.policy.coupling.execution.aliases.core import imported_execution_module_from
from ethos.repository.policy.coupling.execution.aliases.core import module_reference
from ethos.repository.policy.coupling.execution.analysis.scopes import ExecutionScopeTraversal
from ethos.repository.policy.coupling.execution.analysis.scopes import pattern_capture_names
from ethos.repository.policy.coupling.execution.analysis.scopes import single_reference

if TYPE_CHECKING:
    from ethos.repository.policy.coupling.execution.analysis.replay import CallableNode


def collect_external_execution_calls(tree: ast.AST) -> tuple[tuple[ast.Call, str], ...]:
    """Return known external execution calls using bounded lexical alias analysis."""
    collector = _ExecutionCallCollector()
    collector.visit(tree)
    return tuple(collector.calls)


class _ExecutionCallCollector(ExecutionScopeTraversal):
    @override
    def visit_Module(self, node: ast.Module) -> None:
        self._visit_statements(node.body)
        self._replay_deferred_callables()

    @override
    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            name = alias.asname or alias.name.split(".", maxsplit=1)[0]
            bound_module = alias.name if alias.asname is not None else name
            self._rebind(name, modules=single_reference(imported_execution_module(bound_module)))

    @override
    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module is None:
            return
        for alias in node.names:
            if alias.name == "*":
                for function in imported_execution_functions(node.module):
                    self._rebind(
                        function.rsplit(".", maxsplit=1)[1],
                        functions=frozenset({function}),
                    )
                continue
            name = alias.asname or alias.name
            function = canonical_execution_function(node.module, alias.name)
            marker = imported_callable_alias(node.module, alias.name)
            functions = single_reference(function).union(single_reference(marker))
            self._rebind(
                name,
                modules=single_reference(imported_execution_module_from(node.module, alias.name)),
                functions=functions,
            )

    @override
    def visit_Assign(self, node: ast.Assign) -> None:
        self.visit(node.value)
        self._bind_assignment_targets(tuple(node.targets), node.value)

    @override
    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self.visit(node.annotation)
        if node.value is not None:
            self.visit(node.value)
            self._bind_assignment_targets((node.target,), node.value)

    @override
    def visit_NamedExpr(self, node: ast.NamedExpr) -> None:
        self.visit(node.value)
        self._bind_assignment_targets((node.target,), node.value)

    @override
    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self.visit(node.value)
        self._clear_target_aliases(node.target)

    @override
    def visit_Delete(self, node: ast.Delete) -> None:
        for target in node.targets:
            self._delete_target_aliases(target)

    @override
    def visit_If(self, node: ast.If) -> None:
        self.visit(node.test)
        self._visit_branches((node.body, node.orelse), include_entry=not node.orelse)

    @override
    def visit_Try(self, node: ast.Try) -> None:
        self._visit_try(node)

    @override
    def visit_TryStar(self, node: ast.TryStar) -> None:
        self._visit_try(node)

    @override
    def visit_For(self, node: ast.For) -> None:
        self._visit_loop(node.iter, node.target, node.body, node.orelse)

    @override
    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self._visit_loop(node.iter, node.target, node.body, node.orelse)

    @override
    def visit_While(self, node: ast.While) -> None:
        self.visit(node.test)
        self._visit_loop(None, None, node.body, node.orelse)

    @override
    def visit_With(self, node: ast.With) -> None:
        self._visit_with(node.items, node.body)

    @override
    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        self._visit_with(node.items, node.body)

    @override
    def visit_Match(self, node: ast.Match) -> None:
        self.visit(node.subject)
        entry = self._branch_snapshot()
        states = [entry]
        for case in node.cases:
            self._restore_branch(entry)
            self._bind_pattern_aliases(case.pattern, node.subject)
            if case.guard is not None:
                self.visit(case.guard)
            self._visit_statements(case.body)
            states.append(self._branch_snapshot())
        self._restore_branch(self._merged_branch_snapshot(tuple(states)))

    @override
    def visit_ListComp(self, node: ast.ListComp) -> None:
        self._visit_comprehension(node.generators, (node.elt,))

    @override
    def visit_SetComp(self, node: ast.SetComp) -> None:
        self._visit_comprehension(node.generators, (node.elt,))

    @override
    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:
        self._visit_comprehension(node.generators, (node.elt,))

    @override
    def visit_DictComp(self, node: ast.DictComp) -> None:
        self._visit_comprehension(node.generators, (node.key, node.value))

    @override
    def visit_Call(self, node: ast.Call) -> None:
        modules, functions = self._resolution_aliases()
        function = execution_function(node, modules, functions)
        if function is not None:
            self._record_call(node, function)
        if isinstance(node.func, ast.Lambda):
            self._replay_inline_lambda(node.func)
        self._replay_instance_method(node)
        self._apply_instance_method_effects(node)
        self._replay_direct_callable(node)
        self.generic_visit(node)

    @override
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    @override
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    @override
    def visit_Lambda(self, node: ast.Lambda) -> None:
        if id(node) not in self._inline_lambdas:
            self._prepare_lambda(node)
            self._defer_callable(node)

    @override
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        for decorator in node.decorator_list:
            self.visit(decorator)
        for base in node.bases:
            self.visit(base)
        for keyword in node.keywords:
            self.visit(keyword.value)
        parent = next((owner for owner in reversed(self._class_owners) if owner), "")
        owner = f"{parent}.{node.name}" if parent else node.name
        self._visit_scoped_statements(node.body, None, class_owner=owner)
        self._rebind(node.name)

    def _bind_assignment_targets(
        self,
        targets: tuple[ast.expr, ...] | list[ast.expr],
        value: ast.expr,
    ) -> None:
        source_modules, source_functions = self._resolution_aliases()
        modules = module_reference(value, source_modules, source_functions)
        functions = callable_reference(value, source_modules, source_functions)
        for target in targets:
            key = alias_key(target)
            if key is None:
                self._clear_target_aliases(target)
                continue
            self._rebind(key, modules=modules, functions=functions)
            self._record_static_alias(target, modules, functions)
        self._bind_mapping_aliases(targets, value, source_modules, source_functions)
        self._bind_named_callables(targets, value)
        self._bind_instance_targets(targets, value)

    def _bind_named_callables(
        self,
        targets: tuple[ast.expr, ...] | list[ast.expr],
        value: ast.expr,
    ) -> None:
        definitions = self._callable_definitions(value)
        entries = static_mapping_entries(value)
        for target in targets:
            target_key = alias_key(target)
            if target_key is None:
                continue
            self._set_named_callables(target_key, definitions, clear_descendants=True)
            self._bind_class_callable(target, target_key, definitions)
            for path, item in entries:
                item_definitions = self._callable_definitions(item)
                if not item_definitions:
                    continue
                suffix = "".join(f"[{key}]" for key in path)
                item_key = f"{target_key}{suffix}"
                self._set_named_callables(item_key, item_definitions)
                self._bind_class_callable(target, item_key, item_definitions)

    def _callable_definitions(self, value: ast.expr) -> frozenset[CallableNode]:
        if isinstance(value, ast.Lambda):
            return frozenset({value})
        key = alias_key(value)
        if key is None:
            return frozenset()
        return self._named_callable_definitions(key).union(
            self._class_callables.get(key, frozenset())
        )

    def _bind_class_callable(
        self,
        target: ast.expr,
        key: str,
        definitions: frozenset[CallableNode],
    ) -> None:
        owner = self._class_owners[-1]
        if owner is not None and isinstance(target, ast.Name):
            self._set_class_callables(f"{owner}.{key}", definitions)

    def _delete_target_aliases(self, target: ast.expr) -> None:
        key = alias_key(target)
        if key is not None:
            if len(self._class_scopes) == 1:
                self._erase(key)
            else:
                self._rebind(key)
        elif isinstance(target, (ast.List, ast.Tuple)):
            for element in target.elts:
                self._delete_target_aliases(element)

    def _bind_mapping_aliases(
        self,
        targets: tuple[ast.expr, ...] | list[ast.expr],
        value: ast.expr,
        module_aliases: dict[str, frozenset[str]],
        function_aliases: dict[str, frozenset[str]],
    ) -> None:
        entries = static_mapping_entries(value)
        if not entries:
            return
        for target in targets:
            target_key = alias_key(target)
            if target_key is None:
                continue
            for path, item in entries:
                modules = module_reference(item, module_aliases, function_aliases)
                functions = callable_reference(item, module_aliases, function_aliases)
                suffix = "".join(f"[{key}]" for key in path)
                self._rebind(f"{target_key}{suffix}", modules=modules, functions=functions)

    def _record_static_alias(
        self,
        target: ast.expr,
        modules: frozenset[str],
        functions: frozenset[str],
    ) -> None:
        owner = self._class_owners[-1]
        if isinstance(target, ast.Name) and owner is not None:
            self._set_class_member(f"{owner}.{target.id}", modules, functions)
        elif (
            isinstance(target, ast.Attribute)
            and _is_instance_member(target)
            and (method := self._method_context[-1])
        ):
            self._set_method_effect(method, target.attr, modules, functions)

    def _set_class_member(
        self,
        key: str,
        modules: frozenset[str],
        functions: frozenset[str],
    ) -> None:
        self._class_module_aliases.pop(key, None)
        self._class_function_aliases.pop(key, None)
        if modules:
            self._class_module_aliases[key] = modules
        if functions:
            self._class_function_aliases[key] = functions

    def _set_method_effect(
        self,
        method: tuple[str, str],
        attribute: str,
        modules: frozenset[str],
        functions: frozenset[str],
    ) -> None:
        effects = self._method_effects.setdefault(method, {})
        if modules or functions:
            effects[attribute] = (modules, functions)
        else:
            effects.pop(attribute, None)
        if not effects:
            self._method_effects.pop(method, None)

    def _bind_instance_targets(
        self,
        targets: tuple[ast.expr, ...] | list[ast.expr],
        value: ast.expr,
    ) -> None:
        owner = _instance_constructor_owner(
            value,
            self._class_module_aliases,
            self._class_methods,
        )
        for target in targets:
            key = alias_key(target)
            if key is None:
                continue
            self._instance_owners.pop(key, None)
            if owner is not None:
                self._instance_owners[key] = owner

    def _apply_instance_method_effects(self, node: ast.Call) -> None:
        if not isinstance(node.func, ast.Attribute):
            return
        receiver = alias_key(node.func.value)
        if receiver is None or (owner := self._instance_owners.get(receiver)) is None:
            return
        for attribute, (modules, functions) in self._method_effects.get(
            (owner, node.func.attr), {}
        ).items():
            self._rebind(f"{receiver}.{attribute}", modules=modules, functions=functions)

    def _replay_instance_method(self, node: ast.Call) -> None:
        if not isinstance(node.func, ast.Attribute):
            return
        receiver = alias_key(node.func.value)
        if receiver is None or (owner := self._instance_owners.get(receiver)) is None:
            return
        method = self._class_methods.get((owner, node.func.attr))
        if method is not None:
            entry = self._branch_snapshot()
            states = []
            for definition in sorted(
                method,
                key=lambda candidate: (candidate.lineno, candidate.col_offset, id(candidate)),
            ):
                self._restore_branch(entry)
                self._replay_callable(
                    definition,
                    self._snapshot(),
                    propagate_scope_writes=True,
                )
                states.append(self._branch_snapshot())
            self._restore_branch(self._merged_branch_snapshot(tuple(states)))

    def _bind_pattern_aliases(self, pattern: ast.pattern, subject: ast.expr) -> None:
        for name in pattern_capture_names(pattern):
            self._rebind(name)
        self._bind_pattern_value(pattern, subject)

    def _bind_pattern_value(self, pattern: ast.pattern, value: ast.expr) -> None:
        if isinstance(pattern, ast.MatchAs):
            if pattern.name is not None:
                self._bind_name_to_value(pattern.name, value)
            if pattern.pattern is not None:
                self._bind_pattern_value(pattern.pattern, value)
        elif isinstance(pattern, ast.MatchStar) and pattern.name is not None:
            self._bind_name_to_value(pattern.name, value)
        elif isinstance(pattern, ast.MatchMapping):
            items = {
                path[0]: item for path, item in static_mapping_entries(value) if len(path) == 1
            }
            for key, nested in zip(pattern.keys, pattern.patterns, strict=True):
                literal = literal_subscript_key(key)
                item = items.get(literal) if literal is not None else None
                if item is not None:
                    self._bind_pattern_value(nested, item)

    def _bind_name_to_value(self, name: str, value: ast.expr) -> None:
        modules, functions = self._resolution_aliases()
        self._rebind(
            name,
            modules=module_reference(value, modules, functions),
            functions=callable_reference(value, modules, functions),
        )


def _is_instance_member(target: ast.Attribute) -> bool:
    return isinstance(target.value, ast.Name) and target.value.id in {"self", "cls"}


def _instance_constructor_owner(
    value: ast.expr,
    class_aliases: dict[str, frozenset[str]],
    class_methods: dict[tuple[str, str], frozenset[CallableNode]],
) -> str | None:
    if not isinstance(value, ast.Call) or not isinstance(value.func, ast.Name):
        return None
    owner = value.func.id
    prefix = f"{owner}."
    if any(key.startswith(prefix) for key in class_aliases):
        return owner
    return owner if any(candidate[0] == owner for candidate in class_methods) else None
