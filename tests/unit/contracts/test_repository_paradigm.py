"""Repository paradigm contract loading and declaration boundaries."""

from __future__ import annotations

import tomllib
from importlib import resources

import pytest
from pydantic import ValidationError

from ethos.contracts.paradigm.declaration import RepositoryParadigm
from ethos.contracts.paradigm.declaration import load_repository_paradigm


def _packaged() -> dict[str, object]:
    source = resources.files("ethos.contracts.paradigm").joinpath("paradigm.toml")
    return tomllib.loads(source.read_text(encoding="utf-8"))


def test_packaged_paradigm_names_canonical_carriers() -> None:
    """The packaged contract resolves discovered root names to their canonical carrier."""
    paradigm = load_repository_paradigm()
    assert paradigm.id == "repository-paradigm"
    assert paradigm.canonical_carrier("pytest.ini") == ".config/checks/pytest/pytest.toml"
    assert paradigm.canonical_carrier("mise.toml") == ".config/mise/config.toml"
    assert paradigm.canonical_carrier("unrelated.txt") == ""
    assert {module.id for module in paradigm.module} == {"python", "node", "go"}


@pytest.mark.parametrize(
    "mutation",
    ["unknown-key", "duplicate-root-name", "duplicate-module", "unadmitted-document", "scope"],
)
def test_paradigm_declaration_fails_closed(mutation: str) -> None:
    """Unknown keys, ambiguous identities and inconsistent documents never load."""
    payload = _packaged()
    tools = payload["tool"]
    modules = payload["module"]
    root = payload["root"]
    assert isinstance(tools, list)
    assert isinstance(modules, list)
    assert isinstance(root, dict)
    if mutation == "unknown-key":
        payload["exceptions"] = ["pytest.ini"]
    elif mutation == "duplicate-root-name":
        tools.append({"id": "copy", "carrier": ".config/copy", "root_names": ["pytest.ini"]})
    elif mutation == "duplicate-module":
        modules.append(dict(modules[0]))
    elif mutation == "unadmitted-document":
        root["required_documents"] = ["CLAUDE.md"]
    else:
        modules[0] = {**modules[0], "lock_scope": "optional"}
    with pytest.raises(ValidationError):
        RepositoryParadigm.model_validate(payload)
