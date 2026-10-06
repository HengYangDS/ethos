"""Terminal-aware paths for the shared finite Python observation."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from dataclasses import field
from functools import singledispatchmethod
from typing import TYPE_CHECKING
from typing import Literal

from ethos.repository.policy.references.python.bindings import BindingScope
from ethos.repository.policy.references.python.bindings import BindingValue
from ethos.repository.policy.references.python.bindings import MemberDemand
from ethos.repository.policy.references.python.functions.effects import project

if TYPE_CHECKING:
    from ethos.repository.policy.references.python.flow import PythonReferenceFlow


@dataclass(frozen=True, slots=True)
class FlowExit:
    """A path's current environment and pending Python completion."""

    scope: BindingScope
    kind: Literal["normal", "return", "raise", "break", "continue"] = "normal"
    value: BindingValue = field(default_factory=BindingValue)


@dataclass(slots=True)
class PythonControlFlow:
    """Continue only live paths; finalizers preserve or replace pending completions."""

    flow: PythonReferenceFlow

    def block(self, statements: list[ast.stmt], scope: BindingScope) -> tuple[FlowExit, ...]:
        """Observe statements in order without merging exited paths into continuations."""
        paths = (FlowExit(scope),)
        for node in statements:
            paths = self.bounded(
                tuple(
                    result
                    for path in paths
                    for result in (
                        self.statement(node, path.scope) if path.kind == "normal" else (path,)
                    )
                )
            )
        return paths

    @staticmethod
    def bounded(paths: tuple[FlowExit, ...]) -> tuple[FlowExit, ...]:
        """Widen only an exhausted path set, retaining its distinct exit relationships."""
        joined: dict[str, FlowExit] = {}
        for path in paths:
            previous = joined.get(path.kind)
            if previous is None:
                joined[path.kind] = path
                continue
            scope = previous.scope.fork()
            scope.merge(previous.scope, path.scope)
            joined[path.kind] = FlowExit(
                scope,
                path.kind,
                previous.value.join(path.value),
            )
        return tuple(joined.values())

    @singledispatchmethod
    def statement(self, node: ast.stmt, scope: BindingScope) -> tuple[FlowExit, ...]:
        """Non-control syntax uses the same binding and effect owner."""
        self.flow.statement(node, scope)
        return (FlowExit(scope),)

    @statement.register
    def returned(self, node: ast.Return, scope: BindingScope) -> tuple[FlowExit, ...]:
        """Capture the value before finalization, preserving reachable mutable aliases."""
        value = self.flow.expression(node.value, scope) if node.value else BindingValue(local=True)
        return (FlowExit(scope, "return", value),)

    @statement.register
    def raised(self, node: ast.Raise, scope: BindingScope) -> tuple[FlowExit, ...]:
        """A raised path cannot contribute a successful return."""
        self.flow.statement(node, scope)
        return (FlowExit(scope, "raise"),)

    @statement.register
    def broken(self, _node: ast.Break, scope: BindingScope) -> tuple[FlowExit, ...]:
        """Preserve loop completion until its owning loop consumes it."""
        return (FlowExit(scope, "break"),)

    @statement.register
    def continued(self, _node: ast.Continue, scope: BindingScope) -> tuple[FlowExit, ...]:
        """A continue skips the remaining body, not the next iteration."""
        return (FlowExit(scope, "continue"),)

    @statement.register
    def conditional(self, node: ast.If, scope: BindingScope) -> tuple[FlowExit, ...]:
        """Guard each live branch independently and preserve all feasible exits."""
        value = self.flow.truth(self.flow.expression(node.test, scope), scope)
        return tuple(
            result
            for truth, branch in scope.alternatives(node.test, value)
            for result in self.block(node.body if truth else node.orelse, branch)
        )

    @statement.register
    def context(self, node: ast.With | ast.AsyncWith, scope: BindingScope) -> tuple[FlowExit, ...]:
        """Observe context construction without pretending opaque exit methods are pure."""
        for item in node.items:
            self.flow.expression(item.context_expr, scope)
            if item.optional_vars:
                self.flow.assign(item.optional_vars, BindingValue(unknown=True), scope)
        paths = self.block(node.body, scope)
        for path in paths:
            path.scope.invalidate_aggregates(*path.scope.values.values(), path.value)
        return tuple(
            FlowExit(path.scope, path.kind, path.value.join(BindingValue(unknown=True)))
            if path.kind == "return"
            else path
            for path in paths
        )

    @statement.register
    def exception_paths(
        self, node: ast.Try | ast.TryStar, scope: BindingScope
    ) -> tuple[FlowExit, ...]:
        """Else follows normal completion; finally runs on every pending outcome."""
        outgoing = self.block(node.body, scope.fork())
        paths = []
        for path in outgoing:
            paths.extend(self.block(node.orelse, path.scope) if path.kind == "normal" else (path,))
        exceptional = [path.scope for path in outgoing if path.kind == "raise"]
        for handler in node.handlers:
            branches = exceptional or [scope]
            for origin in branches:
                branch = origin.fork()
                if handler.type is not None:
                    self.flow.expression(handler.type, branch)
                if handler.name:
                    branch.assign(handler.name, BindingValue(local=True))
                paths.extend(self.block(handler.body, branch))
        return tuple(
            FlowExit(final.scope, path.kind, path.value) if final.kind == "normal" else final
            for path in paths
            for final in self.block(node.finalbody, path.scope)
        )

    @statement.register
    def loop(
        self, node: ast.For | ast.AsyncFor | ast.While, scope: BindingScope
    ) -> tuple[FlowExit, ...]:
        """Keep exact finite iteration; otherwise join and widen recurrent environments."""
        value = self.flow.expression(
            node.iter if isinstance(node, ast.For | ast.AsyncFor) else node.test, scope
        )
        if isinstance(node, ast.For | ast.AsyncFor):
            shape = project(
                value, MemberDemand("iteration_shape"), scope, self.flow.sources, self.flow.result
            )
        else:
            shape = self.flow.truth(value, scope)
        if (
            isinstance(node, ast.For)
            and shape.ordered
            and shape.items is not None
            and not (shape.unknown or shape.deferred or shape.parameters or shape.projections)
            and len(shape.items) <= 64
        ):
            return self.finite_loop(node, value, shape, scope)
        return self.recurrent_loop(node, value, scope)

    def finite_loop(
        self, node: ast.For, value: BindingValue, shape: BindingValue, scope: BindingScope
    ) -> tuple[FlowExit, ...]:
        """Plan finite shape while demanding each live yield at its own program point."""
        assert shape.items is not None
        active, exited, unresolved = (FlowExit(scope),), [], []
        for index in range(len(shape.items) + 1):
            following = []
            for path in active:
                with path.scope.iteration(node, index):
                    current = project(
                        value,
                        MemberDemand("iteration_shape"),
                        path.scope,
                        self.flow.sources,
                        self.flow.result,
                    )
                    if current != shape:
                        self.flow.result.residual(
                            "value",
                            "unknown",
                            node,
                            path.scope,
                            "builtins.iter",
                            "iteration_topology_not_closed",
                        )
                        unresolved.extend(self.recurrent_loop(node, value, path.scope))
                        continue
                    if index == len(shape.items):
                        exited.append(path)
                        continue
                    item = project(
                        value,
                        MemberDemand("iterate", key=index),
                        path.scope,
                        self.flow.sources,
                        self.flow.result,
                    )
                    self.flow.assign(node.target, item, path.scope)
                    for result in self.block(node.body, path.scope):
                        (following if result.kind in {"normal", "continue"} else exited).append(
                            result
                        )
            active = tuple(following)
        return (*self.loop_exits(node, tuple(exited)), *unresolved)

    def recurrent_loop(
        self, node: ast.For | ast.AsyncFor | ast.While, value: BindingValue, scope: BindingScope
    ) -> tuple[FlowExit, ...]:
        """Widen recurrent environments and re-observe the widened body before leaving."""
        head, exited = scope.fork(), []
        for _ in range(8):
            branch = head.fork()
            if isinstance(node, ast.For | ast.AsyncFor):
                self.flow.assign(
                    node.target,
                    project(
                        value, MemberDemand("iterate"), branch, self.flow.sources, self.flow.result
                    ),
                    branch,
                )
            else:
                self.flow.truth(self.flow.expression(node.test, branch), branch)
            paths = self.block(node.body, branch)
            continuing = [path.scope for path in paths if path.kind in {"normal", "continue"}]
            exited.extend(path for path in paths if path.kind not in {"normal", "continue"})
            joined = head.fork()
            joined.merge(head, *continuing)
            if joined.values == head.values and joined.members == head.members:
                head = joined
                break
            head = joined
        else:
            for name in head.values:
                if head.lookup(name) != scope.lookup(name):
                    head.assign(name, head.lookup(name).join(BindingValue(unknown=True)))
            for name in head.members:
                if head.member(name) != scope.member(name):
                    head.assign_member(name, head.member(name).join(BindingValue(unknown=True)))
            branch = head.fork()
            if isinstance(node, ast.For | ast.AsyncFor):
                self.flow.assign(
                    node.target,
                    project(
                        value, MemberDemand("iterate"), branch, self.flow.sources, self.flow.result
                    ),
                    branch,
                )
            else:
                self.flow.truth(self.flow.expression(node.test, branch), branch)
            paths = self.block(node.body, branch)
            exited.extend(path for path in paths if path.kind not in {"normal", "continue"})
            head.merge(
                head.fork(), *(path.scope for path in paths if path.kind in {"normal", "continue"})
            )
        return self.loop_exits(node, self.bounded((FlowExit(head), *exited)))

    def loop_exits(
        self, node: ast.For | ast.AsyncFor | ast.While, paths: tuple[FlowExit, ...]
    ) -> tuple[FlowExit, ...]:
        """Break bypasses else; return and raise remain pending to the enclosing block."""
        return tuple(
            result
            for path in paths
            for result in (
                self.block(node.orelse, path.scope)
                if path.kind in {"normal", "continue"}
                else (FlowExit(path.scope),)
                if path.kind == "break"
                else (path,)
            )
        )
