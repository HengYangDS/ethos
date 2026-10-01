"""Use compiler scopes and structured flow for bounded call-site observations."""

from __future__ import annotations

import ast
import symtable
from collections import deque
from dataclasses import dataclass
from functools import singledispatchmethod
from typing import TYPE_CHECKING

from ethos.repository.policy.references.python.functions import call_arguments
from ethos.repository.policy.references.python.functions import function_signature
from ethos.repository.policy.references.python.native import native_call
from ethos.repository.policy.references.python.native import read_only_native_call
from ethos.repository.policy.references.python.scope import Scope
from ethos.repository.policy.references.python.values import UNKNOWN
from ethos.repository.policy.references.python.values import BoundCall
from ethos.repository.policy.references.python.values import Expansion
from ethos.repository.policy.references.python.values import Imported
from ethos.repository.policy.references.python.values import Literal
from ethos.repository.policy.references.python.values import LocalFunction
from ethos.repository.policy.references.python.values import MappingValue
from ethos.repository.policy.references.python.values import Sequence
from ethos.repository.policy.references.python.values import Unknown
from ethos.repository.policy.references.python.values import Value
from ethos.repository.policy.references.python.values import attribute
from ethos.repository.policy.references.python.values import iteration_values
from ethos.repository.policy.references.python.values import join
from ethos.repository.policy.references.python.values import origins
from ethos.repository.policy.references.python.values import widen_mutated

if TYPE_CHECKING:
    from inspect import Signature


@dataclass(frozen=True, slots=True)
class PythonBindings:
    """Static imports and scoped call sites; source code is never executed."""

    imports: frozenset[str]
    calls: tuple[BoundCall, ...]
    compiler_valid: bool


def bind_python(tree: ast.AST, text: str) -> PythonBindings:
    """Bind native syntax with the running supported Python compiler's scopes."""
    imports = frozenset(
        name.split(".")[0]
        for node in ast.walk(tree)
        for name in (
            tuple(alias.name for alias in node.names)
            if isinstance(node, ast.Import)
            else (node.module,)
            if isinstance(node, ast.ImportFrom) and node.module
            else ()
        )
    )
    try:
        table = symtable.symtable(text, "<reference-observation>", "exec")
    except (SyntaxError, ValueError):
        return PythonBindings(imports, (), compiler_valid=False)
    flow = _Flow(table)
    flow.block(list(tree.body) if isinstance(tree, ast.Module) else [], Scope(table))
    while flow.deferred:
        node, scope = flow.deferred.popleft()
        if isinstance(node, ast.Lambda):
            flow.expression(node.body, scope)
        else:
            flow.block(node.body, scope)
    return PythonBindings(imports, tuple(flow.calls), compiler_valid=True)


