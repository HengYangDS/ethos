"""Ordered Python binding observation using native lexical and typed AST dispatch."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from dataclasses import field
from functools import singledispatchmethod
from importlib.util import resolve_name
from typing import TYPE_CHECKING

from ethos.repository.policy.references.python.bindings import BindingScope
from ethos.repository.policy.references.python.bindings import BindingValue
from ethos.repository.policy.references.python.bindings import ImportReference
from ethos.repository.policy.references.python.bindings import MemberDemand
from ethos.repository.policy.references.python.control import PythonControlFlow
from ethos.repository.policy.references.python.effects import PythonConsumption
from ethos.repository.policy.references.python.functions.effects import project
from ethos.repository.policy.references.python.functions.effects import stored
from ethos.repository.policy.references.python.native.scalars import concatenate
from ethos.repository.policy.references.python.syntax import LexicalBindings
from ethos.repository.policy.references.python.syntax import NativeScopes
from ethos.repository.policy.references.python.syntax import module_name

if TYPE_CHECKING:
    from ethos.repository.policy.references.python.functions.returns import PythonSourceReturns


@dataclass(slots=True)
class PythonReferenceFlow:
    """One finite source observation; source code and callee effects never execute."""

    path: str
    npm_scripts: dict[str, set[str]]
    sources: PythonSourceReturns | None = None
    result: PythonConsumption = field(init=False)
    lexical: NativeScopes = field(init=False)
    pending: list[
        tuple[
            ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda,
            BindingScope,
            LexicalBindings,
            BindingValue,
        ]
    ] = field(default_factory=list)

    def observe(self, tree: ast.AST, *, source: str) -> PythonConsumption:
        """Use exact-source scopes and retain conservative deferred-body coverage."""
        self.initialize(tree, source=source)
        cursor = 0
        while cursor < len(self.pending):
            function, parent, lexical, value = self.pending[cursor]
            cursor += 1
            name = "<lambda>" if isinstance(function, ast.Lambda) else function.name
            child = BindingScope(
                f"{parent.name}.{name}",
                parent,
                lexical.locals,
                lexical.globals,
                lexical.nonlocals,
                deferred_outer=True,
            )
            if self.sources is not None and len(value.targets) == 1:
                definition = self.sources.definitions[next(iter(value.targets))]
                summary = self.sources.invocations.summary_for(definition, self.result, child)
                if summary.observation is not None:
                    self.result.absorb(summary.observation)
                self.pending.extend(summary.pending)
                continue
            arguments = function.args
            parameters = (*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs)
            for argument in (
                *parameters,
                *((arguments.vararg,) if arguments.vararg else ()),
                *((arguments.kwarg,) if arguments.kwarg else ()),
            ):
                child.assign(argument.arg, BindingValue(deferred=True, local=True))
            if isinstance(function, ast.Lambda):
                self.expression(function.body, child)
            else:
                self.block(function.body, child)
        self.result.uncertainties = list(dict.fromkeys(self.result.uncertainties))
        return self.result

    def initialize(self, tree: ast.AST, *, source: str) -> BindingScope:
        """Read a module's current exports without substituting deferred-body summaries."""
        self.result = PythonConsumption(self.path, self.npm_scripts, sources=self.sources)
        self.lexical = NativeScopes.from_source(source, self.path)
        scope = BindingScope("<module>", kind="module")
        if isinstance(tree, ast.Module):
            self.block(tree.body, scope)
        else:
            self.expression(tree, scope)
        return scope

    def block(
        self, statements: list[ast.stmt], scope: BindingScope
    ) -> ast.Return | ast.Raise | ast.Break | ast.Continue | None:
        """Observe one ordered path until a terminal statement."""
        paths = PythonControlFlow(self).block(statements, scope)
        continuing = [path.scope for path in paths if path.kind == "normal"]
        if continuing:
            scope.merge(*continuing)
            return None
        scope.merge(*(path.scope for path in paths))
        return next(
            (
                statement
                for statement in statements
                if isinstance(statement, ast.Return | ast.Raise | ast.Break | ast.Continue)
            ),
            ast.Return(),
        )

    @singledispatchmethod
    def statement(self, node: ast.stmt, scope: BindingScope) -> None:
        """Retain observations in otherwise unsupported statement children."""
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.expr):
                self.expression(child, scope)
            elif isinstance(child, ast.stmt):
                self.statement(child, scope)

    @statement.register
    def import_binding(self, node: ast.Import | ast.ImportFrom, scope: BindingScope) -> None:
        """Bind qualified import provenance and explicit star-import opacity."""
        module = (node.module or "") if isinstance(node, ast.ImportFrom) and not node.level else ""
        if module:
            self.result.imports.add(module.partition(".")[0])
        for alias in node.names:
            origin = module
            if isinstance(node, ast.ImportFrom) and node.level:
                consumer = module_name(self.path)
                package = (
                    consumer if self.path.endswith("/__init__.py") else consumer.rpartition(".")[0]
                )
                try:
                    origin = resolve_name("." * node.level + (node.module or ""), package)
                except (ImportError, ValueError):
                    self.result.residual(
                        "import",
                        "unknown",
                        node,
                        scope,
                        node.module or "",
                        "relative_import_unresolved",
                    )
                    continue
            self.result.import_sites.append(
                ImportReference(
                    alias.name if isinstance(node, ast.Import) else origin,
                    "" if isinstance(node, ast.Import) else alias.name,
                    node.lineno,
                    node.col_offset,
                )
            )
            if alias.name == "*":
                scope.wildcard = True
                continue
            if isinstance(node, ast.Import):
                self.result.imports.add(alias.name.partition(".")[0])
                target = alias.name if alias.asname else alias.name.partition(".")[0]
            else:
                target = f"{origin}.{alias.name}" if origin else ""
            scope.assign(
                alias.asname or alias.name.partition(".")[0],
                BindingValue(
                    targets=frozenset({target}) if target else frozenset(), local=not bool(target)
                ),
            )

    @statement.register
    def assignment(self, node: ast.Assign | ast.AnnAssign, scope: BindingScope) -> None:
        """Value assignment has program-point order; an annotation is not a value."""
        if node.value is None:
            return
        value = self.expression(node.value, scope)
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        for target in targets:
            self.assign(target, value, scope)

    @statement.register
    def augmented_assignment(self, node: ast.AugAssign, scope: BindingScope) -> None:
        """Observe read-modify-write rather than retaining a stale literal."""
        self.assign(
            node.target,
            self.combine(
                self.expression(node.target, scope), self.expression(node.value, scope), node.op
            ),
            scope,
        )

    @statement.register
    def function_definition(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, scope: BindingScope
    ) -> None:
        """Defaults and decorators execute now; the function body is deferred."""
        for value in node.decorator_list:
            self.expression(value, scope)
        defaults = tuple(self.expression(value, scope) for value in node.args.defaults)
        keywords = tuple(
            self.expression(value, scope) if value is not None else None
            for value in node.args.kw_defaults
        )
        parent = scope
        while parent.kind == "class" and parent.parent is not None:
            parent = parent.parent
        value = (
            self.sources.definition(self, node, parent, defaults, keywords)
            if self.sources is not None
            else BindingValue(local=True)
        )
        scope.assign(
            node.name,
            BindingValue(local=True)
            if node.decorator_list or isinstance(node, ast.AsyncFunctionDef)
            else value,
        )
        self.defer(node, scope, value)

    def defer(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda,
        scope: BindingScope,
        value: BindingValue | None = None,
    ) -> None:
        """Methods close over enclosing functions, not the class execution namespace."""
        parent = scope
        while parent.kind == "class" and parent.parent is not None:
            parent = parent.parent
        lexical = self.lexical.for_node(node)
        child = BindingScope(
            "<deferred>", parent, lexical.locals, lexical.globals, lexical.nonlocals
        )
        child.invalidate_outer(lexical.outer_writes)
        entry = (node, parent, lexical, value if value is not None else BindingValue())
        self.pending.append(entry)
        if self.sources is not None and self.sources.invocations.summarizing:
            summary = self.sources.invocations.summaries[self.sources.invocations.summarizing[-1]]
            summary.pending = (*summary.pending, entry)

    @statement.register
    def class_definition(self, node: ast.ClassDef, scope: BindingScope) -> None:
        """Observe class execution separately from later method lexical lookup."""
        for value in (*node.bases, *node.decorator_list, *(item.value for item in node.keywords)):
            self.expression(value, scope)
        lexical = self.lexical.for_node(node)
        child = BindingScope(
            f"{scope.name}.{node.name}",
            scope,
            lexical.locals,
            lexical.globals,
            lexical.nonlocals,
            kind="class",
        )
        self.block(node.body, child)
        scope.assign(
            node.name,
            self.sources.record(self, node, scope) if self.sources else BindingValue(local=True),
        )

    @statement.register
    def delete_binding(self, node: ast.Delete, scope: BindingScope) -> None:
        """Deletion kills a binding instead of resurrecting its outer namesake."""
        for target in node.targets:
            self.assign(target, BindingValue(unknown=True), scope)

    def assign(self, target: ast.AST, value: BindingValue, scope: BindingScope) -> None:
        """Bind names, destructuring and exact object-member replacements."""
        if isinstance(target, ast.Name):
            scope.assign(target.id, value)
        elif isinstance(target, ast.Tuple | ast.List):
            value = project(value, MemberDemand("structure"), scope, self.sources, self.result)
            symbolic = bool(value.parameters or value.projections) and value.items is None
            for index, item in enumerate(target.elts):
                self.assign(
                    item,
                    value.items[index]
                    if value.items is not None and index < len(value.items)
                    else project(value, MemberDemand("index", key=index), scope, None, self.result)
                    if symbolic
                    else BindingValue(
                        deferred=value.deferred,
                        unknown=value.unknown or value.items is not None or not value.deferred,
                    ),
                    scope,
                )
        elif isinstance(target, ast.Attribute):
            value_owner = self.expression(target.value, scope)
            if self.sources is not None:
                self.sources.invocations.note_mutation(scope, value_owner, native_store=True)
            for owner in value_owner.targets:
                scope.assign_member(f"{owner}.{target.attr}", value)
        elif isinstance(target, ast.Subscript):
            self.assign_item(target, value, scope)

    def assign_item(self, target: ast.Subscript, value: BindingValue, scope: BindingScope) -> None:
        """Replace only exact single-owner mapping slots; join alternatives or havoc the heap."""
        owner = self.expression(target.value, scope)
        if self.sources is not None:
            self.sources.invocations.note_mutation(scope, owner)
        key = self.expression(target.slice, scope)
        strong = len(owner.aggregates) == 1 and not (
            owner.unknown or owner.deferred or key.unknown or key.deferred
        )
        for identity in owner.aggregates:
            current, exact = scope.member(identity), strong and identity not in scope.summarized
            scope.assign_member(identity, stored(current, target.slice, key, value, strong=exact))

    @singledispatchmethod
    def expression(self, node: ast.AST, scope: BindingScope) -> BindingValue:
        """Unknown expressions retain observed children but not invented values."""
        children = [
            self.expression(child, scope)
            for child in ast.iter_child_nodes(node)
            if isinstance(child, ast.expr)
        ]
        return BindingValue(deferred=any(item.deferred for item in children), unknown=True)

    @expression.register
    def literal(self, node: ast.Constant, _scope: BindingScope) -> BindingValue:
        """Preserve closed primitive truth without treating literal spelling as an effect."""
        if isinstance(node.value, str):
            return BindingValue(strings=frozenset({node.value}))
        if node.value is None or isinstance(node.value, bool | int | float | complex | bytes):
            return BindingValue(truths=frozenset({bool(node.value)}))
        return BindingValue(local=True)

    @expression.register
    def name(self, node: ast.Name, scope: BindingScope) -> BindingValue:
        """Read the current lexical binding."""
        return (
            self.sources.invocations.read(scope, node.id)
            if self.sources is not None
            else scope.resolve(scope.lookup(node.id))
        )

    @expression.register
    def attribute(self, node: ast.Attribute, scope: BindingScope) -> BindingValue:
        """Qualified members retain owner provenance and mutation state."""
        owner = self.expression(node.value, scope)
        return self.result.attribute((owner, BindingValue(strings=frozenset({node.attr}))), scope)

    @expression.register
    def sequence(self, node: ast.List | ast.Tuple | ast.Set, scope: BindingScope) -> BindingValue:
        """Preserve finite elements for command prefixes and iteration."""
        value = BindingValue(
            items=tuple(self.expression(item, scope) for item in node.elts),
            ordered=isinstance(node, ast.List | ast.Tuple),
            native_kind="list" if isinstance(node, ast.List) else "",
        )
        return value if isinstance(node, ast.Tuple) else scope.aggregate(value, node)

    @expression.register
    def mapping(self, node: ast.Dict, scope: BindingScope) -> BindingValue:
        """Bound string-key mappings preserve insertion order and alias identity."""
        entries: dict[str, BindingValue] = {}
        unknown = len(node.keys) > 64
        for key, value in zip(node.keys, node.values, strict=True):
            selected = (
                self.expression(key, scope) if key is not None else BindingValue(unknown=True)
            )
            item = self.expression(value, scope)
            if len(selected.strings) == 1 and not selected.unknown and not selected.deferred:
                entries[next(iter(selected.strings))] = item
            else:
                unknown = True
        return scope.aggregate(
            BindingValue(
                entries=None if unknown else tuple(entries.items()), unknown=unknown, ordered=True
            ),
            node,
        )

    @expression.register
    def starred(self, node: ast.Starred, scope: BindingScope) -> BindingValue:
        """Unresolved expansion cannot claim a complete finite sequence."""
        value = self.expression(node.value, scope)
        return BindingValue(deferred=value.deferred, unknown=True, spread=True)

    @expression.register
    def binary(self, node: ast.BinOp, scope: BindingScope) -> BindingValue:
        """Evaluate supported literal composition and retain other operations as unknown."""
        left, right = self.expression(node.left, scope), self.expression(node.right, scope)
        if self.sources is not None:
            left = self.sources.invocations.resolve(left, scope, self.result)
            right = self.sources.invocations.resolve(right, scope, self.result)
        if isinstance(node.op, ast.Div) and left.path and right.strings:
            value = BindingValue()
            for suffix in right.strings:
                if suffix in {"", "."}:
                    current = left
                elif suffix == ".." or "/" in suffix or "\\" in suffix:
                    current = BindingValue(unknown=True)
                else:
                    current = BindingValue(
                        path=True,
                        strings=frozenset({suffix}),
                        deferred=left.deferred or right.deferred or bool(left.parameters),
                        unknown=left.unknown or right.unknown,
                    )
                value = value.join(current)
            return value
        if isinstance(node.op, ast.Add):
            left = project(left, MemberDemand("structure"), scope, self.sources, self.result)
            right = project(right, MemberDemand("structure"), scope, self.sources, self.result)
        return self.combine(left, right, node.op)

    def truth(self, value: BindingValue, scope: BindingScope) -> BindingValue:
        """Consume closed truth independently of operand identity and mutable contents."""
        return project(value, MemberDemand("truth"), scope, self.sources, self.result)

    @expression.register
    def conditional_value(self, node: ast.IfExp, scope: BindingScope) -> BindingValue:
        """Observe alternative values at the same program point."""
        branches = scope.alternatives(
            node.test, self.truth(self.expression(node.test, scope), scope)
        )
        value = BindingValue()
        for truth, branch in branches:
            value = value.join(self.expression(node.body if truth else node.orelse, branch))
        scope.merge(*(branch for _, branch in branches))
        return value

    @expression.register
    def boolean_value(self, node: ast.BoolOp, scope: BindingScope) -> BindingValue:
        """Observe short-circuit values and effects only on reachable alternatives."""
        result = BindingValue()
        branch = scope.fork()
        exits = []
        for index, child in enumerate(node.values):
            value = self.expression(child, branch)
            truth = self.truth(value, branch).truthiness()
            last = index == len(node.values) - 1
            if last or truth is None or truth == isinstance(node.op, ast.Or):
                result = result.join(
                    value if last else value.guarded(truth=isinstance(node.op, ast.Or))
                )
                exit_branch = branch.fork()
                if not last:
                    exit_branch.assume(child, truth=isinstance(node.op, ast.Or))
                exits.append(exit_branch)
            if last or truth == isinstance(node.op, ast.Or):
                break
            branch.assume(child, truth=isinstance(node.op, ast.And))
        scope.merge(*exits)
        return result

    @expression.register
    def named_value(self, node: ast.NamedExpr, scope: BindingScope) -> BindingValue:
        """Expression assignment updates its containing lexical namespace."""
        value = self.expression(node.value, scope)
        target = scope.parent if scope.kind == "comprehension" and scope.parent else scope
        self.assign(node.target, value, target)
        return value

    @expression.register
    def lambda_value(self, node: ast.Lambda, scope: BindingScope) -> BindingValue:
        """A local callable supplies no stdlib provenance by name alone."""
        value = (
            self.sources.definition(
                self,
                node,
                scope,
                tuple(self.expression(value, scope) for value in node.args.defaults),
                tuple(
                    self.expression(value, scope) if value is not None else None
                    for value in node.args.kw_defaults
                ),
            )
            if self.sources
            else BindingValue(local=True)
        )
        self.defer(node, scope, value)
        return value

    @expression.register
    def call(self, node: ast.Call, scope: BindingScope) -> BindingValue:
        """Select the callable before arguments, preserving Python evaluation order."""
        callee = self.expression(node.func, scope)
        if self.sources is not None:
            callee = self.sources.invocations.resolve(callee, scope, self.result, deep=False)
        args = tuple(self.expression(argument, scope) for argument in node.args)
        keywords = {
            argument.arg: self.expression(argument.value, scope) for argument in node.keywords
        }
        if self.sources is not None:
            returned = self.sources.call(callee, args, keywords, node, scope, self.result)
            if returned is not None:
                return returned
        return self.result.call(callee, args, keywords, node, scope)

    @expression.register
    def subscript(self, node: ast.Subscript, scope: BindingScope) -> BindingValue:
        """Environment indexing consumes only a proven namespace."""
        owner, index = self.expression(node.value, scope), self.expression(node.slice, scope)
        if self.sources is not None:
            owner = self.sources.invocations.resolve(owner, scope, self.result, deep=False)
        if "os.environ" in owner.targets or (
            owner.native_kind == "environment"
            and not (index.strings and index.strings <= dict(owner.entries or ()).keys())
        ):
            self.result.consume("value", index, node, scope, "os.environ.__getitem__")
            return BindingValue(deferred=True)
        if owner.parameters and self.sources is not None:
            name = BindingValue(strings=frozenset({"__getitem__"}))
            method = self.result.attribute((owner, name), scope)
            self.sources.invocations.note_call(method, (index,), {}, node, self.path, scope)
        key = (
            node.slice.value
            if isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, str | int)
            and not isinstance(node.slice.value, bool)
            else None
        )
        return project(
            owner,
            MemberDemand("index", key=key, selector=index if key is None else None),
            scope,
            self.sources,
            self.result,
        )

    @expression.register
    def interpolated(self, node: ast.JoinedStr, scope: BindingScope) -> BindingValue:
        """Retain supported strings without guessing formatted objects."""
        value = BindingValue(strings=frozenset({""}))
        for part in node.values:
            value = concatenate(value, self.expression(part, scope))
        return value

    @expression.register
    def formatted(self, node: ast.FormattedValue, scope: BindingScope) -> BindingValue:
        """Preserve literal formatting only without a format spec or opaque conversion."""
        value = self.expression(node.value, scope)
        if node.format_spec is not None:
            self.expression(node.format_spec, scope)
        return (
            value
            if node.format_spec is None and node.conversion in {-1, ord("s")}
            else (BindingValue(deferred=value.deferred, unknown=True))
        )

    @expression.register
    def comprehension(
        self,
        node: ast.ListComp | ast.SetComp | ast.DictComp | ast.GeneratorExp,
        scope: BindingScope,
    ) -> BindingValue:
        """Comprehension targets never overwrite the surrounding namespace."""
        child = BindingScope(f"{scope.name}.<comprehension>", scope, kind="comprehension")
        for index, generator in enumerate(node.generators):
            value = self.expression(generator.iter, scope if index == 0 else child)
            self.assign(
                generator.target,
                project(value, MemberDemand("iterate"), child, self.sources, self.result),
                child,
            )
            for condition in generator.ifs:
                self.expression(condition, child)
        if isinstance(node, ast.DictComp):
            self.expression(node.key, child)
            self.expression(node.value, child)
        else:
            self.expression(node.elt, child)
        return BindingValue(deferred=isinstance(node, ast.GeneratorExp), unknown=True)

    @staticmethod
    def combine(left: BindingValue, right: BindingValue, operator: ast.operator) -> BindingValue:
        """Compose supported values while preserving loss of operation coverage."""
        if isinstance(operator, ast.Add):
            return concatenate(left, right)
        return BindingValue(deferred=left.deferred or right.deferred, unknown=True)
