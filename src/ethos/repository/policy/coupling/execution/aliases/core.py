"""Resolve bounded static references to known external execution APIs."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

import ethos.repository.policy.coupling.execution.aliases.catalog as catalog
from ethos.repository.policy.coupling.execution.aliases.catalog import alias_key
from ethos.repository.policy.coupling.execution.aliases.catalog import literal_subscript_key
from ethos.repository.policy.coupling.execution.aliases.catalog import static_mapping_items

if TYPE_CHECKING:
    from collections.abc import Callable

_BUILTINS_MODULE = "<builtin>.module"
_DYNAMIC_REFERENCE = f"execution{catalog.DYNAMIC_EXECUTION_FUNCTION_SUFFIX}"
GETATTR_ALIAS = "<builtin>.getattr"
SHADOWED_GETATTR_ALIAS = "<builtin>.getattr-shadowed"
_NON_EXECUTION_CALLABLES = frozenset({GETATTR_ALIAS, SHADOWED_GETATTR_ALIAS})
_MIN_GETATTR_ARGUMENTS = 2


def execution_function(
    node: ast.Call,
    module_aliases: dict[str, frozenset[str]],
    function_aliases: dict[str, frozenset[str]],
) -> str | None:
    """Return one known execution function or a fail-closed dynamic marker."""
    candidates = execution_reference(node.func, module_aliases, function_aliases)
    if len(candidates) == 1:
        return next(iter(candidates))
    return f"execution{catalog.DYNAMIC_EXECUTION_FUNCTION_SUFFIX}" if candidates else None


def execution_reference(
    function: ast.expr,
    module_aliases: dict[str, frozenset[str]],
    function_aliases: dict[str, frozenset[str]],
) -> frozenset[str]:
    """Return execution functions, excluding non-execution callable markers."""
    return callable_reference(function, module_aliases, function_aliases).difference(
        _NON_EXECUTION_CALLABLES
    )


def callable_reference(
    function: ast.expr,
    module_aliases: dict[str, frozenset[str]],
    function_aliases: dict[str, frozenset[str]],
) -> frozenset[str]:
    """Return bounded callable aliases, including the builtin ``getattr`` marker."""
    key = alias_key(function)
    if key is not None and (aliases := function_aliases.get(key)):
        return aliases
    if isinstance(function, ast.Attribute):
        candidates = _attribute_callable_reference(function, module_aliases, function_aliases)
    elif isinstance(function, ast.Subscript):
        candidates = _subscript_callable_reference(function, module_aliases, function_aliases)
    elif isinstance(function, ast.Call):
        if is_getattr_reference(function.func, module_aliases, function_aliases):
            candidates = _getattr_callable_reference(function, module_aliases, function_aliases)
        else:
            candidates = _mapping_get_callable_reference(function, module_aliases, function_aliases)
    elif isinstance(function, ast.IfExp):
        candidates = callable_reference(function.body, module_aliases, function_aliases).union(
            callable_reference(function.orelse, module_aliases, function_aliases)
        )
    elif isinstance(function, ast.Name) and function.id == "getattr":
        candidates = frozenset({GETATTR_ALIAS})
    else:
        candidates = frozenset()
    return candidates


def module_reference(
    reference: ast.expr,
    module_aliases: dict[str, frozenset[str]],
    function_aliases: dict[str, frozenset[str]] | None = None,
) -> frozenset[str]:
    """Return all known execution modules denoted by one AST expression."""
    functions = function_aliases or {}
    key = alias_key(reference)
    if key is not None and (aliases := module_aliases.get(key)):
        return aliases
    if isinstance(reference, ast.Attribute):
        return _attribute_module_reference(reference, module_aliases, functions)
    if isinstance(reference, ast.Subscript):
        return _subscript_module_reference(reference, module_aliases, functions)
    if isinstance(reference, ast.Call):
        return _call_module_reference(reference, module_aliases, functions)
    if isinstance(reference, ast.IfExp):
        return module_reference(reference.body, module_aliases, functions).union(
            module_reference(reference.orelse, module_aliases, functions)
        )
    return frozenset()


def imported_execution_module(module: str) -> str | None:
    """Return the canonical module bound by one import statement."""
    if module == "builtins":
        return _BUILTINS_MODULE
    return _canonical_execution_module(module)


def imported_execution_module_from(module: str, name: str) -> str | None:
    """Return the execution module imported by one from-import binding."""
    if _canonical_execution_module(module) == "asyncio" and name == "subprocess":
        return "asyncio"
    return None


def imported_callable_alias(module: str, name: str) -> str | None:
    """Return the bounded callable marker imported by one from-import binding."""
    return GETATTR_ALIAS if module == "builtins" and name == "getattr" else None


def imported_execution_functions(module: str) -> frozenset[str]:
    """Return known public execution functions introduced by one star import."""
    canonical_module = _canonical_execution_module(module)
    if canonical_module is None:
        return frozenset()
    return frozenset(
        f"{canonical_module}.{function}"
        for function in catalog.EXECUTION_FUNCTIONS_BY_MODULE[canonical_module]
    )


def canonical_execution_function(module: str, function: str) -> str | None:
    """Return the canonical execution function represented by module and name."""
    canonical_module = _canonical_execution_module(module)
    if canonical_module is None:
        return None
    declared = catalog.EXECUTION_FUNCTIONS_BY_MODULE[canonical_module]
    return f"{canonical_module}.{function}" if function in declared else None


def is_getattr_reference(
    reference: ast.expr,
    module_aliases: dict[str, frozenset[str]],
    function_aliases: dict[str, frozenset[str]],
) -> bool:
    """Return whether one expression resolves to the builtin ``getattr`` callable."""
    return GETATTR_ALIAS in callable_reference(reference, module_aliases, function_aliases)


def _attribute_callable_reference(
    function: ast.Attribute,
    module_aliases: dict[str, frozenset[str]],
    function_aliases: dict[str, frozenset[str]],
) -> frozenset[str]:
    if isinstance(function.value, ast.Call) and is_getattr_reference(
        function.value.func, module_aliases, function_aliases
    ):
        modules = _getattr_module_reference(function.value, module_aliases, function_aliases)
    else:
        modules = module_reference(function.value, module_aliases, function_aliases)
    candidates = _callable_attributes(modules, function.attr)
    if candidates:
        return candidates
    return _attribute_reference(function.value, function.attr, function_aliases)


def _subscript_callable_reference(
    function: ast.Subscript,
    module_aliases: dict[str, frozenset[str]],
    function_aliases: dict[str, frozenset[str]],
) -> frozenset[str]:
    if (base := _dunder_dict_base(function.value)) is not None:
        return _dunder_dict_callable_reference(
            base,
            function.slice,
            module_aliases,
            function_aliases,
        )
    key = literal_subscript_key(function.slice)
    if key is not None:
        direct = _literal_container_callable_reference(
            function.value,
            function.slice,
            module_aliases,
            function_aliases,
        )
        if direct:
            return direct
        modules = module_reference(function.value, module_aliases, function_aliases)
        candidates = _callable_attributes(modules, _literal_string(function.slice) or "")
        return candidates or _mapping_item_reference(function.value, key, function_aliases)
    return _dynamic_mapping_callable_reference(function.value, module_aliases, function_aliases)


def _getattr_callable_reference(
    reference: ast.Call,
    module_aliases: dict[str, frozenset[str]],
    function_aliases: dict[str, frozenset[str]],
) -> frozenset[str]:
    if not reference.args:
        return frozenset()
    if len(reference.args) < _MIN_GETATTR_ARGUMENTS:
        return _dynamic_getattr_callable_reference(
            reference.args[0], module_aliases, function_aliases
        )
    attribute = _literal_string(reference.args[1])
    if attribute is None:
        return _dynamic_getattr_callable_reference(
            reference.args[0], module_aliases, function_aliases
        )
    aliases = _attribute_reference(reference.args[0], attribute, function_aliases)
    if aliases:
        return aliases
    modules = module_reference(reference.args[0], module_aliases, function_aliases)
    return _callable_attributes(modules, attribute)


def _mapping_get_callable_reference(
    reference: ast.Call,
    module_aliases: dict[str, frozenset[str]],
    function_aliases: dict[str, frozenset[str]],
) -> frozenset[str]:
    if not isinstance(reference.func, ast.Attribute) or reference.func.attr != "get":
        return frozenset()
    if not reference.args:
        return frozenset()
    mapping = reference.func.value
    if (base := _dunder_dict_base(mapping)) is not None:
        return _dunder_dict_callable_reference(
            base,
            reference.args[0],
            module_aliases,
            function_aliases,
        )
    key = literal_subscript_key(reference.args[0])
    if key is not None:
        direct = _literal_container_callable_reference(
            mapping,
            reference.args[0],
            module_aliases,
            function_aliases,
        )
        if direct:
            return direct
        modules = module_reference(mapping, module_aliases, function_aliases)
        candidates = _callable_attributes(modules, _literal_string(reference.args[0]) or "")
        return candidates or _mapping_item_reference(mapping, key, function_aliases)
    return _dynamic_mapping_callable_reference(mapping, module_aliases, function_aliases)


def _attribute_module_reference(
    reference: ast.Attribute,
    module_aliases: dict[str, frozenset[str]],
    function_aliases: dict[str, frozenset[str]],
) -> frozenset[str]:
    modules = module_reference(reference.value, module_aliases, function_aliases)
    if reference.attr == "__dict__" and modules:
        return modules
    return _module_attributes(modules, reference.attr) or _attribute_reference(
        reference.value,
        reference.attr,
        module_aliases,
    )


def _subscript_module_reference(
    reference: ast.Subscript,
    module_aliases: dict[str, frozenset[str]],
    function_aliases: dict[str, frozenset[str]],
) -> frozenset[str]:
    if (base := _dunder_dict_base(reference.value)) is not None:
        return _dunder_dict_module_reference(
            base,
            reference.slice,
            module_aliases,
            function_aliases,
        )
    key = literal_subscript_key(reference.slice)
    if key is not None:
        direct = _literal_container_module_reference(
            reference.value,
            reference.slice,
            module_aliases,
            function_aliases,
        )
        return direct or _mapping_item_reference(reference.value, key, module_aliases)
    return _dynamic_mapping_module_reference(reference.value, module_aliases, function_aliases)


def _call_module_reference(
    reference: ast.Call,
    module_aliases: dict[str, frozenset[str]],
    function_aliases: dict[str, frozenset[str]],
) -> frozenset[str]:
    if is_getattr_reference(reference.func, module_aliases, function_aliases):
        return _getattr_module_reference(reference, module_aliases, function_aliases)
    return _mapping_get_module_reference(reference, module_aliases, function_aliases)


def _getattr_module_reference(
    reference: ast.Call,
    module_aliases: dict[str, frozenset[str]],
    function_aliases: dict[str, frozenset[str]],
) -> frozenset[str]:
    if not reference.args:
        return frozenset()
    if (
        len(reference.args) >= _MIN_GETATTR_ARGUMENTS
        and (attribute := _literal_string(reference.args[1])) is not None
    ):
        aliases = _attribute_reference(reference.args[0], attribute, module_aliases)
        if aliases:
            return aliases
        modules = module_reference(reference.args[0], module_aliases, function_aliases)
        return _module_attributes(modules, attribute)
    if _has_known_attribute_alias(reference.args[0], module_aliases):
        return frozenset({_DYNAMIC_REFERENCE})
    return frozenset()


def _mapping_get_module_reference(
    reference: ast.Call,
    module_aliases: dict[str, frozenset[str]],
    function_aliases: dict[str, frozenset[str]],
) -> frozenset[str]:
    if not isinstance(reference.func, ast.Attribute) or reference.func.attr != "get":
        return frozenset()
    if not reference.args:
        return frozenset()
    mapping = reference.func.value
    if (base := _dunder_dict_base(mapping)) is not None:
        return _dunder_dict_module_reference(
            base,
            reference.args[0],
            module_aliases,
            function_aliases,
        )
    key = literal_subscript_key(reference.args[0])
    if key is not None:
        direct = _literal_container_module_reference(
            mapping,
            reference.args[0],
            module_aliases,
            function_aliases,
        )
        return direct or _mapping_item_reference(mapping, key, module_aliases)
    return _dynamic_mapping_module_reference(mapping, module_aliases, function_aliases)


def _dunder_dict_callable_reference(
    base: ast.expr,
    slice_node: ast.expr,
    module_aliases: dict[str, frozenset[str]],
    function_aliases: dict[str, frozenset[str]],
) -> frozenset[str]:
    attribute = _literal_string(slice_node)
    if attribute is not None:
        aliases = _attribute_reference(base, attribute, function_aliases)
        if aliases:
            return aliases
        modules = module_reference(base, module_aliases, function_aliases)
        return _callable_attributes(modules, attribute)
    modules = module_reference(base, module_aliases, function_aliases)
    if modules or _has_known_attribute_alias(base, function_aliases):
        return _dynamic_callable_references(modules)
    return frozenset()


def _dunder_dict_module_reference(
    base: ast.expr,
    slice_node: ast.expr,
    module_aliases: dict[str, frozenset[str]],
    function_aliases: dict[str, frozenset[str]],
) -> frozenset[str]:
    attribute = _literal_string(slice_node)
    if attribute is not None:
        aliases = _attribute_reference(base, attribute, module_aliases)
        if aliases:
            return aliases
        modules = module_reference(base, module_aliases, function_aliases)
        return _module_attributes(modules, attribute)
    modules = module_reference(base, module_aliases, function_aliases)
    if modules or _has_known_attribute_alias(base, module_aliases):
        return frozenset({_DYNAMIC_REFERENCE})
    return frozenset()


def _dynamic_getattr_callable_reference(
    reference: ast.expr,
    module_aliases: dict[str, frozenset[str]],
    function_aliases: dict[str, frozenset[str]],
) -> frozenset[str]:
    modules = module_reference(reference, module_aliases, function_aliases)
    if modules:
        return _dynamic_callable_references(modules)
    if _has_known_attribute_alias(reference, function_aliases):
        return frozenset({_DYNAMIC_REFERENCE})
    return frozenset()


def _dynamic_mapping_callable_reference(
    reference: ast.expr,
    module_aliases: dict[str, frozenset[str]],
    function_aliases: dict[str, frozenset[str]],
) -> frozenset[str]:
    if _literal_container_callable_references(reference, module_aliases, function_aliases):
        return frozenset({_DYNAMIC_REFERENCE})
    modules = module_reference(reference, module_aliases, function_aliases)
    if modules or _has_mapping_alias(reference, function_aliases):
        return _dynamic_callable_references(modules)
    return frozenset()


def _dynamic_mapping_module_reference(
    reference: ast.expr,
    module_aliases: dict[str, frozenset[str]],
    function_aliases: dict[str, frozenset[str]],
) -> frozenset[str]:
    if _literal_container_module_references(reference, module_aliases, function_aliases):
        return frozenset({_DYNAMIC_REFERENCE})
    modules = module_reference(reference, module_aliases, function_aliases)
    if modules or _has_mapping_alias(reference, module_aliases):
        return frozenset({_DYNAMIC_REFERENCE})
    return frozenset()


def _callable_attributes(modules: frozenset[str], attribute: str) -> frozenset[str]:
    candidates = _canonical_execution_functions(modules, attribute)
    if _BUILTINS_MODULE in modules and attribute == "getattr":
        candidates = candidates.union({GETATTR_ALIAS})
    if _DYNAMIC_REFERENCE in modules:
        candidates = candidates.union({_DYNAMIC_REFERENCE})
    return candidates


def _module_attributes(modules: frozenset[str], attribute: str) -> frozenset[str]:
    if "asyncio" in modules and attribute == "subprocess":
        return frozenset({"asyncio"})
    return frozenset({_DYNAMIC_REFERENCE}) if _DYNAMIC_REFERENCE in modules else frozenset()


def _dynamic_callable_references(modules: frozenset[str]) -> frozenset[str]:
    candidates = frozenset(
        _dynamic_execution_function(module)
        for module in modules
        if module in catalog.EXECUTION_FUNCTIONS_BY_MODULE
    )
    return candidates or frozenset({_DYNAMIC_REFERENCE})


def _dynamic_execution_function(module: str) -> str:
    return f"{module}{catalog.DYNAMIC_EXECUTION_FUNCTION_SUFFIX}"


def _attribute_reference(
    reference: ast.expr,
    attribute: str,
    aliases: dict[str, frozenset[str]],
) -> frozenset[str]:
    key = alias_key(reference)
    if key is not None and (resolved := aliases.get(f"{key}.{attribute}")):
        return resolved
    return frozenset()


def _mapping_item_reference(
    reference: ast.expr,
    key: str,
    aliases: dict[str, frozenset[str]],
) -> frozenset[str]:
    reference_key = alias_key(reference)
    if reference_key is not None and (resolved := aliases.get(f"{reference_key}[{key}]")):
        return resolved
    return frozenset()


def _has_known_attribute_alias(
    reference: ast.expr,
    aliases: dict[str, frozenset[str]],
) -> bool:
    key = alias_key(reference)
    return key is not None and any(name.startswith(f"{key}.") for name in aliases)


def _has_mapping_alias(reference: ast.expr, aliases: dict[str, frozenset[str]]) -> bool:
    key = alias_key(reference)
    return key is not None and any(name.startswith(f"{key}[") for name in aliases)


def _literal_container_callable_reference(
    reference: ast.expr,
    slice_node: ast.expr,
    module_aliases: dict[str, frozenset[str]],
    function_aliases: dict[str, frozenset[str]],
) -> frozenset[str]:
    item = _literal_container_item(reference, slice_node)
    if item is None:
        return frozenset()
    return callable_reference(item, module_aliases, function_aliases)


def _literal_container_module_reference(
    reference: ast.expr,
    slice_node: ast.expr,
    module_aliases: dict[str, frozenset[str]],
    function_aliases: dict[str, frozenset[str]],
) -> frozenset[str]:
    item = _literal_container_item(reference, slice_node)
    if item is None:
        return frozenset()
    return module_reference(item, module_aliases, function_aliases)


def _literal_container_callable_references(
    reference: ast.expr,
    module_aliases: dict[str, frozenset[str]],
    function_aliases: dict[str, frozenset[str]],
) -> frozenset[str]:
    return _literal_container_references(
        reference,
        lambda item: callable_reference(item, module_aliases, function_aliases),
    )


def _literal_container_module_references(
    reference: ast.expr,
    module_aliases: dict[str, frozenset[str]],
    function_aliases: dict[str, frozenset[str]],
) -> frozenset[str]:
    return _literal_container_references(
        reference,
        lambda item: module_reference(item, module_aliases, function_aliases),
    )


def _literal_container_references(
    reference: ast.expr,
    resolve: Callable[[ast.expr], frozenset[str]],
) -> frozenset[str]:
    candidates = resolve(reference)
    if candidates:
        return candidates
    values = _container_values(reference)
    return frozenset().union(*(_literal_container_references(item, resolve) for item in values))


def _container_values(reference: ast.expr) -> tuple[ast.expr, ...]:
    if isinstance(reference, (ast.List, ast.Tuple, ast.Set)):
        return tuple(reference.elts)
    return tuple(item for _, item in static_mapping_items(reference))


def _literal_container_item(reference: ast.expr, slice_node: ast.expr) -> ast.expr | None:
    if isinstance(reference, ast.Subscript):
        selected = _literal_container_item(reference.value, reference.slice)
        return _literal_container_item(selected, slice_node) if selected is not None else None
    key = literal_subscript_key(slice_node)
    if key is not None:
        for item_key, item_value in static_mapping_items(reference):
            if item_key == key:
                return item_value
    if (
        isinstance(reference, (ast.List, ast.Tuple))
        and isinstance(slice_node, ast.Constant)
        and isinstance(slice_node.value, int)
        and -len(reference.elts) <= slice_node.value < len(reference.elts)
    ):
        return reference.elts[slice_node.value]
    return None


def _dunder_dict_base(reference: ast.expr) -> ast.expr | None:
    if isinstance(reference, ast.Attribute) and reference.attr == "__dict__":
        return reference.value
    return None


def _literal_string(node: ast.expr) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _canonical_execution_functions(
    modules: frozenset[str],
    function: str,
) -> frozenset[str]:
    return frozenset(
        candidate
        for module in modules
        if (candidate := canonical_execution_function(module, function)) is not None
    )


def _canonical_execution_module(module: str) -> str | None:
    if module == "asyncio.subprocess":
        return "asyncio"
    return module if module in catalog.EXECUTION_FUNCTIONS_BY_MODULE else None