class _Flow:
    def __init__(self, table: symtable.SymbolTable) -> None:
        self.tables: dict[tuple[str, int], symtable.SymbolTable] = {}
        pending = [table]
        while pending:
            current = pending.pop()
            if current.get_type() in {"function", "class"}:
                self.tables[current.get_name(), current.get_lineno()] = current
            pending.extend(current.get_children())
        self.calls: list[BoundCall] = []
        self.functions: dict[
            LocalFunction, tuple[ast.FunctionDef | ast.AsyncFunctionDef, Scope, Signature]
        ] = {}
        self.active: set[LocalFunction] = set()
        self.local_attempts = 0
        self.returns: list[list[Value]] = []
        self.deferred: deque[tuple[ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda, Scope]] = (
            deque()
        )

    def block(self, statements: list[ast.stmt], scope: Scope) -> bool:
        """Observe statements in order; a return does not reach later statements."""
        return all(self.statement(node, scope) for node in statements)

    @singledispatchmethod
    def statement(self, _node: ast.stmt, _scope: Scope) -> bool:
        """Native AST dispatch keeps each transfer rule local to its statement kind."""
        return True

    @statement.register
    def _imports(self, node: ast.Import | ast.ImportFrom, scope: Scope) -> bool:
        match node:
            case ast.Import(names=names):
                for alias in names:
                    name = alias.name if alias.asname else alias.name.partition(".")[0]
                    scope.store(alias.asname or name, frozenset({Imported(name)}))
            case ast.ImportFrom(module=module, names=names, level=level):
                prefix = "." * level + (f"{module}." if module else "")
                for alias in names:
                    name = f"{prefix}{alias.name}"
                    scope.store(
                        alias.asname or alias.name, scope.member(name, frozenset({Imported(name)}))
                    )
        return True

    @statement.register
    def _assignments(
        self, node: ast.Assign | ast.AnnAssign | ast.AugAssign | ast.Delete, scope: Scope
    ) -> bool:
        match node:
            case ast.Assign(targets=targets, value=value):
                resolved = self.expression(value, scope)
                for target in targets:
                    self.assign(target, resolved, scope)
            case ast.AnnAssign(target=target, value=value) if value is not None:
                self.assign(target, self.expression(value, scope), scope)
            case ast.AugAssign(target=target, value=value):
                resolved = self.add(self.expression(target, scope), self.expression(value, scope))
                self.assign(target, resolved if isinstance(node.op, ast.Add) else UNKNOWN, scope)
            case ast.Delete(targets=targets):
                for target in targets:
                    self.assign(target, UNKNOWN, scope)
        return True

    @statement.register
    def _definitions(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef, scope: Scope
    ) -> bool:
        match node:
            case ast.FunctionDef() | ast.AsyncFunctionDef():
                for decorator in node.decorator_list:
                    self.expression(decorator, scope)
                defaults = tuple(self.expression(value, scope) for value in node.args.defaults)
                keyword_defaults = tuple(
                    self.expression(value, scope) if value is not None else None
                    for value in node.args.kw_defaults
                )
                table = self.tables.get((node.name, node.lineno))
                if table is not None:
                    identity = LocalFunction(node.name, node.lineno)
                    self.functions[identity] = (
                        node,
                        scope,
                        function_signature(node.args, defaults, keyword_defaults),
                    )
                    scope.store(
                        node.name, frozenset({identity}) if not node.decorator_list else UNKNOWN
                    )
                    self.deferred.append((node, Scope(table, scope)))
            case ast.ClassDef():
                for value in (*node.bases, *node.decorator_list):
                    self.expression(value, scope)
                table = self.tables.get((node.name, node.lineno))
                if table is not None:
                    self.block(node.body, Scope(table, scope))
                scope.store(node.name, UNKNOWN)
        return True

    @statement.register
    def _conditional(self, node: ast.If, scope: Scope) -> bool:
        match node:
            case ast.If(test=test, body=body, orelse=orelse):
                truth = self.truth(self.expression(test, scope))
                branches = (
                    [body] if truth is True else [orelse] if truth is False else [body, orelse]
                )
                return self.branches(branches, scope)
        return True

    @statement.register
    def _context(self, node: ast.With | ast.AsyncWith, scope: Scope) -> bool:
        for item in node.items:
            self.expression(item.context_expr, scope)
            if item.optional_vars is not None:
                self.assign(item.optional_vars, UNKNOWN, scope)
        return self.block(node.body, scope)

    @statement.register
    def _exceptions(self, node: ast.Try | ast.TryStar, scope: Scope) -> bool:
        outputs = [dict(scope.values)]
        self.block(node.body + node.orelse, scope)
        outputs.append(dict(scope.values))
        for handler in node.handlers:
            branch = Scope(scope.table, scope.parent, dict(outputs[0]))
            if handler.name is not None:
                branch.store(handler.name, UNKNOWN)
            self.block(handler.body, branch)
            if handler.name is not None:
                branch.store(handler.name, UNKNOWN)
            outputs.append(branch.values)
        for name in set().union(*(output.keys() for output in outputs)):
            scope.store(name, join(output.get(name, UNKNOWN) for output in outputs))
        return self.block(node.finalbody, scope)

    @statement.register
    def _evaluation(
        self,
        node: ast.Return | ast.Raise | ast.Expr | ast.Assert | ast.Break | ast.Continue,
        scope: Scope,
    ) -> bool:
        match node:
            case ast.Return(value=value) | ast.Raise(exc=value):
                result = (
                    self.expression(value, scope)
                    if value is not None
                    else frozenset({Literal(None)})
                )
                if isinstance(node, ast.Return) and self.returns:
                    self.returns[-1].append(result)
                return False
            case ast.Expr(value=value):
                self.expression(value, scope)
            case ast.Assert(test=test):
                self.expression(test, scope)
            case ast.Break() | ast.Continue():
                return False
        return True

    @statement.register
    def _matching(self, node: ast.Match, scope: Scope) -> bool:
        match node:
            case ast.Match(subject=subject, cases=cases):
                self.expression(subject, scope)
                self.branches([[], *(case.body for case in cases)], scope)
        return True

    def branches(self, branches: list[list[ast.stmt]], scope: Scope) -> bool:
        outputs = []
        for statements in branches:
            branch = Scope(scope.table, scope.parent, dict(scope.values))
            if self.block(statements, branch):
                outputs.append(branch.values)
        if not outputs:
            return False
        scope.values = {
            name: join(output.get(name, scope.lookup(name)) for output in outputs)
            for name in set().union(*(output.keys() for output in outputs))
        }
        for name, value in scope.values.items():
            scope.history[name] = scope.history.get(name, frozenset()) | value
        return True

    @statement.register
    def _iteration(self, node: ast.For | ast.AsyncFor | ast.While, scope: Scope) -> bool:
        """Widen loop-carried writes before observing a possible iteration."""
        initial = dict(scope.values)
        pending: list[ast.AST] = list(node.body)
        if isinstance(node, ast.While) and self.truth(self.expression(node.test, scope)) is False:
            self.block(node.orelse, scope)
            return True
        writes: set[str] = set()
        while pending:
            item = pending.pop()
            if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef | ast.Lambda):
                continue
            if isinstance(item, ast.Name) and isinstance(item.ctx, ast.Store):
                writes.add(item.id)
            pending.extend(ast.iter_child_nodes(item))
        for name in writes:
            scope.store(name, frozenset({Unknown(origins(scope.lookup(name)))}))
        if isinstance(node, ast.While):
            self.expression(node.test, scope)
        else:
            value = self.expression(node.iter, scope)
            items = [item for atom in value if isinstance(atom, Sequence) for item in atom.items]
            self.assign(node.target, join(items) if items else UNKNOWN, scope)
        self.block(node.body, scope)
        scope.values = {
            name: join((initial.get(name, UNKNOWN), scope.values.get(name, UNKNOWN)))
            for name in initial.keys() | scope.values.keys()
        }
        self.block(node.orelse, scope)
        return True

    def assign(self, target: ast.expr, value: Value, scope: Scope) -> None:
        match target:
            case ast.Name(id=name):
                scope.store(name, value)
            case ast.Attribute(value=owner, attr=name):
                for atom in self.expression(owner, scope):
                    if isinstance(atom, Imported):
                        scope.store(f"{atom.name}.{name}", value)
            case ast.Subscript(value=owner):
                scope.invalidate(self.expression(owner, scope))
                if isinstance(owner, ast.Name):
                    scope.store(owner.id, UNKNOWN)
            case ast.Tuple(elts=elts) | ast.List(elts=elts):
                for index, element in enumerate(elts):
                    self.assign(
                        element,
                        join(
                            atom.items[index]
                            if isinstance(atom, Sequence) and len(atom.items) == len(elts)
                            else UNKNOWN
                            for atom in value
                        ),
                        scope,
                    )

    @singledispatchmethod
    def expression(self, node: ast.expr, scope: Scope) -> Value:
        child_values = [
            self.expression(child, scope)
            for child in ast.iter_child_nodes(node)
            if isinstance(child, ast.expr)
        ]
        return frozenset({Unknown(origins(join(child_values)))})

    @expression.register
    def _values(
        self, node: ast.Constant | ast.Name | ast.Attribute | ast.List | ast.Tuple, scope: Scope
    ) -> Value:
        match node:
            case ast.Constant(value=value) if isinstance(value, str | bool | int) or value is None:
                return frozenset({Literal(value)})
            case ast.Name(id=name):
                return scope.lookup(name)
            case ast.Attribute(value=value, attr=name):
                bound = attribute(self.expression(value, scope), name)
                return join(
                    scope.member(atom.name, frozenset({atom}))
                    if isinstance(atom, Imported)
                    else frozenset({atom})
                    for atom in bound
                )
            case ast.List(elts=elts) | ast.Tuple(elts=elts):
                return widen_mutated(
                    frozenset(
                        {
                            Sequence(
                                tuple(self.expression(item, scope) for item in elts),
                                (node.lineno, node.col_offset)
                                if isinstance(node, ast.List)
                                else None,
                            )
                        }
                    ),
                    scope.invalidated,
                )
        return UNKNOWN

    @expression.register
    def _operations(self, node: ast.BinOp | ast.IfExp | ast.NamedExpr, scope: Scope) -> Value:
        match node:
            case ast.BinOp(left=left, op=ast.Add(), right=right):
                return self.add(self.expression(left, scope), self.expression(right, scope))
            case ast.IfExp(test=test, body=body, orelse=orelse):
                truth = self.truth(self.expression(test, scope))
                selected = (
                    [body] if truth is True else [orelse] if truth is False else [body, orelse]
                )
                return join(self.expression(item, scope) for item in selected)
            case ast.NamedExpr(target=target, value=value):
                resolved = self.expression(value, scope)
                self.assign(target, resolved, scope)
                return resolved
        return UNKNOWN

    @expression.register
    def _mapping(self, node: ast.Dict, scope: Scope) -> Value:
        """Evaluate each key before its value, then delegate native mapping semantics."""
        return widen_mutated(
            MappingValue.construct(
                (node.lineno, node.col_offset),
                tuple(
                    (
                        self.expression(key, scope) if key is not None else None,
                        self.expression(value, scope),
                    )
                    for key, value in zip(node.keys, node.values, strict=True)
                ),
            ),
            scope.invalidated,
        )

    @expression.register
    def _subscript(self, node: ast.Subscript, scope: Scope) -> Value:
        match node:
            case ast.Subscript(value=value, slice=key):
                owner, index = self.expression(value, scope), self.expression(key, scope)
                self.calls.append(
                    BoundCall(node.lineno, attribute(owner, "__getitem__"), (index,), ())
                )
                return join(
                    atom.items[item.value]
                    if isinstance(atom, Sequence)
                    and isinstance(item, Literal)
                    and isinstance(item.value, int)
                    and -len(atom.items) <= item.value < len(atom.items)
                    else dict(atom.items).get(item.value, UNKNOWN)
                    if isinstance(atom, MappingValue)
                    and isinstance(item, Literal)
                    and isinstance(item.value, str)
                    else UNKNOWN
                    for atom in owner
                    for item in index
                )
        return UNKNOWN

    @expression.register
    def _call(self, node: ast.Call, scope: Scope) -> Value:
        call = BoundCall(
            node.lineno,
            self.expression(node.func, scope),
            tuple(self.expression(arg, scope) for arg in node.args),
            tuple((item.arg, self.expression(item.value, scope)) for item in node.keywords),
        )
        self.calls.append(call)
        result = join(
            self.local_call(target, call)
            if isinstance(target, LocalFunction)
            else native_call(BoundCall(call.line, frozenset({target}), call.args, call.keywords))
            for target in call.targets
        )
        if not read_only_native_call(call) and (
            any(not isinstance(target, LocalFunction) for target in call.targets)
            or any(isinstance(atom, Unknown) for atom in result)
        ):
            scope.invalidate(call.exposed_values())
        return widen_mutated(result, scope.invalidated)

    def local_call(self, identity: LocalFunction, call: BoundCall) -> Value:
        """Observe one bounded concrete invocation without executing source code."""
        if identity in self.active or len(self.active) >= 32 or self.local_attempts >= 1024:
            return UNKNOWN
        self.local_attempts += 1
        node, parent, signature = self.functions[identity]
        scope = Scope(self.tables[(node.name, node.lineno)], parent)
        scope.values.update(call_arguments(signature, call))
        self.active.add(identity)
        self.returns.append([])
        try:
            falls_through = self.block(node.body, scope)
            values = self.returns[-1]
            if falls_through:
                values.append(frozenset({Literal(None)}))
            return join(values) or UNKNOWN
        finally:
            self.returns.pop()
            self.active.remove(identity)

    @expression.register
    def _expansion(self, node: ast.Starred, scope: Scope) -> Value:
        return frozenset({Expansion(self.expression(node.value, scope))})

    @expression.register
    def _lambda(self, node: ast.Lambda, scope: Scope) -> Value:
        table = self.tables.get(("lambda", node.lineno))
        if table is not None:
            self.deferred.append((node, Scope(table, scope)))
        return UNKNOWN

    @expression.register
    def _comprehension(
        self, node: ast.ListComp | ast.SetComp | ast.DictComp | ast.GeneratorExp, scope: Scope
    ) -> Value:
        iteration_names = frozenset(
            item.id
            for generator in node.generators
            for item in ast.walk(generator.target)
            if isinstance(item, ast.Name)
        )
        inner = Scope(scope.table, scope, iteration_names=iteration_names)
        for index, generator in enumerate(node.generators):
            iterable = self.expression(generator.iter, scope if index == 0 else inner)
            values = iteration_values(iterable)
            if not values:
                return UNKNOWN
            self.assign(generator.target, values, inner)
            for condition in generator.ifs:
                self.expression(condition, inner)
        if isinstance(node, ast.DictComp):
            self.expression(node.key, inner)
            self.expression(node.value, inner)
        else:
            self.expression(node.elt, inner)
        return UNKNOWN

    @staticmethod
    def add(left: Value, right: Value) -> Value:
        return join(
            frozenset({Literal(first.value + second.value)})
            if isinstance(first, Literal)
            and isinstance(second, Literal)
            and isinstance(first.value, str)
            and isinstance(second.value, str)
            else frozenset({Unknown(origins(left | right))})
            for first in left
            for second in right
        )

    @staticmethod
    def truth(value: Value) -> bool | None:
        if len(value) != 1:
            return None
        atom = next(iter(value))
        return bool(atom.value) if isinstance(atom, Literal) else None
