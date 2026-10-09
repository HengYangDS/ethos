"""Assign syntax targets through exact lexical, class and instance storage ownership."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from dataclasses import replace
from typing import TYPE_CHECKING

from ethos.repository.policy.references.python.bindings import BindingValue
from ethos.repository.policy.references.python.bindings import MemberDemand
from ethos.repository.policy.references.python.functions.effects import project

if TYPE_CHECKING:
    from ethos.repository.policy.references.python.flow import PythonReferenceFlow
    from ethos.repository.policy.references.python.scope import BindingScope


@dataclass(slots=True)
class PythonStores:
    """One current flow supplies value observation; this owner applies writes."""

    flow: PythonReferenceFlow

    def assign(self, target: ast.AST, value: BindingValue, scope: BindingScope) -> None:
        """Bind names, destructuring and exact object-member replacements."""
        if isinstance(target, ast.Name):
            scope.assign(target.id, value)
        elif isinstance(target, ast.Tuple | ast.List):
            value = project(
                value, MemberDemand("structure"), scope, self.flow.sources, self.flow.result
            )
            for index, item in enumerate(target.elts):
                self.assign(
                    item,
                    value.items[index]
                    if value.items is not None and index < len(value.items)
                    else BindingValue(
                        deferred=value.deferred,
                        unknown=value.unknown or value.items is not None or not value.deferred,
                    ),
                    scope,
                )
        elif isinstance(target, ast.Attribute):
            self.assign_attribute(target, value, scope)
        elif isinstance(target, ast.Subscript):
            self.assign_item(target, value, scope)

    def assign_attribute(
        self, target: ast.Attribute, value: BindingValue, scope: BindingScope
    ) -> None:
        """Resolve the actual store owner before updating class or native instance custody."""
        owner = self.flow.expression(target.value, scope)
        if self.flow.sources is not None:
            owner = self.flow.sources.call_identity(
                self.flow.sources.invocations.resolve(owner, scope, self.flow.result, deep=False)
            )
            value = self.flow.sources.call_identity(value)
            self.flow.sources.invocations.note_mutation(scope, owner, native_store=True)
        if owner.instance_types:
            self.assign_instance_member(target, owner, value, scope)
        strong = len(owner.targets) == 1 and owner == BindingValue(targets=owner.targets)
        for identity in owner.targets:
            if self.flow.sources is None or not self.flow.sources.classes.store(
                identity, target.attr, value, scope, strong=strong
            ):
                member = f"{identity}.{target.attr}"
                scope.assign_member(member, value if strong else scope.member(member).join(value))

    def assign_instance_member(
        self,
        target: ast.Attribute,
        owner: BindingValue,
        value: BindingValue,
        scope: BindingScope,
    ) -> None:
        """An unmodeled store may dispatch or change identity, not silently create a field."""
        native = self.flow.sources is not None and self.flow.sources.classes.instance_storage(
            owner, target.attr, scope
        )
        if not native:
            self.flow.result.escape((owner, value), target, scope)
        strong = len(owner.aggregates) == 1 and owner == BindingValue(
            fields=owner.fields,
            optional_fields=owner.optional_fields,
            aggregates=owner.aggregates,
            instance_types=owner.instance_types,
            allocation_complete=True,
        )
        for identity in owner.aggregates:
            current = scope.member(identity)
            if not native:
                scope.assign_member(identity, replace(current, unknown=True))
                continue
            fields = dict(current.fields or ())
            replace_field = strong and identity not in scope.summarized
            optional = current.optional_fields
            if replace_field:
                optional -= {target.attr}
            elif target.attr not in fields:
                optional |= {target.attr}
            fields[target.attr] = (
                value if replace_field else fields.get(target.attr, BindingValue()).join(value)
            )
            scope.assign_member(
                identity, replace(current, fields=tuple(fields.items()), optional_fields=optional)
            )

    def assign_item(self, target: ast.Subscript, value: BindingValue, scope: BindingScope) -> None:
        """Replace only exact single-owner mapping slots; join alternatives or havoc the heap."""
        owner = self.flow.expression(target.value, scope)
        if self.flow.sources is not None:
            self.flow.sources.invocations.note_mutation(scope, owner)
        key = self.flow.expression(target.slice, scope)
        for identity in owner.aggregates:
            current = scope.member(identity)
            if current.entries is not None and len(key.strings) == 1:
                entries = dict(current.entries)
                name = next(iter(key.strings))
                entries[name] = (
                    value
                    if len(owner.aggregates) == 1
                    and identity not in scope.summarized
                    and not (owner.unknown or owner.deferred or key.unknown or key.deferred)
                    else entries.get(name, BindingValue(unknown=True)).join(value)
                )
                scope.assign_member(
                    identity,
                    replace(current, entries=tuple(entries.items()), mapping_shapes=None),
                )
            else:
                scope.assign_member(identity, BindingValue(unknown=True))
