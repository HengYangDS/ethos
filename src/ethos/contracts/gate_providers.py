"""The gate provider catalog: stable IDs, their callables and the legacy names that still resolve.

A gate declaration names a provider by its catalog ID, or for one support window by the
`ethos.<module>:<callable>` name it used before the catalog. The packaged table beside this module
maps both, so a provider's module can move without an alias module and without an edit to any
declaration.
"""

import tomllib
from collections.abc import Mapping
from functools import lru_cache
from importlib import resources


@lru_cache(maxsize=1)
def provider_catalog() -> tuple[Mapping[str, str], Mapping[str, str]]:
    """Load each provider ID's callable and each legacy name's ID from the packaged table."""
    source = resources.files(__package__).joinpath("gate-providers.toml")
    table = tomllib.loads(source.read_text(encoding="utf-8"))
    return table["providers"], table["legacy"]


def provider_id(reference: str) -> str | None:
    """Return the catalog ID that a declared reference names, itself or by a legacy name."""
    providers, legacy = provider_catalog()
    return reference if reference in providers else legacy.get(reference)


def provider_target(reference: str) -> str:
    """Return the `module:callable` that a declared reference resolves to, or refuse it."""
    identity = provider_id(reference)
    if identity is None:
        message = f"gate_provider_unresolved:{reference}"
        raise ValueError(message)
    return provider_catalog()[0][identity]


def provider_spellings(*identities: str) -> tuple[str, ...]:
    """Return the given IDs with every legacy name that still resolves to one of them."""
    legacy = provider_catalog()[1]
    return (*identities, *(name for name, identity in legacy.items() if identity in identities))
